"""Local JSON store plus CSV/JSON import with dedupe.

The store is a single local file. No network is used anywhere in
this package: import reads only the file the user names.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Lead, normalise_name, phone_digits
from .scoring import score_lead

STORE_VERSION = 1


def load_store(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rows = data.get("leads", [])
    else:
        rows = data
    return [Lead.from_dict(r) for r in rows]


def save_store(path, leads) -> None:
    p = Path(path)
    if p.parent and str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": STORE_VERSION, "tool": "ghostleads",
               "leads": [lead.to_dict() for lead in leads]}
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_import_file(path) -> list:
    """Return a list of raw row dicts from a .csv or .json file."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        # utf-8-sig, same as the CSV reader: a BOM saved by a
        # spreadsheet or editor must not fail the whole import.
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data = data.get("leads", [])
        if not isinstance(data, list):
            raise ValueError("JSON import must be a list, or an object with a leads list")
        return data
    if suffix == ".csv":
        with p.open(newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"unsupported import format {suffix!r}: use .csv or .json")


def same_lead(a, b) -> bool:
    """Dedupe predicate: are these two records the same business?

    Same normalised name, AND either:
    - both records carry a phone and the digits match, or
    - at least one record has no phone and the towns match.

    The old key-based version required a phone on BOTH records to
    use the phone branch, so a lead first imported phone-only and
    later re-imported with a phone (the common directory pattern)
    never merged and silently duplicated."""
    if not normalise_name(a.name) or \
            normalise_name(a.name) != normalise_name(b.name):
        return False
    digits_a = phone_digits(a.phone)
    digits_b = phone_digits(b.phone)
    if digits_a and digits_b:
        return digits_a == digits_b
    town_a = " ".join(str(a.town or "").lower().split())
    town_b = " ".join(str(b.town or "").lower().split())
    if digits_a or digits_b:
        # Exactly one record has a phone: the town has to match and
        # be known, or there is no evidence these are the same lead.
        return bool(town_a) and town_a == town_b
    # Neither record has a phone: towns must match, with two blank
    # towns counting as a match. A sparse lead (no phone, no town)
    # re-imported unchanged must not duplicate itself.
    return town_a == town_b


def merge_leads(existing: list, incoming: list) -> dict:
    """Merge incoming leads into existing (mutated), matched with
    same_lead in store order. First record wins; later records fill
    blanks only. Returns counts: added, merged, total."""
    added = 0
    merged = 0
    for lead in incoming:
        match = None
        for candidate in existing:
            if same_lead(candidate, lead):
                match = candidate
                break
        if match is not None:
            match.fill_blanks_from(lead)
            merged += 1
        else:
            existing.append(lead)
            added += 1
    return {"added": added, "merged": merged, "total": len(existing)}


def import_file(store_path, import_path) -> dict:
    """Import a CSV/JSON file into the store. Returns a report dict
    with added / merged / skipped (each skip has where + why)."""
    rows = read_import_file(import_path)
    leads = load_store(store_path)
    incoming = []
    skipped = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            skipped.append({"where": f"row {idx + 1}", "why": "not an object"})
            continue
        try:
            incoming.append(Lead.from_row(row))
        except ValueError as exc:
            skipped.append({"where": f"row {idx + 1}", "why": str(exc)})
    counts = merge_leads(leads, incoming)
    for lead in leads:
        score_lead(lead)
    leads.sort(key=lambda l: (-l.score, l.name.lower()))
    save_store(store_path, leads)
    return {**counts, "skipped": skipped, "imported_rows": len(rows)}
