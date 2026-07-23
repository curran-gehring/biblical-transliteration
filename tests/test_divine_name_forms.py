from tools.build_divine_name_forms import generate

# Pins the engine output consumed by the FirstWord app's DivineNameStyle table.
# If this fails, the engine's romanization changed — reconcile the app's
# committed table (Core/DivineNameStyle.swift) with the new values; do not
# blindly edit EXPECTED to match.
EXPECTED = {
    "adonai": {"sbl": "ʾăḏōnāy", "simple": "adonay", "phonetic": "ah-doh-NAI"},
    "hashem": {"sbl": "haššēm", "simple": "hashem", "phonetic": "hah-SHEM"},
    "elohim": {"sbl": "ʾĕlōhîm", "simple": "elohim", "phonetic": "eh-loh-HEEM"},
}


def test_generate_matches_expected_forms():
    assert generate() == EXPECTED
