from dataclasses import dataclass
from typing import Optional, Any
import yaml
import sys

CONFIG_FILE = "config.yaml"


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


def validate_jira_base_config(config: Config) -> None:
    if not config.jira.url or not config.jira.token:
        print(f"Jira url or token missing in {CONFIG_FILE}")
        sys.exit(1)


def validate_jira_full_config(config: Config) -> None:
    validate_jira_base_config(config)
    if not config.jira.fields.story_points or not config.jira.fields.sprint:
        print(f"Jira fields (story_points, sprint) missing in {CONFIG_FILE}")
        sys.exit(1)
