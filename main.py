#! /usr/bin/env uv run python3

import argparse
import os

from jira import JIRA

import hours_command as hours
import show_command as show
from shared import (
    Ticket,
    JiraFields,
    load_config,
    validate_jira_full_config,
    CONFIG_FILE,
    CACHE_DIR,
    NO_SPRINT,
    get_cached_tickets,
    fetch_and_cache_tickets,
)
from track_command import track_tickets


def print_tickets(title: str, tickets: list[Ticket], url: str) -> None:
    if not tickets:
        return
    print(f"\n{title}")
    for issue in sorted(tickets, key=lambda x: x.key):
        link = f"{url}/browse/{issue.key}"
        points = issue.story_points
        points_str = f" ({points:g} SP)" if points else ""
        print(f"{issue.key}: {issue.summary} [{issue.status}]{points_str} - {link}")


def fetch_authored_tickets(
    jira: JIRA, issues_data: list[Ticket], fields: JiraFields
) -> list[Ticket]:
    authored_tickets = []
    try:
        jql_authored = "reporter = currentUser() AND statusCategory != Done"
        my_issues_data = fetch_and_cache_tickets(jira, jql_authored, fields)
        for ticket in my_issues_data:
            # Check if we already have it in issues_data (refreshed or cached)
            existing = next((i for i in issues_data if i.key == ticket.key), None)
            if not existing:
                authored_tickets.append(ticket)
    except Exception as e:
        print(f"Could not fetch authored tickets: {e}")
    return authored_tickets


def format_story_pints(closed: float, total: float) -> str:
    if total == closed:
        return f"{total:g} SP"
    else:
        return f"{closed:g} / {total:g} SP"


def print_sprint_story_points(sprint_name: str, closed: float, total: float) -> None:
    print(f"{sprint_name}: {format_story_pints(closed, total)}")


def print_sprint_stats(issues_data: list[Ticket], closed_statuses: list[str]) -> None:
    print("\n--- Story Points by Sprint ---")
    sprint_stats = {}  # sprint_name -> {"total": points, "closed": points}
    for ticket in issues_data:
        sprint_name = ticket.sprint
        points = ticket.story_points
        status = ticket.status

        if sprint_name not in sprint_stats:
            sprint_stats[sprint_name] = {"total": 0, "closed": 0}

        sprint_stats[sprint_name]["total"] += points
        if status in closed_statuses:
            sprint_stats[sprint_name]["closed"] += points

    for sprint, stats in sorted(sprint_stats.items()):
        total = stats["total"]
        closed = stats["closed"]
        print_sprint_story_points(sprint, closed, total)

    # 1. Average excluding last sprint
    real_sprints = {k: v for k, v in sprint_stats.items() if k != NO_SPRINT}
    if len(real_sprints) > 1:
        sorted_keys = sorted(real_sprints.keys())
        all_but_last = [real_sprints[s] for s in sorted_keys[:-1]]
        avg_total_excl = sum(s["total"] for s in all_but_last) / len(all_but_last)
        avg_closed_excl = sum(s["closed"] for s in all_but_last) / len(all_but_last)
        print_sprint_story_points(
            "Average sprint (excl. last)", avg_closed_excl, avg_total_excl
        )

    # 2. Overall Average
    if real_sprints:
        avg_total = sum(s["total"] for s in real_sprints.values()) / len(real_sprints)
        avg_closed = sum(s["closed"] for s in real_sprints.values()) / len(real_sprints)
        print_sprint_story_points("Average sprint", avg_closed, avg_total)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jira Story History Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # track command
    subparsers.add_parser("track", help="Start tracking new tickets assigned to me")

    # hours command
    hours_parser = subparsers.add_parser("hours", help="Track spent hours on tickets")
    hours_parser.add_argument("-a", "-add", dest="add", type=float, help="Hours to add")
    hours_parser.add_argument(
        "ticket",
        nargs="?",
        help="Ticket ID or account",
    )
    hours_parser.add_argument(
        "-l", "-log", dest="log", action="store_true", help="Print weekly log"
    )
    hours_parser.add_argument(
        "-s",
        "-short",
        dest="short",
        action="store_true",
        help="Print log in short format",
    )
    hours_parser.add_argument(
        "-t",
        "-total",
        dest="total",
        action="store_true",
        help="Print total hours spent on a ticket",
    )

    # show command
    show_parser = subparsers.add_parser("show", help="Show story details as markdown")
    show_parser.add_argument("ticket", help="Ticket ID to show")

    args = parser.parse_args()

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    config = load_config()

    if args.command == "hours":
        # Pass relevant args to hours.py main logic
        # We need to adapt hours.py slightly to be callable with args
        hours.run_with_args(args, config)
        return

    if args.command == "show":
        show.run_with_args(args, config)
        return

    validate_jira_full_config(config)

    jira = JIRA(server=config.jira.url, token_auth=config.jira.token)

    if args.command == "track":
        track_tickets(jira, config)
        return

    if not config.tickets:
        print(f"No tickets found in {CONFIG_FILE}")
        return

    # 1. Load from cache
    issues_data, keys_to_fetch = get_cached_tickets(
        config.tickets, config.jira.closed_statuses
    )

    jira = JIRA(server=config.jira.url, token_auth=config.jira.token)

    if keys_to_fetch:
        print(
            f"Refreshing {len(keys_to_fetch)} ticket(s) from Jira: {', '.join(keys_to_fetch)}"
        )
        jql = f"key in ({','.join(keys_to_fetch)})"
        fetched_data = fetch_and_cache_tickets(
            jira, jql, config.jira.fields, limit=len(keys_to_fetch)
        )
        issues_data.extend(fetched_data)

    # 2. Fetch tickets authored by me
    authored_tickets = fetch_authored_tickets(jira, issues_data, config.jira.fields)

    # Features:
    # 1. Show list of still open tickets
    open_tickets = [
        i for i in issues_data if i.status not in config.jira.closed_statuses
    ]
    print_tickets("--- Open Tickets ---", open_tickets, config.jira.url)

    # 2. Show authored tickets
    print_tickets(
        "--- Tickets Authored by Me (Open) ---", authored_tickets, config.jira.url
    )

    # 3. Sprint Stats
    print_sprint_stats(issues_data, config.jira.closed_statuses)


if __name__ == "__main__":
    main()
