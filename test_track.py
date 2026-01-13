import pytest
import os
import yaml
from datetime import date
from unittest.mock import patch
import sys
from hours_command import add_hours, load_hours, save_hours, print_log


def test_print_log_empty(capsys):
    data = {}
    days = [
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
        "2026-01-09",
        "2026-01-10",
        "2026-01-11",
    ]
    print_log(data, days, "common")
    captured = capsys.readouterr()
    assert "No hours tracked this week." in captured.out


def test_print_log_with_data(capsys):
    days = ["2026-01-08", "2026-01-09"]
    data = {
        "2026-01-08": {"PROJ-123": 2.0, "common": 3.0},
        "2026-01-09": {"Z-TICKET": 1.0, "common": 1.5, "A-TICKET": 2.0},
    }
    print_log(data, days, "common")
    captured = capsys.readouterr()

    # Check 2026-01-08: common should be first
    assert "Hours for Thu 2026-01-08" in captured.out
    lines_08 = (
        captured.out.split("--- Hours for Thu 2026-01-08 ---")[1]
        .split("Day Total")[0]
        .strip()
        .split("\n")
    )
    assert lines_08[0].strip().startswith("common:")
    assert lines_08[1].strip().startswith("PROJ-123:")

    # Check 2026-01-09: common first, then A-TICKET, then Z-TICKET
    assert "Hours for Fri 2026-01-09" in captured.out
    lines_09 = (
        captured.out.split("--- Hours for Fri 2026-01-09 ---")[1]
        .split("Day Total")[0]
        .strip()
        .split("\n")
    )
    assert lines_09[0].strip().startswith("common:")
    assert lines_09[1].strip().startswith("A-TICKET:")
    assert lines_09[2].strip().startswith("Z-TICKET:")


def test_print_log_short(capsys):
    days = ["2026-01-08", "2026-01-09"]
    data = {
        "2026-01-08": {"PROJ-123": 2.0, "common": 3.0},
        "2026-01-09": {"Z-TICKET": 1.0, "common": 1.5, "A-TICKET": 2.0},
    }
    print_log(data, days, "common", short=True)
    captured = capsys.readouterr()

    expected_08 = "Thu 2026-01-08: common: 3h, PROJ-123: 2h"
    expected_09 = "Fri 2026-01-09: common: 1.5h, A-TICKET: 2h, Z-TICKET: 1h"

    assert expected_08 in captured.out
    assert expected_09 in captured.out
    assert "Day Total" not in captured.out
    assert "Weekly Total" not in captured.out


def test_add_hours_new_day():
    data = {}
    day = "2026-01-09"
    ticket = "PROJ-123"
    hours = 2.0

    updated_data = add_hours(data, day, ticket, hours)

    assert updated_data[day][ticket] == 2.0
    assert len(updated_data[day]) == 1


def test_add_hours_existing_ticket():
    day = "2026-01-09"
    ticket = "PROJ-123"
    data = {day: {ticket: 1.5}}
    hours = 2.0

    updated_data = add_hours(data, day, ticket, hours)

    assert updated_data[day][ticket] == 3.5


def test_add_hours_different_ticket_same_day():
    day = "2026-01-09"
    data = {day: {"common": 1.0}}
    ticket = "PROJ-123"
    hours = 2.0

    updated_data = add_hours(data, day, ticket, hours)

    assert updated_data[day]["common"] == 1.0
    assert updated_data[day]["PROJ-123"] == 2.0


def test_save_and_load_hours(tmp_path, monkeypatch):
    # Use a temporary file for testing
    hours_file = tmp_path / "test_hours.yaml"
    monkeypatch.setattr("hours_command.HOURS_FILE", str(hours_file))

    data = {"2026-01-09": {"common": 5.0}}
    save_hours(data)

    assert hours_file.exists()

    loaded_data = load_hours()
    assert loaded_data == data


def test_load_hours_non_existent(tmp_path, monkeypatch):
    hours_file = tmp_path / "non_existent.yaml"
    monkeypatch.setattr("hours_command.HOURS_FILE", str(hours_file))

    loaded_data = load_hours()
    assert loaded_data == {}


def test_load_config_permissive(tmp_path, monkeypatch):
    from shared import load_config

    config_file = tmp_path / "config.yaml"
    # No jira config at all
    config_data = {
        "common_label": "Testing",
        "tickets": ["T-1"],
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    monkeypatch.setattr("shared.CONFIG_FILE", str(config_file))

    config = load_config()
    assert config.common_label == "Testing"
    assert config.tickets == ["T-1"]
    assert config.jira.url is None
    assert config.jira.fields.story_points is None
