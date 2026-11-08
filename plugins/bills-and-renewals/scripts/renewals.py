#!/usr/bin/env python3
"""Bills and Renewals - a private, local tracker for what is due and when.
Author: Chandra ObulaReddy (ChandraChaan)

Usage:
  renewals.py add NAME --due YYYY-MM-DD [--kind K] [--repeat R] [--amount N]
                       [--currency C] [--remind DAYS] [--note TEXT]
  renewals.py edit ID [same options as add, plus --name]
  renewals.py list [--json] [--all]
  renewals.py due [--within DAYS] [--json]
  renewals.py paid ID [--on YYYY-MM-DD] [--amount N]
  renewals.py remove ID
  renewals.py summary [--json]
  renewals.py export-ics [--out PATH.ics]

Data lives in ~/.bills-and-renewals/items.json (override with RENEWALS_FILE).
Nothing is sent anywhere. Standard library only.
"""
import argparse
import calendar
import datetime as dt
import json
import os
import re
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

KINDS = ("bill", "subscription", "insurance", "document", "other")
REPEATS = ("none", "weekly", "monthly", "quarterly", "yearly")
DEFAULT_REMIND = {"bill": 3, "subscription": 3, "insurance": 30, "document": 60, "other": 7}
MONTHS_PER_YEAR = Decimal(12)
# Long digit runs are card, bank or government numbers, which must never be stored here.
LONG_NUMBER_RE = re.compile(r"(?:\d[ -]?){12,}")


def die(message):
    sys.exit(f"error: {message}")


def today():
    override = os.environ.get("RENEWALS_TODAY")
    return parse_date(override) if override else dt.date.today()


def parse_date(value):
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        die(f"'{value}' is not a real date in YYYY-MM-DD form")


def parse_amount(value):
    try:
        amount = Decimal(value.replace(",", ""))
    except InvalidOperation:
        die(f"'{value}' is not a number")
    if not amount.is_finite() or amount < 0:
        die("amount must be zero or more")
    return str(amount)


def check_no_account_number(*texts):
    for text in texts:
        if text and LONG_NUMBER_RE.search(text):
            die("that looks like a card, account or ID number. Do not store it here; use the last 4 digits at most.")


def data_path():
    return Path(os.environ.get("RENEWALS_FILE") or Path.home() / ".bills-and-renewals" / "items.json")


def load():
    path = data_path()
    if not path.exists():
        return {"version": 1, "next_id": 1, "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("items"), list):
            raise ValueError("no items list")
    except (ValueError, AttributeError) as exc:
        die(f"{path} is damaged and was left untouched ({exc}). Restore or move it, then retry.")
    return data


def save(data):
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".items-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def find(data, item_id):
    for item in data["items"]:
        if item["id"] == item_id:
            return item
    die(f"no item with id {item_id}. Run 'list --all' to see ids.")


def add_months(day, months, anchor):
    """Move by whole months, clamping to month length but remembering the anchor day."""
    year, month0 = divmod(day.year * 12 + day.month - 1 + months, 12)
    month = month0 + 1
    return dt.date(year, month, min(anchor, calendar.monthrange(year, month)[1]))


def next_due(due, repeat, anchor):
    if repeat == "weekly":
        return due + dt.timedelta(days=7)
    if repeat == "monthly":
        return add_months(due, 1, anchor)
    if repeat == "quarterly":
        return add_months(due, 3, anchor)
    if repeat == "yearly":
        return add_months(due, 12, anchor)
    return None


def view(item, now):
    due = parse_date(item["due"])
    return {**item, "days_left": (due - now).days}


def when_text(days):
    if days < 0:
        return f"OVERDUE by {-days} day{'s' if days != -1 else ''}"
    if days == 0:
        return "due TODAY"
    return f"in {days} day{'s' if days != 1 else ''}"


def line(row):
    money = f"  {row['amount']}{' ' + row['currency'] if row.get('currency') else ''}" if row.get("amount") else ""
    repeat = f"  {row['repeat']}" if row["repeat"] != "none" else ""
    return f"#{row['id']:<3} {row['name']} [{row['kind']}]  {row['due']}  {when_text(row['days_left'])}{money}{repeat}"


def active(data):
    return [i for i in data["items"] if not i.get("done")]


def cmd_add(args):
    check_no_account_number(args.name, args.note)
    due = parse_date(args.due)
    data = load()
    item = {
        "id": data["next_id"],
        "name": args.name,
        "kind": args.kind,
        "due": due.isoformat(),
        "anchor_day": due.day,
        "repeat": args.repeat,
        "amount": parse_amount(args.amount) if args.amount is not None else None,
        "currency": args.currency.upper() if args.currency else None,
        "remind_days": args.remind if args.remind is not None else DEFAULT_REMIND[args.kind],
        "note": args.note,
        "done": False,
        "history": [],
    }
    data["next_id"] += 1
    data["items"].append(item)
    save(data)
    print("added " + line(view(item, today())))


def cmd_edit(args):
    check_no_account_number(args.name, args.note)
    data = load()
    item = find(data, args.id)
    if args.name is not None:
        item["name"] = args.name
    if args.due is not None:
        due = parse_date(args.due)
        item["due"], item["anchor_day"], item["done"] = due.isoformat(), due.day, False
    if args.kind is not None:
        item["kind"] = args.kind
    if args.repeat is not None:
        item["repeat"] = args.repeat
    if args.amount is not None:
        item["amount"] = parse_amount(args.amount)
    if args.currency is not None:
        item["currency"] = args.currency.upper()
    if args.remind is not None:
        item["remind_days"] = args.remind
    if args.note is not None:
        item["note"] = args.note
    save(data)
    print("updated " + line(view(item, today())))


def cmd_list(args):
    data = load()
    now = today()
    items = data["items"] if args.all else active(data)
    rows = sorted((view(i, now) for i in items), key=lambda r: r["due"])
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("Nothing tracked yet.")
    for row in rows:
        print(line(row) + ("  (done)" if row.get("done") else ""))


def cmd_due(args):
    now = today()
    rows = []
    for item in active(load()):
        row = view(item, now)
        window = args.within if args.within is not None else item["remind_days"]
        if row["days_left"] <= window:
            rows.append(row)
    rows.sort(key=lambda r: r["due"])
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("Nothing needs attention right now.")
        return
    for row in rows:
        print(line(row))


def cmd_paid(args):
    data = load()
    item = find(data, args.id)
    if item.get("done"):
        die(f"#{item['id']} {item['name']} is already finished.")
    paid_on = parse_date(args.on) if args.on else today()
    amount = parse_amount(args.amount) if args.amount is not None else item.get("amount")
    item["history"].append({"due": item["due"], "paid_on": paid_on.isoformat(), "amount": amount})
    # Advance from the due date, not the payment date, so paying late keeps the schedule.
    following = next_due(parse_date(item["due"]), item["repeat"], item["anchor_day"])
    if following is None:
        item["done"] = True
        message = f"marked #{item['id']} {item['name']} done"
    else:
        item["due"] = following.isoformat()
        message = f"recorded #{item['id']} {item['name']}; next due {item['due']} ({when_text((following - today()).days)})"
    save(data)
    print(message)


def cmd_remove(args):
    data = load()
    item = find(data, args.id)
    data["items"].remove(item)
    save(data)
    print(f"removed #{item['id']} {item['name']}")


def monthly_equivalent(item):
    amount = Decimal(item["amount"])
    return {
        "weekly": amount * 52 / MONTHS_PER_YEAR,
        "monthly": amount,
        "quarterly": amount / 3,
        "yearly": amount / MONTHS_PER_YEAR,
    }.get(item["repeat"], Decimal(0))


def money(value):
    return str(value.quantize(Decimal("0.01")))


def cmd_summary(args):
    now = today()
    horizon = now + dt.timedelta(days=30)
    totals, no_amount = {}, 0
    for item in active(load()):
        if item.get("amount") is None:
            no_amount += 1
            continue
        bucket = totals.setdefault(item.get("currency") or "unspecified", {"monthly": Decimal(0), "next_30": Decimal(0)})
        bucket["monthly"] += monthly_equivalent(item)
        due = parse_date(item["due"])
        while due is not None and due <= horizon:
            bucket["next_30"] += Decimal(item["amount"])
            due = next_due(due, item["repeat"], item["anchor_day"])
    report = {
        "currencies": {
            cur: {"recurring_per_month": money(b["monthly"]), "recurring_per_year": money(b["monthly"] * MONTHS_PER_YEAR),
                  "due_through_next_30_days": money(b["next_30"])}
            for cur, b in sorted(totals.items())
        },
        "items_without_amount": no_amount,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return
    if not totals:
        print("No amounts recorded yet.")
    for cur, row in report["currencies"].items():
        print(f"{cur}: {row['recurring_per_month']}/month recurring, {row['recurring_per_year']}/year, "
              f"{row['due_through_next_30_days']} due through the next 30 days (includes overdue)")
    if no_amount:
        print(f"{no_amount} item(s) have no amount and are not counted.")


def ics_escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(content):
    """Fold to 75 octets per line (RFC 5545) without splitting a UTF-8 character."""
    lines, current, size = [], "", 0
    for char in content:
        width = len(char.encode("utf-8"))
        if size + width > 75:
            lines.append(current)
            current, size = " ", 1
        current += char
        size += width
    lines.append(current)
    return "\r\n".join(lines)


def ics_rrule(item, due):
    repeat, anchor = item["repeat"], item["anchor_day"]
    if repeat == "none":
        return None
    if repeat == "weekly":
        return "FREQ=WEEKLY"
    # Without BYSETPOS, calendars skip months that lack day 29-31 instead of using the last day.
    if repeat == "yearly":
        if due.month == 2 and anchor == 29:
            return "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=28,29;BYSETPOS=-1"
        return "FREQ=YEARLY"
    interval = ";INTERVAL=3" if repeat == "quarterly" else ""
    if anchor > 28:
        days = ",".join(str(d) for d in range(28, anchor + 1))
        return f"FREQ=MONTHLY{interval};BYMONTHDAY={days};BYSETPOS=-1"
    return f"FREQ=MONTHLY{interval}"


def cmd_export_ics(args):
    out = Path(args.out).expanduser() if args.out else Path.home() / "bills-and-renewals.ics"
    if out.suffix.lower() != ".ics":
        die("the output file must end in .ics")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//bills-and-renewals//EN", "CALSCALE:GREGORIAN"]
    items = active(load())
    for item in items:
        due = parse_date(item["due"])
        title = item["name"]
        if item.get("amount"):
            title += f" ({item['amount']}{' ' + item['currency'] if item.get('currency') else ''})"
        rows += ["BEGIN:VEVENT", f"UID:bills-and-renewals-{item['id']}", f"DTSTAMP:{stamp}",
                 f"DTSTART;VALUE=DATE:{due:%Y%m%d}", f"SUMMARY:{ics_escape(title)}"]
        rule = ics_rrule(item, due)
        if rule:
            rows.append(f"RRULE:{rule}")
        if item.get("note"):
            rows.append(f"DESCRIPTION:{ics_escape(item['note'])}")
        trigger = f"-P{item['remind_days']}D" if item["remind_days"] else "PT0S"
        rows += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{ics_escape(item['name'])}", f"TRIGGER:{trigger}",
                 "END:VALARM", "END:VEVENT"]
    rows.append("END:VCALENDAR")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(("\r\n".join(ics_fold(r) for r in rows) + "\r\n").encode("utf-8"))
    print(f"wrote {len(items)} item(s) to {out}. Open that file to import it into your calendar.")


def item_options(parser, required):
    parser.add_argument("--due", required=required)
    parser.add_argument("--kind", choices=KINDS, default="other" if required else None)
    parser.add_argument("--repeat", choices=REPEATS, default="none" if required else None)
    parser.add_argument("--amount")
    parser.add_argument("--currency")
    parser.add_argument("--remind", type=int, help="days before the due date to start reminding")
    parser.add_argument("--note")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("name")
    item_options(add, True)
    add.set_defaults(func=cmd_add)

    edit = sub.add_parser("edit")
    edit.add_argument("id", type=int)
    edit.add_argument("--name")
    item_options(edit, False)
    edit.set_defaults(func=cmd_edit)

    listing = sub.add_parser("list")
    listing.add_argument("--json", action="store_true")
    listing.add_argument("--all", action="store_true", help="include finished one-off items")
    listing.set_defaults(func=cmd_list)

    due = sub.add_parser("due")
    due.add_argument("--within", type=int, help="override each item's reminder window")
    due.add_argument("--json", action="store_true")
    due.set_defaults(func=cmd_due)

    paid = sub.add_parser("paid")
    paid.add_argument("id", type=int)
    paid.add_argument("--on")
    paid.add_argument("--amount")
    paid.set_defaults(func=cmd_paid)

    remove = sub.add_parser("remove")
    remove.add_argument("id", type=int)
    remove.set_defaults(func=cmd_remove)

    summary = sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    summary.set_defaults(func=cmd_summary)

    export = sub.add_parser("export-ics")
    export.add_argument("--out")
    export.set_defaults(func=cmd_export_ics)

    args = parser.parse_args()
    if getattr(args, "remind", None) is not None and args.remind < 0:
        die("--remind must be zero or more")
    args.func(args)


if __name__ == "__main__":
    main()
