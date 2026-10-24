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
gi.require_version('Pango', '1.0')
from gi.repository import Gdk, GLib, IBus, Pango

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

app = 'ibus-googlepinyin'

import os, sys
import gettext

if os.path.isdir(os.path.dirname(sys.argv[0]) + '/../build/mo'):
    gettext.install(app, os.path.dirname(sys.argv[0]) + '/../build/mo')
else:
    gettext.install(app)

import time
import atexit
atexit.register(lambda *args: im_flush_cache())

IBUS_GOOGLEPINYIN_LOCATION = path.dirname(__file__)


class Engine(ibus.Engine):

    def __init__(self, **kwargs):
        super(Engine, self).__init__(**kwargs)
        im_open_decoder()
        self.__is_invalidate = False
        self.__prepinyin_string = ""
        self.__lookup_table = ibus.LookupTable()
        self.__lookup_table.set_page_size(5)

        # 0 = english input mode
        # 1 = chinese input mode
        self.__mode = 1
        self.__full_width_letter = [False, False]
        self.__full_width_punct = [False, True]
        self.__full_width_punct[1] = True #config.get_value("engine/PinYin/FullWidthPunct", True)
        self.__trad_chinese = [False, False]

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

    @staticmethod
    def __new_property(key):
        return IBus.Property.new(key, IBus.PropType.NORMAL,
                                 IBus.Text.new_from_string(""), "",
                                 IBus.Text.new_from_string(""), True, True,
                                 IBus.PropState.UNCHECKED)

    def __refresh_properties(self):
        try:
            self.__refresh_properties2()
        except Exception as e:
            print(e)

    def __refresh_properties2(self):
        if self.__mode == 1: # refresh mode
            self.__status_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "chinese.svg")
            self.__status_property.label = _("CN")
            self.__status_property.tooltip = _("Switch to English mode")
        else:
            self.__status_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "english.svg")
            self.__status_property.label = _("EN")
            self.__status_property.tooltip = _("Switch to Chinese mode")

        if self.__full_width_letter[self.__mode]:
            self.__letter_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "full-letter.svg")
            self.__letter_property.label = "Ａａ"
            self.__letter_property.tooltip = _("Switch to half letter mode")
        else:
            self.__letter_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "half-letter.svg")
            self.__letter_property.label = "Aa"
            self.__letter_property.tooltip = _("Switch to full letter mode")

        if self.__full_width_punct[self.__mode]:
            self.__punct_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "full-punct.svg")
            self.__punct_property.label = "，。"
            self.__punct_property.tooltip = _("Switch to half punctuation mode")
        else:
            self.__punct_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "half-punct.svg")
            self.__punct_property.label = ".,"
            self.__punct_property.tooltip = _("Switch to full punctuation mode")

        if self.__trad_chinese[self.__mode]:
            self.__trad_chinese_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "trad-chinese.svg")
            self.__trad_chinese_property.label = "，。"
            self.__trad_chinese_property.tooltip = _("Switch to Traditional Chinese mode")
        else:
            self.__trad_chinese_property.icon = path.join(IBUS_GOOGLEPINYIN_LOCATION, "icons", "simp-chinese.svg")
            self.__trad_chinese_property.label = ".,"
            self.__trad_chinese_property.tooltip = _("Switch to Simplified Chinese mode")

        properties =(
            self.__status_property,
            self.__letter_property,
            self.__punct_property,
            self.__trad_chinese_property,
            )

        for prop in properties:
            self.update_property(prop)


    def __change_mode(self):
        self.__mode =(self.__mode + 1) % 2
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
            self.do_property_activate("status", IBus.PropState.UNCHECKED)
            self.do_reset()
            return False
        ## ignore key release events
        else:
            return False

        if self.__is_input_english():
            if 32 <= keyval < 127 and self.__full_width_letter[self.__mode] :
                c = chr(keyval)
                c = _half_to_full(c)
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
                index += self.__lookup_table.get_current_page_start()
                num = im_choose(int(index))
                self.__candidate_num = num
                if num == 1:
                    candidate = im_get_candidate(0)
                    if self.__trad_chinese[self.__mode]:
                        candidate = libopencc.convert(candidate)
                        pass
                    self.__commit_string(candidate)
                    im_reset_search()
                    if time.time() - self.__last_im_flush_cache_time > 300:
                        im_flush_cache()
                        self.__last_im_flush_cache_time = time.time()
                        pass
                    return True
                self.__update()
                return True
            # press , - Page_Up
            elif keyval == keysyms.comma or keyval == keysyms.minus or keyval == keysyms.Page_Up or keyval == keysyms.KP_Page_Up:
                self.page_up()
                return True
            # press . = Page_Down
            elif keyval == keysyms.period or keyval == keysyms.equal or keyval == keysyms.Page_Down or keyval == keysyms.KP_Page_Down:
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
                (keyval == keysyms.quoteright and self.__prepinyin_string):
            if self.__lookup_table.get_number_of_candidates() \
                    and len(self.__lookup_table.get_candidate(0).text)\
                        >= MAX_SPELLINGS:
                return True
            if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK) == 0:
                self.__prepinyin_string += chr(keyval)
                self.__invalidate()
                return True
        else:
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
                text = im_get_candidate(i)
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(text))
                pass
            self.__lookup_candidate_num = num
            self.__update_lookup_table()
            pass
        pass

    def page_up(self):
        if self.__lookup_table.page_up():
            self.page_up_lookup_table()
            return True
        return False

    def page_down(self):
        self.__lookup_more_candidates()
        if self.__lookup_table.page_down():
            self.page_down_lookup_table()
            return True
        return False

    def cursor_up(self):
        if self.__lookup_table.cursor_up():
            self.cursor_up_lookup_table()
            return True
        return False

    def cursor_down(self):
        self.__lookup_more_candidates()
        if self.__lookup_table.cursor_down():
            self.cursor_down_lookup_table()
            return True
        return False

    def __commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.__prepinyin_string = ""
        self.__prev_char = text and text[-1] or ''
        self.__update()

    def __update(self):
        prepinyin_len = len(self.__prepinyin_string)
        attrs = ibus.AttrList()
        self.__lookup_table.clean()
        if prepinyin_len > 0:
            #attrs.append(ibus.AttributeForeground(0x0000ff, 0, prepinyin_len))
            num = im_search(self.__prepinyin_string.encode('utf8'))
            self.__candidate_num = num
            self.__lookup_candidate_num = min(num, self.__lookup_table.get_page_size() + 1)
            for i in range(self.__lookup_candidate_num):
                text = im_get_candidate(i)
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(text))
                pass
            pass
        preedit_string = self.__lookup_table \
                and self.__lookup_table.get_number_of_candidates() \
                and self.__lookup_table.get_candidate(0).text or ""
        preedit_len = len(preedit_string)
        preedit_pos = im_get_fixed_len()

        self.update_auxiliary_text(IBus.Text.new_from_string(self.__prepinyin_string), prepinyin_len > 0)
        attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE, Pango.Underline.SINGLE, 0, preedit_len))
        if prepinyin_len > preedit_pos:
            attrs.append(IBus.Attribute.new(IBus.AttrType.BACKGROUND, 0xc8c8f0, preedit_pos, preedit_len))
        preedit = IBus.Text.new_from_string(preedit_string)
        preedit.set_attributes(attrs)
        self.update_preedit_text(preedit, preedit_pos, preedit_len > 0)
        self.__update_lookup_table()
        self.__is_invalidate = False

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


    def do_focus_in(self):
        self.do_reset()
        self.register_properties(self.__prop_list)
        self.__refresh_properties()

    def do_focus_out(self):
        self.do_reset()
        pass

    def do_reset(self):
        im_reset_search()
        self.__double_quotation_state = False
        self.__single_quotation_state = False
        self.__prepinyin_string = ""
        self.__candidate_num = 0
        self.__lookup_candidate_num = 0
        self.__invalidate()
        pass

    def do_property_activate(self, prop_name, prop_state=IBus.PropState.UNCHECKED):
        #print "PropertyActivate(%s)" % prop_name
        if prop_name == "status":
            self.__change_mode()
        elif prop_name == "full_letter":
            self.__full_width_letter [self.__mode] = not self.__full_width_letter [self.__mode]
            self.__refresh_properties()
        elif prop_name == "full_punct":
            self.__full_width_punct [self.__mode] = not self.__full_width_punct [self.__mode]
            self.__refresh_properties()
        elif prop_name == "_trad chinese":
            self.__trad_chinese [self.__mode] = not self.__trad_chinese [self.__mode]
            self.__refresh_properties()
        self.__refresh_properties()

