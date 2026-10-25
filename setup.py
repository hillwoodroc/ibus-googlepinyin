#!/usr/bin/env python3
"""Google Pinyin preferences using ibus-libpinyin's page layout.

Copyright (c) 2026 ibus-googlepinyin contributors
SPDX-License-Identifier: GPL-2.0-or-later
Layout reference: ibus-libpinyin/setup/ibus-libpinyin-preferences.ui,
Peng Huang, BYVoid, Peng Wu.
"""
from i18n import _
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk
from settings import new_settings, CORRECTIONS, FUZZY, SHORTCUTS
from pinyin import SCHEME_NAMES


class Preferences(Gtk.Window):
    def __init__(self):
        super().__init__(title=_('Preferences'))
        self.settings = new_settings()
        self.set_default_size(820, 820)
        self._handlers = []
        self.connect('destroy', self.closed)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=12)
        self.add(outer)
        self.notebook = Gtk.Notebook()
        outer.pack_start(self.notebook, True, True, 0)
        self.controls = {}
        self.general()
        self.pinyin()
        self.fuzzy()
        self.user_data()
        self.shortcuts()
        self.about()
        close = Gtk.Button.new_with_mnemonic(_('_Close'))
        close.set_halign(Gtk.Align.END)
        close.connect('clicked', lambda *_: self.destroy())
        outer.pack_start(close, False, False, 0)

    def watch(self, signal, callback):
        self._handlers.append(self.settings.connect(signal, callback))

    def closed(self, *_args):
        for handler in self._handlers:
            self.settings.disconnect(handler)
        self._handlers.clear()
        if Gtk.main_level():
            Gtk.main_quit()

    def page(self, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, margin=12)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(box)
        self.notebook.append_page(scroll, Gtk.Label(label=title))
        return box

    def label(self, box, text, bold=False):
        label = Gtk.Label(xalign=0, wrap=True)
        if bold:
            label.set_markup('<b>' + GLib.markup_escape_text(text) + '</b>')
        else:
            label.set_text(text)
        box.pack_start(label, False, False, 0)
        return label

    def section(self, box, title):
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.label(group, title, True)
        grid = Gtk.Grid(column_spacing=18, row_spacing=12, margin_start=18)
        grid.set_hexpand(True)
        group.pack_start(grid, False, False, 0)
        box.pack_start(group, False, False, 0)
        return grid

    def check(self, key, text, parent=None):
        widget = Gtk.CheckButton(label=_(text))
        widget.set_hexpand(True)
        widget.set_halign(Gtk.Align.FILL)
        self.settings.bind(key, widget, 'active', Gio.SettingsBindFlags.DEFAULT)
        if parent:
            parent.bind_property('active', widget, 'sensitive', 2)
        self.controls[key] = widget
        return widget

    def combo(self, key, choices):
        combo = Gtk.ComboBoxText()
        for choice in choices:
            combo.append_text(_(choice))
        combo.set_hexpand(True)
        self.settings.bind(key, combo, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.controls[key] = combo
        return combo

    def radio_pair(self, grid, row, key, label, left, right, left_value=True):
        text = Gtk.Label(label=label, xalign=0)
        text.set_hexpand(True)
        grid.attach(text, 0, row, 1, 1)
        first = Gtk.RadioButton.new_with_label_from_widget(None, left)
        second = Gtk.RadioButton.new_with_label_from_widget(first, right)
        first.set_hexpand(True)
        second.set_hexpand(True)
        first.set_active(self.settings.get_boolean(key) == left_value)
        second.set_active(self.settings.get_boolean(key) != left_value)
        first.connect('toggled', lambda w: self.settings.set_boolean(key, left_value) if w.get_active() else None)
        second.connect('toggled', lambda w: self.settings.set_boolean(key, not left_value) if w.get_active() else None)
        def changed(settings, _key):
            (first if settings.get_boolean(key) == left_value else second).set_active(True)
        self.watch('changed::' + key, changed)
        grid.attach(first, 1, row, 1, 1)
        grid.attach(second, 2, row, 1, 1)
        self.controls[key] = (first, second)
        return first, second

    def general(self):
        box = self.page(_('General'))
        grid = self.section(box, _('Initial State'))
        grid.set_column_homogeneous(True)
        self.radio_pair(grid, 0, 'initial-chinese', _('Language:'), _('Chinese'), _('English'))
        self.radio_pair(grid, 1, 'initial-full-width', _('Full/Half Width:'), _('Full'), _('Half'))
        self.radio_pair(grid, 2, 'initial-full-punct', _('Punctuation:'), _('Full'), _('Half'))
        # Traditional output is optional; omit it if conversion is unavailable.
        try:
            import libopencc
        except (ImportError, OSError, RuntimeError, AttributeError):
            pass
        else:
            self.radio_pair(grid, 3, 'initial-traditional', _('Chinese:'), _('Simplified'), _('Traditional'), False)
        grid = self.section(box, _('Appearance'))
        grid.set_column_homogeneous(True)
        for row, (key, label, choices) in enumerate((
                ('display-style', _('Display Style:'), [_('Default'), _('Pinyin')]),
                ('orientation', _('Candidate Word Orientation:'), [_('Horizontal'), _('Vertical'), _('System Default')]))):
            grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
            grid.attach(self.combo(key, choices), 1, row, 1, 1)
        grid.attach(Gtk.Label(label=_('Number of Candidates:'), xalign=0), 0, 2, 1, 1)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 9, 1)
        scale.set_digits(0)
        scale.set_value_pos(Gtk.PositionType.LEFT)
        scale.set_value(self.settings.get_int('page-size'))
        scale.connect('value-changed', lambda w: self.settings.set_int('page-size', int(w.get_value())))
        self.watch('changed::page-size', lambda s, k: scale.set_value(s.get_int(k)))
        scale.set_hexpand(True)
        grid.attach(scale, 1, 2, 1, 1)
        self.controls['page-size'] = scale
        grid = self.section(box, _('Candidates'))
        grid.set_column_homogeneous(True)
        grid.attach(Gtk.Label(label=_('Sort Candidates by:'), xalign=0), 0, 0, 1, 1)
        grid.attach(self.combo('sort-order', [_('Frequency'), _('Longest First'), _('Shortest First')]), 1, 0, 1, 1)

    def pinyin(self):
        box = self.page(_('Pinyin Mode'))
        grid = self.section(box, _('Pinyin Mode'))
        grid.set_column_homogeneous(True)
        full = Gtk.RadioButton.new_with_label_from_widget(None, _('Full Pinyin'))
        double = Gtk.RadioButton.new_with_label_from_widget(full, _('Double Pinyin'))
        full.set_active(not self.settings.get_boolean('double-pinyin'))
        double.set_active(self.settings.get_boolean('double-pinyin'))
        full.connect('toggled', lambda w: self.settings.set_boolean('double-pinyin', False) if w.get_active() else None)
        double.connect('toggled', lambda w: self.settings.set_boolean('double-pinyin', True) if w.get_active() else None)
        self.watch('changed::double-pinyin', lambda s, k: (double if s.get_boolean(k) else full).set_active(True))
        grid.attach(full, 0, 0, 1, 1)
        row = Gtk.Box(spacing=12)
        row.pack_start(double, False, False, 0)
        combo = self.combo('double-pinyin-schema', SCHEME_NAMES)
        double.bind_property('active', combo, 'sensitive', 2)
        row.pack_start(combo, True, True, 0)
        grid.attach(row, 1, 0, 1, 1)
        grid.attach(self.check('incomplete-pinyin', _('Incomplete Pinyin')), 0, 1, 1, 1)
        grid.attach(self.check('double-pinyin-show-raw', _('Show Raw Double Pinyin'), double), 1, 1, 1, 1)
        self.controls['double-pinyin'] = (full, double)
        grid = self.section(box, _('Input Custom'))
        grid.set_column_homogeneous(True)
        for key, label, column, row in (
                ('shift-select', _('[Shift] Selects the Second Candidate'), 0, 0),
                ('minus-equal-page', _('[-][=] Flip Page'), 1, 0),
                ('comma-period-page', _('[,][.] Flip Page'), 0, 1),
                ('bracket-page', _('[ ][ ] Flip Page'), 1, 1),
                ('auto-commit', _('Auto Commit'), 0, 2)):
            grid.attach(self.check(key, label), column, row, 1, 1)
        grid = self.section(box, _('Pinyin Correction'))
        grid.set_column_homogeneous(True)
        correct = self.check('correct-pinyin', _('Enable Pinyin Correction'))
        grid.attach(correct, 0, 0, 2, 1)
        positions = {'gn-ng': (0, 1), 'mg-ng': (0, 2), 'iou-iu': (0, 3),
                     'uei-ui': (1, 1), 'uen-un': (1, 2), 'ue-ve': (1, 3),
                     'v-u': (0, 4), 'on-ong': (0, 5)}
        for key, text in CORRECTIONS:
            col, row = positions[key]
            grid.attach(self.check('correct-pinyin-' + key, text, correct), col, row, 2 if key == 'v-u' else 1, 1)

    def fuzzy(self):
        box = self.page(_('Fuzzy Pinyin'))
        grid = Gtk.Grid(column_homogeneous=True, column_spacing=24, row_spacing=34,
                        margin_start=18, margin_top=18)
        grid.set_hexpand(True)
        box.pack_start(grid, False, False, 0)
        toggle = self.check('fuzzy-pinyin', _('Enable Fuzzy Pinyin'))
        grid.attach(toggle, 0, 0, 2, 1)
        for i, (key, text) in enumerate(FUZZY):
            col, row = (0, i + 1) if i < 7 else (1, i - 6)
            grid.attach(self.check('fuzzy-pinyin-' + key, text, toggle), col, row, 1, 1)

    def user_data(self):
        box = self.page(_('User Data'))
        from googlepinyin import FN_USR_DICT
        grid = self.section(box, _('User Dictionary'))
        label = Gtk.Label(label=FN_USR_DICT, xalign=0, wrap=True, selectable=True)
        grid.attach(label, 0, 0, 2, 1)
        label = Gtk.Label(label=_('Exit IBus before backing up or restoring the dictionary. The original file will be saved as .bak.'), xalign=0, wrap=True)
        grid.attach(label, 0, 1, 2, 1)
        for col, (text, action) in enumerate(((_('Back Up User Dictionary…'), 'backup'), (_('Restore User Dictionary…'), 'restore'))):
            button = Gtk.Button(label=text)
            button.connect('clicked', self.transfer, action)
            grid.attach(button, col, 2, 1, 1)

    def transfer(self, button, action):
        import shutil
        from googlepinyin import FN_USR_DICT
        # Do not manipulate a dictionary while its owner is running.
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                              'org.freedesktop.DBus', 'NameHasOwner',
                              GLib.Variant('(s)', ('org.freedesktop.IBus',)),
                              None, Gio.DBusCallFlags.NONE, -1, None)
        if reply.unpack()[0]:
            self.message(_('Please exit IBus before backing up or restoring the user dictionary.'))
            return
        save = action == 'backup'
        dialog = Gtk.FileChooserDialog(title=_('Back Up User Dictionary') if save else _('Restore User Dictionary'),
                                       transient_for=self,
                                       action=Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(_('_Cancel'), Gtk.ResponseType.CANCEL, _('_OK'), Gtk.ResponseType.OK)
        if save:
            dialog.set_current_name('userdict_pinyin.dat')
            dialog.set_do_overwrite_confirmation(True)
        if dialog.run() == Gtk.ResponseType.OK:
            try:
                source = Path(FN_USR_DICT) if save else Path(dialog.get_filename())
                target = Path(dialog.get_filename()) if save else Path(FN_USR_DICT)
                if not save and target.exists():
                    shutil.copy2(target, str(target) + '.bak')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                self.message(_('Operation completed. Restart IBus to apply the changes.'))
            except (OSError, shutil.Error) as error:
                self.message(str(error))
        dialog.destroy()

    def message(self, text):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   buttons=Gtk.ButtonsType.OK, text=text)
        dialog.run()
        dialog.destroy()

    def shortcuts(self):
        box = self.page(_('Keyboard Shortcuts'))
        box.set_spacing(6)
        self.shortcut_store = Gtk.ListStore(str, str, str)
        for key, label, _default in SHORTCUTS:
            self.shortcut_store.append([_(label), self.settings.get_string('shortcut-' + key), key])
        self.shortcut_view = Gtk.TreeView(model=self.shortcut_store)
        for i, title in enumerate((_('Description'), _('Shortcut'))):
            column = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
            column.set_expand(i == 1)
            column.set_min_width(245 if i == 0 else 200)
            self.shortcut_view.append_column(column)
        self.shortcut_view.get_selection().select_path(0)
        self.shortcut_view.connect('row-activated', self.edit_shortcut)
        box.pack_start(self.shortcut_view, False, False, 0)
        buttons = Gtk.Box(spacing=0)
        reset = Gtk.Button.new_with_mnemonic(_('_Default'))
        reset.connect('clicked', self.reset_shortcuts)
        edit = Gtk.Button.new_with_mnemonic(_('_Edit'))
        edit.connect('clicked', self.edit_shortcut)
        buttons.pack_start(reset, False, False, 0)
        buttons.pack_start(edit, False, False, 0)
        box.pack_start(buttons, False, False, 0)
        for key, _label, _default in SHORTCUTS:
            self.watch('changed::shortcut-' + key, self.refresh_shortcuts)

    def refresh_shortcuts(self, *_args):
        for row in self.shortcut_store:
            row[1] = self.settings.get_string('shortcut-' + row[2])

    def edit_shortcut(self, *_args):
        model, selected = self.shortcut_view.get_selection().get_selected()
        if selected is None:
            return
        label, value, key = model[selected]
        dialog = Gtk.Dialog(title=_('Edit Shortcut'), transient_for=self, modal=True)
        dialog.add_buttons(_('_Cancel'), Gtk.ResponseType.CANCEL, _('_OK'), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_border_width(12)
        content.set_spacing(12)
        content.pack_start(Gtk.Label(label=label, xalign=0), False, False, 0)
        entry = Gtk.Entry(text=value)
        entry.set_width_chars(32)
        entry.set_activates_default(True)
        dialog.set_default_response(Gtk.ResponseType.OK)
        content.pack_start(entry, False, False, 0)
        content.pack_start(Gtk.Label(label=_('Press a key combination, or enter <Control><Shift>f. Leave empty to disable.'), xalign=0), False, False, 0)
        warning = Gtk.Label(xalign=0)
        content.pack_start(warning, False, False, 0)
        def capture(widget, event):
            if event.keyval in (0xffe1, 0xffe2) and key == 'switch-mode':
                widget.set_text('<Shift>')
                return True
            mods = event.state & Gtk.accelerator_get_default_mod_mask()
            if mods:
                widget.set_text(Gtk.accelerator_name(event.keyval, mods))
                return True
            return False
        entry.connect('key-press-event', capture)
        dialog.show_all()
        while dialog.run() == Gtk.ResponseType.OK:
            value = entry.get_text().strip()
            valid = not value or (value == '<Shift>' and key == 'switch-mode') or Gtk.accelerator_parse(value)[0] != 0
            duplicate = value and any(row[2] != key and row[1] == value for row in self.shortcut_store)
            if valid and not duplicate:
                self.settings.set_string('shortcut-' + key, value)
                break
            warning.set_text(_('The shortcut is invalid or already assigned. Please choose another.'))
        dialog.destroy()

    def reset_shortcuts(self, *_args):
        for key, _label, _default in SHORTCUTS:
            self.settings.reset('shortcut-' + key)
        self.refresh_shortcuts()

    def about(self):
        box = self.page(_('About'))
        box.set_valign(Gtk.Align.CENTER)
        box.set_spacing(16)
        image = Gtk.Image.new_from_file(str(Path(__file__).parent / 'icons' / 'ibus-googlepinyin.png'))
        box.pack_start(image, False, False, 0)
        title = Gtk.Label()
        title.set_markup('<span size="large" weight="bold">%s 0.2.0</span>' % GLib.markup_escape_text(_('IBus Google Pinyin')))
        box.pack_start(title, False, False, 0)
        box.pack_start(Gtk.Label(label=_('IBus Google Pinyin Input Method')), False, False, 0)
        box.pack_start(Gtk.LinkButton(uri='https://github.com/hillwoodroc/ibus-googlepinyin',
                                     label='https://github.com/hillwoodroc/ibus-googlepinyin'), False, False, 0)
        for text in (_('Authors:\nJiahua Huang\nHillwood Yang'), _('Preferences layout based on:\nibus-libpinyin\nPeng Huang, BYVoid, Peng Wu'),
                     _('License: GPL-2.0-or-later')):
            label = Gtk.Label(label=text, justify=Gtk.Justification.CENTER)
            box.pack_start(label, False, False, 8)


if __name__ == '__main__':
    Preferences().show_all()
    Gtk.main()
