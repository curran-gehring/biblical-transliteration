"""Hebrew transliteration.

Converts Hebrew text (with or without nikkud) to Latin transliteration in
three schemes:

- ``SBL`` — Society of Biblical Literature academic conventions, with full
  diacritics for begadkefat spirantization (ḇ ḡ ḏ ḵ p̄ ṯ), shewa, qamats,
  and proper distinctions between ḥet/ṭet/ṣade/qof.
- ``SIMPLE`` — ASCII-friendly approximation suitable for non-academic use.
- ``PHONETIC`` — modern Hebrew pronunciation hints (e.g. vav as ``v``,
  qof as ``k``).
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import re
import unicodedata


class TransliterationScheme(Enum):
    """Different transliteration schemes available."""
    SBL = "sbl"           # Society of Biblical Literature (academic)
    SIMPLE = "simple"     # Simplified for general use
    PHONETIC = "phonetic" # Approximate pronunciation


# Unicode ranges for Hebrew
HEBREW_CONSONANTS = {
    # Letter: (SBL, Simple, Phonetic)
    '\u05D0': ('ʾ', '',  ''),       # Aleph א — SBL: ʾ; Simple/Phonetic: dropped
    '\u05D1': ('b', 'b', 'v'),     # Bet ב (without dagesh = v)
    '\u05D2': ('g', 'g', 'g'),     # Gimel ג
    '\u05D3': ('d', 'd', 'd'),     # Dalet ד
    '\u05D4': ('h', 'h', 'h'),     # He ה
    '\u05D5': ('w', 'v', 'v'),     # Vav ו
    '\u05D6': ('z', 'z', 'z'),     # Zayin ז
    '\u05D7': ('ḥ', 'ḥ', 'ch'),    # Chet ח → 'ch' (phonetic; SBL keeps ḥ)
    '\u05D8': ('ṭ', 't', 't'),     # Tet ט
    '\u05D9': ('y', 'y', 'y'),     # Yod י
    '\u05DA': ('k', 'kh', 'kh'),   # Final Kaf ך
    '\u05DB': ('k', 'k', 'kh'),    # Kaf כ (without dagesh = kh)
    '\u05DC': ('l', 'l', 'l'),     # Lamed ל
    '\u05DD': ('m', 'm', 'm'),     # Final Mem ם
    '\u05DE': ('m', 'm', 'm'),     # Mem מ
    '\u05DF': ('n', 'n', 'n'),     # Final Nun ן
    '\u05E0': ('n', 'n', 'n'),     # Nun נ
    '\u05E1': ('s', 's', 's'),     # Samekh ס
    '\u05E2': ('ʿ', '',  ''),       # Ayin ע — SBL: ʿ; Simple/Phonetic: dropped
    '\u05E3': ('p', 'f', 'f'),     # Final Pe ף
    '\u05E4': ('p', 'p', 'f'),     # Pe פ (without dagesh = f)
    '\u05E5': ('ṣ', 'ts', 'ts'),   # Final Tsade ץ
    '\u05E6': ('ṣ', 'ts', 'ts'),   # Tsade צ
    '\u05E7': ('q', 'q', 'k'),     # Qof ק
    '\u05E8': ('r', 'r', 'r'),     # Resh ר
    '\u05E9': ('ś', 's', 's'),     # Shin ש (default, sin dot changes it)
    '\u05EA': ('t', 't', 't'),     # Tav ת
}

# Vowel points (nikkud)
HEBREW_VOWELS = {
    # Point: (SBL, Simple, Phonetic)
    '\u05B0': ('ǝ', 'e', 'e'),       # Shva — SBL turned-e U+01DD שְׁוָא (vocal shva)
    '\u05B1': ('ĕ', 'e', 'e'),     # Hataf Segol חֲטַף סֶגּוֹל
    '\u05B2': ('ă', 'a', 'a'),     # Hataf Patach חֲטַף פַּתָח
    '\u05B3': ('ŏ', 'o', 'o'),     # Hataf Qamats חֲטַף קָמָץ
    '\u05B4': ('i', 'i', 'ee'),     # Hiriq חִירִיק
    '\u05B5': ('ē', 'e', 'ey'),     # Tsere צֵירֵי
    '\u05B6': ('e', 'e', 'eh'),     # Segol סֶגּוֹל
    '\u05B7': ('a', 'a', 'ah'),     # Patach פַּתָח
    '\u05B8': ('ā', 'a', 'ah'),     # Qamats קָמָץ (could be qamats gadol or qatan)
    '\u05B9': ('ō', 'o', 'oh'),     # Holam חוֹלָם
    '\u05BA': ('ō', 'o', 'oh'),     # Holam Haser (for vav)
    '\u05BB': ('u', 'u', 'oo'),     # Qibbuts קִבּוּץ
    '\u05BC': ('', '', ''),        # Dagesh דָּגֵשׁ (handled separately)
    '\u05BD': ('', '', ''),        # Meteg מֶתֶג (stress mark, usually ignored)
    '\u05BE': ('-', '-', '-'),     # Maqaf מַקָּף (hyphen)
    '\u05BF': ('', '', ''),        # Rafe רָפֶה (mark for no dagesh)
    '\u05C1': ('', '', ''),        # Shin dot (handled in shin logic)
    '\u05C2': ('', '', ''),        # Sin dot (handled in shin logic)
    '\u05C3': ('', '', ''),        # Sof Pasuq — verse divider, not phoneme סוֹף פָּסוּק (end of verse)
    '\u05C4': ('', '', ''),        # Upper dot
    '\u05C5': ('', '', ''),        # Lower dot
    '\u05C7': ('o', 'o', 'oh'),     # Qamats Qatan (explicit, modern WLC)
}

# BeGaD KeFaT letters change pronunciation with/without dagesh.
# Per scheme: (with_dagesh, without_dagesh).
# SBL §5.1.1 academic uses macron-under/over for spirants: ḇ ḡ ḏ ḵ p̄ ṯ.
# Simple/Phonetic use the general convention: v g d kh f t.
BEGADKEFAT = {
    # letter:    (SBL,            Simple,        Phonetic)
    '\u05D1': (('b', 'ḇ'),  ('b', 'v'),  ('b', 'v')),   # Bet
    '\u05D2': (('g', 'ḡ'),  ('g', 'g'),  ('g', 'g')),   # Gimel
    '\u05D3': (('d', 'ḏ'),  ('d', 'd'),  ('d', 'd')),   # Dalet
    '\u05DB': (('k', 'ḵ'),  ('k', 'kh'), ('k', 'kh')),  # Kaf
    '\u05E4': (('p', 'p̄'),  ('p', 'f'),  ('p', 'f')),   # Pe (p̄ = p + U+0304)
    '\u05EA': (('t', 'ṯ'),  ('t', 't'),  ('t', 't')),   # Tav
}

# Final letter mappings
FINAL_FORMS = {
    '\u05DA': '\u05DB',  # Final Kaf -> Kaf
    '\u05DD': '\u05DE',  # Final Mem -> Mem
    '\u05DF': '\u05E0',  # Final Nun -> Nun
    '\u05E3': '\u05E4',  # Final Pe -> Pe
    '\u05E5': '\u05E6',  # Final Tsade -> Tsade
}

# Special marks
DAGESH = '\u05BC'
SHIN_DOT = '\u05C1'
SIN_DOT = '\u05C2'


@dataclass
class TransliterationOptions:
    """Configuration options for transliteration."""
    scheme: TransliterationScheme = TransliterationScheme.SBL
    preserve_dagesh_distinction: bool = True  # Distinguish b/v, k/kh, p/f
    mark_shva_na: bool = True                 # Mark vocal shva
    handle_qamats_qatan: bool = True          # Detect qamats qatan (o) vs gadol (a)
    include_cantillation: bool = False        # Include te'amim marks
    preserve_final_he: bool = True            # Keep final he even when mater lectionis
    divine_name_substitute: Optional[str] = None  # None=raw transliteration; "Hashem"/"Adonai" available as opt-in


class HebrewTransliterator:
    """
    Main class for Hebrew to Latin transliteration.
    
    Usage:
        # Default - uses Adonai for the divine name
        transliterator = HebrewTransliterator()
        result = transliterator.transliterate("בְּרֵאשִׁית")
        print(result)  # bərēʾšît
        
        # Use Hashem instead of Adonai
        from hebrew_transliteration import TransliterationOptions
        options = TransliterationOptions(divine_name_substitute="Hashem")
        transliterator = HebrewTransliterator(options)
        
        # Use original transliteration (yehvah/YHWH)
        options = TransliterationOptions(divine_name_substitute=None)
        transliterator = HebrewTransliterator(options)
    """
    
    _SCHEME_INDEX_MAP = {
        TransliterationScheme.SBL: 0,
        TransliterationScheme.SIMPLE: 1,
        TransliterationScheme.PHONETIC: 2,
    }

    def __init__(self, options: Optional[TransliterationOptions] = None):
        self.options = options or TransliterationOptions()

    @property
    def _scheme_index(self) -> int:
        return self._SCHEME_INDEX_MAP[self.options.scheme]

    @property
    def scheme(self) -> TransliterationScheme:
        return self.options.scheme

    @scheme.setter
    def scheme(self, value: TransliterationScheme) -> None:
        self.options.scheme = value

    def transliterate(self, hebrew_text: str, scheme: Optional[TransliterationScheme] = None) -> str:
        """
        Transliterate Hebrew text to Latin characters.

        Args:
            hebrew_text: Hebrew string (with or without nikkud)
            scheme: Optional per-call override; falls back to instance scheme.

        Returns:
            Transliterated string
        """
        if scheme is not None:
            saved = self.options.scheme
            self.options.scheme = scheme
            try:
                return self.transliterate(hebrew_text)
            finally:
                self.options.scheme = saved

        hebrew_text = unicodedata.normalize("NFC", hebrew_text)
        hebrew_text = self._substitute_divine_name(hebrew_text)

        # Per-consonant tracking for Phonetic syllabification + stress.
        # Each entry: (text_emitted, has_taam, has_vowel, is_word_break_after)
        is_phonetic = self.options.scheme == TransliterationScheme.PHONETIC
        units: list = [] if is_phonetic else None

        result = []
        chars = list(hebrew_text)
        i = 0

        while i < len(chars):
            char = chars[i]

            # Skip non-Hebrew characters (pass through). Real word boundaries
            # split syllable runs; morpheme separator "/" is a morphhb
            # annotation, not a word break — te'am still scopes the whole
            # compound. In Phonetic mode the "/" is omitted altogether so the
            # output reads as the word is actually pronounced.
            if not self._is_hebrew(char):
                if not self._is_combining_mark(char):
                    if not (is_phonetic and char == '/'):
                        result.append(char)
                    if is_phonetic and units and not units[-1][3] and char != '/':
                        last = units[-1]
                        units[-1] = (last[0], last[1], last[2], True)
                i += 1
                continue

            # Check if this is a mater lectionis (vowel letter to skip)
            if self._is_mater_lectionis(chars, i):
                i += 1
                while i < len(chars) and self._is_combining_mark(chars[i]):
                    i += 1
                continue

            # Look ahead for combining marks
            marks = []
            j = i + 1
            while j < len(chars) and self._is_combining_mark(chars[j]):
                marks.append(chars[j])
                j += 1

            transliterated = self._process_character(char, marks, result, chars, i)
            result.append(transliterated)

            if is_phonetic:
                has_taam = any('֑' <= m <= '֯' for m in marks)
                # Strip the maqaf-as-vowel hyphen from the unit text — it's a
                # word-boundary marker, not part of the syllable.
                unit_text = transliterated.replace('-', '')
                has_vowel = self._unit_has_vowel(unit_text, marks)
                # If maqaf was in this consonant's marks, it ends a word.
                ends_word = '־' in marks
                # Vowel-only emission (vav-with-holam, shuruk) belongs with
                # the previous syllable since it's a postposed mater providing
                # the vowel for the preceding consonant — e.g. ל + ו(holam) =
                # `lo`, not `l` followed by a free-standing `o`.
                only_vowel = bool(unit_text) and all(c.lower() in 'aeiou' for c in unit_text)
                if only_vowel and units and not units[-1][2]:
                    prev_text, prev_taam, _, prev_break = units[-1]
                    units[-1] = (prev_text + unit_text, prev_taam or has_taam, True, prev_break or ends_word)
                else:
                    units.append((unit_text, has_taam, has_vowel, ends_word))

            i = j

        output = ''.join(result)
        output = self._post_process(output)

        if is_phonetic and units:
            output = self._format_phonetic_with_stress(output, units)

        return output

    @staticmethod
    def _unit_has_vowel(text: str, marks: list) -> bool:
        """Did this consonant emit a vowel in its output? Used to decide if a
        following consonant-only emission closes the previous syllable."""
        # In Phonetic, a consonant gets a vowel if the marks include a real
        # vowel point (excluding silent shewa). We approximate by checking the
        # text for any ASCII vowel character.
        return any(c in 'aeiou' for c in text)

    def _format_phonetic_with_stress(self, output: str, units: list) -> str:
        """Hyphenate Phonetic output and capitalize the te'am-bearing syllable.

        Algorithm:
            1. Group consonant-emission units into words (split on the
               is_word_break flag).
            2. Within each word, merge consonant-only units into the previous
               syllable so closed syllables stay intact (mishpat → mish-PAT,
               not mish-pa-t).
            3. The unit carrying the te'am is the stressed syllable. If no
               te'am is found (unpointed text), default to ultima.
            4. Reconstruct each word: hyphen-join syllables, uppercase the
               stressed one. Splice back into the original output, replacing
               only the consecutive Hebrew-emission span for that word so we
               don't disturb spaces, slashes, or punctuation.
        """
        # Walk units, group into words.
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
            # Merge consonant-only units into preceding syllable.
            syllables: list[tuple[str, bool]] = []  # (text, taam)
            for text, taam, has_vowel, _ in word_units:
                if syllables and not has_vowel:
                    prev_text, prev_taam = syllables[-1]
                    syllables[-1] = (prev_text + text, prev_taam or taam)
                else:
                    syllables.append((text, taam))

            if not syllables:
                continue

            stressed = next((idx for idx, (_, t) in enumerate(syllables) if t), None)
            if stressed is None:
                stressed = len(syllables) - 1  # ultima default

            parts = [
                (text.upper() if idx == stressed else text)
                for idx, (text, _) in enumerate(syllables)
            ]
            formatted_words.append('-'.join(p for p in parts if p))

        # Replace each Hebrew-letter run in `output` with the formatted word.
        # A "Hebrew letter run" is any maximal substring of letters; we keep
        # everything else (spaces, /, punctuation) as-is.
        rebuilt: list[str] = []
        word_idx = 0
        i = 0
        while i < len(output):
            ch = output[i]
            if ch.isalpha() or ch == 'ʾ' or ch == 'ʿ':  # ʾ ʿ kept as letters
                # capture run of letters (and any combining marks) as one word
                start = i
                while i < len(output) and (output[i].isalpha() or output[i] in 'ʾʿ'):
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
    
    def _is_hebrew(self, char: str) -> bool:
        """Check if character is a Hebrew letter."""
        return '\u05D0' <= char <= '\u05EA'
    
    def _is_combining_mark(self, char: str) -> bool:
        """Check if character is a Hebrew combining mark (vowel, dagesh, etc.)."""
        return '\u05B0' <= char <= '\u05C7' or '\u0591' <= char <= '\u05AF'

    def _find_tetragrammaton(self, chars: list) -> list:
        """
        Find all occurrences of the Tetragrammaton (יהוה) in the text.

        Returns list of (start_index, end_index) tuples marking spans to replace.
        Handles vowel points interspersed between consonants.
        """
        TETRA_CONSONANTS = ['\u05D9', '\u05D4', '\u05D5', '\u05D4']  # י ה ו ה

        spans = []
        i = 0

        while i < len(chars):
            # Try to match Tetragrammaton starting at position i
            if chars[i] == TETRA_CONSONANTS[0]:  # Yod
                match_positions = [i]
                tetra_idx = 1
                j = i + 1

                # Walk through chars, skipping combining marks, matching consonants
                while j < len(chars) and tetra_idx < 4:
                    if self._is_combining_mark(chars[j]):
                        j += 1  # Skip vowel points, cantillation, etc.
                    elif chars[j] == TETRA_CONSONANTS[tetra_idx]:
                        match_positions.append(j)
                        tetra_idx += 1
                        j += 1
                    else:
                        break  # Wrong consonant, no match

                if tetra_idx == 4:
                    # Found all four consonants - include trailing marks
                    end = match_positions[-1] + 1
                    while end < len(chars) and self._is_combining_mark(chars[end]):
                        end += 1

                    spans.append((i, end))
                    i = end  # Skip past this match
                    continue

            i += 1

        return spans

    def _substitute_divine_name(self, text: str) -> str:
        """
        Replace Tetragrammaton with substitute before transliteration.

        Returns modified text with divine name replaced by the configured substitute.
        """
        if self.options.divine_name_substitute is None:
            return text  # Raw transliteration requested

        chars = list(text)
        spans = self._find_tetragrammaton(chars)

        if not spans:
            return text

        # Build result, replacing spans with placeholder
        result = []
        last_end = 0

        for start, end in spans:
            # Add text before this span
            result.append(text[last_end:start])
            # Add substitute
            result.append(self.options.divine_name_substitute)
            last_end = end

        # Add remaining text
        result.append(text[last_end:])

        return ''.join(result)

    def _process_character(self, char: str, marks: list, previous: list, chars: list = None, index: int = None) -> str:
        """Process a single Hebrew character with its combining marks."""
        
        has_dagesh = DAGESH in marks
        has_shin_dot = SHIN_DOT in marks
        has_sin_dot = SIN_DOT in marks
        
        # Handle Shin/Sin
        if char == '\u05E9':  # Shin
            if has_sin_dot:
                consonant = 's'  # Sin
            else:
                consonant = 'š' if self._scheme_index == 0 else 'sh'  # Shin
        
        # Handle BeGaD KeFaT with dagesh
        elif char in BEGADKEFAT and self.options.preserve_dagesh_distinction:
            with_dagesh, without_dagesh = BEGADKEFAT[char][self._scheme_index]
            consonant = with_dagesh if has_dagesh else without_dagesh

        # Handle final forms — route through BEGADKEFAT for final kaf/pe so spirants
        # (e.g. ḵ in מֶלֶךְ) are emitted in SBL academic style.
        elif char in FINAL_FORMS:
            base_char = FINAL_FORMS[char]
            if base_char in BEGADKEFAT and self.options.preserve_dagesh_distinction:
                with_dagesh, without_dagesh = BEGADKEFAT[base_char][self._scheme_index]
                consonant = with_dagesh if has_dagesh else without_dagesh
            elif base_char in HEBREW_CONSONANTS:
                consonant = HEBREW_CONSONANTS[base_char][self._scheme_index]
            else:
                consonant = HEBREW_CONSONANTS.get(char, ('?', '?', '?'))[self._scheme_index]
        # Standard consonant
        elif char in HEBREW_CONSONANTS:
            consonant = HEBREW_CONSONANTS[char][self._scheme_index]
        
        else:
            consonant = '?'
        
        # Process vowels
        vowels = []
        for mark in marks:
            if mark in HEBREW_VOWELS:
                vowel = HEBREW_VOWELS[mark][self._scheme_index]
                if vowel and mark != DAGESH:  # Don't add dagesh as vowel
                    # Special handling for qamats - distinguish qamats gadol (a) from qamats qatan (o)
                    if mark == '\u05B8' and self.options.handle_qamats_qatan:  # Qamats
                        if self._is_qamats_qatan(chars, index):
                            # Qamats qatan = 'o' in all schemes per SBLHS;
                            # ŏ is reserved for hataf qamats.
                            vowel = 'o'
                    # Special handling for shva
                    if mark == '\u05B0':  # Shva
                        if self._is_vocal_shva(char, marks, previous, chars, index):
                            vowels.append(vowel)
                        # Silent shva: don't add anything
                    else:
                        vowels.append(vowel)
        
        # Mater-lengthening for SBL academic: hiriq+yod → î, tsere+yod → ê, segol+yod → ê.
        # We detect this by looking for a yod immediately after the current consonant's marks
        # that _is_mater_lectionis() would skip.
        if (chars is not None and index is not None
                and self._scheme_index == 0  # SBL only
                and vowels):
            j = index + 1
            while j < len(chars) and self._is_combining_mark(chars[j]):
                j += 1
            if j < len(chars) and chars[j] == '\u05D9' and self._is_mater_lectionis(chars, j):
                _LONG = {'i': 'î', 'ē': 'ê', 'e': 'ê'}
                last = vowels[-1]
                if last in _LONG:
                    vowels[-1] = _LONG[last]

        # Handle vav as vowel letter (mater lectionis)
        if char == '\u05D5':  # Vav
            if '\u05B9' in marks or '\u05BA' in marks:  # Holam on vav
                return 'ô' if self._scheme_index == 0 else ('oh' if self._scheme_index == 2 else 'o')
            elif has_dagesh and not any(v in marks for v in ['\u05B4', '\u05B5', '\u05B6', '\u05B7', '\u05B8']):
                # Shuruk (vav with dagesh, no other vowel) = u
                return 'û' if self._scheme_index == 0 else ('oo' if self._scheme_index == 2 else 'u')
        
        # Note: Yod as mater lectionis is handled by _is_mater_lectionis() in transliterate()
        # If we get here, the yod is consonantal, so output it normally with any vowels
        
        # Handle dagesh forte (gemination) - double the consonant
        # Dagesh forte occurs in non-BeGaD KeFaT letters, or in BeGaD KeFaT after a vowel
        if has_dagesh and char not in ['\u05D0', '\u05D4', '\u05D7', '\u05E2', '\u05E8']:
            # These letters (א ה ח ע ר) cannot take dagesh forte (gutturals + resh)
            # For BeGaD KeFaT, dagesh can be either lene (hardening) or forte (doubling)
            # We check if previous letter had a vowel - if so, it's likely dagesh forte
            if chars is not None and index is not None:
                has_preceding_vowel = False
                for k in range(index - 1, -1, -1):
                    if self._is_hebrew(chars[k]):
                        # Check if this consonant had a vowel
                        for m in range(k + 1, index):
                            if chars[m] in ['\u05B4', '\u05B5', '\u05B6', '\u05B7', '\u05B8', '\u05B9', '\u05BB']:
                                has_preceding_vowel = True
                                break
                        break
                
                # Double consonant for dagesh forte (non-BeGaD KeFaT, or BeGaD KeFaT after vowel).
                # In Simple/Phonetic, skip doubling when the consonant is a digraph
                # (sh, ts, ch, etc.) — `shshamayim`/`tstsel` reads worse than the
                # un-doubled form, and popular romanizations omit the gemination there.
                # SBL keeps the doubling because its single-codepoint forms (š, ṣ) double cleanly.
                if char not in BEGADKEFAT or has_preceding_vowel:
                    if self._scheme_index == 0 or len(consonant) == 1:
                        consonant = consonant + consonant

        # Handle furtive patach - patach under word-final guttural is pronounced BEFORE the consonant
        # e.g., רוּחַ = ruach (not rucha), שָׁמֵעַ = shamea (not shama)
        FURTIVE_GUTTURALS = {'\u05D7', '\u05E2'}  # ח, ע (ה with mappiq handled separately)
        if char in FURTIVE_GUTTURALS and '\u05B7' in marks:  # Patach under guttural
            # Check if word-final
            is_word_final = True
            if chars is not None and index is not None:
                for k in range(index + 1, len(chars)):
                    if self._is_hebrew(chars[k]):
                        is_word_final = False
                        break
                    elif not self._is_combining_mark(chars[k]):
                        break
            
            if is_word_final:
                # Furtive patach: vowel comes BEFORE consonant
                patach = 'a'
                # Remove patach from vowels list and prepend it
                vowels = [v for v in vowels if v != 'a']
                return patach + consonant + ''.join(vowels)
        
        # Also handle ה with mappiq (dagesh in final he) - it can have furtive patach
        if char == '\u05D4' and has_dagesh and '\u05B7' in marks:  # He with mappiq and patach
            is_word_final = True
            if chars is not None and index is not None:
                for k in range(index + 1, len(chars)):
                    if self._is_hebrew(chars[k]):
                        is_word_final = False
                        break
                    elif not self._is_combining_mark(chars[k]):
                        break
            
            if is_word_final:
                patach = 'a'
                vowels = [v for v in vowels if v != 'a']
                return patach + consonant + ''.join(vowels)

        return consonant + ''.join(vowels)
    
    def _is_mater_lectionis(self, chars: list, index: int) -> bool:
        """
        Check if the character at index is a mater lectionis (vowel letter).
        
        Matres lectionis:
        - Yod after hiriq (חִירִיק מָלֵא) - yod just lengthens the /i/
        - Yod after tsere (צֵירֵי מָלֵא) - yod just lengthens the /e/
        - Vav with holam (חוֹלָם מָלֵא) - handled elsewhere
        - Vav with shuruk - handled elsewhere
        - He at end of word after qamats/segol - handled elsewhere
        - Aleph after certain vowels (often silent)
        """
        if index <= 0 or index >= len(chars):
            return False
        
        char = chars[index]
        
        # Look back for the previous consonant and its vowels
        prev_consonant_idx = None
        prev_vowels = []
        for j in range(index - 1, -1, -1):
            if self._is_hebrew(chars[j]):
                prev_consonant_idx = j
                # Collect vowels between prev consonant and current char
                for k in range(j + 1, index):
                    if self._is_combining_mark(chars[k]):
                        prev_vowels.append(chars[k])
                break
            elif self._is_combining_mark(chars[j]):
                prev_vowels.append(chars[j])
        
        # Yod as mater lectionis
        if char == '\u05D9':  # Yod
            # Check if this is word-initial - if so, it's NOT mater lectionis
            is_word_initial = True
            for k in range(index - 1, -1, -1):
                if self._is_hebrew(chars[k]):
                    is_word_initial = False
                    break
                elif not self._is_combining_mark(chars[k]):
                    # Hit a non-mark character (space, punctuation, etc.)
                    break
            
            if is_word_initial:
                return False  # Word-initial yod is always consonantal
            
            # After hiriq = hiriq male (long i)
            if '\u05B4' in prev_vowels:
                return True
            # After tsere = tsere male (long e)  
            if '\u05B5' in prev_vowels:
                return True
            # After segol in some cases
            if '\u05B6' in prev_vowels:
                return True
        
        # Aleph as mater lectionis. SBL §5.1.1 academic always emits ʾ even
        # when phonologically silent, so we only treat aleph as mater for Simple/Phonetic.
        if char == '\u05D0' and self.options.scheme != TransliterationScheme.SBL:
            aleph_vowels = []
            for k in range(index + 1, len(chars)):
                if self._is_combining_mark(chars[k]):
                    aleph_vowels.append(chars[k])
                else:
                    break

            if prev_vowels and not any(v in aleph_vowels for v in
                ['\u05B0', '\u05B1', '\u05B2', '\u05B3', '\u05B4', '\u05B5',
                 '\u05B6', '\u05B7', '\u05B8', '\u05B9', '\u05BB']):
                return True
        
        # He as mater lectionis (silent at end of word after vowel)
        if char == '\u05D4':  # He
            # If preserve_final_he is True, don't treat as mater lectionis —
            # UNLESS phonetic scheme is active, where silent final he is
            # always treated as mater so "SEH-lah" doesn't render as
            # "SEH-lahh" (the final h is silent in pronunciation).
            if (self.options.preserve_final_he
                    and self.options.scheme != TransliterationScheme.PHONETIC):
                return False
            
            # Check if this is word-final
            is_final = True
            for k in range(index + 1, len(chars)):
                if self._is_hebrew(chars[k]):
                    is_final = False
                    break
                elif not self._is_combining_mark(chars[k]):
                    break
            
            if is_final and prev_vowels:
                # Final he after a vowel is typically mater lectionis
                # Exception: if He has a mappiq (dagesh in final he), it's consonantal
                he_marks = []
                for k in range(index + 1, len(chars)):
                    if self._is_combining_mark(chars[k]):
                        he_marks.append(chars[k])
                    else:
                        break
                
                if DAGESH not in he_marks:  # No mappiq
                    return True
        
        return False
    
    def _is_qamats_qatan(self, chars: list, index: int) -> bool:
        """
        Determine if a qamats (ָ) is qamats qatan (short o) or qamats gadol (long a).

        Triggers for qatan:
        1. Before maqqef (־) - e.g., כָּל־
        2. Before hataf qamats (ֳ) - vowel harmony, e.g., צָהֳרַיִם
        3. Closed unaccented syllable: qamats followed by consonant + shewa nach,
           where another full vowel follows (so this syllable is unaccented).
           E.g., חָכְמָה, אָכְלָה, קָדְשִׁי.
        4. Closed final monosyllable (e.g., כָּל without maqqef).
        """
        if chars is None or index is None:
            return False

        SHEWA = "ְ"
        HATAF_QAMATS = "ֳ"
        MAQQEF = "־"
        FULL_VOWELS = ("ֱ", "ֲ", "ֳ", "ִ", "ֵ",
                       "ֶ", "ַ", "ָ", "ֹ", "ֺ", "ֻ", "ׇ")

        next_consonant_idx = None
        next_marks = []
        for k in range(index + 1, len(chars)):
            ch = chars[k]
            if ch in " \t\n":
                break
            if ch == MAQQEF:
                return True
            if self._is_hebrew(ch):
                next_consonant_idx = k
                for m in range(k + 1, len(chars)):
                    if chars[m] == MAQQEF:
                        return True
                    if self._is_combining_mark(chars[m]):
                        next_marks.append(chars[m])
                    else:
                        break
                break
            if not self._is_combining_mark(ch):
                break

        if next_consonant_idx is None:
            return False

        if HATAF_QAMATS in next_marks:
            return True

        has_shewa = SHEWA in next_marks
        has_full_vowel = any(v in next_marks for v in FULL_VOWELS)

        if has_shewa and not has_full_vowel:
            for k in range(next_consonant_idx + 1, len(chars)):
                ch = chars[k]
                if ch in (" ", "\t", "\n", MAQQEF):
                    break
                if ch in FULL_VOWELS:
                    return True
            return False

        if not has_shewa and not has_full_vowel:
            is_next_final = True
            for k in range(next_consonant_idx + 1, len(chars)):
                if self._is_hebrew(chars[k]):
                    is_next_final = False
                    break
                if not self._is_combining_mark(chars[k]):
                    break
            if not is_next_final:
                return False
            if chars[next_consonant_idx] == "ה" and DAGESH not in next_marks:
                return False
            consonants_before = 0
            for k in range(index - 1, -1, -1):
                if self._is_hebrew(chars[k]):
                    consonants_before += 1
                elif not self._is_combining_mark(chars[k]):
                    break
            return consonants_before == 0

        return False
    
    def _is_vocal_shva(self, char: str, marks: list, previous: list, chars: list = None, index: int = None) -> bool:
        """
        Determine if a shva is vocal (na) or silent (nach).
        
        Rules:
        1. Shva at end of word is ALWAYS silent
        2. Shva at beginning of word is vocal
        3. Shva after a short vowel is silent (closes syllable)
        4. Shva after a long vowel is vocal
        5. Two shvas in a row: first is silent, second is vocal
        6. Shva under a dagesh hazaq letter is vocal
        """
        if not self.options.mark_shva_na:
            return True  # Treat all as vocal if not distinguishing
        
        if chars is None or index is None:
            return True  # Can't determine without context
        
        # Check if this is word-final (shva nach). morphhb-style "/" is a morpheme
        # separator, not a word boundary — keep scanning past it.
        is_final = True
        for k in range(index + 1, len(chars)):
            if self._is_hebrew(chars[k]):
                is_final = False
                break
            elif chars[k] == '/':
                continue
            elif not self._is_combining_mark(chars[k]):
                break
        
        if is_final:
            return False  # Final shva is always silent
        
        # Check if word-initial (no previous Hebrew consonants in this word)
        # Maqqef (־) acts as a word boundary for shva rules
        MAQQEF = '\u05BE'
        is_word_initial = True
        for k in range(index - 1, -1, -1):
            if self._is_hebrew(chars[k]):
                is_word_initial = False
                break
            elif chars[k] == MAQQEF:
                # Maqqef acts as word boundary - letter after maqqef is word-initial
                break
            elif not self._is_combining_mark(chars[k]):
                # Hit a non-mark character (space, punctuation, etc.)
                # If it's a delimiter, we're word-initial
                break

        if is_word_initial:
            return True  # Word-initial shva is vocal
        
        # Shva with dagesh (usually vocal - dagesh hazaq)
        if DAGESH in marks:
            return True
        
        # Check for short vowel preceding this consonant
        SHORT_VOWELS = {'\u05B7', '\u05B6', '\u05B4', '\u05BB'}  # patach, segol, hiriq, qibbuts
        LONG_VOWELS = {'\u05B5', '\u05B9', '\u05BA'}  # tsere, holam, holam haser
        
        prev_vowels = []
        for k in range(index - 1, -1, -1):
            if self._is_hebrew(chars[k]):
                # Found previous consonant, collect its vowels
                for m in range(k + 1, index):
                    if self._is_combining_mark(chars[m]) and chars[m] != DAGESH:
                        prev_vowels.append(chars[m])
                break
        
        # Special case: shva before an identical consonant is usually vocal
        # (e.g., הַלְלוּיָה - the shva before the second lamed is vocal)
        next_consonant = None
        for k in range(index + 1, len(chars)):
            if self._is_hebrew(chars[k]):
                next_consonant = chars[k]
                break
            elif not self._is_combining_mark(chars[k]):
                break
        
        if next_consonant == char:
            return True  # Shva before identical consonant is vocal
        
        # Consecutive shvas rule: if previous consonant also has shva, THIS shva is vocal
        # (First shva closes syllable, second shva opens next syllable)
        if '\u05B0' in prev_vowels:  # Previous consonant has shva
            return True  # Second of two consecutive shvas is vocal
        
        # If previous vowel was short, shva is silent
        if any(v in SHORT_VOWELS for v in prev_vowels):
            return False
        
        # If previous vowel was long, shva is vocal
        if any(v in LONG_VOWELS for v in prev_vowels):
            return True
        
        # Default: assume silent for closed syllables
        return False
    
    def _post_process(self, text: str) -> str:
        """Apply post-processing rules to the transliterated text."""
        
        # Handle divine name (YHWH) - in Phonetic mode, replace with "Adonai" (how it's spoken)
        if self.options.scheme == TransliterationScheme.PHONETIC:
            # Pattern for יהוה with various vowel patterns
            pattern = r'\by[eə]?h[wv]a?h\b'
            text = re.sub(pattern, 'Adonai', text, flags=re.IGNORECASE)
        
        # In phonetic mode, collapse consecutive identical vowels (actual pronunciation)
        # e.g., "vaarets" → "varets" (silent gutturals don't create audible hiatus)
        if self.options.scheme == TransliterationScheme.PHONETIC:
            text = re.sub(r'([aeiou])\1{2,}', r'\1', text)
        else:
            # In other modes, only clean up triple+ vowels (likely errors)
            text = re.sub(r'([aeiou])\1{2,}', r'\1', text)
        
        # Handle word boundaries
        text = text.strip()
        
        return text
    
    def transliterate_word(self, word: str) -> str:
        """Transliterate a single Hebrew word."""
        return self.transliterate(word)
    
    def transliterate_verse(self, verse: str) -> str:
        """Transliterate a full verse, preserving spacing and punctuation."""
        return self.transliterate(verse)


def analyze_hebrew_word(word: str) -> dict:
    """
    Analyze a Hebrew word and return detailed information.
    
    Returns dict with:
        - consonants: list of consonants
        - vowels: list of vowels  
        - has_dagesh: letters with dagesh
        - transliterations: dict of different schemes
    """
    analysis = {
        'original': word,
        'consonants': [],
        'vowels': [],
        'dagesh_letters': [],
        'transliterations': {}
    }
    
    for char in word:
        if '\u05D0' <= char <= '\u05EA':
            analysis['consonants'].append(char)
        elif '\u05B0' <= char <= '\u05BB':
            analysis['vowels'].append(char)
        elif char == DAGESH:
            if analysis['consonants']:
                analysis['dagesh_letters'].append(analysis['consonants'][-1])
    
    # Generate all transliteration schemes
    for scheme in TransliterationScheme:
        options = TransliterationOptions(scheme=scheme)
        transliterator = HebrewTransliterator(options)
        analysis['transliterations'][scheme.value] = transliterator.transliterate(word)
    
    return analysis


# Convenience functions
def transliterate_sbl(text: str) -> str:
    """Quick transliteration using SBL scheme."""
    return HebrewTransliterator(TransliterationOptions(scheme=TransliterationScheme.SBL)).transliterate(text)


def transliterate_simple(text: str) -> str:
    """Quick transliteration using simple scheme."""
    return HebrewTransliterator(TransliterationOptions(scheme=TransliterationScheme.SIMPLE)).transliterate(text)


def transliterate_phonetic(text: str) -> str:
    """Quick transliteration using phonetic scheme."""
    return HebrewTransliterator(TransliterationOptions(scheme=TransliterationScheme.PHONETIC)).transliterate(text)


# Demo / CLI
if __name__ == "__main__":
    # Example Hebrew texts
    examples = [
        ("בְּרֵאשִׁית", "Genesis (In the beginning)"),
        ("יְהוָה", "YHWH (the LORD)"),
        ("שָׁלוֹם", "Shalom (peace)"),
        ("תּוֹרָה", "Torah (instruction/law)"),
        ("אֱלֹהִים", "Elohim (God)"),
        ("מֶלֶךְ", "Melek (king)"),
        ("דָּבָר", "Davar (word/thing)"),
        ("נָבִיא", "Navi (prophet)"),
        ("כֹּהֵן", "Kohen (priest)"),
        ("מִשְׁפָּט", "Mishpat (judgment)"),
    ]
    
    print("=" * 70)
    print("Hebrew Transliteration Program")
    print("=" * 70)
    print()
    
    # Create transliterators for each scheme
    schemes = [
        (TransliterationScheme.SBL, "SBL (Academic)"),
        (TransliterationScheme.SIMPLE, "Simple"),
        (TransliterationScheme.PHONETIC, "Phonetic"),
    ]
    
    for hebrew, description in examples:
        print(f"Hebrew: {hebrew}  ({description})")
        print("-" * 50)
        for scheme, scheme_name in schemes:
            options = TransliterationOptions(scheme=scheme)
            transliterator = HebrewTransliterator(options)
            result = transliterator.transliterate(hebrew)
            print(f"  {scheme_name:15} → {result}")
        print()
    
    # Interactive mode
    print("=" * 70)
    print("Enter Hebrew text to transliterate (or 'quit' to exit):")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\nHebrew > ").strip()
            if user_input.lower() in ('quit', 'exit', 'q'):
                break
            if not user_input:
                continue
                
            print("\nTransliterations:")
            for scheme, scheme_name in schemes:
                options = TransliterationOptions(scheme=scheme)
                transliterator = HebrewTransliterator(options)
                result = transliterator.transliterate(user_input)
                print(f"  {scheme_name:15} → {result}")
            
            # Word analysis
            print("\nWord Analysis:")
            analysis = analyze_hebrew_word(user_input)
            print(f"  Consonants: {' '.join(analysis['consonants'])}")
            print(f"  Vowels: {' '.join(analysis['vowels']) if analysis['vowels'] else '(none/unpointed)'}")
            if analysis['dagesh_letters']:
                print(f"  Dagesh in: {' '.join(analysis['dagesh_letters'])}")
                
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n")
            break
    
    print("\nשָׁלוֹם! (Shalom!)")