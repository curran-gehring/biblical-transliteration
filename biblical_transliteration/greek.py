"""Koine Greek transliteration.

Converts Greek text (Koine, as found in the New Testament and LXX) to Latin
transliteration in three schemes:

- ``SBL`` — Society of Biblical Literature academic conventions, with macrons
  for eta/omega, proper handling of breathing marks, iota subscript, and
  diphthongs in their canonical forms (αι→ai, ει→ei, οι→oi, υι→ui).
- ``SIMPLE`` — ASCII-friendly approximation (no macrons).
- ``PHONETIC`` — Erasmian (Mounce-style seminary) pronunciation spelled so a
  native American English reader lands near the right sound, with the stressed
  syllable upper-cased. Pronunciation legend:
      ah=father  eh=met  ay=obey  ee=see  o=lot  oh=tone  oo=food
      ai=aisle  ay=eight  oy=oil  ow=cow  ew=few  oo=food
      th=thin  kh=k (loch)  f=φ  ks=ξ  ps=ψ  g=hard g  h-=rough breathing

Handles breathing marks, accents, iota subscript, diphthongs, and the
contextual rules that distinguish Koine from Modern or Classical Greek.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple
import functools
import unicodedata


class TransliterationScheme(Enum):
    """Different transliteration schemes available."""
    SBL = "sbl"           # Society of Biblical Literature (academic, with macrons)
    SIMPLE = "simple"     # Simplified ASCII-friendly (no macrons)
    PHONETIC = "phonetic" # Erasmian pronunciation spelled for English readers


# =============================================================================
# GREEK CHARACTER MAPPINGS
# =============================================================================

# Base consonants: (SBL, Simple, Phonetic/Koine)
GREEK_CONSONANTS = {
    # Uppercase
    'Β': ('B', 'B', 'B'),      # Koine: /b/ (not modern /v/)
    'Γ': ('G', 'G', 'G'),
    'Δ': ('D', 'D', 'D'),
    'Ζ': ('Z', 'Z', 'Z'),
    'Θ': ('Th', 'Th', 'Th'),
    'Κ': ('K', 'K', 'K'),
    'Λ': ('L', 'L', 'L'),
    'Μ': ('M', 'M', 'M'),
    'Ν': ('N', 'N', 'N'),
    'Ξ': ('X', 'X', 'Ks'),     # phonetic: "ks" (X reads /z/ word-initially)
    'Π': ('P', 'P', 'P'),
    'Ρ': ('R', 'R', 'R'),
    'Σ': ('S', 'S', 'S'),
    'Τ': ('T', 'T', 'T'),
    'Φ': ('Ph', 'Ph', 'F'),    # phonetic: /f/ for English readers
    'Χ': ('Ch', 'Ch', 'Kh'),   # phonetic: "kh" (ch would read /tʃ/ = wrong)
    'Ψ': ('Ps', 'Ps', 'Ps'),
    # Lowercase
    'β': ('b', 'b', 'b'),      # Koine: /b/ (not modern /v/)
    'γ': ('g', 'g', 'g'),
    'δ': ('d', 'd', 'd'),
    'ζ': ('z', 'z', 'z'),
    'θ': ('th', 'th', 'th'),
    'κ': ('k', 'k', 'k'),
    'λ': ('l', 'l', 'l'),
    'μ': ('m', 'm', 'm'),
    'ν': ('n', 'n', 'n'),
    'ξ': ('x', 'x', 'ks'),     # phonetic: "ks"
    'π': ('p', 'p', 'p'),
    'ρ': ('r', 'r', 'r'),
    'σ': ('s', 's', 's'),
    'ς': ('s', 's', 's'),      # Final sigma
    'τ': ('t', 't', 't'),
    'φ': ('ph', 'ph', 'f'),    # phonetic: /f/ for English readers
    'χ': ('ch', 'ch', 'kh'),   # phonetic: "kh" (ch would read /tʃ/ = wrong)
    'ψ': ('ps', 'ps', 'ps'),
}

# Base vowels (without diacritics): (SBL, Simple, Phonetic/Koine)
GREEK_VOWELS = {
    # Phonetic column = Erasmian (Mounce-style seminary) spelled for an American
    # English reader: η→ay (obey), ι→ee, υ→oo, ο→o, ω→oh, α→ah, ε→eh.
    # Uppercase
    'Α': ('A', 'A', 'Ah'),
    'Ε': ('E', 'E', 'Eh'),
    'Η': ('Ē', 'E', 'Ay'),     # Eta - Erasmian long "ay" as in "obey"
    'Ι': ('I', 'I', 'Ee'),
    'Ο': ('O', 'O', 'O'),
    'Υ': ('Y', 'Y', 'Oo'),     # Upsilon - Erasmian /y/, English approx "oo"
    'Ω': ('Ō', 'O', 'Oh'),     # Omega - long "oh"
    # Lowercase
    'α': ('a', 'a', 'ah'),
    'ε': ('e', 'e', 'eh'),
    'η': ('ē', 'e', 'ay'),     # Eta - Erasmian long "ay" as in "obey"
    'ι': ('i', 'i', 'ee'),
    'ο': ('o', 'o', 'o'),
    'υ': ('y', 'y', 'oo'),     # Upsilon - Erasmian /y/, English approx "oo"
    'ω': ('ō', 'o', 'oh'),     # Omega - long "oh"
}

# Diphthongs - order matters (check longer patterns first)
# Format: (greek_pattern, (SBL, Simple, Phonetic/Koine))
DIPHTHONGS = [
    # Improper diphthongs (with iota subscript) - handled separately
    # Proper diphthongs - Koine preserves diphthong sounds
    # Phonetic column = Erasmian for English readers: αι "aisle", ει/ηυ "ay",
    # οι "oy", αυ "ow" (cow), ευ "ew" (few), ου "oo", υι "wee".
    ('αι', ('ai', 'ai', 'ai')),     # Erasmian /ai/ (aisle)
    ('ει', ('ei', 'ei', 'ay')),     # Erasmian /ei/ → English "ay" (eight)
    ('οι', ('oi', 'oi', 'oy')),     # Erasmian /oi/ (oil)
    ('υι', ('ui', 'ui', 'wee')),    # SBLHS ui; Erasmian "wee"
    ('αυ', ('au', 'au', 'ow')),     # Erasmian /au/ → English "ow" (cow)
    ('ευ', ('eu', 'eu', 'ew')),     # Erasmian /eu/ → English "ew" (few)
    ('ου', ('ou', 'ou', 'oo')),     # Erasmian /ou/ → "oo"
    ('ηυ', ('ēu', 'eu', 'ayoo')),   # SBLHS ēu; Erasmian "ay-oo"
    # Uppercase versions
    ('Αι', ('Ai', 'Ai', 'Ai')),
    ('Ει', ('Ei', 'Ei', 'Ay')),
    ('Οι', ('Oi', 'Oi', 'Oy')),
    ('Υι', ('Ui', 'Ui', 'Wee')),    # verse-initial Υἱός
    ('Αυ', ('Au', 'Au', 'Ow')),
    ('Ευ', ('Eu', 'Eu', 'Ew')),
    ('Ου', ('Ou', 'Ou', 'Oo')),
    ('Ηυ', ('Ēu', 'Eu', 'Ayoo')),
    ('ΑΙ', ('AI', 'AI', 'AI')),
    ('ΕΙ', ('EI', 'EI', 'AY')),
    ('ΟΙ', ('OI', 'OI', 'OY')),
    ('ΥΙ', ('UI', 'UI', 'WEE')),
    ('ΑΥ', ('AU', 'AU', 'OW')),
    ('ΕΥ', ('EU', 'EU', 'EW')),
    ('ΟΥ', ('OU', 'OU', 'OO')),
    ('ΗΥ', ('ĒU', 'EU', 'AYOO')),
]

# Gamma nasals - γ before certain consonants
GAMMA_NASALS = {
    'γγ': ('ng', 'ng', 'ng'),
    'γκ': ('nk', 'nk', 'nk'),
    'γξ': ('nx', 'nx', 'nks'),
    'γχ': ('nch', 'nch', 'nkh'),
    'ΓΓ': ('NG', 'NG', 'NG'),
    'ΓΚ': ('NK', 'NK', 'NK'),
    'ΓΞ': ('NX', 'NX', 'NKS'),
    'ΓΧ': ('NCH', 'NCH', 'NKH'),
}


# =============================================================================
# UNICODE HANDLING FOR GREEK DIACRITICS
# =============================================================================

# Greek Extended block contains precomposed characters with diacritics
# We need to decompose and analyze them

@functools.lru_cache(maxsize=2048)
def get_base_and_diacritics(char: str) -> Tuple[str, frozenset]:
    """
    Decompose a Greek character into its base letter and diacritics.
    Returns (base_char, frozenset_of_diacritics).

    Cached: the transliterator calls this several times per character
    (is-Greek check, vowel/consonant dispatch, accent lookup), and the
    underlying unicodedata.normalize/name calls dominate the runtime.
    The frozen return value keeps the shared cache entries immutable.
    """
    # Normalize to NFD (decomposed form)
    decomposed = unicodedata.normalize('NFD', char)

    if not decomposed:
        return char, frozenset()

    base = decomposed[0]
    diacritics = set()
    
    for c in decomposed[1:]:
        code = ord(c)
        name = unicodedata.name(c, '')
        
        # Rough breathing: COMBINING REVERSED COMMA ABOVE (U+0314)
        # Also known as dasia
        if code == 0x0314 or 'DASIA' in name or 'REVERSED COMMA ABOVE' in name:
            diacritics.add('rough')
        # Smooth breathing: COMBINING COMMA ABOVE (U+0313)
        # Also known as psili
        elif code == 0x0313 or 'PSILI' in name or ('COMMA ABOVE' in name and 'REVERSED' not in name):
            diacritics.add('smooth')
        elif 'OXIA' in name or 'TONOS' in name or 'ACUTE' in name:
            diacritics.add('acute')
        elif 'VARIA' in name or 'GRAVE' in name:
            diacritics.add('grave')
        elif 'PERISPOMENI' in name or 'CIRCUMFLEX' in name or code == 0x0342:
            diacritics.add('circumflex')
        elif 'YPOGEGRAMMENI' in name or 'IOTA SUBSCRIPT' in name or code == 0x0345:
            diacritics.add('iota_subscript')
        elif 'PROSGEGRAMMENI' in name or 'IOTA ADSCRIPT' in name:
            diacritics.add('iota_adscript')
        elif 'DIALYTIKA' in name or 'DIAERESIS' in name or code == 0x0308:
            diacritics.add('diaeresis')
        elif 'MACRON' in name:
            diacritics.add('macron')
        elif 'VRACHY' in name or 'BREVE' in name:
            diacritics.add('breve')

    return base, frozenset(diacritics)


def has_rough_breathing(char: str) -> bool:
    """Check if character has rough breathing mark."""
    _, diacritics = get_base_and_diacritics(char)
    return 'rough' in diacritics


def has_smooth_breathing(char: str) -> bool:
    """Check if character has smooth breathing mark."""
    _, diacritics = get_base_and_diacritics(char)
    return 'smooth' in diacritics


def has_iota_subscript(char: str) -> bool:
    """Check if character has iota subscript."""
    _, diacritics = get_base_and_diacritics(char)
    return 'iota_subscript' in diacritics or 'iota_adscript' in diacritics


def has_diaeresis(char: str) -> bool:
    """Check if character has diaeresis (indicating separate vowel, not diphthong)."""
    _, diacritics = get_base_and_diacritics(char)
    return 'diaeresis' in diacritics


def get_base_char(char: str) -> str:
    """Get the base character without any diacritics."""
    base, _ = get_base_and_diacritics(char)
    return base


def normalize_greek(text: str) -> str:
    """Normalize Greek text to a consistent Unicode form."""
    # First normalize to NFC (composed), then we'll handle character by character
    return unicodedata.normalize('NFC', text)


# =============================================================================
# TRANSLITERATION OPTIONS
# =============================================================================

@dataclass
class TransliterationOptions:
    """Configuration options for Greek transliteration."""
    scheme: TransliterationScheme = TransliterationScheme.SBL
    
    # Breathing marks. Smooth breathing (ἀ) correctly produces no marker — the
    # bare vowel — so there is no option for it; only rough breathing (ἁ → ha)
    # is toggleable.
    show_rough_breathing: bool = True       # ἁ → ha (vs a)

    # Vowel length
    mark_vowel_length: bool = True          # η → ē, ω → ō (SBL only)
    
    # Iota subscript
    show_iota_subscript: bool = True        # ᾳ → āi or ā
    
    # Accents (typically not shown in transliteration)
    show_accents: bool = False
    
    # Diphthong handling
    use_diphthongs: bool = True             # αι → ai vs a-i
    
    # Gamma nasal
    use_gamma_nasal: bool = True            # γγ → ng vs gg
    
    # Initial rho
    rough_initial_rho: bool = True          # ῥ → rh (rough breathing on rho)


# =============================================================================
# MAIN TRANSLITERATOR CLASS
# =============================================================================

class GreekTransliterator:
    """Transliterates Greek text to Latin characters."""

    _SCHEME_INDEX_MAP = {
        TransliterationScheme.SBL: 0,
        TransliterationScheme.SIMPLE: 1,
        TransliterationScheme.PHONETIC: 2,
    }

    def __init__(self, options: Optional[TransliterationOptions] = None):
        self.options = options or TransliterationOptions()

    @property
    def scheme(self) -> TransliterationScheme:
        return self.options.scheme

    @scheme.setter
    def scheme(self, value: TransliterationScheme) -> None:
        self.options.scheme = value

    def get_scheme_index(self) -> int:
        """Get the index for the current scheme in mapping tuples."""
        return self._SCHEME_INDEX_MAP[self.options.scheme]
    
    def transliterate_consonant(self, char: str) -> str:
        """Transliterate a single consonant."""
        base = get_base_char(char)
        idx = self.get_scheme_index()
        
        if base in GREEK_CONSONANTS:
            return GREEK_CONSONANTS[base][idx]
        return char
    
    # Vowels that gain a macron when iota is subscript: ᾳ → ā, ῃ → ē, ῳ → ō.
    _IOTA_SUBSCRIPT_MACRON = {
        'a': 'ā', 'e': 'ē', 'o': 'ō',
        'A': 'Ā', 'E': 'Ē', 'O': 'Ō',
    }

    def _apply_accent(self, vowel_str: str, diacritics: set) -> str:
        """Append acute/grave/circumflex to the last alpha char in vowel_str."""
        if not vowel_str:
            return vowel_str
        if 'acute' in diacritics:
            mark = '\u0301'
        elif 'grave' in diacritics:
            mark = '\u0300'
        elif 'circumflex' in diacritics:
            mark = '\u0302'
        else:
            return vowel_str
        for i in range(len(vowel_str) - 1, -1, -1):
            if vowel_str[i].isalpha():
                return vowel_str[: i + 1] + mark + vowel_str[i + 1:]
        return vowel_str

    def transliterate_vowel(self, char: str, add_h: bool = False) -> str:
        """
        Transliterate a single vowel.
        add_h: whether to prepend \'h\' for rough breathing
        """
        base = get_base_char(char)
        idx = self.get_scheme_index()
        _, diacritics = get_base_and_diacritics(char)

        if base not in GREEK_VOWELS:
            return char

        result = GREEK_VOWELS[base][idx]

        # η/ω carry their macron in the SBL mapping; strip it for the other
        # schemes, and for SBL too when vowel-length marking is disabled.
        if (self.options.scheme != TransliterationScheme.SBL
                or not self.options.mark_vowel_length):
            result = result.replace('ē', 'e').replace('ō', 'o')
            result = result.replace('Ē', 'E').replace('Ō', 'O')

        # Iota subscript: SBL renders as macron-only (ᾳ → ā) so it doesn\'t
        # collide with the αι diphthong. Simple keeps \'i\'. Phonetic (Erasmian)
        # leaves it silent — the subscript iota is not pronounced.
        if has_iota_subscript(char) and self.options.show_iota_subscript:
            if self.options.scheme == TransliterationScheme.SBL:
                result = self._IOTA_SUBSCRIPT_MACRON.get(result, result)
            elif self.options.scheme == TransliterationScheme.SIMPLE:
                result += 'i'

        if self.options.show_accents:
            result = self._apply_accent(result, diacritics)

        if add_h:
            if base.isupper():
                result = 'H' + result.lower()
            else:
                result = 'h' + result

        return result
    
    def transliterate(self, text: str, scheme: Optional[TransliterationScheme] = None) -> str:
        """
        Transliterate Greek text to Latin characters.

        Args:
            text: Greek string.
            scheme: Optional per-call override; falls back to instance scheme.
        """
        if scheme is not None:
            saved = self.options.scheme
            self.options.scheme = scheme
            try:
                return self.transliterate(text)
            finally:
                self.options.scheme = saved

        text = normalize_greek(text)
        result = []
        i = 0
        idx = self.get_scheme_index()

        # Per-emission tracking for Phonetic syllabification + stress.
        # Each entry: (text, has_accent, is_nucleus, is_word_break_after).
        is_phonetic = self.options.scheme == TransliterationScheme.PHONETIC
        units: list = [] if is_phonetic else None

        def _has_accent(ch: str) -> bool:
            _, dia = get_base_and_diacritics(ch)
            return bool(dia & {"acute", "grave", "circumflex"})

        while i < len(text):
            char = text[i]
            base = get_base_char(char)

            # Skip non-Greek characters (pass through). Word boundaries split
            # syllable runs so each word gets its own stress markup.
            if not self._is_greek(char):
                result.append(char)
                if is_phonetic and units and not units[-1][3]:
                    last = units[-1]
                    units[-1] = (last[0], last[1], last[2], True)
                i += 1
                continue

            # Check for gamma nasals (two-character sequences)
            if self.options.use_gamma_nasal and i + 1 < len(text):
                two_char = get_base_char(char) + get_base_char(text[i + 1])
                if two_char in GAMMA_NASALS:
                    emission = GAMMA_NASALS[two_char][idx]
                    result.append(emission)
                    if is_phonetic:
                        # Gamma-nasal first half (n) and second half (g/k/x/ch)
                        # syllabify separately: an-gel-os, not a-ngelos.
                        units.append((emission[0], False, False, False))
                        if len(emission) > 1:
                            units.append((emission[1:], False, False, False))
                    i += 2
                    continue

            # Check for diphthongs
            if self.options.use_diphthongs and i + 1 < len(text):
                next_char = text[i + 1]
                next_base = get_base_char(next_char)

                # Check if next vowel has diaeresis (breaks diphthong)
                if not has_diaeresis(next_char):
                    two_base = base + next_base
                    matched_diphthong = False

                    for pattern, translits in DIPHTHONGS:
                        if two_base == pattern:
                            translit = translits[idx]

                            # ηυ carries a macron in the SBL mapping; strip it
                            # when vowel-length marking is disabled.
                            if (self.options.scheme == TransliterationScheme.SBL
                                    and not self.options.mark_vowel_length):
                                translit = translit.replace('ē', 'e').replace('Ē', 'E')

                            # Breathing on a Greek diphthong is typographically written
                            # over the SECOND vowel (αἷ, οὕ, εὑ). Read both vowels.
                            rough_on_diphthong = (
                                has_rough_breathing(char) or has_rough_breathing(next_char)
                            )
                            if rough_on_diphthong and self.options.show_rough_breathing:
                                if base.isupper():
                                    translit = 'H' + translit.lower()
                                else:
                                    translit = 'h' + translit

                            # Handle iota subscript (rare on diphthongs, but possible).
                            # Phonetic (Erasmian) leaves it silent.
                            if (has_iota_subscript(char)
                                    and self.options.show_iota_subscript
                                    and self.options.scheme != TransliterationScheme.PHONETIC):
                                translit += 'i'

                            result.append(translit)
                            if is_phonetic:
                                accent = _has_accent(char) or _has_accent(next_char)
                                units.append((translit, accent, True, False))
                            i += 2
                            matched_diphthong = True
                            break

                    if matched_diphthong:
                        continue

            # Handle rho with rough breathing
            if base in ('ρ', 'Ρ'):
                translit = self.transliterate_consonant(char)
                if has_rough_breathing(char) and self.options.rough_initial_rho:
                    if base.isupper():
                        translit = 'Rh'
                    else:
                        translit = 'rh'
                result.append(translit)
                if is_phonetic:
                    units.append((translit, False, False, False))
                i += 1
                continue

            # Handle vowels
            if base in GREEK_VOWELS:
                add_h = has_rough_breathing(char) and self.options.show_rough_breathing
                vowel_str = self.transliterate_vowel(char, add_h)
                result.append(vowel_str)
                if is_phonetic:
                    units.append((vowel_str, _has_accent(char), True, False))
                i += 1
                continue

            # Handle consonants
            if base in GREEK_CONSONANTS:
                cons = self.transliterate_consonant(char)
                result.append(cons)
                if is_phonetic:
                    units.append((cons, False, False, False))
                i += 1
                continue

            # Unknown character - pass through
            result.append(char)
            i += 1

        output = ''.join(result)
        if is_phonetic and units:
            output = self._format_phonetic_with_stress(output, units)
        return output

    def _format_phonetic_with_stress(self, output: str, units: list) -> str:
        """Hyphenate Greek output and uppercase the stressed syllable.

        Each vowel/diphthong unit is a syllable nucleus. Intervening
        consonants distribute by VC-CV: a single intervocalic consonant goes
        with the next syllable; multiple consonants split (first goes with
        previous, rest with next). Word-initial consonant clusters (pn-, ps-,
        kr-, etc.) all attach to the first syllable's onset.

        Stress: the syllable whose nucleus carries acute / grave / circumflex.
        Default to ultima when no accent is present (rare in pointed Greek).
        """
        # Group units into words.
        words: list[list] = [[]]
        for u in units:
            words[-1].append(u)
            if u[3]:
                words.append([])
        if not words[-1]:
            words.pop()

        formatted_words: list[str] = []
        for word_units in words:
            if not word_units:
                continue
            syllables: list[dict] = []  # {"text": str, "stressed": bool}
            pending_cons: list[str] = []
            for text, has_accent, is_nucleus, _ in word_units:
                if is_nucleus:
                    if not pending_cons:
                        onset = ''
                    elif syllables:
                        # Word-internal: first cons → coda of prev, rest → onset of new.
                        if len(pending_cons) == 1:
                            onset = pending_cons[0]
                        else:
                            syllables[-1]["text"] += pending_cons[0]
                            onset = ''.join(pending_cons[1:])
                    else:
                        # Word-initial cluster: all to onset.
                        onset = ''.join(pending_cons)
                    syllables.append({"text": onset + text, "stressed": has_accent})
                    pending_cons = []
                else:
                    pending_cons.append(text)
            # Trailing consonants → coda of last syllable.
            if pending_cons:
                if syllables:
                    syllables[-1]["text"] += ''.join(pending_cons)
                else:
                    syllables.append({"text": ''.join(pending_cons), "stressed": True})

            if not syllables:
                continue
            if not any(s["stressed"] for s in syllables):
                syllables[-1]["stressed"] = True

            parts = [
                (s["text"].upper() if s["stressed"] else s["text"])
                for s in syllables
            ]
            formatted_words.append('-'.join(parts))

        # Replace each Latin-letter run in `output` with the next formatted word.
        rebuilt: list[str] = []
        word_idx = 0
        i = 0
        while i < len(output):
            ch = output[i]
            if ch.isalpha():
                start = i
                while i < len(output) and output[i].isalpha():
                    i += 1
                if word_idx < len(formatted_words):
                    rebuilt.append(formatted_words[word_idx])
                    word_idx += 1
                else:
                    rebuilt.append(output[start:i])
            else:
                rebuilt.append(ch)
                i += 1
        return ''.join(rebuilt)
    
    def _is_greek(self, char: str) -> bool:
        """Check if a character is Greek."""
        base = get_base_char(char)
        return base in GREEK_VOWELS or base in GREEK_CONSONANTS
    
    def analyze(self, text: str) -> dict:
        """
        Analyze Greek text and return detailed information.
        """
        text = normalize_greek(text)
        analysis = {
            'original': text,
            'characters': [],
            'breathing_marks': [],
            'accents': [],
            'diphthongs': [],
            'gamma_nasals': [],
        }
        
        i = 0
        while i < len(text):
            char = text[i]
            base = get_base_char(char)
            _, diacritics = get_base_and_diacritics(char)
            
            char_info = {
                'char': char,
                'base': base,
                'position': i,
                'diacritics': list(diacritics),
                'type': 'unknown'
            }
            
            if base in GREEK_VOWELS:
                char_info['type'] = 'vowel'
                if 'rough' in diacritics:
                    analysis['breathing_marks'].append((i, 'rough', char))
                elif 'smooth' in diacritics:
                    analysis['breathing_marks'].append((i, 'smooth', char))
                if any(acc in diacritics for acc in ('acute', 'grave', 'circumflex')):
                    accent_type = 'acute' if 'acute' in diacritics else 'grave' if 'grave' in diacritics else 'circumflex'
                    analysis['accents'].append((i, accent_type, char))
            elif base in GREEK_CONSONANTS:
                char_info['type'] = 'consonant'
            
            analysis['characters'].append(char_info)
            
            # Check for diphthongs
            if i + 1 < len(text) and base in GREEK_VOWELS:
                next_base = get_base_char(text[i + 1])
                two_base = base + next_base
                for pattern, _ in DIPHTHONGS:
                    if two_base == pattern:
                        analysis['diphthongs'].append((i, pattern, char + text[i + 1]))
                        break
            
            # Check for gamma nasals
            if i + 1 < len(text):
                two_char = base + get_base_char(text[i + 1])
                if two_char in GAMMA_NASALS:
                    analysis['gamma_nasals'].append((i, two_char, char + text[i + 1]))
            
            i += 1
        
        return analysis


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def transliterate_sbl(text: str) -> str:
    """Transliterate using SBL academic scheme."""
    options = TransliterationOptions(scheme=TransliterationScheme.SBL)
    return GreekTransliterator(options).transliterate(text)


def transliterate_simple(text: str) -> str:
    """Transliterate using simplified ASCII scheme."""
    options = TransliterationOptions(scheme=TransliterationScheme.SIMPLE)
    return GreekTransliterator(options).transliterate(text)


def transliterate_phonetic(text: str) -> str:
    """Transliterate using phonetic (Koine pronunciation) scheme."""
    options = TransliterationOptions(scheme=TransliterationScheme.PHONETIC)
    return GreekTransliterator(options).transliterate(text)


# =============================================================================
# DEMO AND TESTING
# =============================================================================

def demo():
    """Demonstrate the transliteration program with NT examples."""
    
    # Famous NT words and phrases
    examples = [
        ("Ἐν ἀρχῇ", "In the beginning (John 1:1)"),
        ("ὁ λόγος", "the Word (John 1:1)"),
        ("θεός", "God"),
        ("ἀγάπη", "love"),
        ("πίστις", "faith"),
        ("χάρις", "grace"),
        ("εἰρήνη", "peace"),
        ("ἐκκλησία", "church/assembly"),
        ("βασιλεία", "kingdom"),
        ("εὐαγγέλιον", "gospel/good news"),
        ("ἀλήθεια", "truth"),
        ("ζωή", "life"),
        ("δικαιοσύνη", "righteousness"),
        ("πνεῦμα", "spirit"),
        ("σάρξ", "flesh"),
        ("κύριος", "Lord"),
        ("Χριστός", "Christ/Anointed One"),
        ("Ἰησοῦς", "Jesus"),
        ("ἀμήν", "amen"),
        ("ἄγγελος", "angel/messenger"),  # gamma nasal
        ("ῥῆμα", "word/saying"),  # initial rho with rough breathing
        ("ψυχή", "soul"),
        ("Ἁγίου Πνεύματος", "Holy Spirit"),
    ]
    
    print("=" * 70)
    print("GREEK NEW TESTAMENT TRANSLITERATION DEMO")
    print("=" * 70)
    print()
    
    # Create transliterators for each scheme
    sbl_trans = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.SBL))
    simple_trans = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.SIMPLE))
    phonetic_trans = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.PHONETIC))
    
    for greek, meaning in examples:
        print(f"Greek: {greek}  ({meaning})")
        print("-" * 50)
        print(f"  SBL (Academic)  → {sbl_trans.transliterate(greek)}")
        print(f"  Simple          → {simple_trans.transliterate(greek)}")
        print(f"  Phonetic        → {phonetic_trans.transliterate(greek)}")
        print()
    
    # Show a longer passage
    print("=" * 70)
    print("JOHN 1:1-5 (NA28)")
    print("=" * 70)
    
    john_1 = """Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος.
οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν θεόν.
πάντα δι᾽ αὐτοῦ ἐγένετο, καὶ χωρὶς αὐτοῦ ἐγένετο οὐδὲ ἕν ὃ γέγονεν.
ἐν αὐτῷ ζωὴ ἦν, καὶ ἡ ζωὴ ἦν τὸ φῶς τῶν ἀνθρώπων·
καὶ τὸ φῶς ἐν τῇ σκοτίᾳ φαίνει, καὶ ἡ σκοτία αὐτὸ οὐ κατέλαβεν."""
    
    print()
    print("Greek Text:")
    print(john_1)
    print()
    print("SBL Transliteration:")
    print(sbl_trans.transliterate(john_1))
    print()
    print("Simple Transliteration:")
    print(simple_trans.transliterate(john_1))
    print()


def interactive():
    """Interactive mode for transliterating Greek text."""
    print("=" * 70)
    print("GREEK TRANSLITERATION - INTERACTIVE MODE")
    print("=" * 70)
    print("Enter Greek text to transliterate (or 'quit' to exit)")
    print("Commands: 'sbl', 'simple', 'phonetic' to change scheme")
    print("          'analyze' to see detailed analysis of last input")
    print("          'demo' to run demonstration")
    print()
    
    current_scheme = TransliterationScheme.SBL
    last_input = ""
    
    while True:
        try:
            user_input = input(f"[{current_scheme.value}] > ").strip()
        except EOFError:
            break
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        elif user_input.lower() == 'sbl':
            current_scheme = TransliterationScheme.SBL
            print("Switched to SBL (Academic) scheme")
            continue
        elif user_input.lower() == 'simple':
            current_scheme = TransliterationScheme.SIMPLE
            print("Switched to Simple scheme")
            continue
        elif user_input.lower() == 'phonetic':
            current_scheme = TransliterationScheme.PHONETIC
            print("Switched to Phonetic scheme")
            continue
        elif user_input.lower() == 'demo':
            demo()
            continue
        elif user_input.lower() == 'analyze' and last_input:
            trans = GreekTransliterator()
            analysis = trans.analyze(last_input)
            print(f"\nAnalysis of: {analysis['original']}")
            print(f"Breathing marks: {analysis['breathing_marks']}")
            print(f"Accents: {analysis['accents']}")
            print(f"Diphthongs: {analysis['diphthongs']}")
            print(f"Gamma nasals: {analysis['gamma_nasals']}")
            print()
            continue
        
        last_input = user_input
        
        # Transliterate with all three schemes
        sbl = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.SBL))
        simple = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.SIMPLE))
        phonetic = GreekTransliterator(TransliterationOptions(scheme=TransliterationScheme.PHONETIC))
        
        print(f"\n  SBL       → {sbl.transliterate(user_input)}")
        print(f"  Simple    → {simple.transliterate(user_input)}")
        print(f"  Phonetic  → {phonetic.transliterate(user_input)}")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo()
    else:
        demo()
        print()
        interactive()