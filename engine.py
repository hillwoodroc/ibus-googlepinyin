# -*- coding: utf-8 -*-
# vim:set et sts=4 sw=4:
#
# ibus-tmpl - The Input Bus template project
#
# Copyright (c) 2007-2011 Peng Huang <shawn.p.huang@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.  

import os
import signal
import os.path as path
import gi
gi.require_version('IBus', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gdk, GLib, Gtk, IBus, Pango
from settings import new_settings, SHORTCUTS
from decoder import Decoder

ibus = IBus
pango = Pango
gobject = GLib
class _Keysyms:
    def __getattr__(self, name):
        return getattr(Gdk, 'KEY_' + name.lstrip('_'))

keysyms = _Keysyms()
modifier = IBus.ModifierType

def _half_to_full(char):
    codepoint = ord(char)
    if codepoint == 0x20:
        return '\u3000'
    if 0x21 <= codepoint <= 0x7e:
        return chr(codepoint + 0xfee0)
    return char

#from pygooglepinyin import *
from googlepinyin import *

try:
    import libopencc
except:
    pass

MAX_SPELLINGS = 26

import os, sys
from i18n import _

import time
import atexit
atexit.register(lambda *args: im_flush_cache())

IBUS_GOOGLEPINYIN_LOCATION = path.dirname(__file__)


class Engine(ibus.Engine):

    def __init__(self, **kwargs):
        super(Engine, self).__init__(**kwargs)
        im_open_decoder()
        self.settings = new_settings()
        self.decoder = Decoder(lambda key: self.settings.get_value(key).unpack())
        self.__is_invalidate = False
        self.__prepinyin_string = ""
        self.__lookup_table = ibus.LookupTable()
        self.__lookup_table.set_page_size(self.settings.get_int("page-size"))

        # 0 = english input mode
        # 1 = chinese input mode
        self.__mode = int(self.settings.get_boolean("initial-chinese"))
        self.__full_width_letter = [False, self.settings.get_boolean("initial-full-width")]
        self.__full_width_punct = [False, True]
        self.__full_width_punct[1] = self.settings.get_boolean("initial-full-punct")
        self.__trad_chinese = [False, self.settings.get_boolean("initial-traditional") and bool(globals().get("libopencc"))]

        self.do_reset()

        # init properties
        self.__prop_list = ibus.PropList()
        self.__status_property = self.__new_property("status")
        self.__prop_list.append(self.__status_property)
        self.__letter_property = self.__new_property("full_letter")
        self.__prop_list.append(self.__letter_property)
        self.__punct_property = self.__new_property("full_punct")
        self.__prop_list.append(self.__punct_property)
        self.__trad_chinese_property = self.__new_property("_trad chinese")
        if globals().get('libopencc'):
            self.__prop_list.append(self.__trad_chinese_property)
            pass

        self.__setup_property = self.__new_property("setup")
        self.__setup_property.set_label(IBus.Text.new_from_string(_('Preferences')))
        self.__setup_property.set_icon("preferences-system")
        self.__prop_list.append(self.__setup_property)
        self.__settings_handler = self.settings.connect('changed', self.__settings_changed)
        self.__apply_appearance()
        self.__refresh_properties()

    def __apply_appearance(self):
        self.__lookup_table.set_page_size(self.settings.get_int('page-size'))
        self.__lookup_table.set_orientation(self.settings.get_int('orientation'))

    def __settings_changed(self, settings, key):
        self.__apply_appearance()
        if key == 'initial-chinese':
            self.__mode = int(settings.get_boolean(key))
        elif key == 'initial-full-width':
            self.__full_width_letter[1] = settings.get_boolean(key)
        elif key == 'initial-full-punct':
            self.__full_width_punct[1] = settings.get_boolean(key)
        elif key == 'initial-traditional':
            self.__trad_chinese[1] = settings.get_boolean(key) and bool(globals().get('libopencc'))
        if key in ('double-pinyin-show-raw', 'display-style'):
            self.__invalidate()
        else:
            self.do_reset()
        self.__refresh_properties()

    def do_destroy(self):
        self.settings.disconnect(self.__settings_handler)
        im_flush_cache()
        IBus.Engine.do_destroy(self)

    def __shortcut_action(self, keyval, state):
        for name, _label, _default in SHORTCUTS:
            shortcut = self.settings.get_string('shortcut-' + name)
            if not shortcut or shortcut == '<Shift>':
                continue
            # IBus parses the same accelerator notation as GTK.
            expected_key, expected_mods = Gtk.accelerator_parse(shortcut)
            ok = bool(expected_key)
            mask = modifier.CONTROL_MASK | modifier.SHIFT_MASK | modifier.MOD1_MASK | modifier.SUPER_MASK
            if ok and Gdk.keyval_to_lower(keyval) == Gdk.keyval_to_lower(expected_key) and state & mask == expected_mods & mask:
                return {'switch-mode': 'status', 'full-width': 'full_letter',
                        'punctuation': 'full_punct', 'traditional': '_trad chinese',
                        'all-width': 'all_width'}[name]
        return None

    @staticmethod
    def __new_property(key):
        return IBus.Property.new(key, IBus.PropType.NORMAL,
                                 IBus.Text.new_from_string(""), "",
                                 IBus.Text.new_from_string(""), True, True,
                                 IBus.PropState.UNCHECKED)

    def __refresh_properties(self):
        # Labels are used by the IBus dropdown; symbols are used by panels.
        # Always update the serializable IBus.Property, not Python attributes.
        chinese = self.__mode == 1
        full_letter = self.__full_width_letter[self.__mode]
        full_punct = self.__full_width_punct[self.__mode]
        traditional = self.__trad_chinese[self.__mode]
        items = [
            (self.__status_property,
             _('Chinese') if chinese else _('English'), _('CN') if chinese else _('EN'),
             _('Switch to English Mode') if chinese else _('Switch to Chinese Mode'),
             'chinese.svg' if chinese else 'english.svg'),
            (self.__letter_property,
             _('Full Width Letters') if full_letter else _('Half Width Letters'), 'Ａ' if full_letter else 'A',
             _('Switch to Half Width Letters') if full_letter else _('Switch to Full Width Letters'),
             'full-letter.svg' if full_letter else 'half-letter.svg'),
            (self.__punct_property,
             _('Full Width Punctuation') if full_punct else _('Half Width Punctuation'), '。' if full_punct else '.',
             _('Switch to Half Width Punctuation') if full_punct else _('Switch to Full Width Punctuation'),
             'full-punct.svg' if full_punct else 'half-punct.svg'),
        ]
        if globals().get('libopencc'):
            items.append((self.__trad_chinese_property,
                          _('Traditional Chinese') if traditional else _('Simplified Chinese'),
                          _('Trad') if traditional else _('Simp'),
                          _('Switch to Simplified Chinese') if traditional else _('Switch to Traditional Chinese'),
                          'trad-chinese.svg' if traditional else 'simp-chinese.svg'))
        for prop, label, symbol, tooltip, icon in items:
            prop.set_label(IBus.Text.new_from_string(label))
            prop.set_symbol(IBus.Text.new_from_string(symbol))
            prop.set_tooltip(IBus.Text.new_from_string(tooltip))
            prop.set_icon(path.join(IBUS_GOOGLEPINYIN_LOCATION, 'icons', icon))
            self.update_property(prop)

    def __change_mode(self):
        self.__mode = (self.__mode + 1) % 2
        self.do_reset()
        self.__refresh_properties()

    def __is_input_english(self):
        return self.__mode == 0

    def __is_trad_chinese(self):
        return self.__trad_chinese[self.__mode]

    __last_press_keyval = None
    __last_im_flush_cache_time = 0
    __candidate_num = 0
    __lookup_candidate_num = 0
    __prev_char = ''

    def do_process_key_event(self, keyval, keycode, state):
        ## for key release events
        is_press = ((state & modifier.RELEASE_MASK) == 0)
        if is_press:
            self.__last_press_keyval = keyval
            pass
        ## Match Shift to switcc English/Chinese mode
        elif keyval == self.__last_press_keyval \
                and (keyval == keysyms.Shift_L or keyval == keysyms.Shift_R):
            if self.settings.get_boolean("shift-select") and self.__prepinyin_string:
                return self.do_process_key_event(keysyms._2, 0, 0)
            if self.settings.get_string("shortcut-switch-mode") != "<Shift>":
                return False
            self.do_property_activate("status", IBus.PropState.UNCHECKED)
            self.do_reset()
            return False
        ## ignore key release events
        else:
            return False

        if not is_press:
            return False
        action = self.__shortcut_action(keyval, state)
        if action:
            self.do_property_activate(action)
            return True
        if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK | modifier.SUPER_MASK):
            return False
        if self.__is_input_english():
            if 32 <= keyval < 127 and self.__full_width_letter[self.__mode] :
                c = _half_to_full(chr(keyval))
                self.__commit_string(c)
                return True
            return False

        if self.__prepinyin_string:
            if keyval == keysyms.Return:
                if self.__full_width_letter[self.__mode]:
                    self.__prepinyin_string = ''.join(
                            (_half_to_full(c) for c in self.__prepinyin_string))
                    pass
                self.__commit_string(self.__prepinyin_string)
                return True
            elif keyval == keysyms.Escape:
                self.__prepinyin_string = ""
                self.__update()
                return True
            elif keyval == keysyms.BackSpace:
                self.__prepinyin_string = self.__prepinyin_string[:-1]
                self.__invalidate()
                return True
            elif (keyval >= keysyms._1 and keyval <= keysyms._9) or keyval == keysyms.space: 
                if not self.__lookup_table.get_number_of_candidates() > 0:
                    self.__commit_string(self.__prepinyin_string)
                    return True
                if keyval == keysyms.space:
                    keyval = keysyms._1
                    pass
                ##
                index = keyval - keysyms._1
                if index >= self.__lookup_table.get_page_size():
                    return False
                index += (self.__lookup_table.get_cursor_pos() // self.__lookup_table.get_page_size()) * self.__lookup_table.get_page_size()
                if index >= self.__lookup_table.get_number_of_candidates():
                    return True
                num = self.decoder.choose(int(index))
                self.__candidate_num = num
                if num == 1:
                    candidate = self.decoder.candidate(0)
                    if self.__trad_chinese[self.__mode]:
                        candidate = libopencc.convert(candidate)
                        pass
                    self.__commit_string(candidate)
                    self.decoder.reset()
                    if time.time() - self.__last_im_flush_cache_time > 300:
                        im_flush_cache()
                        self.__last_im_flush_cache_time = time.time()
                        pass
                    return True
                self.__update()
                return True
            # press , - Page_Up
            elif (keyval in (keysyms.Page_Up, keysyms.KP_Page_Up) or
                  keyval == keysyms.comma and self.settings.get_boolean('comma-period-page') or
                  keyval == keysyms.minus and self.settings.get_boolean('minus-equal-page') or
                  keyval == keysyms.bracketleft and self.settings.get_boolean('bracket-page')):
                self.page_up()
                return True
            # press . = Page_Down
            elif (keyval in (keysyms.Page_Down, keysyms.KP_Page_Down) or
                  keyval == keysyms.period and self.settings.get_boolean('comma-period-page') or
                  keyval == keysyms.equal and self.settings.get_boolean('minus-equal-page') or
                  keyval == keysyms.bracketright and self.settings.get_boolean('bracket-page')):
                self.page_down()
                return True
            elif keyval == keysyms.Up:
                self.cursor_up()
                return True
            elif keyval == keysyms.Down:
                self.cursor_down()
                return True
            elif keyval == keysyms.Left or keyval == keysyms.Right:
                return True
        if keyval in range(keysyms.a, keysyms.z + 1) or \
                (keyval == keysyms.quoteright and self.__prepinyin_string) or (
                keyval == keysyms.semicolon and self.__prepinyin_string and
                self.settings.get_boolean('double-pinyin') and
                self.settings.get_int('double-pinyin-schema') in (1, 3)):
            if self.__lookup_table.get_number_of_candidates() \
                    and len(self.__lookup_table.get_candidate(0).text)\
                        >= MAX_SPELLINGS:
                return True
            if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK) == 0:
                if len(self.__prepinyin_string) >= 64:
                    return True
                self.__prepinyin_string += chr(keyval)
                self.__invalidate()
                return True
        else:
            if keyval > 0x10ffff:
                return False
            c = chr(keyval)
            if c == "." and self.__prev_char and self.__prev_char.isdigit():
                return False
            if self.__full_width_punct[self.__mode] and c in '~!$^&*()_[{]}\\|;:\'",<.>/?':
                c = self.__convert_to_full_width(c)
                self.__commit_string(c)
                return True
            if self.__full_width_letter[self.__mode] and 32 <= keyval < 127:
                c = _half_to_full(c)
                self.__commit_string(c)
                return True
            if keyval < 128 and self.__prepinyin_string:
                self.__commit_string(self.__prepinyin_string)
                return True
            if c.isdigit():
                self.__commit_string(c)
                return True

        return False

    def __invalidate(self):
        if self.__is_invalidate:
            return
        self.__is_invalidate = True
        gobject.idle_add(self.__update, priority=GLib.PRIORITY_LOW)


    def __lookup_more_candidates(self):
        if self.__lookup_candidate_num < self.__candidate_num:
            num = min(self.__candidate_num,
                    self.__lookup_candidate_num + self.__lookup_table.get_page_size() + 1)
            for i in range(self.__lookup_candidate_num, num):
                text = self.decoder.candidate(i)
                if self.__is_trad_chinese() and globals().get("libopencc"):
                    text = libopencc.convert(text)
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(text))
                pass
            self.__lookup_candidate_num = num
            self.__update_lookup_table()
            pass
        pass

    def page_up(self):
        if self.__lookup_table.page_up():
            self.__update_lookup_table()
            return True
        return False

    def page_down(self):
        self.__lookup_more_candidates()
        if self.__lookup_table.page_down():
            self.__update_lookup_table()
            return True
        return False

    def cursor_up(self):
        if self.__lookup_table.cursor_up():
            self.__update_lookup_table()
            return True
        return False

    def cursor_down(self):
        self.__lookup_more_candidates()
        if self.__lookup_table.cursor_down():
            self.__update_lookup_table()
            return True
        return False

    def __commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.__prepinyin_string = ""
        self.decoder.reset()
        self.__prev_char = text and text[-1] or ''
        self.__update()

    def __update(self):
        prepinyin_len = len(self.__prepinyin_string)
        attrs = ibus.AttrList()
        self.__lookup_table.clean()
        if prepinyin_len > 0:
            #attrs.append(ibus.AttributeForeground(0x0000ff, 0, prepinyin_len))
            num = self.decoder.search(self.__prepinyin_string)
            self.__candidate_num = num
            self.__lookup_candidate_num = min(num, self.__lookup_table.get_page_size() + 1)
            for i in range(self.__lookup_candidate_num):
                text = self.decoder.candidate(i)
                if self.__is_trad_chinese() and globals().get("libopencc"):
                    text = libopencc.convert(text)
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(text))
                pass
            pass
        preedit_string = self.__lookup_table \
                and self.__lookup_table.get_number_of_candidates() \
                and self.__lookup_table.get_candidate(0).text or ""
        spelling_text = self.__prepinyin_string
        if (self.settings.get_boolean('double-pinyin') and
                not self.settings.get_boolean('double-pinyin-show-raw')):
            spelling_text = self.decoder.display_spelling
        spelling_preedit = (self.settings.get_int('display-style') == 1 or
                            self.settings.get_boolean('double-pinyin') and
                            self.settings.get_boolean('double-pinyin-show-raw'))
        if spelling_preedit:
            preedit_string = spelling_text
        preedit_len = len(preedit_string)
        preedit_pos = preedit_len if spelling_preedit else min(len(self.decoder.fixed), preedit_len)

        self.update_auxiliary_text(IBus.Text.new_from_string(spelling_text), prepinyin_len > 0)
        attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE, Pango.Underline.SINGLE, 0, preedit_len))
        if not spelling_preedit and preedit_len > preedit_pos:
            attrs.append(IBus.Attribute.new(IBus.AttrType.BACKGROUND, 0xc8c8f0, preedit_pos, preedit_len))
        preedit = IBus.Text.new_from_string(preedit_string)
        preedit.set_attributes(attrs)
        self.update_preedit_text(preedit, preedit_pos, preedit_len > 0)
        self.__update_lookup_table()
        self.__is_invalidate = False
        if prepinyin_len and self.__candidate_num == 1 and self.settings.get_boolean('auto-commit'):
            self.do_process_key_event(keysyms.space, 0, 0)

    def __update_lookup_table(self):
        visible = self.__lookup_table.get_number_of_candidates() > 0
        self.update_lookup_table(self.__lookup_table, visible)


    __double_quotation_state = 0
    __single_quotation_state = 0
    def __convert_to_full_width(self, c):
        if c == ".":
            return "\u3002"
        elif c == "\\":
            return "\u3001"
        elif c == "^":
            return "\u2026\u2026"
        elif c == "_":
            return "\u2014\u2014"
        elif c == "$":
            return "\uffe5"
        elif c == "\"":
            self.__double_quotation_state = not self.__double_quotation_state
            if self.__double_quotation_state:
                return "\u201c"
            else:
                return "\u201d"
        elif c == "'":
            self.__single_quotation_state = not self.__single_quotation_state
            if self.__single_quotation_state:
                return "\u2018"
            else:
                return "\u2019"

        elif c == "<":
            return "\u300a"
        elif c == ">":
            return "\u300b"

        return _half_to_full(c)


    def do_candidate_clicked(self, index, button, state):
        if button == 1 and index < self.__lookup_table.get_page_size():
            self.do_process_key_event(keysyms._1 + index, 0, 0)

    def do_page_up(self):
        return self.page_up()

    def do_page_down(self):
        return self.page_down()

    def do_focus_in(self):
        self.do_reset()
        self.register_properties(self.__prop_list)
        self.__refresh_properties()

    def do_focus_out(self):
        self.do_reset()
        pass

    def do_reset(self):
        self.decoder.reset()
        self.__double_quotation_state = False
        self.__single_quotation_state = False
        self.__prepinyin_string = ""
        self.__candidate_num = 0
        self.__lookup_candidate_num = 0
        self.__invalidate()
        pass

    def do_property_activate(self, prop_name, prop_state=IBus.PropState.UNCHECKED):
        if prop_name == 'setup':
            import subprocess
            subprocess.Popen([sys.executable, path.join(IBUS_GOOGLEPINYIN_LOCATION, 'setup.py')])
            return
        if prop_name == 'all_width':
            full = not self.__full_width_letter[self.__mode]
            self.__full_width_letter[self.__mode] = full
            self.__full_width_punct[self.__mode] = full
            self.__refresh_properties()
            return
        if prop_name == "status":
            self.__change_mode()
            return
        elif prop_name == "full_letter":
            self.__full_width_letter[self.__mode] = not self.__full_width_letter[self.__mode]
        elif prop_name == "full_punct":
            self.__full_width_punct[self.__mode] = not self.__full_width_punct[self.__mode]
        elif prop_name == "_trad chinese" and globals().get("libopencc"):
            self.__trad_chinese[self.__mode] = not self.__trad_chinese[self.__mode]
            self.__invalidate()
        else:
            return
        self.__refresh_properties()
