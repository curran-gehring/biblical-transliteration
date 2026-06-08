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
# Phonetic column = modern-Hebrew-for-English-readers: qamats/patach→ah,
# holam→oh, qibbuts/shuruk→oo, hiriq male→ee but closed hiriq→i (0.2.7),
# chet→kh (0.2.7), tsere→ey; stressed syllable upper-cased (te'am or ultima).
HEBREW_CASES = [
    ("בְּרֵאשִׁית", "bǝrēʾšîṯ", "bereshit", "be-rey-SHEET",
     "Vocal shewa (U+01DD), aleph kept in SBL, final spirant tav (ṯ); hiriq male → ee"),
    ("שְׁמַע",      "šǝmaʿ",   "shema",   "she-MAH",
     "Word-initial vocal shewa; ayin dropped in Simple/Phonetic; patach → ah"),
    ("כָּל־",       "kol-",    "kol-",    "KOL-",
     "Qamats qatan before maqaf"),
    ("חָכְמָה",     "ḥoḵmāh",  "ḥokhmah", "khokh-MAH",
     "Polysyllabic qamats qatan; chet → kh in Phonetic; ultima default"),
    ("מֶלֶךְ",      "meleḵ",   "melekh",  "me-LEKH",
     "Final kaf without dagesh = ḵ in SBL academic; ultima default"),
    ("שָׁלוֹם",     "šālôm",   "shalom",  "shah-LOHM",
     "Holam male on vav (→ oh); qamats → ah; vowel-only mater attaches to prev"),
    ("דָּבָר",      "dāḇār",   "davar",   "dah-VAHR",
     "Bet with dagesh (b), without dagesh = spirant ḇ; both qamats → ah"),
    ("מִשְׁפָּט",   "mišpāṭ",  "mishpat", "mish-PAHT",
     "Closed hiriq → i (not ee); final qamats gadol → ah; ultima"),
    ("הַשָּׁמַיִם",  "haššāmayim", "hashamayim", "hah-shah-mah-YIM",
     "Dagesh forte on shin: SBL doubles (šš), Phonetic skips digraph doubling; closed hiriq → i"),
    ("וַיֹּאמֶר",    "wayyōʾmer",  "vayyomer",   "vah-yyoh-MER",
     "Dagesh forte on yod doubles; patach → ah, holam → oh"),
    # Words with te'amim — stress comes from the accent mark, not ultima default.
    ("הַ/שָּׁמַ֖יִם", "ha/ššāmayim", "ha/shamayim", "hah-shah-MAH-yim",
     "WLC tipeha on the ma syllable → penult stress; Phonetic strips morpheme /"),
    ("מֶ֣לֶךְ",       "meleḵ",   "melekh",  "ME-lekh",
     "WLC munach on mem-syllable → segolate penultima"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", HEBREW_CASES)
def test_hebrew_golden(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic hiriq (0.2.7): long "ee" only when hiriq male (a yod mater follows);
# a bare/closed-syllable hiriq is short "i".
HIRIQ_CASES = [
    ("מִשְׁפָּט", "mish-PAHT", "closed hiriq → i (mish, not meesh)"),
    ("יִשְׂרָאֵל", "yis-rah-EYL", "closed hiriq → i (yis, not yees)"),
    ("נָבִיא",   "nah-VEE",    "hiriq male before yod → ee"),
    ("עִיר",     "EER",        "hiriq male before yod → ee (city)"),
    ("שִׁיר",    "SHEER",      "hiriq male before yod → ee (song)"),
]


@pytest.mark.parametrize("surface,phonetic,why", HIRIQ_CASES)
def test_hebrew_phonetic_hiriq_length(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic chet (0.2.7): ḥet → "kh", never English "ch" (which reads /tʃ/).
CHET_CASES = [
    ("רוּחַ",   "roo-AKH",   "furtive-patach chet → kh (spirit)"),
    ("חָכְמָה", "khokh-MAH", "initial chet → kh (wisdom)"),
    ("מָשִׁיחַ", "mah-shee-AKH", "final furtive chet → kh (messiah)"),
]


@pytest.mark.parametrize("surface,phonetic,why", CHET_CASES)
def test_hebrew_phonetic_chet_is_kh(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why
    assert "ch" not in heb.transliterate(surface, scheme=HScheme.PHONETIC), why


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

# Phonetic column = Erasmian (Mounce-style) spelled for American English readers:
# η→ay, ι→ee, ου→oo, ευ→ew, ω→oh, χ→kh, φ→f; stressed syllable upper-cased.
GREEK_CASES = [
    ("λόγος",   "logos",   "logos",   "LO-gos",  "Plain word; oxytone-no-accent default → ultima"),
    ("Ἰησοῦς",  "Iēsous",  "Iesous",  "Ee-ay-SOOS",  "Erasmian ι→ee, η→ay, ου→oo; perispomenon stress"),
    ("πνεῦμα",  "pneuma",  "pneuma",  "PNEW-mah", "ευ→ew (few), α→ah; circumflex stress"),
    ("υἱός",    "huios",   "huios",   "hwee-OS",
     "Rough breathing on SECOND vowel of diphthong; υι→wee"),
    ("ἄγγελος", "angelos", "angelos", "AHN-geh-los", "γγ → ng nasal; gamma nasal splits at syllable break"),
    ("ῥῆμα",    "rhēma",   "rhema",   "RHAY-mah",  "Initial rho with rough breathing; η→ay"),
    ("αἷμα",    "haima",   "haima",   "HAI-mah",
     "Diphthong + rough breathing on iota; αι→ai (aisle)"),
    ("εὑρίσκω", "heuriskō", "heurisko", "hew-REES-koh",
     "Diphthong εὑ with rough breathing on second vowel; ι→ee, ω→oh"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", GREEK_CASES)
def test_greek_golden(grk, surface, sbl, simple, phonetic, why):
    assert grk.transliterate(surface, scheme=GScheme.SBL) == sbl, why
    assert grk.transliterate(surface, scheme=GScheme.SIMPLE) == simple, why
    assert grk.transliterate(surface, scheme=GScheme.PHONETIC) == phonetic, why


# Erasmian phonetic spot-checks for the mappings rebuilt in 0.2.6.
# (surface, expected_phonetic, why)
GREEK_ERASMIAN_CASES = [
    ("ἀγάπη",  "ah-GAH-pay", "η→ay (obey), not bare e → 'agap' read as 'uh-gape'"),
    ("ψυχή",   "psoo-KHAY",  "χ→kh (not ch=/tʃ/), υ→oo, η→ay"),
    ("θεός",   "theh-OS",    "ε→eh, ο→o, θ→th"),
    ("φῶς",    "FOHS",       "φ→f, ω→oh"),
    ("εἰρήνη", "ay-RAY-nay", "ει→ay and η→ay both render the long-a sound"),
    ("κύριος", "KOO-ree-os", "υ→oo, ι→ee"),
    ("ἀρχῇ",   "ahr-KHAY",   "χ→kh; iota subscript is silent in Erasmian"),
    ("ζωή",    "zoh-AY",     "ω→oh, η→ay"),
]


@pytest.mark.parametrize("surface,phonetic,why", GREEK_ERASMIAN_CASES)
def test_greek_erasmian_phonetic(grk, surface, phonetic, why):
    assert grk.transliterate(surface, scheme=GScheme.PHONETIC) == phonetic, why


def test_greek_phonetic_iota_subscript_silent(grk):
    """Erasmian does not pronounce subscript iota; Simple still appends 'i'."""
    assert grk.transliterate("τῇ", scheme=GScheme.PHONETIC) == "TAY"
    assert grk.transliterate("τῇ", scheme=GScheme.SIMPLE).endswith("i")


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
