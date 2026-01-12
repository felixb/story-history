from unittest.mock import MagicMock, patch

import pytest
import yaml

from main import (
    Ticket,
    JiraFields,
    extract_sprint_name,
    is_cache_fresh,
    get_cached_tickets,
    process_jira_issue,
    print_sprint_stats,
    NO_SPRINT,
)
from shared import load_config, validate_jira_full_config


def test_load_config_missing_fields(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "jira": {
            "url": "https://jira.example.com",
            "token": "secret",
            "fields": {
                "story_points": "customfield_123"
                # "sprint" is missing
            },
        },
        "tickets": [],
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    monkeypatch.setattr("shared.CONFIG_FILE", str(config_file))

    config = load_config()
    with pytest.raises(SystemExit) as excinfo:
        validate_jira_full_config(config)
    assert excinfo.value.code == 1


def test_load_config_success(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "jira": {
            "url": "https://jira.example.com",
            "token": "secret",
            "fields": {"story_points": "customfield_123", "sprint": "customfield_456"},
        },
        "tickets": ["T-1"],
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    monkeypatch.setattr("shared.CONFIG_FILE", str(config_file))

    config = load_config()
    assert config.jira.fields.story_points == "customfield_123"
    assert config.jira.fields.sprint == "customfield_456"
    assert config.tickets == ["T-1"]


def test_extract_sprint_name():
    fields = JiraFields(story_points="customfield_101", sprint="customfield_102")

    # Mock issue with no sprint field
    issue_no_sprint = MagicMock()
    del issue_no_sprint.fields.customfield_102
    assert extract_sprint_name(issue_no_sprint, fields) == NO_SPRINT

    # Mock issue with empty sprint list
    issue_empty_sprint = MagicMock()
    issue_empty_sprint.fields.customfield_102 = []
    assert extract_sprint_name(issue_empty_sprint, fields) == NO_SPRINT

    # Mock issue with sprint objects
    sprint_mock = MagicMock()
    sprint_mock.name = "Sprint 1"
    issue_with_sprint = MagicMock()
    issue_with_sprint.fields.customfield_102 = [sprint_mock]
    assert extract_sprint_name(issue_with_sprint, fields) == "Sprint 1"

    # Mock issue with multiple sprints (should take the last one)
    sprint_mock2 = MagicMock()
    sprint_mock2.name = "Sprint 2"
    issue_with_multiple_sprints = MagicMock()
    issue_with_multiple_sprints.fields.customfield_102 = [sprint_mock, sprint_mock2]
    assert extract_sprint_name(issue_with_multiple_sprints, fields) == "Sprint 2"

    # Mock issue with string sprint representation
    issue_str_sprint = MagicMock()
    issue_str_sprint.fields.customfield_102 = [
        "com.atlassian.greenhopper.service.sprint.Sprint@...[name=Sprint 3,goal=...]"
    ]
    assert extract_sprint_name(issue_str_sprint, fields) == "Sprint 3"


def test_is_cache_fresh():
    closed_statuses = ["Done", "Closed"]

    # None should be stale
    assert not is_cache_fresh(None, closed_statuses)

    # Open status should be stale
    assert not is_cache_fresh(
        Ticket(key="A", summary="S", status="Open", story_points=1, sprint="S1"),
        closed_statuses,
    )
    assert not is_cache_fresh(
        Ticket(key="B", summary="S", status="In Progress", story_points=1, sprint="S1"),
        closed_statuses,
    )

    # Closed status should be fresh
    assert is_cache_fresh(
        Ticket(key="C", summary="S", status="Done", story_points=1, sprint="S1"),
        closed_statuses,
    )
    assert is_cache_fresh(
        Ticket(key="D", summary="S", status="Closed", story_points=1, sprint="S1"),
        closed_statuses,
    )


@patch("main.load_ticket_from_cache")
def test_get_cached_tickets(mock_load):
    closed_statuses = ["Done", "Closed"]

    # Ticket A is in cache and fresh
    # Ticket B is in cache but stale
    # Ticket C is not in cache

    ticket_a = Ticket("A", "S", "Done", 1, "S1")
    ticket_b = Ticket("B", "S", "Open", 1, "S1")

    def side_effect(key):
        if key == "A":
            return ticket_a
        if key == "B":
            return ticket_b
        return None

    mock_load.side_effect = side_effect

    cached, to_fetch = get_cached_tickets(["A", "B", "C"], closed_statuses)

    assert cached == [ticket_a]
    assert to_fetch == ["B", "C"]


def test_process_jira_issue():
    fields = JiraFields(story_points="customfield_101", sprint="customfield_102")

    issue = MagicMock()
    issue.key = "PROJ-1"
    issue.fields.summary = "Test Summary"
    issue.fields.status.name = "In Progress"
    setattr(issue.fields, "customfield_101", 5.0)

    # Mock extract_sprint_name to avoid nested mocking complexity
    with patch("main.extract_sprint_name", return_value="Sprint 1"):
        ticket = process_jira_issue(issue, fields)

    assert ticket.key == "PROJ-1"
    assert ticket.summary == "Test Summary"
    assert ticket.status == "In Progress"
    assert ticket.story_points == 5.0
    assert ticket.sprint == "Sprint 1"


def test_process_jira_issue_null_points():
    fields = JiraFields(story_points="customfield_101", sprint="customfield_102")

    issue = MagicMock()
    issue.key = "PROJ-2"
    issue.fields.summary = "Null Points"
    issue.fields.status.name = "Open"
    setattr(issue.fields, "customfield_101", None)

    with patch("main.extract_sprint_name", return_value=NO_SPRINT):
        ticket = process_jira_issue(issue, fields)

    assert ticket.story_points == 0.0


def test_print_sprint_stats(capsys):
    closed_statuses = ["Done"]
    issues = [
        Ticket("A", "S1", "Done", 3.0, "Sprint 1"),
        Ticket("B", "S2", "Open", 5.0, "Sprint 1"),
        Ticket("C", "S3", "Done", 2.0, "Sprint 2"),
        Ticket("E", "S5", "Done", 4.0, "Sprint 3"),
        Ticket("D", "S4", "Done", 1.0, NO_SPRINT),
    ]

    print_sprint_stats(issues, closed_statuses)

    captured = capsys.readouterr()
    output = captured.out

    assert "--- Story Points by Sprint ---" in output
    assert "Sprint 1: 3 / 8 SP" in output
    assert "Sprint 2: 2 SP" in output
    assert "Sprint 3: 4 SP" in output
    assert f"{NO_SPRINT}: 1 SP" in output
    # Total real sprints: 3. Total SP: 8+2+4=14. Closed: 3+2+4=9.
    # Avg: 9/3 = 3. 14/3 = 4.666...
    assert "Average sprint: 3 / 4.66667 SP" in output
    # Excl last (Sprint 3): Sprints 1 & 2. Total SP: 8+2=10. Closed: 3+2=5.
    # Avg: 5/2 = 2.5. 10/2 = 5.
    assert "Average sprint (excl. last): 2.5 / 5 SP" in output


def test_print_sprint_stats_no_real_sprints(capsys):
    closed_statuses = ["Done"]
    issues = [
        Ticket("D", "S4", "Done", 1.0, NO_SPRINT),
    ]

    print_sprint_stats(issues, closed_statuses)

    captured = capsys.readouterr()
    output = captured.out

    assert "Average" not in output
    assert f"{NO_SPRINT}: 1 SP" in output
