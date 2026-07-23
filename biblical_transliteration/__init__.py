"""Biblical Hebrew and Koine Greek transliteration in three schemes (SBL, Simple, Phonetic)."""

from biblical_transliteration.hebrew import (
    HebrewTransliterator,
    TransliterationOptions as HebrewOptions,
    TransliterationScheme as HebrewScheme,
)
from biblical_transliteration.greek import (
    GreekTransliterator,
    TransliterationOptions as GreekOptions,
    TransliterationScheme as GreekScheme,
)

# Single source of truth is pyproject.toml; read it from the installed
# distribution metadata so __version__ can never drift from the release
# (a hardcoded string silently stayed "0.4.0" across 0.5.x).
try:
    from importlib.metadata import version as _dist_version, PackageNotFoundError

    try:
        __version__ = _dist_version("biblical-transliteration")
    except PackageNotFoundError:  # running from a source tree without an install
        __version__ = "0.0.0+unknown"
except ImportError:  # pragma: no cover - importlib.metadata is stdlib on 3.10+
    __version__ = "0.0.0+unknown"

__all__ = [
    "HebrewTransliterator",
    "HebrewOptions",
    "HebrewScheme",
    "GreekTransliterator",
    "GreekOptions",
    "GreekScheme",
    "__version__",
]
