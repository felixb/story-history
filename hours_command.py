#! /usr/bin/env uv run python3
import os
from datetime import date, timedelta

import yaml

from shared import load_ticket_from_cache

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

    for key in tickets:
        hours = day_entries[key]
        ticket_info = load_ticket_from_cache(key)
        if ticket_info:
            print(f"{key}: {hours:g}h - {ticket_info.summary} [{ticket_info.status}]")
        else:
            print(f"{key}: {hours:g}h")
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


def print_ticket_total(data, ticket_key):
    total = 0
    for day_iso in data:
        day_entries = data[day_iso]
        total += day_entries.get(ticket_key, 0)

    ticket_info = load_ticket_from_cache(ticket_key)
    if ticket_info:
        print(
            f"{ticket_key}: {total:g}h - {ticket_info.summary} [{ticket_info.status}]"
        )
    else:
        print(f"{ticket_key}: {total:g}h")


def run_with_args(args, config):
    today = date.today()
    today_iso = today.isoformat()
    data = load_hours()

    ticket_key = args.ticket or config.common_label

    if args.add:
        data = add_hours(data, today_iso, ticket_key, args.add)
        save_hours(data)
        print(f"Added {args.add:g}h to {ticket_key} for {today_iso}.")

    if args.total:
        print_ticket_total(data, ticket_key)
        return

    if args.log or args.short or not (args.add or args.total):
        start_of_week = today - timedelta(days=today.weekday())
        week_days = [(start_of_week + timedelta(days=i)).isoformat() for i in range(7)]
        print_log(data, week_days, config.common_label, short=args.short)
