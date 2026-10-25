"""Shared preferences, following ibus-libpinyin's GSettings key conventions.

SPDX-License-Identifier: GPL-2.0-or-later
"""
from i18n import N_
from pathlib import Path
from gi.repository import Gio

SCHEMA = 'org.freedesktop.ibus.engine.googlepinyin'
CORRECTIONS = [('gn-ng', 'gn ⇒ ng'), ('mg-ng', 'mg ⇒ ng'), ('iou-iu', 'iou ⇒ iu'),
               ('uei-ui', 'uei ⇒ ui'), ('uen-un', 'uen ⇒ un'), ('ue-ve', 'ue ⇒ ve'),
               ('v-u', 'v ⇒ u, ve ⇒ ue, van ⇒ uan'), ('on-ong', 'on ⇒ ong')]
FUZZY = [('c-ch', 'c ⇔ ch'), ('z-zh', 'z ⇔ zh'), ('s-sh', 's ⇔ sh'),
         ('l-n', 'l ⇔ n'), ('f-h', 'f ⇔ h'), ('l-r', 'l ⇔ r'), ('g-k', 'g ⇔ k'),
         ('an-ang', 'an ⇔ ang'), ('en-eng', 'en ⇔ eng'), ('in-ing', 'in ⇔ ing')]
SHORTCUTS = [('switch-mode', N_('Switch Chinese/English Mode'), '<Shift>'),
             ('full-width', N_('Full/Half Width Letters'), '<Shift>space'),
             ('punctuation', N_('Full/Half Width Punctuation'), '<Control>period'),
             ('all-width', N_('Toggle All Full/Half Width'), ''),
             ('traditional', N_('Switch Traditional/Simplified Chinese'), '<Control><Shift>f')]
DEFAULTS = {
    'initial-chinese': True, 'initial-full-width': False, 'initial-full-punct': True,
    'initial-traditional': False, 'orientation': 0, 'page-size': 9,
    'display-style': 0,
    'sort-order': 0, 'double-pinyin': False,
    'double-pinyin-schema': 0, 'double-pinyin-show-raw': False, 'incomplete-pinyin': True,
    'shift-select': False, 'minus-equal-page': True, 'comma-period-page': False,
    'bracket-page': False, 'auto-commit': False, 'correct-pinyin': True,
    'fuzzy-pinyin': False,
}
DEFAULTS.update({'correct-pinyin-' + key: True for key, _ in CORRECTIONS})
DEFAULTS.update({'fuzzy-pinyin-' + key: key not in ('l-r', 'g-k') for key, _ in FUZZY})
DEFAULTS.update({'shortcut-' + key: value for key, _, value in SHORTCUTS})


def new_settings():
    source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup(SCHEMA, True) if source else None
    if schema is None:
        for directory in (Path(__file__).parent / 'build' / 'schemas',
                          Path(__file__).parent / 'data'):
            if (directory / 'gschemas.compiled').exists():
                local = Gio.SettingsSchemaSource.new_from_directory(str(directory), source, False)
                schema = local.lookup(SCHEMA, False)
                if schema:
                    break
    if schema is None:
        raise RuntimeError('GSettings schema missing; run cmake -S . -B build first.')
    return Gio.Settings.new_full(schema, None, None)
