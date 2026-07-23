"""Generate the reverent divine-name substitute transliterations.

Source of truth for the strings committed into the FirstWord app's
`DivineNameStyle` table (ios/FirstWord/FirstWord/Core/DivineNameStyle.swift).

Run: python3 -m tools.build_divine_name_forms
"""
import json

from biblical_transliteration import HebrewTransliterator, HebrewOptions, HebrewScheme

_LEMMAS = {"adonai": "אֲדֹנָי", "hashem": "הַשֵּׁם", "elohim": "אֱלֹהִים"}
_SCHEMES = {
    "sbl": HebrewScheme.SBL,
    "simple": HebrewScheme.SIMPLE,
    "phonetic": HebrewScheme.PHONETIC,
}


def generate() -> dict:
    out = {}
    for name, hebrew in _LEMMAS.items():
        out[name] = {
            key: HebrewTransliterator(HebrewOptions(scheme=scheme)).transliterate(hebrew)
            for key, scheme in _SCHEMES.items()
        }
    return out


if __name__ == "__main__":
    print(json.dumps(generate(), ensure_ascii=False, indent=2))
