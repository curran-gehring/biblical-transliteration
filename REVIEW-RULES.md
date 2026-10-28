# biblical-transliteration review rules

Sent to the adversarial review lenses when a diff touches a matching path. Each rule records a defect that shipped or was caught once. Add a rule when a reviewer could have seen the defect in the diff.

## Divine name
paths: biblical_transliteration/hebrew.py tests/test_transliteration.py tests/test_divine_name_forms.py tools/build_divine_name_forms.py

- The Tetragrammaton is masked with the private-use sentinel before any transliteration, in every scheme and regardless of options. It is rendered as bare consonants (`yah-WEH` in Phonetic) or as `divine_name_substitute`, and never as the qere-vowel hybrid (`yǝhwāh`, the "Jehovah" error). A change that lets the mechanical pass see the qere vowels of יהוה reintroduces it (found by the first Codex review).
- Masking requires no Hebrew letter immediately after the name (a longer word is not the divine name) but allows prefixed forms (וַיהוָה, לַיהוָה, בַּיהוָה); a maqaf after it must survive. Do not "fix" one of these two conditions without the tests for both.
- `EXPECTED` in `tests/test_divine_name_forms.py` pins the strings FirstWord commits in `DivineNameStyle.swift`. When it fails, reconcile the app table with the new engine output; do not edit `EXPECTED` to make the test pass.

## Hebrew rules
paths: biblical_transliteration/hebrew.py biblical_transliteration/data/* tools/build_stress_lexicon.py

- Any table keyed by Hebrew text is NFC-normalized when loaded, because `transliterate()` NFC-normalizes its input and NFC reorders marks (shin dot against vowel). The stress lexicon shipped with raw source-order keys that never matched.
- Chet (ח) is `ḥ` in every scheme, Phonetic included, with `Ḥ` when stressed. `kh` belongs to soft kaf, and `ch` reads as a hard /k/. It was changed three times (`ch`, `kh`, `ḥ`); the tests assert `"ch" not in` the output.
- The maqaf is a word boundary for syllabification, stress, qamats qatan, furtive patach and the lexicon lookup. Shuruk is told apart from a consonantal vav with dagesh by whether the previous consonant in the same word carries a vowel point (`_prev_consonant_has_vowel`) (shuruk detection was a v0.4.0 fix, pinned by `test_hebrew_consonantal_vav_dagesh_not_shuruk`).
- Phonetic stress comes from te'amim first, then the OSHB lexicon, then the rule fallback. Regenerate `data/stress_lexicon.json` with `tools/build_stress_lexicon.py`; do not hand-edit it.

## Greek rules
paths: biblical_transliteration/greek.py tests/test_transliteration.py

- SBL and Simple are Koine: β is `b`, φ is `ph`, υ in a diphthong is `u`. Only PHONETIC is Erasmian (χ `kh`, φ `f`). Modern-Greek values (`v`, `f`) in the first two schemes are wrong.
- In SBL an iota subscript is a macron-only vowel (`ā ē ō`) so it cannot collide with the αι diphthong. A diaeresis breaks a diphthong, and repeated or uppercase diphthongs must not fall through to the single-letter path.
- Do not keep an option nothing reads (`show_smooth_breathing` was dead and removed after review).

## Changing output
paths: biblical_transliteration/*.py pyproject.toml

- A diff that changes any scheme's output for existing input must raise `version` in `pyproject.toml` and update the golden tests in the same change. FirstWord stores these strings in its data packs; after the Greek package was upgraded, old LXX rows kept the previous spelling (`BIB-los` beside `BEEB-lahs`) until all three columns were regenerated.
