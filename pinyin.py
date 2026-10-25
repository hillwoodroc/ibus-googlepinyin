"""Input spelling adapter for the Google decoder (GPL-2.0-or-later)."""
from i18n import N_
import re
from itertools import product, islice

# Key positions are factual scheme data, checked against libpinyin's
# src/storage/double_pinyin_table.h and Rime's double_pinyin_flypy schema.
# IDs are persistent: keep natural code at zero for existing installations.
SCHEME_NAMES = (N_('Natural Code'), N_('Microsoft Pinyin'), N_('Intelligent ABC'), N_('Ziguang Pinyin'), N_('Pinyin Jiajia'), N_('Xiaohe'))
KEYS = 'abcdefghijklmnopqrstuvwxyz;'
_FINAL_ROWS = (
    'a ou iao uang/iang e en eng/ng ang i an ao ai ian in uo/o un iu uan/er ong/iong ue u ui/v ia/ua ie uai/ing ei -',
    'a ou iao uang/iang e en eng/ng ang i an ao ai ian in uo/o un iu uan/er ong/iong ue u ui/ue ia/ua ie uai/v ei ing',
    'a ou in/uai ia/ua e en eng/ng ang i an ao ai ue/ui un uo/o uan ei er/iu ong/iong iang/uang u v/ue ian ie ing iao -',
    'a iao - ie e ian iang/uang ong/iong i er/iu ei uan un ue/ui uo/o ai ao an ang eng/ng u v en ia/ua in/uai ou ing',
    'a ia/ua uan ao e an ang iang/uang i ian iao in ie iu uo/o ou er/ing en ai eng/ng u v/ui ei uai/ue ong/iong un -',
    'a in ao ai e en eng/ng ang i an uai/ing iang/uang ian iao uo/o ie iu uan/er ong/iong ue u v/ui ei ia/ua un ou -',
)
FINALS = tuple({key: tuple(value.split('/')) for key, value in zip(KEYS, row.split())
                if value != '-'} for row in _FINAL_ROWS)
INITIALS = (
    {'i': 'ch', 'u': 'sh', 'v': 'zh'},
    {'i': 'ch', 'u': 'sh', 'v': 'zh'},
    {'a': 'zh', 'e': 'ch', 'v': 'sh'},
    {'a': 'ch', 'i': 'sh', 'u': 'zh'},
    {'i': 'sh', 'u': 'ch', 'v': 'zh'},
    {'i': 'ch', 'u': 'sh', 'v': 'zh'},
)
ZERO_FALLBACK = dict(zip(('aa', 'ai', 'an', 'ah', 'ao', 'ee', 'ei', 'en', 'er', 'oo', 'ou'),
                         ('a', 'ai', 'an', 'ang', 'ao', 'e', 'ei', 'en', 'er', 'o', 'ou')))
# Zero-initial prefixes used by the original schemes.
ZERO_PREFIXES = ('o', 'o', 'o', 'o', 'ao', 'o')


def native_spelling(spelling):
    """Google uses nue/lue for nüe/lüe, but nv/lv for nü/lü."""
    return re.sub(r'([nl])ve', r'\1ue', spelling)


def double_syllables(pair, scheme, valid_syllable=None):
    initials, finals = INITIALS[scheme], FINALS[scheme]
    if len(pair) == 1:
        if pair in 'aeo' and pair not in initials:
            return [pair]
        if pair in 'bpmfdtnlgkhjqxrzcsyw' or pair in initials:
            return [initials.get(pair, pair)]
        return []
    first, last = pair
    result = []
    if scheme in (0, 5) and pair in ZERO_FALLBACK:
        result.append(ZERO_FALLBACK[pair])
    if scheme == 4:
        fallback = dict(zip(('aa', 'as', 'af', 'ag', 'ad', 'ee', 'ew', 'er', 'eq', 'oo', 'op'),
                            ('a', 'ai', 'an', 'ang', 'ao', 'e', 'ei', 'en', 'er', 'o', 'ou')))
        if pair in fallback:
            result.append(fallback[pair])
    for final in finals.get(last, ()):
        if first in ZERO_PREFIXES[scheme]:
            if final in ('a', 'ai', 'an', 'ang', 'ao', 'e', 'ei', 'en', 'eng', 'er', 'o', 'ou', 'ng'):
                result.append(final)
        elif first in initials or first in 'bpmfdtnlgkhjqxrzcsyw':
            initial = initials.get(first, first)
            if final == 'v' and initial in ('j', 'q', 'x', 'y'):
                final = 'u'
            result.append(initial + final)
    result = list(dict.fromkeys(result))
    if valid_syllable is not None:
        result = [spelling for spelling in result if valid_syllable(native_spelling(spelling))]
    return result


def spellings(raw, get, valid_syllable=None):
    variants = [raw]
    if get('double-pinyin'):
        scheme = get('double-pinyin-schema')
        if not 0 <= scheme < len(SCHEME_NAMES):
            scheme = 0
        pieces = []
        for word in raw.split("'"):
            for i in range(0, len(word), 2):
                pieces.append(double_syllables(word[i:i+2], scheme, valid_syllable))
        variants = ["'".join(parts) for parts in islice(product(*pieces), 32)]
    if get('correct-pinyin'):
        for suffix in ('gn-ng', 'mg-ng', 'iou-iu', 'uei-ui', 'uen-un', 'on-ong'):
            if get('correct-pinyin-' + suffix):
                old, new = suffix.split('-')
                variants = [re.sub(old + r"(?='|$|[bpmfdtnlkhjqxzcsryw])", new, v)
                            for v in variants]
        if get('correct-pinyin-ue-ve'):
            variants = [re.sub(r'([nl])ue', r'\1ve', v) for v in variants]
        if get('correct-pinyin-v-u'):
            variants = [re.sub(r'([jqxy])v', r'\1u', v) for v in variants]
    if get('fuzzy-pinyin'):
        from settings import FUZZY
        for key, _ in FUZZY:
            if not get('fuzzy-pinyin-' + key):
                continue
            a, b = key.split('-')
            extra = []
            # Initials only at syllable starts; finals only at syllable ends.
            for spelling in variants:
                for old, new in ((a, b), (b, a)):
                    pattern = (r'(^|\')' + old + r'(?!h)' if len(a) == 1
                               else old + r"(?='|$|[bpmfdtnlgkhjqxzcsrwy])")
                    replacement = r'\g<1>' + new if len(a) == 1 else new
                    changed = re.sub(pattern, replacement, spelling)
                    if changed != spelling:
                        extra.append(changed)
            variants = list(dict.fromkeys(variants + extra))[:64]
    return variants
