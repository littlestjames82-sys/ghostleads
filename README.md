# GhostLeads

**Score the local business leads you already found, and draft a pitch pack for the best ones. All on your own computer.**

GhostLeads is a studio-internal tool for Ghost Developer Studio. It takes a list of businesses you researched yourself, in a CSV or JSON file, scores each one for a website outreach angle, removes duplicates, and writes a draft pitch pack you can check before you decide whether to contact anyone.

It does not find businesses. It does not contact businesses. Finding leads is your research. Sending anything is your manual step, outside this tool.

By Ghost Developer Studio. GhostLeads is the business-side companion in the GhostSlice suite: the other tools govern what an agent reads and does, this one governs your own outreach pipeline.

## What GhostLeads does not do

- It does not scrape, search, crawl, or look anything up. There is no network use of any kind.
- It does not send email, texts, messages, or forms. There is no send command.
- It does not find phone numbers, emails, or any other detail that is not already in your file.
- It does not invent business details. If a field is blank in your file, it stays blank in the score and in the pack. Unknown is never treated as a gap.
- It does not judge a business. A low score only means a weak website angle from the fields you supplied, nothing more.

## Input format

A CSV file with a header row, or a JSON file holding a list (or an object with a `leads` list). Only `name` is required.

| Field | Values | Notes |
|---|---|---|
| name | text | Required. Rows with no name are skipped and reported. |
| trade | text | Blank if unknown. |
| town | text | Blank if unknown. |
| phone | text | Blank if unknown. Example files use fictional 555 numbers. |
| email | text | Blank if unknown. Most leads are phone only, and email is never required. |
| has_website | true/false, yes/no, 1/0, blank | Blank means unknown, and unknown scores zero. It is not treated as no website. |
| website_status | live, dead, template, none, unknown | `404` is read as dead. `business.site` is read as template. |
| google_profile | claimed, unclaimed, listing-only, none, unknown | Blank or unknown scores zero. |
| rating | 0 to 5, or blank | Out of range values are rejected on import, never quietly fixed. |
| notes | text | Your own notes, kept with the record. |
| source | text | Where the lead came from, shown in the pack so you can re-verify it. |

The store is one local JSON file. You choose its path with `--store`. It is the only state the tool keeps.

## The four commands

You need Python 3.10 or newer. From the GhostLeads folder:

```bash
# 1. Import a file you researched into the local store
PYTHONPATH=src python3 -m ghostleads import examples/sample_leads.csv --store leads.json

# 2. Score every lead and print the ranked table
PYTHONPATH=src python3 -m ghostleads score --store leads.json

# 3. List leads, with filters if you want them
PYTHONPATH=src python3 -m ghostleads list --store leads.json --tier 1
PYTHONPATH=src python3 -m ghostleads list --store leads.json --town Exampleton --json

# 4. Draft a pitch pack
PYTHONPATH=src python3 -m ghostleads pack --store leads.json --out packs/
PYTHONPATH=src python3 -m ghostleads pack --store leads.json --out packs/ --all
```

With no selector, `pack` drafts only the single highest scoring lead, so a stray run never floods your disk. Add `--all`, or `--lead NAME` for one named lead.

A worked run is in `examples/WALKTHROUGH.md`. The sample files use clearly fictional businesses, fictional 555 phone numbers, and `.example` addresses, so you can try every command safely.

## How scoring works

Scoring is additive, capped at 100, and every point carries a reason that is shown in the output and in the pack. It is never just a number.

| Signal | Points |
|---|---|
| No dedicated website | +30 |
| Website status: dead | +20 |
| Website status: template only | +15 |
| Website status: none | +10 |
| Google profile: unclaimed | +20 |
| Google profile: none | +15 |
| Google profile: listing only | +10 |
| Rating below 3.8 (reputation angle) | +10 |
| Rating 4.5 or above (strong reviews to showcase) | +8 |
| Rating 3.8 to 4.49 | +3 |
| Phone on file | +5 |
| Email on file | +5 |

Tiers: 60 and above is Tier 1, 40 to 59 is Tier 2, below 40 is Tier 3.

Rating cuts both ways and the reason says which: a low rating is a reputation rebuild angle, a high rating is proof worth showcasing on a real site. A lead with a live website, a claimed profile, and a middle rating scores low, and a lead with everything unknown scores zero. That honesty is the point.

## Duplicates

Import dedupes against the store and inside the file. Two rows are the same lead when the normalised name matches (an `&` reads as "and", and apostrophes are ignored, so directory spelling variants line up) and either the phone digits match, or the towns match and at least one of the two rows has no phone to compare. Phone digits ignore formatting and a leading US country code `1`, so `1-423-555-0100` and `(423) 555-0100` are the same number. Two rows with different phones on file never merge: they may be two branches, or one business with an old and a new number, and only a human can tell which.

The first record wins. A later duplicate can only fill in fields that are blank in the first record. It can never overwrite a different value you already had. Import prints how many leads were imported, merged, and skipped, so you can spot a merge that looks wrong.

## What is in a pack

One Markdown file per lead, named from the business name:

- Lead snapshot: name, trade, town, phone, and email, exactly as stored. Unknown fields are blank, never filled in. If two stored fields contradict each other (for example, no website, but the website status says live), the snapshot flags the conflict instead of picking a side.
- Score snapshot: score, tier, and every score reason, plus the import source so you can re-verify the lead.
- Suggested angle: sentences built only from the score reasons. No reason, no angle.
- Draft pitch: a short outreach draft using only known fields. It offers a free custom website concept, names Ghost Developer Studio and Ryan Cotten, and gives the studio public contact phone (423) 408-2150 as the studio contact only. It is never presented as the lead's phone.
- Verification checklist: re-check the business is still operating, the website status is still accurate, and the phone still matches, before any manual send.
- A closing line on every pack: DRAFT ONLY. Not sent. Sending is Ryan's manual step.

Copy rules are enforced in code: no em dash character appears in a generated pack, and no business detail appears in a pack unless it is in the stored record.

## Two things to know before you trust it

**Imported data goes stale fast.** A business can close, get a website, or change its phone after you researched it. GhostLeads scores the data it was given. That is why every pack carries a re-verify warning and a checklist. Verify first, every time.

**A score is a ranking aid, not a verdict.** Use it to decide who to look at next, then use your own judgement.

## Your responsibility

Only import businesses and contact details you gathered yourself through legitimate research, and handle them under the rules that apply to you. The store is a local file. This tool never uploads it.

## Status

Version 0.1. Local CLI only, Python standard library only, no accounts, no cloud, no telemetry. Pricing and any public release are not decided. Nothing about this tool is announced or published by building it.
