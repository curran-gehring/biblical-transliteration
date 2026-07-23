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
import functools
import json
import os
import re
import unicodedata


@functools.lru_cache(maxsize=1)
def _stress_lexicon() -> tuple:
    """Lazily load the OSHB-derived stress lexicon bundled with the package.

    Returns ``(pointed, skeleton)`` dicts mapping a Hebrew key to the stressed
    syllable position counted from the end (1 = ultima, 2 = penult, …). Missing
    or unreadable data degrades gracefully to empty maps (rules-only).

    Keys are NFC-normalized to match runtime lookups (transliterate() NFC-
    normalizes its input, and NFC reorders Hebrew marks — e.g. shin-dot vs
    vowel — so raw source-order keys would never match).
    """
    path = os.path.join(os.path.dirname(__file__), "data", "stress_lexicon.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        pointed = {
            unicodedata.normalize("NFC", k): v
            for k, v in data.get("pointed", {}).items()
        }
        return pointed, data.get("skeleton", {})
    except (OSError, ValueError):
        return {}, {}


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
    '\u05D7': ('ḥ', 'ḥ', 'kh'),    # Chet ח → 'kh' phonetic (English 'ch'=/tʃ/ is wrong); SBL/Simple keep ḥ
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
    '\u05B5': ('ē', 'e', 'ey'),     # Tsere צֵירֵי (phonetic 'ey' = tsere male; plain tsere → 'e' contextually)
    '\u05B6': ('e', 'e', 'e'),      # Segol סֶגּוֹל (short, like 'bed')
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
    preserve_final_he: bool = True            # Keep final he even when mater lectionis
    # None = default policy: bare consonants (SBL yhwh / Simple yhvh), or the
    # spoken "Adonai" in Phonetic — never the qere-vowel hybrid. Set a string
    # ("Adonai"/"Hashem"/"YHWH"/"ʾăḏōnāy") to substitute it in every scheme.
    divine_name_substitute: Optional[str] = None


class HebrewTransliterator:
    """
    Main class for Hebrew to Latin transliteration.
    
    Usage:
        # Default — the Tetragrammaton renders as the bare consonants
        # (SBL: yhwh, Simple: yhvh) and, in Phonetic, as the spoken "Adonai".
        # It is NEVER rendered as the hybrid qere-vowel form (yǝhwāh).
        transliterator = HebrewTransliterator()
        result = transliterator.transliterate("בְּרֵאשִׁית")
        print(result)  # bǝrēʾšîṯ

        # Substitute a reading name for the divine name in every scheme:
        from biblical_transliteration import HebrewOptions
        options = HebrewOptions(divine_name_substitute="Adonai")  # or "Hashem", "YHWH", "ʾăḏōnāy"
        transliterator = HebrewTransliterator(options)
    """
    
    _SCHEME_INDEX_MAP = {
        TransliterationScheme.SBL: 0,
        TransliterationScheme.SIMPLE: 1,
        TransliterationScheme.PHONETIC: 2,
    }

    # Whether the text currently being transliterated carries nikkud; set per
    # call in transliterate(). Pointed default so helpers behave sensibly if
    # ever reached outside transliterate().
    _text_has_nikkud = True

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
        # Unpointed text carries no dagesh information, so begadkefat letters
        # default to their stop values (b g d k p t) rather than spirantizing
        # everywhere — word-initial spirants are the worse guess.
        self._text_has_nikkud = any(
            'ְ' <= c <= 'ּ' or c in ('ׁ', 'ׂ', 'ׇ') for c in hebrew_text
        )
        # Mask the Tetragrammaton with a sentinel BEFORE transliteration so the
        # Masoretic qere vowels never get mechanically rendered into the hybrid
        # "yǝhwāh" form (the classic Jehovah error). The sentinel is non-Hebrew,
        # non-alpha, and non-combining, so it survives the main loop, the
        # phonetic stress-formatter, and post-processing untouched; we swap it
        # for the final rendering as the very last step.
        hebrew_text = self._mask_divine_name(hebrew_text)

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
                if char == '־':
                    # Maqaf: word-joining punctuation (not a combining mark) —
                    # render as a hyphen and mark the word break. This is the
                    # single place maqaf is emitted, including after a masked
                    # divine name or a skipped mater.
                    result.append('-')
                    if is_phonetic and units and not units[-1][3]:
                        last = units[-1]
                        units[-1] = (last[0], last[1], last[2], True, last[4])
                elif not self._is_combining_mark(char):
                    if not (is_phonetic and char == '/'):
                        result.append(char)
                    if is_phonetic and units and not units[-1][3] and char != '/':
                        last = units[-1]
                        units[-1] = (last[0], last[1], last[2], True, last[4])
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

            transliterated = self._process_character(char, marks, chars, i)
            result.append(transliterated)

            if is_phonetic:
                has_taam = any('֑' <= m <= '֯' for m in marks)
                # Strip the maqaf-as-vowel hyphen from the unit text — it's a
                # word-boundary marker, not part of the syllable.
                unit_text = transliterated.replace('-', '')
                has_vowel = self._unit_has_vowel(unit_text, marks)
                # If maqaf was in this consonant's marks, it ends a word.
                ends_word = '־' in marks
                # Coarse nucleus tag for rule-based stress when no te'am is
                # present: 'furtive' (final-guttural furtive patach → penult,
                # e.g. רוּחַ) or 'segol' (segolate/retracted penult, e.g. מֶלֶךְ,
                # וַיֹּאמֶר). Everything else defaults to ultima.
                if self._is_furtive_patach(char, marks, chars, i):
                    vtag = 'furtive'
                elif 'ֶ' in marks:  # segol U+05B6
                    vtag = 'segol'
                else:
                    vtag = None
                # Vowel-only emission (vav-with-holam, shuruk) belongs with
                # the previous syllable since it's a postposed mater providing
                # the vowel for the preceding consonant — e.g. ל + ו(holam) =
                # `lo`, not `l` followed by a free-standing `o`.
                # Phonetic v0.2.0 digraphs ("oh", "ee", "oo", "ah", "eh",
                # "ey") emit a vowel sound but contain a non-vowel
                # letter ('h', 'y'), so the strict all-vowel check would
                # reject them and the syllabifier would never merge a
                # vav-holam "oh" with the preceding consonant. Recognize
                # the known digraphs explicitly.
                only_vowel = bool(unit_text) and (
                    all(c.lower() in 'aeiou' for c in unit_text)
                    or unit_text.lower() in {'oh', 'ee', 'oo', 'ah', 'eh', 'ey'}
                )
                if only_vowel and units and not units[-1][2]:
                    prev_text, prev_taam, _, prev_break, prev_vtag = units[-1]
                    units[-1] = (prev_text + unit_text, prev_taam or has_taam, True,
                                 prev_break or ends_word, prev_vtag or vtag)
                else:
                    units.append((unit_text, has_taam, has_vowel, ends_word, vtag))

            i = j

        output = ''.join(result)
        output = self._post_process(output)

        if is_phonetic and units:
            word_keys = self._hebrew_word_keys(hebrew_text)
            output = self._format_phonetic_with_stress(output, units, word_keys)

        # Swap the divine-name sentinel for its final rendering last, so the
        # replacement text is immune to syllabification and stress markup.
        if self._DIVINE_SENTINEL in output:
            output = output.replace(self._DIVINE_SENTINEL, self._render_divine_name())

        return output

    @staticmethod
    def _unit_has_vowel(text: str, marks: list) -> bool:
        """Did this consonant emit a vowel in its output? Used to decide if a
        following consonant-only emission closes the previous syllable."""
        # In Phonetic, a consonant gets a vowel if the marks include a real
        # vowel point (excluding silent shewa). We approximate by checking the
        # text for any ASCII vowel character.
        return any(c in 'aeiou' for c in text)

    def _is_furtive_patach(self, char: str, marks: list,
                           chars: list = None, index: int = None) -> bool:
        """Patach under a word-final guttural (ח/ע, or ה with mappiq) — the
        furtive patach. Its vowel is an epenthetic glide, so stress falls on
        the preceding syllable (רוּחַ → ROO-akh)."""
        if 'ַ' not in marks:  # patach U+05B7
            return False
        is_guttural = char in ('ח', 'ע') or (char == 'ה' and DAGESH in marks)
        if not is_guttural or chars is None or index is None:
            return False
        for k in range(index + 1, len(chars)):
            if self._is_hebrew(chars[k]):
                return False
            if not self._is_combining_mark(chars[k]):
                break
        return True

    @staticmethod
    def _rule_stress_index(vtags: list) -> int:
        """Best-guess stressed-syllable index when no te'am is available.

        Hebrew default stress is ultima (milra). The common penult (milel)
        exceptions we can detect from the vowel pattern alone:
          - a furtive patach in the final syllable (rúaḥ, gāḇíaʿ);
          - a final segol, the hallmark of segolate nouns (mélek, séfer) and of
            retracted forms like wayyiqtol (wayyómer).
        Fully unpointed input has no tags here, so it falls through to ultima.
        """
        n = len(vtags)
        if n <= 1:
            return n - 1
        if vtags[-1] in ('furtive', 'segol'):
            return n - 2  # penult
        return n - 1      # ultima

    @staticmethod
    def _strip_teamim(s: str) -> str:
        return ''.join(c for c in s if not ('֑' <= c <= '֯'))

    def _hebrew_word_keys(self, text: str) -> list:
        """Split ``text`` into Hebrew words (the same boundaries the phonetic
        formatter uses) and return ``(pointed_key, skeleton_key)`` for each, so
        a per-word stress can be looked up in the OSHB lexicon.

        pointed_key = letters + vowels (te'amim and morpheme '/' removed);
        skeleton_key = consonants only. Maqaf and any non-Hebrew delimiter end a
        word; '/' and combining marks stay within it.
        """
        words: list = []
        cur: list = []

        def flush():
            if cur:
                w = ''.join(cur)
                pointed = self._strip_teamim(w).replace('/', '')
                skeleton = ''.join(c for c in w if self._is_hebrew(c))
                words.append((pointed, skeleton))
                cur.clear()

        for ch in text:
            if self._is_hebrew(ch):
                cur.append(ch)
            elif ch == '־':      # maqaf — word boundary
                flush()
            elif self._is_combining_mark(ch):
                cur.append(ch)        # vowels / dagesh / te'amim stay with the word
            elif ch == '/':
                cur.append(ch)        # morpheme separator (stripped from the key)
            else:
                flush()               # whitespace, sentinel, punctuation
        flush()
        return words

    @staticmethod
    def _lexicon_stress(keys: tuple) -> Optional[int]:
        """Look up a word's stress position (from the end) in the OSHB lexicon.
        Tries the exact pointed form first, then the consonantal skeleton."""
        if keys is None:
            return None
        pointed, skeleton = _stress_lexicon()
        pk, sk = keys
        if pk and pk in pointed:
            return pointed[pk]
        if sk and sk in skeleton:
            return skeleton[sk]
        return None

    def _format_phonetic_with_stress(self, output: str, units: list,
                                     word_keys: Optional[list] = None) -> str:
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

        # The lexicon override is keyed per word; only trust the alignment when
        # the word counts match, otherwise degrade safely to rules-only.
        use_keys = word_keys is not None and len(word_keys) == len(words)

        formatted_words: list[str] = []
        for word_idx, word_units in enumerate(words):
            if not word_units:
                continue
            # Merge consonant-only units into preceding syllable.
            syllables: list[tuple[str, bool, object]] = []  # (text, taam, vtag)
            for text, taam, has_vowel, _, vtag in word_units:
                if syllables and not has_vowel:
                    prev_text, prev_taam, prev_vtag = syllables[-1]
                    syllables[-1] = (prev_text + text, prev_taam or taam, prev_vtag)
                else:
                    syllables.append((text, taam, vtag))

            if not syllables:
                continue

            n = len(syllables)
            # A te'am, when present, is authoritative. Otherwise prefer the
            # OSHB lexicon (exact stress for known words), then fall back to the
            # rule heuristic keyed on the syllable nucleus tags.
            stressed = next((idx for idx, (_, t, _) in enumerate(syllables) if t), None)
            if stressed is None:
                pos = self._lexicon_stress(word_keys[word_idx]) if use_keys else None
                if pos is not None:
                    stressed = max(0, min(n - 1, n - pos))
                else:
                    stressed = self._rule_stress_index([v for _, _, v in syllables])

            parts = [
                (text.upper() if idx == stressed else text)
                for idx, (text, _, _) in enumerate(syllables)
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
                    word = formatted_words[word_idx]
                    word_idx += 1
                else:
                    word = output[start:i]
                # An inseparable prefix fused directly onto the masked divine
                # name (לַיהוָה → la-Adonai) is proclitic: it carries no stress
                # of its own and needs a separator before the substitute that is
                # spliced in later. A space or maqaf between the two already
                # supplies both, so this only fires on direct fusion.
                if i < len(output) and output[i] == self._DIVINE_SENTINEL:
                    word = word.lower() + '-'
                rebuilt.append(word)
            else:
                rebuilt.append(ch)
                i += 1
        return ''.join(rebuilt)
    
    def _is_hebrew(self, char: str) -> bool:
        """Check if character is a Hebrew letter."""
        return '\u05D0' <= char <= '\u05EA'
    
    def _is_combining_mark(self, char: str) -> bool:
        """Check if character is a Hebrew combining mark (vowel, dagesh, etc.).

        Maqaf (U+05BE) sits inside the points block but is punctuation \u2014 a
        word boundary, not a mark on the preceding consonant. Excluding it
        here makes every word-boundary scan (mater detection, shva rules,
        furtive patach, qamats qatan, divine-name masking) treat it
        correctly; the main loop renders it as a hyphen."""
        if char == '\u05BE':
            return False
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
                    # (maqaf is not a combining mark, so it survives in output).
                    end = match_positions[-1] + 1
                    while end < len(chars) and self._is_combining_mark(chars[end]):
                        end += 1

                    # YHWH never takes suffixes: a Hebrew letter right after
                    # means this is a longer word, not the divine name.
                    # (Leading letters are NOT checked — prefixed forms like
                    # וַיהוָה / לַיהוָה / בַּיהוָה are real and must mask.)
                    if end < len(chars) and self._is_hebrew(chars[end]):
                        i += 1
                        continue

                    spans.append((i, end))
                    i = end  # Skip past this match
                    continue

            i += 1

        return spans

    # Sentinel marking a masked Tetragrammaton through the pipeline. Private-use
    # codepoint U+E000 (written as an escape so editors cannot mangle it): not Hebrew, not a combining mark, and str.isalpha() is False, so
    # neither the main loop nor the phonetic stress-formatter touch it.
    _DIVINE_SENTINEL = ''

    def _mask_divine_name(self, text: str) -> str:
        """Replace every Tetragrammaton span with the divine-name sentinel.

        Always runs (regardless of options) so the qere-pointed form is never
        transliterated mechanically. The sentinel is resolved to its final
        rendering at the end of :meth:`transliterate`.
        """
        chars = list(text)
        spans = self._find_tetragrammaton(chars)

        if not spans:
            return text

        result = []
        last_end = 0
        for start, end in spans:
            result.append(text[last_end:start])
            result.append(self._DIVINE_SENTINEL)
            last_end = end
        result.append(text[last_end:])

        return ''.join(result)

    def _render_divine_name(self) -> str:
        """The string the Tetragrammaton sentinel resolves to for this scheme.

        - An explicit ``divine_name_substitute`` always wins (e.g. "Adonai",
          "Hashem", "YHWH", "ʾăḏōnāy").
        - Phonetic defaults to "Adonai" — the spoken qere — because the bare
          consonants are unpronounceable, which is the whole point of phonetic.
        - SBL/Simple default to the four bare consonants (yhwh / yhvh) via the
          scheme's own consonant map. We deliberately never emit the hybrid
          qere-vowel form (yǝhwāh): that is the Jehovah error.
        """
        if self.options.divine_name_substitute is not None:
            return self.options.divine_name_substitute
        if self.options.scheme == TransliterationScheme.PHONETIC:
            return 'Adonai'
        idx = self._scheme_index
        # Yod-He-Vav-He through the scheme's consonant mapping.
        return ''.join(
            HEBREW_CONSONANTS[c][idx]
            for c in ('י', 'ה', 'ו', 'ה')
        )

    def _process_character(self, char: str, marks: list, chars: list = None, index: int = None) -> str:
        """Process a single Hebrew character with its combining marks."""
        
        has_dagesh = DAGESH in marks
        has_shin_dot = SHIN_DOT in marks
        has_sin_dot = SIN_DOT in marks
        
        # Handle Shin/Sin
        if char == '\u05E9':  # Shin
            if has_sin_dot:
                # SBL academic keeps \u015Bin distinct from samek (s); only the
                # ASCII Simple/Phonetic schemes collapse both to plain 's'.
                consonant = '\u015B' if self._scheme_index == 0 else 's'  # Sin
            else:
                consonant = 'š' if self._scheme_index == 0 else 'sh'  # Shin
        
        # Handle BeGaD KeFaT with dagesh. Unpointed text has no dagesh
        # information, so default to the stop value there.
        elif char in BEGADKEFAT and self.options.preserve_dagesh_distinction:
            with_dagesh, without_dagesh = BEGADKEFAT[char][self._scheme_index]
            consonant = with_dagesh if (has_dagesh or not self._text_has_nikkud) else without_dagesh

        # Handle final forms — route through BEGADKEFAT for final kaf/pe so spirants
        # (e.g. ḵ in מֶלֶךְ) are emitted in SBL academic style. Finals keep the
        # spirant default even in unpointed text: word-final position is
        # post-vocalic, so the spirant is the right guess there.
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
        
        # Process vowels. Qere-perpetuum stacking (יְרוּשָׁלִַם / pausal
        # יְרוּשָׁלִָם): when hiriq is written together with patach or qamats
        # under one consonant, the a-vowel is read first (-laim), regardless
        # of mark order in the source.
        vowel_marks = marks
        if 'ִ' in marks and ('ַ' in marks or 'ָ' in marks):
            vowel_marks = sorted(
                marks, key=lambda m: m not in ('ַ', 'ָ')
            )
        vowels = []
        for mark in vowel_marks:
            if mark in HEBREW_VOWELS:
                vowel = HEBREW_VOWELS[mark][self._scheme_index]
                if vowel and mark != DAGESH:  # Don't add dagesh as vowel
                    # Special handling for qamats - distinguish qamats gadol (a) from qamats qatan (o)
                    if mark == '\u05B8' and self.options.handle_qamats_qatan:  # Qamats
                        if self._is_qamats_qatan(chars, index):
                            # Qamats qatan = 'o' in all schemes per SBLHS;
                            # ŏ is reserved for hataf qamats.
                            vowel = 'o'
                    # Phonetic hiriq: long "ee" only when hiriq male (a yod mater
                    # follows, e.g. נָבִיא → nah-VEE). A bare/closed-syllable hiriq
                    # is short — render "i" so מִשְׁפָּט reads mish-PAHT, not
                    # meesh-PAHT. (SBL/Simple keep their single 'i'.)
                    if (mark == 'ִ' and self._scheme_index == 2
                            and not self._followed_by_yod_mater(chars, index)):
                        vowel = 'i'
                    # Phonetic tsere: plain tsere is modern /e/ (כֹּהֵן →
                    # koh-HEN, not koh-HEYN). Only tsere male — a yod mater
                    # follows — diphthongizes to "ey" (בֵּית → beyt, אֵין →
                    # eyn). (SBL/Simple keep their single value.)
                    if (mark == 'ֵ' and self._scheme_index == 2
                            and not self._followed_by_yod_mater(chars, index)):
                        vowel = 'e'
                    # Phonetic /ay/ diphthong: patach or qamats-gadol + a
                    # syllable-closing consonantal yod is the glide (laylah →
                    # LAY-lah, ḥay → KHAY, ʾadonai → a-doh-NAY, Sinai → see-NAY).
                    # Emit the short "a" so the yod's "y" completes "ay"; the full
                    # "ah" here mis-renders as "ahy" (LAHY). A yod with its own
                    # vowel (bayit → BAH-yit) is excluded by
                    # _followed_by_diphthong_yod(); qamats qatan (already 'o' via
                    # the block above) is excluded so it never becomes "ay".
                    if (mark in ('ַ', 'ָ') and self._scheme_index == 2
                            and vowel != 'o'
                            and self._followed_by_diphthong_yod(chars, index)):
                        vowel = 'a'
                    # Special handling for shva
                    if mark == '\u05B0':  # Shva
                        if self._is_vocal_shva(char, marks, chars, index):
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
            has_holam_haser = '\u05BA' in marks  # holam haser FOR VAV
            if '\u05B9' in marks or has_holam_haser:  # Holam on vav
                # Consonantal vav bearing holam (vav = /w/,/v/ + o) vs. holam
                # male (a mater supplying the *preceding* consonant's o). When
                # that preceding consonant already carries its own vowel the vav
                # can't be its mater -- it is a consonant + holam: an ayin with
                # qamats + vav-holam reads 'awon'/'avon', not 'aon'. U+05BA
                # (holam haser for vav) exists precisely to mark this consonantal
                # reading, so it forces the consonant regardless of context.
                if has_holam_haser or self._prev_consonant_has_vowel(chars, index):
                    holam = HEBREW_VOWELS['\u05B9'][self._scheme_index]  # o / o / oh
                    return consonant + holam
                # Holam male: emit the plene o vowel only (the vav is silent).
                return 'ô' if self._scheme_index == 0 else ('oh' if self._scheme_index == 2 else 'o')
            elif (has_dagesh
                    and not any('ְ' <= m <= 'ֻ' or m == 'ׇ' for m in marks)
                    and not self._prev_consonant_has_vowel(chars, index)):
                # Shuruk: vav+dagesh with no vowel point of its own, supplying /u/
                # to a vowel-less preceding consonant (or word-initially, e.g.
                # וּבְ). When the preceding consonant already carries a vowel — the
                # qibbuts in the pual מְצֻוּוֹת — the dagesh is forte and the vav is a
                # doubled consonant, not shuruk; fall through to gemination below.
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
                # Furtive patach: vowel comes BEFORE consonant. The
                # moved vowel is a transitional ultrashort 'a' regardless
                # of scheme (traditional 'ach', 'ruach', 'shamea'). The
                # FILTER target tracks the scheme's full patach mapping
                # ('ah' in phonetic, 'a' in SBL/simple) so the would-
                # have-been-emitted full vowel doesn't double-render
                # at the tail of the consonant.
                patach_emit = 'a'
                patach_full = HEBREW_VOWELS['\u05B7'][self._scheme_index]
                vowels = [v for v in vowels if v != patach_full]
                return patach_emit + consonant + ''.join(vowels)
        
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
                # See chet/ayin branch above — emit short 'a',
                # filter the scheme's full patach value.
                patach_emit = 'a'
                patach_full = HEBREW_VOWELS['\u05B7'][self._scheme_index]
                vowels = [v for v in vowels if v != patach_full]
                return patach_emit + consonant + ''.join(vowels)

        return consonant + ''.join(vowels)

    def _followed_by_yod_mater(self, chars: list, index: int) -> bool:
        """True if the consonant at ``index`` is immediately followed (after its
        own combining marks) by a yod acting as a mater lectionis — i.e. the
        vowel here is *male* (written long, e.g. hiriq male in נָבִיא)."""
        if chars is None or index is None:
            return False
        j = index + 1
        while j < len(chars) and self._is_combining_mark(chars[j]):
            j += 1
        return (j < len(chars) and chars[j] == 'י'
                and self._is_mater_lectionis(chars, j))

    def _followed_by_diphthong_yod(self, chars: list, index: int) -> bool:
        """True if the consonant at ``index`` is immediately followed by a
        consonantal yod that closes the syllable — one carrying no vowel of its
        own beyond a silent shva. With a preceding patach this is the /ay/
        diphthong (laylah, ḥay, ʾadonai, Sinai): the phonetic scheme renders it
        "ay" rather than spelling the patach's full "ah" plus a separate glide
        "y" ("ahy"/"LAHY"). A yod that carries its own vowel is a real consonant
        onset (bayit → BAH-yit), and a yod mater (hiriq/tsere male) only
        lengthens the vowel — neither is a diphthong glide, so both return False.
        """
        if chars is None or index is None:
            return False
        j = index + 1
        while j < len(chars) and self._is_combining_mark(chars[j]):
            j += 1
        if j >= len(chars) or chars[j] != 'י':  # not a yod
            return False
        if self._is_mater_lectionis(chars, j):        # hiriq/tsere male, not a glide
            return False
        # The yod must be vowelless (bare, or a silent shva). Any real vowel
        # point on it makes it a consonant onset (bayit, ayin), not a glide.
        for k in range(j + 1, len(chars)):
            m = chars[k]
            if not self._is_combining_mark(m):
                break
            if m == 'ְ' or m == DAGESH:  # silent shva / dagesh — not a vowel
                continue
            if 'ֱ' <= m <= 'ֻ' or m == 'ׇ':  # any real vowel point
                return False
        return True

    def _prev_consonant_has_vowel(self, chars: list, index: int) -> bool:
        """Does the Hebrew consonant immediately before ``index`` (within the
        same word) carry a vowel point of its own? Distinguishes shuruk (the
        vav supplies /u/ to a vowel-less consonant) from a consonantal vav
        doubled by dagesh forte after a real vowel."""
        if chars is None or index is None:
            return False
        marks_between = []
        for k in range(index - 1, -1, -1):
            ch = chars[k]
            if self._is_hebrew(ch):
                return any(
                    'ְ' <= m <= 'ֻ' or m == 'ׇ'
                    for m in marks_between
                )
            if ch == '/':
                continue  # morphhb morpheme separator stays within the word
            if self._is_combining_mark(ch):
                marks_between.append(ch)
                continue
            break  # word boundary (space, maqaf, punctuation)
        return False

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

            # A yod bearing its OWN dagesh (forte doubling, as in -iyya-) or
            # its own vowel point is a consonant, not a mater lengthening the
            # previous vowel. Without this guard a yod after hiriq/tsere/segol
            # is always read as a mater, dropping the consonant AND its vowel
            # (aliyah lost its -yah, Zion its -y-).
            own_marks = []
            for k in range(index + 1, len(chars)):
                if self._is_combining_mark(chars[k]):
                    own_marks.append(chars[k])
                else:
                    break
            if any(m == DAGESH or '\u05B0' <= m <= '\u05BB' or m == '\u05C7'
                   for m in own_marks):
                return False  # consonantal yod, not a mater lectionis
            
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
                # A maqqef beyond the next consonant signals qatan only when
                # that consonant CLOSES the syllable. A final mater he/aleph
                # leaves the syllable open, so the qamats stays gadol there
                # (תּוֹרָה־, נָא־ — not toroh-/no-).
                maqqef_after = False
                for m in range(k + 1, len(chars)):
                    if chars[m] == MAQQEF:
                        maqqef_after = True
                        break
                    if self._is_combining_mark(chars[m]):
                        next_marks.append(chars[m])
                    else:
                        break
                if maqqef_after:
                    is_open_mater = (
                        (ch == 'ה' and DAGESH not in next_marks)  # he without mappiq
                        or ch == 'א'                              # silent aleph
                    )
                    if not is_open_mater:
                        return True
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

        # NOTE: A bare closed monosyllable (CāC, e.g. אָב דָּם יָד עָם דָּג) is
        # NOT inferred as qatan. Most such words are long-qamats gadol
        # (ʾāḇ, dām, yāḏ, ʿām, dāḡ); whether a given one is qatan depends on
        # lexical/morphological knowledge we do not have here. The earlier
        # blanket "final monosyllable → qatan" heuristic corrupted far more
        # words than it fixed, so qatan in this position must be signalled
        # explicitly — via maqqef (handled above), an explicit Qamats Qatan
        # point (U+05C7, mapped to 'o' directly), or hataf-qamats harmony.

        return False
    
    def _is_vocal_shva(self, char: str, marks: list, chars: list = None, index: int = None) -> bool:
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
        prev_consonant_idx = None
        for k in range(index - 1, -1, -1):
            if self._is_hebrew(chars[k]):
                # Found previous consonant, collect its vowels
                prev_consonant_idx = k
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
        
        # Qamats needs disambiguation the fixed sets can't provide: qamats
        # gadol (long a) takes a vocal shva, qamats qatan (short o) a silent
        # one (the qatan closes its syllable). Reuse the qatan detector on the
        # consonant that actually bears the qamats, so the shva and the vowel
        # agree -- '\u05d7\u05b8\u05db\u05b0\u05de\u05b8\u05d4' stays silent,
        # '\u05e9\u05c1\u05b8\u05de\u05b0\u05e8\u05d5\u05bc' becomes vocal.
        if '\u05B8' in prev_vowels and prev_consonant_idx is not None:
            if (self.options.handle_qamats_qatan
                    and self._is_qamats_qatan(chars, prev_consonant_idx)):
                return False  # qamats qatan -> silent shva (closed syllable)
            return True       # qamats gadol -> vocal shva

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

        # NOTE: the divine name is handled structurally via the sentinel in
        # transliterate()/_render_divine_name(), not by a fragile regex here.

        # Collapse runs of 3+ identical vowels: silent gutturals dropping out
        # (Simple/Phonetic) can stack identical vowels; in SBL such runs only
        # arise from transcription errors.
        text = re.sub(r'([aeiou])\1{2,}', r'\1', text)

        return text.strip()
    
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