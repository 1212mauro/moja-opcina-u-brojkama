"""Text helpers for Croatian names."""

import re
import unicodedata

# NFKD decomposes č, ć, š, ž into base letter + accent, but đ has no decomposition.
_EXTRA_FOLD = str.maketrans({"đ": "d", "Đ": "D"})


def ascii_fold(text: str) -> str:
    """Lower-case and strip diacritics: "Čakovec" -> "cakovec", "Đurđevac" -> "durdevac"."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_EXTRA_FOLD))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def slugify(text: str) -> str:
    """URL slug: "Breznički Hum" -> "breznicki-hum"."""
    return re.sub(r"[^a-z0-9]+", "-", ascii_fold(text)).strip("-")


def name_key(text: str) -> str:
    """Key for matching one place across sources that differ in case, spacing, diacritics."""
    return " ".join(ascii_fold(text).split())
