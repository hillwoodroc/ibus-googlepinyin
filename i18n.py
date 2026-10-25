"""Shared GNU gettext setup for the engine and preferences.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import gettext
import locale
import os
from pathlib import Path

DOMAIN = 'ibus-googlepinyin'
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    # Minimal build/test environments may not have the requested locale.
    pass
try:
    from config import LOCALEDIR as INSTALLED_LOCALEDIR
except ImportError:
    INSTALLED_LOCALEDIR = '/usr/share/locale'

_local_build = Path(__file__).resolve().parent / 'build' / 'locale'
LOCALEDIR = os.environ.get('IBUS_LOCALEDIR') or (
    str(_local_build) if _local_build.is_dir() else INSTALLED_LOCALEDIR)
gettext.bindtextdomain(DOMAIN, LOCALEDIR)
gettext.textdomain(DOMAIN)
_ = gettext.translation(DOMAIN, LOCALEDIR, fallback=True).gettext


def N_(message):
    """Mark a message for extraction and translate it when it is displayed."""
    return message
