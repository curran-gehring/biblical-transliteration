"""Build the phonetic stress lexicon from the Open Scriptures Hebrew Bible.

The Westminster Leningrad Codex (morphhb ``wlc/*.xml``) carries cantillation
accents (te'amim), which mark the stressed syllable. For each word we:

1. transliterate it as-is — the te'am fixes the *true* stress;
2. transliterate it again with the te'amim removed — now the rule-based
   fallback (segolate / furtive / ultima) makes its *guess*;
3. if the guess differs from the truth, record a correction keyed on the word.

Only the corrections are stored, so the bundled file stays small and is, by
construction, exactly the set of words the rules get wrong. Two keys are kept:
``pointed`` (vowels, no accents — for pointed input without cantillation) and
``skeleton`` (consonants only — a most-frequent guess for unpointed input).

Stress is stored as a position counted from the end of the word
(1 = ultima, 2 = penult, …), which stays meaningful even when the runtime
syllable count differs slightly from the build-time one.

Usage:
    python tools/build_stress_lexicon.py /path/to/morphhb/wlc \
        biblical_transliteration/data/stress_lexicon.json

Source: Open Scriptures Hebrew Bible (morphhb), CC BY 4.0.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

# Allow running from a source checkout without installing.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from biblical_transliteration.hebrew import transliterate_phonetic  # noqa: E402

TAAM_LO, TAAM_HI = "֑", "֯"      # te'amim / cantillation block
CONS_LO, CONS_HI = "א", "ת"      # Hebrew consonant block
WORD_RE = re.compile(r"<w\b[^>]*>(.*?)</w>", re.S)
TAG_RE = re.compile(r"<[^>]+>")

# Pre-/post-positive accents are written on the first/last letter of the word
# regardless of which syllable is actually stressed, so accent *position* is a
# false stress signal for any word carrying one. We exclude such words from the
# ground-truth vote (the same word almost always recurs elsewhere with an
# ordinary accent, so coverage barely suffers).
POSITIONAL_ACCENTS = {
    "֒",  # segol (postpositive)
    "֘",  # zarqa / tsinnor (postpositive)
    "֙",  # pashta (postpositive)
    "֩",  # telisha qetana (postpositive)
    "֮",  # zinor (postpositive)
    "֠",  # telisha gedola (prepositive)
    "֭",  # dehi (prepositive)
}


def strip_teamim(s: str) -> str:
    return "".join(c for c in s if not (TAAM_LO <= c <= TAAM_HI))


def pointed_key(s: str) -> str:
    """Vowels + dagesh kept, accents and morpheme '/' removed."""
    return strip_teamim(s).replace("/", "")


def skeleton_key(s: str) -> str:
    return "".join(c for c in s if CONS_LO <= c <= CONS_HI)


def stress_position(phonetic: str) -> int | None:
    """Position (from the end, 1 = ultima) of the upper-cased syllable."""
    parts = phonetic.split("-")
    for i, p in enumerate(parts):
        letters = [c for c in p if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            return len(parts) - i
    return None


def iter_words(wlc_dir: str):
    for path in sorted(glob.glob(os.path.join(wlc_dir, "*.xml"))):
        data = open(path, encoding="utf-8").read()
        for raw in WORD_RE.findall(data):
            txt = TAG_RE.sub("", raw).strip()
            if txt:
                yield txt


def build(wlc_dir: str) -> dict:
    # Tally the te'am-derived stress position per key, ignoring words whose
    # accent is pre-/post-positive (its position lies about the stress).
    pointed_votes: dict[str, Counter] = defaultdict(Counter)
    skeleton_votes: dict[str, Counter] = defaultdict(Counter)
    seen = used = 0

    for word in iter_words(wlc_dir):
        seen += 1
        if any(a in word for a in POSITIONAL_ACCENTS):
            continue
        truth = stress_position(transliterate_phonetic(word))
        if truth is None:
            continue
        used += 1
        pk, sk = pointed_key(word), skeleton_key(word)
        if pk:
            pointed_votes[pk][truth] += 1
        if sk:
            skeleton_votes[sk][truth] += 1

    def mode(counter: Counter) -> int:
        return counter.most_common(1)[0][0]

    # `pointed`: store a key only when its winning stress disagrees with what the
    # rule fallback would predict — i.e. exactly the words the rules get wrong.
    pointed_out: dict[str, int] = {}
    for pk, votes in pointed_votes.items():
        truth = mode(votes)
        guess = stress_position(transliterate_phonetic(pk))
        if guess is not None and truth != guess:
            pointed_out[pk] = truth

    # `skeleton`: a best-effort guess for unpointed input. Unpointed rules always
    # yield ultima, so we keep non-ultima skeletons that win by a clear majority.
    skeleton_out: dict[str, int] = {}
    for sk, votes in skeleton_votes.items():
        total = sum(votes.values())
        win_pos, win_n = votes.most_common(1)[0]
        if win_pos != 1 and total >= 3 and win_n / total >= 0.75:
            skeleton_out[sk] = win_pos

    return {
        "_meta": {
            "source": "Open Scriptures Hebrew Bible (morphhb) WLC, CC BY 4.0",
            "words_seen": seen,
            "words_used": used,
            "pointed_corrections": len(pointed_out),
            "skeleton_entries": len(skeleton_out),
        },
        "pointed": pointed_out,
        "skeleton": skeleton_out,
    }


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    wlc_dir, out_path = sys.argv[1], sys.argv[2]
    table = build(wlc_dir)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(table, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"wrote {out_path}: {table['_meta']}")


if __name__ == "__main__":
    main()
