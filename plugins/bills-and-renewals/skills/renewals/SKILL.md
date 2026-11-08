---
name: renewals
description: Track bills, subscriptions, insurance and document expiry dates privately on this computer, show what is due or overdue, record payments, total recurring spending, and export calendar reminders. Use when the user says "what bills are due", "remind me to renew", "add my Netflix subscription", "I paid the electricity bill", "when does my passport expire", "how much do my subscriptions cost", or asks to track any due date.
argument-hint: "due | add <what and when> | paid <what> | summary | calendar"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/renewals.py *)
---

# Bills and renewals

Everything is stored in one local file, `~/.bills-and-renewals/items.json`. Run every command through:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/renewals.py" <command>
```

## Safety rules

- Never store card numbers, bank account numbers, CVVs, passwords, passport numbers or government ID numbers, even if the user offers them. At most keep the last 4 digits in `--note`. The script refuses long digit runs.
- `remove` cannot be undone. State which item will be deleted and get a yes first.
- Never pay a bill, open a payment page or contact a provider. This skill only tracks.

## Adding an item

Turn the user's words into exact arguments. Resolve "next Friday" or "the 5th" to a `YYYY-MM-DD` date from today's date. If the due date is missing, ask for it; do not guess. Ask about the amount only when it matters to the request.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/renewals.py" add "Netflix" --due 2026-11-20 --kind subscription --repeat monthly --amount 649 --currency INR
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/renewals.py" add "Passport" --due 2029-03-14 --kind document --remind 180
```

- `--kind`: `bill`, `subscription`, `insurance`, `document`, `other`
- `--repeat`: `none`, `weekly`, `monthly`, `quarterly`, `yearly`
- `--remind`: days of warning. Defaults: 3 for bills and subscriptions, 30 for insurance, 60 for documents, 7 otherwise. Many countries need 6 months of passport validity to travel, so suggest `--remind 180` for passports.

Use the same `--due` day the provider uses. An item due on the 31st falls on the last day of shorter months and returns to the 31st afterwards.

## Everyday commands

| The user wants | Command |
|---|---|
| What needs attention | `due` |
| Everything due within N days | `due --within N` |
| All tracked items | `list` (`--all` includes finished ones) |
| Record a payment or renewal | `paid ID` (`--on DATE`, `--amount N` if it differed) |
| Change a price or date | `edit ID --amount N` or `edit ID --due DATE` |
| Delete an item | `remove ID` (confirm first) |
| Spending totals | `summary` |
| Calendar reminders | `export-ics --out ~/bills-and-renewals.ics` |

Add `--json` to `list`, `due` or `summary` when you need to read the results precisely, for example to match "the electricity bill" to its id. If two items could match, ask which one.

`paid` moves a repeating item forward one cycle from its due date, so a late payment keeps the schedule. If the next date is still overdue, say so: another cycle is unpaid. To correct a mistaken `paid`, use `edit ID --due <the original date>`.

## Presenting results

Lead with anything overdue, then due today, then upcoming. Give the date and amount for each, and keep it short. Totals are grouped by currency and are never converted.

This plugin does not send notifications itself. When the user wants real alerts on their phone or computer, run `export-ics` and tell them to open the file to import it into their calendar, and to export again after adding or changing items. Importing again may create duplicates in some calendar apps, so suggest importing into a dedicated calendar they can replace.
