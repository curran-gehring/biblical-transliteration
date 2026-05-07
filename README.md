# biblical-transliteration

[![PyPI](https://img.shields.io/pypi/v/biblical-transliteration.svg)](https://pypi.org/project/biblical-transliteration/)
[![tests](https://github.com/curran-gehring/biblical-transliteration/actions/workflows/test.yml/badge.svg)](https://github.com/curran-gehring/biblical-transliteration/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/curran-gehring/biblical-transliteration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Biblical Hebrew and Koine Greek transliteration in three schemes — academic
([SBL](https://www.sbl-site.org/assets/pdfs/SBLHSrevised2_09.pdf)), simple
ASCII, and phonetic. Pure Python, no dependencies.

```python
from biblical_transliteration import (
    HebrewTransliterator, HebrewScheme, HebrewOptions,
    GreekTransliterator, GreekScheme, GreekOptions,
)

heb = HebrewTransliterator(HebrewOptions(scheme=HebrewScheme.SBL))
heb.transliterate("בְּרֵאשִׁית")
# 'bǝrēʾšîṯ'

grk = GreekTransliterator(GreekOptions(scheme=GreekScheme.SBL))
grk.transliterate("Ἐν ἀρχῇ ἦν ὁ λόγος")
# 'En archē ēn ho logos'
```

## Install

```bash
pip install biblical-transliteration
```

Requires Python 3.10+. Zero runtime dependencies.

## Schemes

Each transliterator supports three output styles via `TransliterationScheme`:

| Scheme | Hebrew (`שָׁלוֹם`) | Greek (`λόγος`) | Use when |
| --- | --- | --- | --- |
| `SBL` | `šālôm` | `logos` | Academic writing, scholarly publications, lexicon entries. Full SBL Handbook of Style diacritics. |
| `SIMPLE` | `shalom` | `logos` | Reader-friendly Latin, no diacritics. Good for UI labels and casual contexts. |
| `PHONETIC` | `sha-LOM` | `LO-gos` | Pronunciation cues with syllable boundaries and stress (capitalized syllable). For learners and audio-aligned uses. |

## What this handles

**Hebrew** (~1,000 lines of rules):

- Full nikkud (vowel point) coverage, including hataf vowels
- BeGaD KeFaT spirantization with proper SBL macron-under marks
  (`ḇ ḡ ḏ ḵ p̄ ṯ`)
- Vocal vs silent shewa distinction
- Qamats qatan (`o`) vs qamats gadol (`a`) detection
- Dagesh forte vs lene
- Shin/sin dot disambiguation
- Final letter forms (ך ם ן ף ץ)
- Optional cantillation marks
- Maqaf, meteg, sof pasuq

**Koine Greek** (~800 lines of rules):

- Diphthongs in canonical order (αι, ει, οι, υι, αυ, ευ, ηυ, ου)
- Breathing marks read off either vowel of a diphthong
- Iota subscript (η̄ in SBL, dropped elsewhere)
- Final sigma (ς)
- Koine-correct phonemes — β = `b` (not modern `v`),
  φ = `ph` (not modern `f`), υ = `u` in diphthongs
- Eta/omega macron distinction in SBL
- Accents and breathing marks normalized

## Why three schemes?

Open-source transliterators tend to pick one and stick with it, which forces
you to choose between accuracy (SBL is hard to read for non-specialists) and
readability (loose ASCII loses important phonemic distinctions). Three
schemes lets you produce SBL-compliant output for academic work, ASCII for
UI labels, and pronunciation cues for learners — from the same source text.

## Why a separate Hebrew + Greek package?

Most existing PyPI packages are language-specific and use inconsistent APIs.
This package presents a single mental model — `Transliterator(Options(scheme=...))`
— that works identically across both languages, so consumer code that
transliterates whatever script it encounters stays clean.

## Comparison with related packages

This package fills a specific gap in the Python biblical-NLP ecosystem.
Other tools cover adjacent problems well; here's what they do differently
so you can pick the right one:

| Package | Scope | Notes |
| --- | --- | --- |
| **biblical-transliteration** *(this)* | Hebrew + Koine Greek, three schemes (SBL/Simple/Phonetic) | Designed for biblical use specifically. Koine-correct phonemes for Greek; full nikkud + begadkefat + qamats qatan handling for Hebrew. Single consistent API across both languages. |
| [`transliterate`](https://pypi.org/project/transliterate/) | 9 languages including (Modern/Classical) Greek; no Hebrew | Excellent general-purpose romanizer for European/Caucasian scripts. Greek pack is calibrated for Modern Greek phonology, not Koine — β→v, φ→f, eta and epsilon collapsed. Use this if you need Russian/Armenian/Georgian/Bulgarian etc. alongside Greek. |
| [`beta-code`](https://pypi.org/project/beta-code/) | Greek only | Solves a different problem: BETA encoding ↔ Greek Unicode (e.g. `mh=nin` ↔ `μῆνιν`). Pair it with this package when working with CCAT/TLG sources — first beta→Unicode with `beta-code`, then Unicode→Latin with this. |
| Hebrew transliteration on PyPI | — | As of 2026, there is no actively maintained Biblical Hebrew transliterator on PyPI. This package fills that gap. |

If your workflow needs SBL Handbook of Style-compliant academic
transliteration with proper diacritics for both Hebrew (`bǝrēʾšîṯ`,
`šālôm`) and Greek (`logos`, `Iēsous`), this package is the only option in
the Python ecosystem at the time of writing.

## Limitations

- **Hebrew text must be Unicode** (with or without nikkud). Beta-coded
  Hebrew (CCAT/Michigan-Claremont format) is not handled by this library —
  use a beta→Unicode converter first.
- **Greek text is assumed Koine.** Modern Greek and Classical Greek work
  with the `SBL` and `SIMPLE` schemes, but `PHONETIC` is calibrated for
  Koine and may not match what you expect for Classical or Modern texts.
- **Qamats qatan detection is rule-based**, not perfect. Texts with
  explicit U+05C7 marking (modern WLC) work reliably; older texts using
  the ambiguous U+05B8 may occasionally guess wrong.

## Examples

```python
from biblical_transliteration import HebrewTransliterator, HebrewOptions, HebrewScheme

# All three schemes for the same word
word = "שָׁלוֹם"
for scheme in HebrewScheme:
    t = HebrewTransliterator(HebrewOptions(scheme=scheme))
    print(f"{scheme.value:10} {t.transliterate(word)}")
# sbl        šālôm
# simple     shalom
# phonetic   sha-LOM
```

```python
from biblical_transliteration import GreekTransliterator, GreekOptions, GreekScheme

# John 1:1
text = "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος."
for scheme in GreekScheme:
    t = GreekTransliterator(GreekOptions(scheme=scheme))
    print(f"{scheme.value:10} {t.transliterate(text)}")
```

## Development

```bash
git clone https://github.com/curran-gehring/biblical-transliteration.git
cd biblical-transliteration
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Transliteration rules were developed against the
[Society of Biblical Literature Handbook of Style (2nd ed., 2014)](https://www.sbl-site.org/assets/pdfs/SBLHSrevised2_09.pdf)
and validated against verses from the
[CATSS](https://github.com/curran-gehring/catss) parallel corpus.
