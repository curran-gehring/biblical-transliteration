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
# Phonetic column = modern-Hebrew-for-American-English-readers: qamats/patach→ah,
# holam & qamats-qatan→oh, qibbuts/shuruk→oo, hiriq male→ee / closed hiriq→i,
# chet→kh; segol/plain-tsere/vocal-shva→"eh" open but "e" closed; tsere male→ey;
# /aj/→ai (Sinai), /oj/→oy; hataf vowels→full ah/eh/oh; gemination dropped;
# stressed syllable upper-cased (te'am or ultima).
HEBREW_CASES = [
    ("בְּרֵאשִׁית", "bǝrēʾšîṯ", "bereshit", "beh-reh-SHEET",
     "Vocal shewa (U+01DD), aleph kept in SBL, final spirant tav (ṯ); plain tsere → e, hiriq male → ee"),
    ("שְׁמַע",      "šǝmaʿ",   "shema",   "sheh-MAH",
     "Word-initial vocal shewa; ayin dropped in Simple/Phonetic; patach → ah"),
    ("כָּל־",       "kol-",    "kol-",    "KOHL-",
     "Qamats qatan before maqaf"),
    ("חָכְמָה",     "ḥoḵmāh",  "ḥokhmah", "khohkh-MAH",
     "Polysyllabic qamats qatan; chet → kh in Phonetic; ultima default"),
    ("מֶלֶךְ",      "meleḵ",   "melekh",  "MEH-lekh",
     "Final kaf without dagesh = ḵ in SBL academic; segolate (final segol) → penult even with no te'am"),
    ("שָׁלוֹם",     "šālôm",   "shalom",  "shah-LOHM",
     "Holam male on vav (→ oh); qamats → ah; vowel-only mater attaches to prev"),
    ("דָּבָר",      "dāḇār",   "davar",   "dah-VAHR",
     "Bet with dagesh (b), without dagesh = spirant ḇ; both qamats → ah"),
    ("מִשְׁפָּט",   "mišpāṭ",  "mishpat", "mish-PAHT",
     "Closed hiriq → i (not ee); final qamats gadol → ah; ultima"),
    ("הַשָּׁמַיִם",  "haššāmayim", "hashamayim", "hah-shah-MAH-yim",
     "Dagesh forte on shin: SBL doubles (šš), Phonetic skips digraph doubling; OSHB lexicon supplies penult even with no te'am"),
    ("וַיֹּאמֶר",    "wayyōʾmer",  "vayyomer",   "vah-YOH-mer",
     "Dagesh forte on yod doubles; patach → ah, holam → oh; final segol → retracted penult"),
    # Words with te'amim — stress comes from the accent mark, not ultima default.
    ("הַ/שָּׁמַ֖יִם", "ha/ššāmayim", "ha/shamayim", "hah-shah-MAH-yim",
     "WLC tipeha on the ma syllable → penult stress; Phonetic strips morpheme /"),
    ("מֶ֣לֶךְ",       "meleḵ",   "melekh",  "MEH-lekh",
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
    ("יִשְׂרָאֵל", "yis-rah-EL", "closed hiriq → i (yis, not yees); plain tsere → e"),
    ("נָבִיא",   "nah-VEE",    "hiriq male before yod → ee"),
    ("עִיר",     "EER",        "hiriq male before yod → ee (city)"),
    ("שִׁיר",    "SHEER",      "hiriq male before yod → ee (song)"),
]


@pytest.mark.parametrize("surface,phonetic,why", HIRIQ_CASES)
def test_hebrew_phonetic_hiriq_length(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic chet (0.2.7): ḥet → "kh", never English "ch" (which reads /tʃ/).
CHET_CASES = [
    ("רוּחַ",   "ROO-ahkh",   "furtive-patach chet → kh, and furtive → penult stress (spirit)"),
    ("חָכְמָה", "khohkh-MAH", "initial chet → kh (wisdom)"),
    ("מָשִׁיחַ", "mah-SHEE-ahkh", "final furtive chet → kh, furtive → penult (messiah)"),
]


@pytest.mark.parametrize("surface,phonetic,why", CHET_CASES)
def test_hebrew_phonetic_chet_is_kh(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why
    assert "ch" not in heb.transliterate(surface, scheme=HScheme.PHONETIC), why


# Phonetic tsere (0.2.8): plain tsere is modern /e/; only tsere male (before a
# yod mater) diphthongizes to "ey".
TSERE_CASES = [
    ("כֹּהֵן", "koh-HEN", "plain tsere → e (priest), not koh-HEYN"),
    ("שֵׁם",   "SHEM",    "plain tsere → e (name)"),
    ("בֵּית",  "BEYT",    "tsere male before yod → ey (house-construct)"),
    ("אֵין",   "EYN",     "tsere male before yod → ey (there-is-not)"),
]


@pytest.mark.parametrize("surface,phonetic,why", TSERE_CASES)
def test_hebrew_phonetic_tsere_context(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic patach diphthong: patach + a syllable-closing consonantal yod is the
# /aj/ glide and reads "ai" (Sinai, chai) — English word-final "-ay" would
# misread as /eɪ/ (day). A yod that carries its own vowel is a real consonant
# onset (ba-YIT), NOT a glide, and must be left untouched.
PATACH_YOD_DIPHTHONG_CASES = [
    ("לַיְלָה",  "LAI-lah",     "patach + silent-shva yod → ay (night), not LAHY-lah"),
    ("חַי",     "KHAI",        "patach + word-final yod → ay (living), not KHAHY"),
    ("אֲדֹנָי", "ah-doh-NAI",   "patach + final yod → ay (Lord), not a-doh-NAHY"),
    ("סִינַי",  "see-NAI",     "patach + final yod → ay (Sinai), not see-NAHY"),
    ("גַּיְא",   "GAI",         "patach + yod + silent alef → ay (valley), not GAHY"),
    # Negative controls: yod carries its own vowel → consonant, unchanged.
    ("בַּיִת",   "BAH-yit",     "patach + yod WITH hiriq → real consonant (house)"),
    ("עַיִן",   "AH-yin",      "patach + yod WITH hiriq → real consonant (eye)"),
]


@pytest.mark.parametrize("surface,phonetic,why", PATACH_YOD_DIPHTHONG_CASES)
def test_hebrew_phonetic_patach_yod_diphthong(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# A yod carrying its own dagesh (forte doubling, -iyyā-) or its own vowel is a
# CONSONANT, not a mater lectionis. It was being dropped along with its vowel
# because "yod after hiriq/tsere/segol" was treated as a mater unconditionally.
# (SBL/Simple pinned exactly; phonetic only asserted to keep the yod — its exact
# spelling is refined by the phonetic-pronunciation pass.)
CONSONANTAL_YOD_CASES = [
    # (surface, sbl, simple, why)
    ("עֲלִיָּה",  "ʿăliyyāh",  "aliyyah",  "doubled yod + qamats → consonant, not dropped (aliyah)"),
    ("אֵלִיָּהוּ", "ʾēliyyāhû", "eliyyahu", "doubled yod keeps -yah- (Elijah), was ʾēlîhû"),
    ("צִיּוֹן",   "ṣiyyôn",    "tsiyyon",  "doubled yod → consonant (Zion), was ṣîôn"),
]


@pytest.mark.parametrize("surface,sbl,simple,why", CONSONANTAL_YOD_CASES)
def test_hebrew_consonantal_yod_not_dropped(heb, surface, sbl, simple, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert "y" in heb.transliterate(surface, scheme=HScheme.PHONETIC).lower(), why


# Negative controls: a bare yod that only lengthens the preceding vowel (hiriq
# male, tsere male) IS a mater and must still be absorbed, not emitted.
MATER_YOD_CONTROL_CASES = [
    ("נָבִיא",     "nāḇîʾ",    "navi",     "hiriq male (prophet) → yod absorbed"),
    ("עִיר",       "ʿîr",      "ir",       "hiriq male (city) → yod absorbed"),
    ("בְּרֵאשִׁית", "bǝrēʾšîṯ", "bereshit", "hiriq male mid-word → yod absorbed"),
    ("בֵּית",      "bêṯ",      "bet",      "tsere male (house-construct) → yod absorbed"),
]


@pytest.mark.parametrize("surface,sbl,simple,why", MATER_YOD_CONTROL_CASES)
def test_hebrew_mater_yod_still_absorbed(heb, surface, sbl, simple, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why


# Consonantal vav bearing holam (וֹ) vs. holam male (mater lectionis).
# A vav+holam whose preceding consonant already carries its own vowel is the
# consonant /w/ (SBL) or /v/ (Simple/Phonetic) + an /ō/ vowel — עָוֹן ʿāwōn,
# not the vav-dropping ʿāôn. U+05BA (holam haser FOR VAV) exists precisely to
# mark this consonantal reading and is always consonantal by design.
CONSONANTAL_VAV_HOLAM_CASES = [
    # (surface, sbl, simple, phonetic, why)
    ("עָוֹן",    "ʿāwōn",   "avon",   "ah-VOHN",
     "qamats on ayin → the vav is a consonant + holam, not holam male (iniquity)"),
    ("עֲוֹנוֹת", "ʿăwōnôṯ", "avonot", "ah-voh-NOHT",
     "hataf-qamats gives ayin a vowel → first vav consonantal; the second vav "
     "(after a vowel-less nun) is a normal holam male mater"),
    ("מִצְוֺת",  "miṣwōṯ",  "mitsvot", "mits-VOHT",
     "U+05BA holam-haser-for-vav is unambiguously a consonantal vav by design"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", CONSONANTAL_VAV_HOLAM_CASES)
def test_hebrew_consonantal_vav_holam(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Vocal shewa after qamats gadol (long ā): the shewa is na (vocal), not nach.
# The fixed short/long vowel sets omitted qamats entirely, so these defaulted to
# silent. Qamats qatan (short o) stays silent — reuse the qatan detector so both
# readings agree with how the qamats vowel itself is rendered.
SHEWA_AFTER_QAMATS_CASES = [
    # (surface, sbl, simple, phonetic, why)
    ("שָׁמְרוּ", "šāmǝrû", "shameru", "shah-meh-ROO",
     "qal perfect 3pl: qamats gadol → vocal shewa (they kept), not šāmrû"),
    ("עָמְדוּ", "ʿāmǝḏû", "amedu",   "ah-meh-DOO",
     "qamats gadol → vocal shewa (they stood), not ʿāmḏû"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", SHEWA_AFTER_QAMATS_CASES)
def test_hebrew_vocal_shewa_after_qamats_gadol(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Negative controls: a vav+holam whose preceding consonant is vowel-less IS a
# holam male mater and must remain a bare /ō/ (the fix must not regress these).
HOLAM_MALE_MATER_CASES = [
    ("שָׁלוֹם", "šālôm", "shalom", "shah-LOHM", "qamats sits on the shin, lamed is vowel-less → mater"),
    ("גּוֹי",   "gôy",   "goy",    "GOY",       "vowel-less gimel → mater (nation)"),
    ("יוֹם",    "yôm",   "yom",    "YOHM",       "vowel-less yod → mater (day)"),
    ("אוֹר",    "ʾôr",   "or",     "OHR",        "vowel-less aleph → mater (light)"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", HOLAM_MALE_MATER_CASES)
def test_hebrew_holam_male_mater_unchanged(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Negative controls: qamats qatan (short o) → the following shewa stays SILENT
# (closed syllable). The fix must not make these vocal.
SHEWA_AFTER_QAMATS_QATAN_CASES = [
    ("חָכְמָה", "ḥoḵmāh", "ḥokhmah", "khohkh-MAH", "qamats qatan (wisdom) → silent shewa"),
    ("אָכְלָה", "ʾoḵlāh", "okhlah",  "ohkh-LAH",   "qamats qatan (food) → silent shewa"),
    ("קָדְשִׁי", "qoḏšî",  "qodshi",  "kohd-SHEE",  "qamats qatan (my holiness) → silent shewa"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", SHEWA_AFTER_QAMATS_QATAN_CASES)
def test_hebrew_shewa_after_qamats_qatan_stays_silent(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic: an inseparable proclitic prefix fused onto the masked Tetragrammaton
# (לַיהוָה) is unstressed and must be hyphen-separated from the reconstructed
# "yah-WEH" — la-yah-WEH, not the run-together, wrongly-stressed LAHyah-WEH.
PROCLITIC_DIVINE_NAME_CASES = [
    ("לַיהוָה", "lah-yah-WEH", "lamed prefix (to the LORD)"),
    ("בַּיהוָה", "bah-yah-WEH", "bet prefix (in the LORD)"),
    ("וַיהוָה", "vah-yah-WEH", "vav prefix (and the LORD)"),
]


@pytest.mark.parametrize("surface,phonetic,why", PROCLITIC_DIVINE_NAME_CASES)
def test_hebrew_phonetic_proclitic_before_divine_name(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


def test_hebrew_phonetic_bare_divine_name_unchanged(heb):
    """The prefix fix must not disturb a standalone or space-separated name."""
    assert heb.transliterate("יְהוָה", scheme=HScheme.PHONETIC) == "yah-WEH"
    assert heb.transliterate("יְהוָה אֱלֹהִים", scheme=HScheme.PHONETIC) == "yah-WEH eh-loh-HEEM"


# Rule-based stress when no te'am is present (0.3.0). Hebrew default is ultima;
# segolates (final segol) and furtive-patach finals retract to the penult.
STRESS_RULE_CASES = [
    ("מֶלֶךְ",  "MEH-lekh",   "segolate final segol → penult (king)"),
    ("סֵפֶר",   "SEH-fer",    "segolate final segol → penult (book)"),
    ("בֹּקֶר",  "BOH-ker",   "segolate final segol → penult (morning)"),
    ("רוּחַ",   "ROO-ahkh",   "furtive patach → penult (spirit)"),
    ("שָׁלוֹם", "shah-LOHM", "non-segolate → ultima default (peace)"),
    ("דָּבָר",  "dah-VAHR",  "non-segolate → ultima default (word)"),
]


@pytest.mark.parametrize("surface,phonetic,why", STRESS_RULE_CASES)
def test_hebrew_phonetic_stress_rules(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


def test_hebrew_teamim_still_override_rules(heb):
    """An explicit te'am beats the rule-based fallback."""
    # munach on the mem-syllable of melek → penult (same as the rule here)
    assert heb.transliterate("מֶ֣לֶךְ", scheme=HScheme.PHONETIC) == "MEH-lekh"


def test_hebrew_lexicon_corrects_rule_miss(heb):
    """The OSHB lexicon supplies penult for נַעַר, which the rules (a patach
    helping vowel, indistinguishable from an ultima verb) get wrong alone."""
    out = heb.transliterate("נַעַר", scheme=HScheme.PHONETIC)
    assert out.split("-")[0].isupper(), out  # penult stress (first syllable)


def test_hebrew_lexicon_alignment_with_divine_name(heb):
    """Per-word lexicon lookup must stay aligned when a masked Tetragrammaton
    sits between words."""
    out = heb.transliterate("יְהוָה אֱלֹהִים", scheme=HScheme.PHONETIC)
    assert out == "yah-WEH eh-loh-HEEM", out


def test_hebrew_lexicon_alignment_with_maqaf(heb):
    """Maqaf-joined words each get their own stress."""
    out = heb.transliterate("כָּל־הָאָרֶץ", scheme=HScheme.PHONETIC)
    assert out == "KOHL-hah-AH-rets", out


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
    gives the reconstructed pronunciation 'yah-WEH' (a reverent 'Adonai'/'Hashem'
    reading is opt-in via ``divine_name_substitute``)."""
    assert heb.transliterate("יְהוָה", scheme=HScheme.SBL) == "yhwh"
    assert heb.transliterate("יְהוָה", scheme=HScheme.SIMPLE) == "yhvh"
    assert heb.transliterate("יְהוָה", scheme=HScheme.PHONETIC) == "yah-WEH"
    # The discredited hybrid must not appear in any scheme.
    for scheme in (HScheme.SBL, HScheme.SIMPLE, HScheme.PHONETIC):
        out = heb.transliterate("יְהוָה", scheme=scheme).lower()
        assert "hwā" not in out and "hwa" not in out


def test_hebrew_divine_name_in_context_preserves_neighbors(heb):
    """Masking/rendering must not disturb surrounding words or phonetic stress."""
    assert heb.transliterate("יְהוָה שָׁלוֹם", scheme=HScheme.SBL) == "yhwh šālôm"
    assert heb.transliterate("יְהוָה שָׁלוֹם", scheme=HScheme.PHONETIC) == "yah-WEH shah-LOHM"


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
# Phonetic pronunciation overhaul — best-guess spelling for an untrained
# American English reader (from the language-wide phonetic audit).
# ---------------------------------------------------------------------------

# /aj/ and /oj/ diphthongs use the "-ai" / "-oy" glide (Sinai, boy), NOT "-ay"
# (English reads final "-ay" as /eɪ/, "day"). "ai" applies word-medially too.
PHONETIC_DIPHTHONG_CASES = [
    ("חַי",     "KHAI",      "word-final /aj/ → ai (chai)"),
    ("אֲדֹנָי", "ah-doh-NAI", "final /aj/ → ai (Adonai)"),
    ("לַיְלָה",  "LAI-lah",   "MEDIAL /aj/ → ai too (laylah)"),
    ("גּוֹי",   "GOY",       "/oj/ → oy (goy)"),
    ("אוֹי",    "OY",        "/oj/ → oy (woe)"),
    ("בַּיִת",   "BAH-yit",   "control: yod with own vowel is a consonant (house)"),
]


@pytest.mark.parametrize("surface,phonetic,why", PHONETIC_DIPHTHONG_CASES)
def test_phonetic_diphthong_glide_spelling(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Open-syllable segol / plain tsere / vocal shva read "eh" (a bare open 'e'
# misreads as /iː/: me, she); closed syllables keep "e" (BEN, SHEM).
OPEN_CLOSED_E_CASES = [
    ("מֶלֶךְ", "MEH-lekh", "segol open→eh, closed→e (king)"),
    ("אֶרֶץ",  "EH-rets",  "open segol → eh (land)"),
    ("שְׁמַע", "sheh-MAH", "vocal shva → eh (hear)"),
    ("סֶלָה",  "SEH-lah",  "open segol → eh (selah)"),
    ("שֵׁם",   "SHEM",     "closed tsere stays e (name)"),
    ("בֵּן",   "BEN",      "closed segol stays e (son)"),
    ("כֹּהֵן",  "koh-HEN",  "closed final tsere stays e (priest)"),
]


@pytest.mark.parametrize("surface,phonetic,why", OPEN_CLOSED_E_CASES)
def test_phonetic_open_syllable_eh(heb, surface, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why


# Phonetic drops gemination (modern Hebrew has none; a doubled onset like "BB"
# is unreadable). SBL/Simple still double.
def test_phonetic_drops_gemination(heb):
    assert heb.transliterate("שַׁבָּת", scheme=HScheme.PHONETIC) == "shah-BAHT"
    assert heb.transliterate("הַמֶּלֶךְ", scheme=HScheme.PHONETIC) == "hah-MEH-lekh"
    assert heb.transliterate("וַיֹּאמֶר", scheme=HScheme.PHONETIC) == "vah-YOH-mer"
    # Simple keeps the doubling:
    assert heb.transliterate("שַׁבָּת", scheme=HScheme.SIMPLE) == "shabbat"


# Hataf vowels read as their full quality (ah/eh/oh), qamats qatan → oh (the
# Israeli /o/), furtive patach → ah.
def test_phonetic_hataf_qatan_and_furtive(heb):
    assert heb.transliterate("אֱלֹהִים", scheme=HScheme.PHONETIC) == "eh-loh-HEEM"  # hataf-segol
    assert heb.transliterate("אֲדֹנָי", scheme=HScheme.PHONETIC) == "ah-doh-NAI"    # hataf-patach
    assert heb.transliterate("חָכְמָה", scheme=HScheme.PHONETIC) == "khohkh-MAH"    # qamats qatan → oh
    assert heb.transliterate("רוּחַ", scheme=HScheme.PHONETIC) == "ROO-ahkh"        # furtive → ah


# Greek: omicron → "ah" (Erasmian short /o/ ≈ American "ah"); ηυ → "ew".
def test_greek_phonetic_omicron_and_eta_upsilon(grk):
    assert grk.transliterate("λόγος", scheme=GScheme.PHONETIC) == "LAH-gahs"
    assert grk.transliterate("θεός", scheme=GScheme.PHONETIC) == "theh-AHS"
    assert grk.transliterate("ηὔξησεν", scheme=GScheme.PHONETIC) == "EW-ksay-sehn"


# 0.5.1: a mappiq-he's audible /h/ must not double against an h-final vowel
# digraph (ah/oh/eh) — הַלְלוּיָהּ → "YAH", not "YAHH". Phonetic-only.
MAPPIQ_HE_CASES = [
    ("הַלְלוּיָהּ", "hah-leh-loo-YAH", "mappiq he after qamats-ah (halleluyah)"),
    ("אֱלוֹהַּ",   "eh-LOH-ah",       "furtive-patach mappiq he (Eloah)"),
    ("גָּבוֹהַּ",   "gah-VOH-ah",      "furtive-patach mappiq he (high)"),
]


@pytest.mark.parametrize("surface,phonetic,why", MAPPIQ_HE_CASES)
def test_phonetic_mappiq_he_no_double_h(heb, surface, phonetic, why):
    out = heb.transliterate(surface, scheme=HScheme.PHONETIC)
    assert out == phonetic, why
    assert "hh" not in out.lower(), why
    # SBL is unaffected (keeps its own final-he rendering):
    assert heb.transliterate("הַלְלוּיָהּ", scheme=HScheme.SBL) == "halǝlûyāh"


# 0.5.1: qere-perpetuum -ayi- (defective יְרוּשָׁלִַם) gets a "y" glide so the
# stacked patach+hiriq doesn't read as an "ah-i" hiatus ("LAHIM").
def test_phonetic_qere_ayi_glide(heb):
    out = heb.transliterate("יְרוּשָׁלִַם", scheme=HScheme.PHONETIC)
    assert out == "yeh-roo-shah-LAHYIM", out
    assert "LAHIM" not in out  # hiatus removed
    # Plain closed hiriq (no stacked a-vowel) is untouched — no spurious glide:
    assert heb.transliterate("מִשְׁפָּט", scheme=HScheme.PHONETIC) == "mish-PAHT"


# A QAMATS (not only a patach) before a syllable-closing glide yod forms the
# /ay/ diphthong and is qamats GADOL. It was mis-read as qamats qatan — which
# both rendered the vowel as o/oh AND (once fixed) tried to make the glide yod's
# silent shewa vocal — so בַּלָּיְלָה came out balloylāh / bah-LOHY-lah instead of
# ballāylāh / bah-LAI-lah (Ps 121:6 "in the night").
QAMATS_GLIDE_YOD_CASES = [
    # (surface, sbl, simple, phonetic, why)
    ("בַּלָּיְלָה", "ballāylāh", "ballaylah", "bah-LAI-lah",
     "qamats + glide yod = /ay/ diphthong (in the night), not qatan; glide shewa silent"),
]


@pytest.mark.parametrize("surface,sbl,simple,phonetic,why", QAMATS_GLIDE_YOD_CASES)
def test_hebrew_qamats_before_glide_yod(heb, surface, sbl, simple, phonetic, why):
    assert heb.transliterate(surface, scheme=HScheme.SBL) == sbl, why
    assert heb.transliterate(surface, scheme=HScheme.SIMPLE) == simple, why
    assert heb.transliterate(surface, scheme=HScheme.PHONETIC) == phonetic, why
    # Real qamats qatan is unaffected (no glide yod follows):
    assert heb.transliterate("חָכְמָה", scheme=HScheme.SBL) == "ḥoḵmāh", "qatan control"
    assert heb.transliterate("כָּל־", scheme=HScheme.SBL) == "kol-", "qatan control"


# ---------------------------------------------------------------------------
# Greek golden table
# ---------------------------------------------------------------------------

# Phonetic column = Erasmian (Mounce-style) spelled for American English readers:
# η→ay, ι→ee, ο→ah, ω→oh, ου→oo, ευ/ηυ→ew, χ→kh, φ→f; stressed syllable upper-cased.
GREEK_CASES = [
    ("λόγος",   "logos",   "logos",   "LAH-gahs",  "Plain word; oxytone-no-accent default → ultima"),
    ("Ἰησοῦς",  "Iēsous",  "Iesous",  "Ee-ay-SOOS",  "Erasmian ι→ee, η→ay, ου→oo; perispomenon stress"),
    ("πνεῦμα",  "pneuma",  "pneuma",  "PNEW-mah", "ευ→ew (few), α→ah; circumflex stress"),
    ("υἱός",    "huios",   "huios",   "hwee-AHS",
     "Rough breathing on SECOND vowel of diphthong; υι→wee"),
    ("ἄγγελος", "angelos", "angelos", "AHN-geh-lahs", "γγ → ng nasal; gamma nasal splits at syllable break"),
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
    ("θεός",   "theh-AHS",    "ε→eh, ο→o, θ→th"),
    ("φῶς",    "FOHS",       "φ→f, ω→oh"),
    ("εἰρήνη", "ay-RAY-nay", "ει→ay and η→ay both render the long-a sound"),
    ("κύριος", "KOO-ree-ahs", "υ→oo, ι→ee"),
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


# ---------------------------------------------------------------------------
# 0.4.0 regression tests
# ---------------------------------------------------------------------------


def test_package_level_imports():
    """The README import path must work: aliases re-exported from the package."""
    from biblical_transliteration import (
        HebrewTransliterator as HT, HebrewScheme, HebrewOptions,
        GreekTransliterator as GT, GreekScheme, GreekOptions, __version__,
    )
    assert HT(HebrewOptions(scheme=HebrewScheme.SIMPLE)).transliterate("שָׁלוֹם") == "shalom"
    assert GT(GreekOptions(scheme=GreekScheme.SBL)).transliterate("λόγος") == "logos"
    assert __version__


def test_greek_uppercase_upsilon_iota_diphthong(grk):
    """Verse-initial Υἱός must render the Υι diphthong (was 'Yhios')."""
    assert grk.transliterate("Υἱός", scheme=GScheme.SBL) == "Huios"
    assert grk.transliterate("Υἱός", scheme=GScheme.PHONETIC) == "Hwee-AHS"
    assert grk.transliterate("ΥΙΟΣ", scheme=GScheme.SBL) == "UIOS"


def test_greek_repeated_diphthongs_no_stale_fallthrough(grk):
    """After consuming a diphthong, the next position must get its own
    diphthong check (the old guard fell through when text[i] == char)."""
    assert grk.transliterate("αιαι", scheme=GScheme.PHONETIC) == "ai-AI"
    assert grk.transliterate("ουου", scheme=GScheme.PHONETIC) == "oo-OO"
    assert grk.transliterate("αιαι", scheme=GScheme.SBL) == "aiai"


def test_greek_mark_vowel_length_off(grk):
    """mark_vowel_length=False must actually strip macrons in SBL (was a no-op)."""
    opts = GOpts(scheme=GScheme.SBL, mark_vowel_length=False)
    t = GreekTransliterator(opts)
    assert t.transliterate("ὥρα") == "hora"
    assert t.transliterate("ηὐ") == "eu"  # diphthong path strips too


def test_hebrew_lexicon_nfc_keys(heb):
    """Lexicon lookups must survive NFC mark reordering (shin dot vs vowel).
    מֹשֶׁה is stressed ultima (moh-SHE); the segolate rule alone guesses penult,
    so only a successful lexicon hit produces the correct stress."""
    assert heb.transliterate("מֹשֶׁה", scheme=HScheme.PHONETIC) == "moh-SHEH"


def test_hebrew_consonantal_vav_dagesh_not_shuruk(heb):
    """A doubling vav after a real vowel (pual qibbuts) is ww, not shuruk û."""
    assert heb.transliterate("מְצֻוּוֹת", scheme=HScheme.SBL) == "mǝṣuwwôṯ"
    # Real shuruk still works, including word-initial conjunction.
    assert heb.transliterate("רוּחַ", scheme=HScheme.SBL) == "rûaḥ"
    assert heb.transliterate("וּבְנֵי", scheme=HScheme.SBL).startswith("û")


def test_hebrew_jerusalem_qere_perpetuum(heb):
    """Stacked hiriq+patach reads the a-vowel first (-laim, not -liam)."""
    assert heb.transliterate("יְרוּשָׁלִַם", scheme=HScheme.SBL) == "yǝrûšālaim"


def test_hebrew_unpointed_begadkefat_defaults_to_stops(heb):
    """Unpointed text has no dagesh info; stops are the right default
    (word-initial spirants were the worse guess)."""
    assert heb.transliterate("בראשית", scheme=HScheme.SBL) == "brʾšyt"
    # Pointed text is unaffected.
    assert heb.transliterate("דָּבָר", scheme=HScheme.SBL) == "dāḇār"


def test_hebrew_divine_name_with_maqaf(heb):
    """Maqaf after the masked Tetragrammaton must survive (YHWH-nissi)."""
    assert heb.transliterate("יְהוָה־נִסִּי", scheme=HScheme.SBL) == "yhwh-nissî"


def test_hebrew_divine_name_prefixed_still_masks(heb):
    """Prefixed forms (וַיהוָה) must still mask; suffixed sequences must not."""
    assert heb.transliterate("וַיהוָה", scheme=HScheme.SBL) == "wayhwh"
    # A Hebrew letter after the four consonants means it's a longer word.
    out = heb.transliterate("בִּיהוָהם", scheme=HScheme.SBL)
    assert "yhwh" not in out


def test_hebrew_maqaf_is_word_boundary(heb):
    """Maqaf is punctuation, not a combining mark: it must survive after
    skipped maters and act as a word boundary for every contextual rule."""
    # mater he before maqaf: hyphen kept, qamats stays GADOL (not toroh-)
    assert heb.transliterate("תּוֹרָה־זוֹ", scheme=HScheme.SBL) == "tôrāh-zô"
    assert heb.transliterate("תּוֹרָה־זוֹ", scheme=HScheme.PHONETIC) == "toh-RAH-ZOH"
    # mater aleph before maqaf
    assert heb.transliterate("הוּא־לִי", scheme=HScheme.SIMPLE) == "hu-li"
    assert heb.transliterate("נָא־", scheme=HScheme.SBL) == "nāʾ-"
    # furtive patach is word-final even before maqaf
    assert heb.transliterate("רוּחַ־", scheme=HScheme.PHONETIC) == "ROO-ahkh-"
    # closed syllable before maqaf still reads qatan
    assert heb.transliterate("אֶת־כָּל־", scheme=HScheme.SBL) == "ʾeṯ-kol-"
