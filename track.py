#! /usr/bin/env uv run python3
import argparse
import yaml
import os
from datetime import date, timedelta
from shared import load_config

HOURS_FILE = "hours.yaml"


def load_hours():
    if not os.path.exists(HOURS_FILE):
        return {}
    with open(HOURS_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def save_hours(data):
    with open(HOURS_FILE, "w") as f:
        yaml.dump(data, f, sort_keys=True)


def add_hours(data, day, ticket, hours):
    if day not in data:
        data[day] = {}
    current_hours = data[day].get(ticket, 0)
    data[day][ticket] = current_hours + hours
    return data


def print_day_log(day_iso, day_entries, common_label, short=False):
    day_date = date.fromisoformat(day_iso)
    day_str = day_date.strftime("%a %Y-%m-%d")

    # Sort: common_label first, then rest alphabetically
    tickets = sorted(day_entries.keys(), key=lambda x: (x != common_label, x))

    if short:
        entries = [f"{t}: {day_entries[t]:g}h" for t in tickets]
        print(f"{day_str}: {', '.join(entries)}")
        return 0

    print(f"\n--- Hours for {day_str} ---")
    day_total = 0

    for ticket in tickets:
        hours = day_entries[ticket]
        print(f"{ticket}: {hours:g}h")
        day_total += hours
    print(f"Day Total: {day_total:g}h")
    return day_total


def print_log(data, days, common_label, short=False):
    total_week = 0
    for day_iso in days:
        day_entries = data.get(day_iso, {})
        if not day_entries:
            continue

        total_week += print_day_log(day_iso, day_entries, common_label, short)

    if not short:
        if total_week > 0:
            print("\n=======================")
            print(f"Weekly Total: {total_week:g}h")
        else:
            print("\nNo hours tracked this week.")
    elif not any(data.get(day) for day in days):
        print("No hours tracked this week.")


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Track spent hours on tickets.")
    parser.add_argument("-a", "-add", dest="add", type=float, help="Hours to add")
    parser.add_argument(
        "ticket",
        nargs="?",
        default=config.common_label,
        help=f"Ticket ID or account (default: {config.common_label})",
    )
    parser.add_argument(
        "-l", "-log", dest="log", action="store_true", help="Print weekly log"
    )
    parser.add_argument(
        "-s",
        "-short",
        dest="short",
        action="store_true",
        help="Print log in short format",
    )

    args = parser.parse_args()

    if not args.add and not args.log and not args.short:
        parser.print_help()
        return

    today = date.today()
    today_iso = today.isoformat()
    data = load_hours()

    if args.add:
        data = add_hours(data, today_iso, args.ticket, args.add)
        save_hours(data)
        print(f"Added {args.add:g}h to {args.ticket} for {today_iso}.")

    if args.log or args.short:
        start_of_week = today - timedelta(days=today.weekday())
        week_days = [(start_of_week + timedelta(days=i)).isoformat() for i in range(7)]
        print_log(data, week_days, config.common_label, short=args.short)


if __name__ == "__main__":
    main()
