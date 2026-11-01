"""Asynchronous Google cloud candidates for IBus.

SPDX-License-Identifier: GPL-2.0-or-later
Protocol and interaction reference: ibus-libpinyin/src/PYPCloudCandidates.cc
(linyu Xu and Weixuan XIAO). This is an independent Python implementation.
All network I/O is asynchronous; only GLib main-context callbacks touch IBus.
"""
from collections import OrderedDict
import json
import re
import time
from urllib.parse import urlencode

import gi
from gi.repository import Gio, GLib
from i18n import N_
try:
    gi.require_version('Soup', '3.0')
    from gi.repository import Soup
except (ValueError, ImportError):
    Soup = None

AVAILABLE = Soup is not None
SOURCE_NAMES = (N_('Domestic Source'), N_('International Source'))
ENDPOINTS = ('https://www.google.cn/inputtools/request',
             'https://www.google.com/inputtools/request')
MAX_RESPONSE_BYTES = 65536
MAX_CANDIDATE_LENGTH = 128


def normalize_pinyin(text):
    if not isinstance(text, str) or len(text) > 256:
        return ''
    text = re.sub(r"[ '\t]+", "'", text.lower().strip(" '\t"))
    return text if re.fullmatch(r"[a-z]+(?:'[a-z]+)*", text) else ''


def request_url(pinyin, source, number):
    return ENDPOINTS[source] + '?' + urlencode({'ime': 'pinyin', 'text': pinyin, 'num': number})


def parse_response(body, requested, number):
    """Accept only the echoed input's candidate segment, never a partial one."""
    if len(body) > MAX_RESPONSE_BYTES:
        return []
    try:
        data = json.loads(body)
        if not isinstance(data, list) or len(data) < 2 or data[0] != 'SUCCESS':
            return []
        segments = data[1]
        if not isinstance(segments, list) or len(segments) != 1:
            return []
        segment = segments[0]
        if not isinstance(segment, list) or len(segment) < 2:
            return []
        if (normalize_pinyin(segment[0]).replace("'", '') != requested.replace("'", '')
                or not isinstance(segment[1], list)):
            return []
        candidates = []
        for text in segment[1]:
            if (not isinstance(text, str) or not 0 < len(text) <= MAX_CANDIDATE_LENGTH
                    or any(ord(c) < 32 or ord(c) == 127 for c in text)):
                continue
            if text not in candidates:
                candidates.append(text)
            if len(candidates) >= number:
                break
        return candidates
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return []


class _Request:
    def __init__(self, session, pinyin, source, number, callback, timeout_ms):
        self.session = session
        self.pinyin = pinyin
        self.number = number
        self.callback = callback
        self.cancellable = Gio.Cancellable()
        self.stream = None
        self.body = bytearray()
        self.finished = False
        self.message = Soup.Message.new('GET', request_url(pinyin, source, number))
        self.deadline = GLib.timeout_add(timeout_ms, self._timeout)
        session.send_async(self.message, GLib.PRIORITY_DEFAULT, self.cancellable, self._headers)

    def _timeout(self):
        self.deadline = 0
        self.cancellable.cancel()
        self._finish([])
        return GLib.SOURCE_REMOVE

    def _headers(self, session, result):
        try:
            stream = session.send_finish(result)
            if self.finished:
                stream.close_async(GLib.PRIORITY_DEFAULT, None, None)
                return
            self.stream = stream
            if self.message.get_status() != 200:
                self._finish([])
                return
            self._read()
        except GLib.Error:
            self._finish([])

    def _read(self):
        self.stream.read_bytes_async(8192, GLib.PRIORITY_DEFAULT, self.cancellable, self._chunk)

    def _chunk(self, stream, result):
        try:
            chunk = stream.read_bytes_finish(result).get_data()
            if self.finished:
                return
            if not chunk:
                self._finish(parse_response(bytes(self.body), self.pinyin, self.number))
            elif len(self.body) + len(chunk) > MAX_RESPONSE_BYTES:
                self.cancellable.cancel()
                self._finish([])
            else:
                self.body.extend(chunk)
                self._read()
        except GLib.Error:
            self._finish([])

    def _finish(self, candidates):
        if self.finished:
            return
        self.finished = True
        if self.deadline:
            GLib.source_remove(self.deadline)
            self.deadline = 0
        if self.stream:
            self.stream.close_async(GLib.PRIORITY_DEFAULT, None, None)
            self.stream = None
        callback, self.callback = self.callback, None
        if callback:
            callback(candidates)

    def cancel(self):
        self.callback = None
        self.cancellable.cancel()
        self._finish([])


class SoupTransport:
    def __init__(self, timeout_ms=3000):
        self.timeout_ms = timeout_ms
        self.session = Soup.Session(timeout=4) if AVAILABLE else None

    def start(self, pinyin, source, number, callback):
        if self.session is None:
            return None
        return _Request(self.session, pinyin, source, number, callback, self.timeout_ms)

    def close(self):
        if self.session:
            self.session.abort()


class CloudInput:
    """Debounce requests, cancel old work, and discard stale responses.

    Cache keys include the source and candidate count. The cache is bounded,
    in-memory only, and expires after one minute; no typed text is logged.
    A transport can be injected for deterministic offline tests.
    """
    def __init__(self, transport=None):
        self.transport = transport if transport is not None else SoupTransport()
        self._generation = 0
        self._timer = 0
        self._active = None
        self._key = None
        self._closed = False
        self._cache = OrderedDict()

    def cancel(self):
        self._generation += 1
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        if self._active:
            self._active.cancel()
            self._active = None
        self._key = None

    def query(self, pinyin, source, number, delay_ms, callback):
        pinyin = normalize_pinyin(pinyin)
        if self._closed:
            return
        if not pinyin or source not in (0, 1) or not 1 <= number <= 9:
            self.cancel()
            return
        key = (pinyin, source, number)
        if key == self._key:
            return
        self.cancel()
        self._key = key
        generation = self._generation
        def deliver(candidates):
            if self._closed or generation != self._generation or self._key != key:
                return
            self._active = None
            if candidates:
                self._cache[key] = (time.monotonic(), tuple(candidates))
                self._cache.move_to_end(key)
                while len(self._cache) > 64:
                    self._cache.popitem(last=False)
            callback(list(candidates))
        def start():
            self._timer = 0
            if self._closed or generation != self._generation:
                return GLib.SOURCE_REMOVE
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < 60:
                deliver(cached[1])
            else:
                self._active = self.transport.start(pinyin, source, number, deliver)
            return GLib.SOURCE_REMOVE
        self._timer = GLib.timeout_add(max(1, delay_ms), start)

    def close(self):
        self.cancel()
        self._closed = True
        self._cache.clear()
        self.transport.close()
