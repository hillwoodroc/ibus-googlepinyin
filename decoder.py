"""Candidate search adapter; preserves decoder IDs across spelling variants.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import googlepinyin as native
from pinyin import spellings, native_spelling


class Decoder:
    def __init__(self, get):
        self.get = get
        self.candidates = []
        self.choices = []
        self.raw = None
        self._syllables = {}
        self.fixed = ''
        self.display_spelling = ''

    def reset(self):
        native.im_reset_search()
        self.candidates = []
        self.choices = []
        self.raw = None
        self.fixed = ''
        self.display_spelling = ''

    def is_full_syllable(self, spelling):
        """Validate shared-key expansions against the actual decoder lexicon.

        Disable abbreviation here: every completed double-pinyin pair must
        correspond to exactly one fully decoded syllable, never mu + o.
        Search state is restored by the caller before retrieving candidates.
        """
        if spelling not in self._syllables:
            native.im_enable_shm_as_szm(False)
            native.im_enable_ym_as_szm(False)
            native.im_reset_search()
            count = native.im_search(spelling)
            boundaries = native.spelling_boundaries()
            self._syllables[spelling] = bool(count and boundaries == [0, len(spelling)])
        return self._syllables[spelling]

    def search(self, raw):
        if raw == self.raw:
            return len(self.candidates)
        self.raw = raw
        self.choices = []
        self.candidates = []
        self.fixed = ''
        self.display_spelling = raw
        seen = set()
        native.im_enable_shm_as_szm(self.get('incomplete-pinyin'))
        native.im_enable_ym_as_szm(self.get('incomplete-pinyin'))
        def without_fuzzy(key):
            return False if key == 'fuzzy-pinyin' else self.get(key)
        base = [native_spelling(value) for value in spellings(raw, without_fuzzy, self.is_full_syllable)]
        # Validation temporarily disables initials; restore the user's choice.
        native.im_enable_shm_as_szm(self.get('incomplete-pinyin'))
        native.im_enable_ym_as_szm(self.get('incomplete-pinyin'))
        if base:
            self.display_spelling = base[0]
        expanded = []
        for spelling in base:
            expanded.append(spelling)
            if self.get('fuzzy-pinyin'):
                native.im_reset_search()
                native.im_search(spelling)
                boundaries = native.spelling_boundaries()
                segmented = "'".join(spelling[a:b].strip("'") for a, b in zip(boundaries, boundaries[1:]))
                if segmented and boundaries[-1] == len(spelling):
                    def fuzzy_only(key):
                        return False if key in ('double-pinyin', 'correct-pinyin') else self.get(key)
                    expanded.extend(native_spelling(value) for value in spellings(segmented, fuzzy_only))
        for spelling in list(dict.fromkeys(expanded))[:64]:
            native.im_reset_search()
            count = native.im_search(spelling)
            for index in range(min(count, 200)):
                text = native.im_get_candidate(index)
                if text and text not in seen:
                    seen.add(text)
                    self.candidates.append(text)
                    self.choices.append((spelling, index))
        order = self.get('sort-order')
        if order:
            entries = sorted(zip(self.candidates, self.choices),
                             key=lambda item: len(item[0]), reverse=order == 1)
            self.candidates = [item[0] for item in entries]
            self.choices = [item[1] for item in entries]
        if self.choices:
            self.display_spelling = self.choices[0][0]
        return len(self.candidates)

    def choose(self, index):
        spelling, native_index = self.choices[index]
        if spelling is not None:
            self.display_spelling = spelling
            native.im_reset_search()
            native.im_search(spelling)
        count = native.im_choose(native_index)
        self.candidates = [native.im_get_candidate(i) for i in range(count)]
        self.choices = [(None, i) for i in range(count)]
        self.fixed = native.im_get_candidate(0)[:native.im_get_fixed_len()] if count else ''
        return count

    def candidate(self, index):
        return self.candidates[index]
