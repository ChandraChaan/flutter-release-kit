# Bills and Renewals

**A Claude Code plugin that keeps track of what is due, without sending your data anywhere.**

Tell Claude things in plain words:

- "Add my Netflix, 649 rupees, renews on the 20th every month"
- "My passport expires on 14 March 2029"
- "What's due this week?"
- "I paid the electricity bill"
- "How much do my subscriptions cost per year?"
- "Put these in my calendar"

## Install

Inside Claude Code:

```
/plugin marketplace add ChandraChaan/flutter-release-kit
/plugin install bills-and-renewals@chandrachaan-plugins
```

Python 3 is the only requirement.

## What it does

- Tracks bills, subscriptions, insurance, documents and anything else with a date.
- Repeats weekly, monthly, quarterly or yearly. A date on the 31st uses the last day of shorter months, then returns to the 31st.
- Gives each kind a sensible warning period, which you can change per item.
- Totals recurring costs per currency, without converting between them.
- Exports an `.ics` file with alarms, so your own calendar delivers the reminders.

## Privacy

Your list is one JSON file on your computer, `~/.bills-and-renewals/items.json`, readable only by your user account. The script makes no network requests. When Claude reads your list to answer you, that content is handled like the rest of your Claude conversation.

Do not store card, bank or ID numbers. The script refuses long digit runs for that reason.

## Without Claude

```bash
python3 scripts/renewals.py add "Rent" --due 2026-12-01 --kind bill --repeat monthly --amount 15000 --currency INR
```

```bash
python3 scripts/renewals.py due
```

Run `python3 scripts/renewals.py --help` for every command.

## License

MIT
