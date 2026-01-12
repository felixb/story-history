#! /usr/bin/env uv run python3

import os
import re
from dataclasses import asdict
from typing import Optional, Any

import yaml
from jira import JIRA

CACHE_DIR = ".cache"
CONFIG_FILE = "config.yaml"
NO_SPRINT = "No Sprint"


from shared import (
    Ticket,
    JiraFields,
    load_config,
    validate_jira_full_config,
    CONFIG_FILE,
)


def print_tickets(title: str, tickets: list[Ticket], url: str) -> None:
    if not tickets:
        return
    print(f"\n{title}")
    for issue in sorted(tickets, key=lambda x: x.key):
        link = f"{url}/browse/{issue.key}"
        points = issue.story_points
        points_str = f" ({points:g} SP)" if points else ""
        print(f"{issue.key}: {issue.summary} [{issue.status}]{points_str} - {link}")


def extract_sprint_name(issue: Any, fields: JiraFields) -> str:
    sprint_field = fields.sprint
    if not sprint_field or not hasattr(issue.fields, sprint_field):
        return NO_SPRINT

    sprints = getattr(issue.fields, sprint_field)
    if not sprints or not isinstance(sprints, list) or len(sprints) == 0:
        return NO_SPRINT

    sprint = sprints[-1]
    if hasattr(sprint, "name"):
        return sprint.name
    elif isinstance(sprint, str) and "name=" in sprint:
        match = re.search(r"name=([^,]+)", sprint)
        if match:
            return match.group(1)
    return str(sprint)


def save_ticket_to_cache(ticket: Ticket) -> None:
    cache_path = os.path.join(CACHE_DIR, f"{ticket.key}.yaml")
    with open(cache_path, "w") as f:
        yaml.dump(asdict(ticket), f)


def process_jira_issue(issue: Any, fields: JiraFields) -> Ticket:
    status = issue.fields.status.name
    points = getattr(issue.fields, fields.story_points, 0)
    if points is None:
        points = 0

    return Ticket(
        key=issue.key,
        summary=issue.fields.summary,
        status=status,
        story_points=float(points),
        sprint=extract_sprint_name(issue, fields),
    )


def fetch_and_cache_tickets(
    jira: JIRA, jql: str, fields: JiraFields, limit: int = 50
) -> list[Ticket]:
    fetched_issues = jira.search_issues(jql, maxResults=limit)
    processed_tickets = []

    for issue in fetched_issues:
        issue_info = process_jira_issue(issue, fields)
        processed_tickets.append(issue_info)
        save_ticket_to_cache(issue_info)

    return processed_tickets


def load_ticket_from_cache(key: str) -> Optional[Ticket]:
    cache_path = os.path.join(CACHE_DIR, f"{key}.yaml")
    if not os.path.exists(cache_path):
        return None
    with open(cache_path, "r") as f:
        data = yaml.safe_load(f)
        if data:
            return Ticket(**data)
        return None


def is_cache_fresh(ticket: Optional[Ticket], closed_statuses: list[str]) -> bool:
    if ticket is None:
        return False
    return ticket.status in closed_statuses


def get_cached_tickets(
    ticket_keys: list[str], closed_statuses: list[str]
) -> tuple[list[Ticket], list[str]]:
    cached_issues = []
    keys_to_fetch = []

    for key in ticket_keys:
        ticket = load_ticket_from_cache(key)
        if is_cache_fresh(ticket, closed_statuses):
            cached_issues.append(ticket)
        else:
            keys_to_fetch.append(key)

    return cached_issues, keys_to_fetch


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
            if existing:
                authored_tickets.append(existing)
            else:
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
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    config = load_config()
    validate_jira_full_config(config)

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
