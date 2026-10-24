"""Name folding: the one rule used for matching, in the data builder and at runtime."""
from __future__ import annotations

import unicodedata


def fold(name: str) -> str:
    """Casefold, NFKC-normalise and drop everything that is not a letter or digit.

    'APT 29', 'apt-29' and 'APT29' all fold to 'apt29'; 'Cozy-Bear' to 'cozybear'.
    """
    text = unicodedata.normalize("NFKC", name or "").casefold()
    return "".join(ch for ch in text if ch.isalnum())
