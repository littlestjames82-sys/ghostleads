"""GhostLeads CLI.

  ghostleads import <file.csv|file.json> [--store leads.json]
  ghostleads score [--store leads.json] [--json]
  ghostleads list [--store leads.json] [--tier N] [--town X]
                  [--trade Y] [--min-score N] [--json]
  ghostleads pack [--store leads.json] [--out packs/]
                  [--lead NAME] [--all]

Exit codes: 0 = ok, 1 = no leads matched, 2 = could not run
(missing store, unreadable import file, invalid data).

Fully offline. There is no send command by design: drafts only,
sending stays Ryan's manual gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .packs import slugify, write_packs
from .scoring import score_lead
from .store import import_file, load_store, save_store

DEFAULT_STORE = "leads.json"


def _require_store(args) -> list:
    if not Path(args.store).exists():
        print(f"error: store not found: {args.store} (run ghostleads import first)",
              file=sys.stderr)
        return None
    try:
        return load_store(args.store)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read store {args.store}: {exc}", file=sys.stderr)
        return None


def _ranked(leads) -> list:
    return sorted(leads, key=lambda l: (-l.score, l.name.lower()))


def _print_table(leads) -> None:
    print(f"{'Score':>5}  {'Tier':>4}  {'Name':<38} {'Trade':<22} {'Town':<16} Phone")
    for lead in leads:
        print(f"{lead.score:>5}  {lead.tier:>4}  {lead.name[:38]:<38} "
              f"{lead.trade[:22]:<22} {lead.town[:16]:<16} {lead.phone}")


def _cmd_import(args) -> int:
    try:
        report = import_file(args.store, args.file)
    except (OSError, ValueError) as exc:
        print(f"error: import failed: {exc}", file=sys.stderr)
        return 2
    print(f"imported rows: {report['imported_rows']}")
    print(f"added: {report['added']}  merged (duplicates): {report['merged']}  "
          f"total in store: {report['total']}")
    for skip in report["skipped"]:
        print(f"  skipped {skip['where']}: {skip['why']}")
    return 0


def _cmd_score(args) -> int:
    leads = _require_store(args)
    if leads is None:
        return 2
    for lead in leads:
        score_lead(lead)
    leads = _ranked(leads)
    save_store(args.store, leads)
    if args.json:
        print(json.dumps([l.to_dict() for l in leads], indent=2))
    else:
        _print_table(leads)
    return 0 if leads else 1


def _cmd_list(args) -> int:
    leads = _require_store(args)
    if leads is None:
        return 2
    out = _ranked(leads)
    if args.tier is not None:
        out = [l for l in out if l.tier == args.tier]
    if args.town:
        out = [l for l in out if l.town.lower() == args.town.lower()]
    if args.trade:
        out = [l for l in out if l.trade.lower() == args.trade.lower()]
    if args.min_score is not None:
        out = [l for l in out if l.score >= args.min_score]
    if args.json:
        print(json.dumps([l.to_dict() for l in out], indent=2))
    else:
        _print_table(out)
    return 0 if out else 1


def _cmd_pack(args) -> int:
    leads = _require_store(args)
    if leads is None:
        return 2
    ranked = _ranked(leads)
    if args.all:
        selected = ranked
    elif args.lead:
        wanted = args.lead.lower()
        selected = [l for l in ranked
                    if l.name.lower() == wanted or slugify(l.name) == slugify(args.lead)]
        if not selected:
            print(f"error: no lead matches --lead {args.lead!r}", file=sys.stderr)
            return 1
    else:
        selected = ranked[:1]
    if not selected:
        print("error: store is empty, nothing to pack", file=sys.stderr)
        return 1
    written = write_packs(selected, args.out)
    for path in written:
        print(f"pack: {path}")
    print("DRAFT ONLY. Not sent. Sending is Ryan's manual step.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ghostleads",
        description="Offline lead manager and scorer. Import, score, list, draft. No scraping, no sending.")
    parser.add_argument("--version", action="version", version=f"ghostleads {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import", help="import a local CSV or JSON lead list into the store")
    p.add_argument("file")
    p.add_argument("--store", default=DEFAULT_STORE)

    p = sub.add_parser("score", help="recompute scores and tiers, print a ranked table")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("list", help="list leads ranked by score, with filters")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.add_argument("--tier", type=int, choices=[1, 2, 3])
    p.add_argument("--town")
    p.add_argument("--trade")
    p.add_argument("--min-score", type=int)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("pack", help="generate draft pitch pack markdown (never sends)")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.add_argument("--out", default="packs")
    p.add_argument("--lead", help="pack only this lead (name or slug)")
    p.add_argument("--all", action="store_true", help="pack every lead")

    args = parser.parse_args(argv)
    if args.command == "import":
        return _cmd_import(args)
    if args.command == "score":
        return _cmd_score(args)
    if args.command == "list":
        return _cmd_list(args)
    if args.command == "pack":
        return _cmd_pack(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
