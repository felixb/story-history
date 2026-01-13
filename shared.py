import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Any

import yaml
from jira import JIRA

CONFIG_FILE = "config.yaml"
CACHE_DIR = ".cache"
NO_SPRINT = "No Sprint"


@dataclass
class Ticket:
    key: str
    summary: str
    status: str
    story_points: float
    sprint: str


@dataclass
class JiraFields:
    story_points: Optional[str] = None
    sprint: Optional[str] = None


@dataclass
class JiraConfig:
    url: Optional[str] = None
    token: Optional[str] = None
    fields: Optional[JiraFields] = None
    closed_statuses: list[str] = None


@dataclass
class Config:
    jira: JiraConfig
    tickets: list[str]
    common_label: str


def load_config() -> Config:
    try:
        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"{CONFIG_FILE} not found")
        sys.exit(1)

    jira_data = data.get("jira", {})
    fields_data = jira_data.get("fields", {})

    fields = JiraFields(
        story_points=fields_data.get("story_points"),
        sprint=fields_data.get("sprint"),
    )

    jira_config = JiraConfig(
        url=jira_data.get("url"),
        token=jira_data.get("token"),
        fields=fields,
        closed_statuses=jira_data.get("closed_statuses", ["Done", "Closed"]),
    )

    return Config(
        jira=jira_config,
        tickets=data.get("tickets", []),
        common_label=data.get("common_label", "common"),
    )


def save_config(config: Config) -> None:
    # We want to preserve the structure but update tickets
    # To preserve comments and formatting, we'd need a more sophisticated YAML library
    # but for now, we'll just rewrite it as per dataclass structure
    data = {
        "jira": {
            "url": config.jira.url,
            "token": config.jira.token,
            "fields": {
                "story_points": config.jira.fields.story_points,
                "sprint": config.jira.fields.sprint,
            },
        },
        "tickets": config.tickets,
        "common_label": config.common_label,
    }
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f, sort_keys=False)


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
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
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


def validate_jira_base_config(config: Config) -> None:
    if not config.jira.url or not config.jira.token:
        print(f"Jira url or token missing in {CONFIG_FILE}")
        sys.exit(1)


def validate_jira_full_config(config: Config) -> None:
    validate_jira_base_config(config)
    if not config.jira.fields.story_points or not config.jira.fields.sprint:
        print(f"Jira fields (story_points, sprint) missing in {CONFIG_FILE}")
        sys.exit(1)
