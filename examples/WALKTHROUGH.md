# GhostLeads walkthrough

A full run on the fictional sample file. Every business here is made up, every phone number is a fictional 555 number, and every email ends in `.example`. Nothing in this walkthrough is a real lead, and nothing is sent anywhere.

Run from the GhostLeads folder.

## 1. Import

```bash
PYTHONPATH=src python3 -m ghostleads import examples/sample_leads.csv --store /tmp/ghostleads-demo.json
```

Expected shape: the command reports how many leads were imported, how many were merged as duplicates, and how many rows were skipped. The sample file has 5 clean rows, so expect 5 imported, 0 merged, 0 skipped.

## 2. Score

```bash
PYTHONPATH=src python3 -m ghostleads score --store /tmp/ghostleads-demo.json
PYTHONPATH=src python3 -m ghostleads score --store /tmp/ghostleads-demo.json --json
```

Expected ranking, from the scoring table in the README:

| Lead | Math | Score | Tier |
|---|---|---|---|
| Hilltop Quarry Hauling | 30 no website + 20 dead + 20 unclaimed + 10 rating 3.7 + 5 phone | 85 | Tier 1 |
| Cedar Sign Works | 30 + 15 template + 10 listing only + 8 rating 4.8 + 5 phone | 68 | Tier 1 |
| Riverbend Fictional HVAC | 30 + 10 none + 0 claimed + 3 rating 4.0 + 5 phone | 48 | Tier 2 |
| Maple Street Corner Bakery | 0 live + 0 claimed + 3 rating 4.2 + 5 phone + 5 email | 13 | Tier 3 |
| Mystery Works | every optional field unknown | 0 | Tier 3 |

Mystery Works is the honesty check: it has no website field at all, so it earns no no-website points. Unknown scores zero.

## 3. List with a filter

```bash
PYTHONPATH=src python3 -m ghostleads list --store /tmp/ghostleads-demo.json --tier 1
PYTHONPATH=src python3 -m ghostleads list --store /tmp/ghostleads-demo.json --town exampleton --json
```

The tier filter should return only Hilltop Quarry Hauling and Cedar Sign Works. The town filter is case-insensitive, so `exampleton` should return the same two leads.

## 4. Draft packs

```bash
PYTHONPATH=src python3 -m ghostleads pack --store /tmp/ghostleads-demo.json --out /tmp/ghostleads-packs/
PYTHONPATH=src python3 -m ghostleads pack --store /tmp/ghostleads-demo.json --out /tmp/ghostleads-packs/ --all
```

The first command drafts exactly one pack, for Hilltop Quarry Hauling, the highest scoring lead. The second drafts all five.

Open the Mystery Works pack and check the honesty rules yourself:

- Trade, town, phone, email, and rating are blank, not filled in.
- There is no suggested angle about a dead site, an unclaimed profile, or a rating, because none of that is known.
- There is no price, no web address, and no phone number other than the studio contact (423) 408-2150, shown as the studio contact only.
- The pack ends with the draft line: DRAFT ONLY. Not sent.

## 5. Duplicates, if you want to see them

Import the same file a second time into the same store. Every row should merge instead of duplicating, and the lead count should stay at 5.
