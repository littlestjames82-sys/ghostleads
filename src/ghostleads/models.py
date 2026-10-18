"""Lead model, field normalisation, and dedupe keys.

Fields mirror the Sep 25, 2026 East TN prospects file. Every field
except name is optional: blank means unknown, and unknown is never
treated as a known gap or filled with a guess.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

WEBSITE_STATUSES = ("live", "dead", "template", "none", "unknown")
GOOGLE_PROFILES = ("claimed", "unclaimed", "listing-only", "none", "unknown")

_TRUE = {"true", "yes", "y", "1", "t"}
_FALSE = {"false", "no", "n", "0", "f"}


def _clean(value) -> str:
    if value is None:
        return ""
    # Collapse every whitespace run, newlines included: imported
    # fields are single-line values, and a quoted CSV newline must
    # not be able to inject lines (for example fake markdown
    # headings) into a generated pack.
    return " ".join(str(value).split())


def parse_bool(value):
    """Return True/False, or None for blank/unknown/unrecognised."""
    if isinstance(value, bool):
        return value
    s = _clean(value).lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return None


def parse_rating(value):
    """Return a float in [0, 5], None for blank. Raise ValueError if invalid."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        # JSON true/false is not a rating; float(True) would silently
        # store 1.0, an invented low rating.
        raise ValueError(f"rating is not a number: {value!r}")
    try:
        rating = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"rating is not a number: {value!r}")
    if not 0.0 <= rating <= 5.0:
        raise ValueError(f"rating out of range 0-5: {value!r}")
    return rating


def normalise_website_status(value) -> str:
    s = _clean(value).lower().replace("_", "-").replace(" ", "-")
    if not s:
        return "unknown"
    if s in ("dead", "404", "dead-404", "gone", "retired"):
        return "dead"
    if s in ("template", "business.site", "business-site", "google-site", "google-template"):
        return "template"
    if s in ("live", "real", "dedicated", "active"):
        return "live"
    if s in ("none", "no", "missing", "facebook-only", "directory-only", "directories-only"):
        return "none"
    if s == "unknown":
        return "unknown"
    raise ValueError(f"unknown website_status: {value!r} "
                     f"(expected one of {', '.join(WEBSITE_STATUSES)}, dead, or template)")


def normalise_google_profile(value) -> str:
    s = _clean(value).lower().replace("_", "-").replace(" ", "-")
    if not s:
        return "unknown"
    if s in ("listing", "listing-only", "directory", "directory-only", "directories-only",
             "google-listing", "gbp", "google-business-profile"):
        return "listing-only"
    if s in ("claimed", "verified"):
        return "claimed"
    if s in ("unclaimed", "not-claimed"):
        return "unclaimed"
    if s in ("none", "no", "missing"):
        return "none"
    if s == "unknown":
        return "unknown"
    raise ValueError(f"unknown google_profile: {value!r} "
                     f"(expected one of {', '.join(GOOGLE_PROFILES)})")


def phone_digits(value) -> str:
    digits = re.sub(r"\D", "", _clean(value))
    # Directory listings often carry the US country code: 1-865-555-0100
    # and (865) 555-0100 are the same number and must dedupe together.
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def normalise_name(value) -> str:
    s = _clean(value).lower()
    # "&" and "and" are the same word in directory variants
    # (C & C Ready Mix vs C and C Ready Mix), and an apostrophe is
    # not a letter boundary (Buck's vs Bucks).
    s = s.replace("&", " and ")
    s = re.sub(r"['\u2019`]", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(llc|inc|co|company|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Lead:
    name: str
    trade: str = ""
    town: str = ""
    phone: str = ""
    email: str = ""
    has_website: object = None  # True / False / None (unknown)
    website_status: str = "unknown"
    google_profile: str = "unknown"
    rating: object = None  # float or None
    notes: str = ""
    source: str = ""
    score: int = 0
    tier: int = 3
    reasons: list = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> "Lead":
        """Build a Lead from a CSV/JSON row. Keys are case-insensitive."""
        low = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        name = _clean(low.get("name") or low.get("business") or low.get("business_name"))
        if not name:
            raise ValueError("row has no name")
        lead = cls(
            name=name,
            trade=_clean(low.get("trade") or low.get("type") or low.get("category")),
            town=_clean(low.get("town") or low.get("city") or low.get("location")),
            phone=_clean(low.get("phone")),
            email=_clean(low.get("email")),
            has_website=parse_bool(low.get("has_website", low.get("has website"))),
            website_status=normalise_website_status(low.get("website_status", "")),
            google_profile=normalise_google_profile(low.get("google_profile", "")),
            rating=parse_rating(low.get("rating")),
            notes=_clean(low.get("notes") or low.get("angle")),
            source=_clean(low.get("source")),
        )
        # Consistency: explicit has_website False + unknown status is
        # scored as status none only via has_website; do not invent a
        # status. True + unknown stays unknown.
        return lead

    def dedupe_key(self) -> tuple:
        name = normalise_name(self.name)
        digits = phone_digits(self.phone)
        if digits:
            return (name, digits)
        return (name, _clean(self.town).lower())

    def fill_blanks_from(self, other: "Lead") -> bool:
        """Fill blank/unknown fields from other. Never overwrite a
        known non-blank value. Returns True if anything changed."""
        changed = False
        for attr in ("trade", "town", "phone", "email", "notes", "source"):
            if not getattr(self, attr) and getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
                changed = True
        if self.has_website is None and other.has_website is not None:
            self.has_website = other.has_website
            changed = True
        if self.website_status == "unknown" and other.website_status != "unknown":
            self.website_status = other.website_status
            changed = True
        if self.google_profile == "unknown" and other.google_profile != "unknown":
            self.google_profile = other.google_profile
            changed = True
        if self.rating is None and other.rating is not None:
            self.rating = other.rating
            changed = True
        return changed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Lead":
        """Rebuild a Lead from a stored record, with validation.

        The store is a plain JSON file a human can hand-edit, so its
        values get the same checks as an import row. A bad stored
        value raises ValueError here (the CLI reports it as a clean
        cannot-read-store error) instead of crashing later inside
        scoring or pack generation."""
        if not isinstance(data, dict):
            raise ValueError("stored lead is not an object")
        known = {f for f in cls.__dataclass_fields__}
        out = {k: v for k, v in data.items() if k in known}
        name = _clean(out.get("name"))
        if not name:
            raise ValueError("stored lead has no name")
        out["name"] = name
        for attr in ("trade", "town", "phone", "email", "notes", "source"):
            if attr in out:
                out[attr] = _clean(out[attr])
        if "has_website" in out and out["has_website"] is not None \
                and not isinstance(out["has_website"], bool):
            out["has_website"] = parse_bool(out["has_website"])
        if "website_status" in out:
            out["website_status"] = normalise_website_status(out["website_status"])
        if "google_profile" in out:
            out["google_profile"] = normalise_google_profile(out["google_profile"])
        if "rating" in out:
            out["rating"] = parse_rating(out["rating"])
        for attr in ("score", "tier"):
            if attr in out:
                try:
                    out[attr] = int(out[attr])
                except (TypeError, ValueError):
                    out[attr] = 0 if attr == "score" else 3
        if "reasons" in out and not isinstance(out["reasons"], list):
            out["reasons"] = []
        return cls(**out)
