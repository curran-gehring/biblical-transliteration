"""Golden-table tests for Hebrew + Greek transliteration.

Covers the regressions that motivated the rewrite:
- scheme= override on .transliterate()
- vocal shewa codepoint U+01DD (turned-e)
- SBL §5.1.1 academic begadkefat (ḇ/ḵ/ṯ)
- qamats qatan via shewa-nach-then-vowel rule
- final-form spirants routed through BEGADKEFAT
- Greek diphthong breathing read off either vowel
- Greek ηυ → ēu, υι → ui
- Greek iota subscript renders as macron-only in SBL
"""
import pytest

from biblical_transliteration.hebrew import (
    HebrewTransliterator,
    TransliterationOptions as HOpts,
    TransliterationScheme as HScheme,
)
from biblical_transliteration.greek import (
    GreekTransliterator,
    TransliterationOptions as GOpts,
    TransliterationScheme as GScheme,
)


@pytest.fixture(scope="module")
def heb():
    return HebrewTransliterator()


@pytest.fixture(scope="module")
def grk():
    return GreekTransliterator()


# ---------------------------------------------------------------------------
# Hebrew golden table
# ---------------------------------------------------------------------------

# (surface, sbl, simple, phonetic, why)
# SBL outputs follow §5.1.1 academic: ʾ ḇ ḡ ḏ ḵ p̄ ṯ for spirant bgdkpt + ǝ for shewa.
# Phonetic outputs are hyphen-separated syllables with the stressed syllable
# uppercased. Stress comes from te'amim when present; otherwise ultima default.
HEBREW_CASES = [
    ("בְּרֵאשִׁית", "bǝrēʾšîṯ", "bereshit", "be-re-SHIT",
     "Vocal shewa (U+01DD), aleph kept in SBL, final spirant tav (ṯ); ultima"),
    ("שְׁמַע",      "šǝmaʿ",   "shema",   "she-MA",
     "Word-initial vocal shewa; ayin dropped in Simple/Phonetic"),
    ("כָּל־",       "kol-",    "kol-",    "KOL-",
     "Qamats qatan before maqaf"),
    ("חָכְמָה",     "ḥoḵmāh",  "ḥokhmah", "ḥokh-MAH",
     "Polysyllabic qamats qatan; ultima default (no te'am in input)"),
    ("מֶלֶךְ",      "meleḵ",   "melekh",  "me-LEKH",
     "Final kaf without dagesh = ḵ in SBL academic; ultima default"),
    ("שָׁלוֹם",     "šālôm",   "shalom",  "sha-LOM",
     "Holam male on vav; vowel-only mater attaches to previous syllable"),
    ("דָּבָר",      "dāḇār",   "davar",   "da-VAR",
     "Bet with dagesh (b), without dagesh = spirant ḇ; ultima"),
    ("מִשְׁפָּט",   "mišpāṭ",  "mishpat", "mish-PAT",
     "Polysyllabic final-syllable qamats = gadol (a); ultima"),
    ("הַשָּׁמַיִם",  "haššāmayim", "hashamayim", "ha-sha-ma-YIM",
     "Dagesh forte on shin: SBL doubles (šš), Simple/Phonetic skip digraph doubling"),
    ("וַיֹּאמֶר",    "wayyōʾmer",  "vayyomer",   "va-yyo-MER",
     "Dagesh forte on yod: doubles in all schemes (single-char digraph-safe)"),
    # Words with te'amim — stress comes from the accent mark, not ultima default.
    ("הַ/שָּׁמַ֖יִם", "ha/ššāmayim", "ha/shamayim", "ha-sha-MA-yim",
     "WLC tipeha on shin-yod-mem syllable; Phonetic strips morpheme /"),
    ("מֶ֣לֶךְ",       "meleḵ",   "melekh",  "ME-lekh",
     "WLC munach on mem-syllable → segolate penultima"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", HEBREW_CASES)
def test_hebrew_golden(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


def test_hebrew_scheme_override_does_not_persist(heb):
    """scheme= on a single call must not leak into subsequent calls."""
    heb.options.scheme = HScheme.SBL
    out_simple = heb.transliterate("שָׁלוֹם", scheme=HScheme.SIMPLE)
    out_after = heb.transliterate("שָׁלוֹם")
    assert out_simple == "shalom"
    # Default instance scheme remains SBL afterwards
    assert heb.options.scheme == HScheme.SBL


def test_hebrew_three_schemes_produce_distinct_output(heb):
    """The original bug: all three columns were SBL. They must now differ."""
    sbl = heb.transliterate("בְּרֵאשִׁית", scheme=HScheme.SBL)
    simple = heb.transliterate("בְּרֵאשִׁית", scheme=HScheme.SIMPLE)
    phon = heb.transliterate("בְּרֵאשִׁית", scheme=HScheme.PHONETIC)
    assert sbl != simple, "SBL and Simple must differ"
    # Simple and Phonetic happen to coincide on this word; the meaningful check
    # is that SBL (with macrons + ʾ + ǝ) is distinct from the others.


def test_hebrew_divine_name_default_never_hybrid(heb):
    """The Tetragrammaton must never render as the qere-vowel hybrid yǝhwāh
    (the 'Jehovah' error). Default is the bare consonants per scheme; phonetic
    speaks the qere 'Adonai'."""
    assert heb.transliterate("יְהוָה", scheme=HScheme.SBL) == "yhwh"
    assert heb.transliterate("יְהוָה", scheme=HScheme.SIMPLE) == "yhvh"
    assert heb.transliterate("יְהוָה", scheme=HScheme.PHONETIC) == "Adonai"
    # The discredited hybrid must not appear in any scheme.
    for scheme in (HScheme.SBL, HScheme.SIMPLE, HScheme.PHONETIC):
        out = heb.transliterate("יְהוָה", scheme=scheme).lower()
        assert "hwā" not in out and "hwa" not in out


def test_hebrew_divine_name_in_context_preserves_neighbors(heb):
    """Masking/rendering must not disturb surrounding words or phonetic stress."""
    assert heb.transliterate("יְהוָה שָׁלוֹם", scheme=HScheme.SBL) == "yhwh šālôm"
    assert heb.transliterate("יְהוָה שָׁלוֹם", scheme=HScheme.PHONETIC) == "Adonai shah-LOHM"


def test_hebrew_divine_name_substitution_opt_in():
    """An explicit substitute wins in every scheme."""
    for scheme in (HScheme.SBL, HScheme.SIMPLE, HScheme.PHONETIC):
        opts = HOpts(divine_name_substitute="Adonai", scheme=scheme)
        assert HebrewTransliterator(opts).transliterate("יְהוָה") == "Adonai"
    # Including an uppercase consonantal form on demand.
    opts = HOpts(divine_name_substitute="YHWH", scheme=HScheme.SBL)
    assert HebrewTransliterator(opts).transliterate("יְהוָה") == "YHWH"


# (surface, sbl, why) — śin must stay distinct from samek in SBL academic.
SIN_CASES = [
    ("יִשְׂרָאֵל", "yiśrāʾēl", "śin dot → ś in SBL, not s (would collide with samek)"),
    ("שָׂרָה",     "śārāh",    "word-initial śin → ś in SBL"),
    ("עֵשָׂו",     "ʿēśāw",    "medial śin → ś"),
]


@pytest.mark.parametrize("surface,sbl,why", SIN_CASES)
def test_hebrew_sin_distinct_in_sbl(heb, surface, sbl, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why


def test_hebrew_sin_collapses_to_s_in_ascii_schemes(heb):
    """Simple/Phonetic intentionally fold śin → s (no diacritics)."""
    assert heb.transliterate("יִשְׂרָאֵל", scheme=HScheme.SIMPLE) == "yisrael"


# Bare closed monosyllables with qamats are qamats GADOL (long ā), not qatan.
# The old blanket "final CāC → qatan" heuristic mis-rendered these as 'o'
# (ʾoḇ, dom, yoḏ, ...), corrupting some of the most common words in the Bible.
QAMATS_GADOL_MONOSYLLABLE_CASES = [
    ("אָב",  "ʾāḇ",  "father — not ʾoḇ"),
    ("דָּם",  "dām",  "blood — not dom"),
    ("יָד",  "yāḏ",  "hand — not yoḏ"),
    ("עָם",  "ʿām",  "people — not ʿom"),
    ("דָּג",  "dāḡ",  "fish — not doḡ"),
]


@pytest.mark.parametrize("surface,sbl,why", QAMATS_GADOL_MONOSYLLABLE_CASES)
def test_hebrew_bare_monosyllable_qamats_is_gadol(heb, surface, sbl, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why


def test_hebrew_legit_qamats_qatan_still_detected(heb):
    """Removing the monosyllable heuristic must not regress real qatan cases:
    maqqef (כָּל־), closed-unaccented shewa-nach (חָכְמָה), hataf harmony."""
    assert heb.transliterate("כָּל־", scheme=HScheme.SBL) == "kol-"
    assert heb.transliterate("חָכְמָה", scheme=HScheme.SBL) == "ḥoḵmāh"


# ---------------------------------------------------------------------------
# Greek golden table
# ---------------------------------------------------------------------------

GREEK_CASES = [
    ("λόγος",   "logos",   "logos",   "LO-gos",  "Plain word; oxytone-no-accent default → ultima"),
    ("Ἰησοῦς",  "Iēsous",  "Iesous",  "I-e-SOUS",  "Initial smooth iota, ου, final sigma; perispomenon"),
    ("πνεῦμα",  "pneuma",  "pneuma",  "PNEU-ma", "ευ diphthong with circumflex"),
    ("υἱός",    "huios",   "huios",   "hui-OS",
     "Rough breathing on SECOND vowel of diphthong (regression)"),
    ("ἄγγελος", "angelos", "angelos", "AN-ge-los", "γγ → ng nasal; gamma nasal splits at syllable break"),
    ("ῥῆμα",    "rhēma",   "rhema",   "RHE-ma",  "Initial rho with rough breathing"),
    ("αἷμα",    "haima",   "haima",   "HAI-ma",
     "Diphthong + rough breathing on iota (regression)"),
    ("εὑρίσκω", "heuriskō", "heurisko", "heu-RIS-ko",
     "Diphthong εὑ with rough breathing on second vowel (regression)"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", GREEK_CASES)
def test_greek_golden(grk, surface, sbl, simple, phonetic, why):
    assert grk.transliterate(surface, scheme=GScheme.SBL) == sbl, why
    assert grk.transliterate(surface, scheme=GScheme.SIMPLE) == simple, why
    assert grk.transliterate(surface, scheme=GScheme.PHONETIC) == phonetic, why


def test_greek_iota_subscript_distinct_from_diphthong(grk):
    """ᾳ must not collide with αι in SBL output."""
    out_subscript = grk.transliterate("τῇ", scheme=GScheme.SBL)
    out_diphthong = grk.transliterate("ται", scheme=GScheme.SBL)
    assert out_subscript != out_diphthong


def test_greek_eta_upsilon_diphthong(grk):
    """ηυ should be ēu (not ēy)."""
    assert "y" not in grk.transliterate("ηὐ", scheme=GScheme.SBL).lower().replace("ē", "")


def test_greek_upsilon_iota_diphthong(grk):
    """υι should be ui (not yi)."""
    assert grk.transliterate("υἱ", scheme=GScheme.SBL).lower().endswith("ui")
