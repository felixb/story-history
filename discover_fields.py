#! /usr/bin/env uv run python3

import sys

import yaml
from jira import JIRA

from main import CONFIG_FILE


def main() -> None:
    try:
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"{CONFIG_FILE} not found")
        sys.exit(1)

    url = config.get("jira", {}).get("url")
    token = config.get("jira", {}).get("token")

    if not url or not token:
        print(f"Jira url or token missing in {CONFIG_FILE}")
        sys.exit(1)

    jira = JIRA(server=url, token_auth=token)

    print("Fetching Jira fields...")
    fields = jira.fields()

    sp_fields = [f for f in fields if 'Story Point' in f['name']]
    sprint_fields = [f for f in fields if 'Sprint' in f['name']]

    print("\n--- Potential Story Points Fields ---")
    for f in sp_fields:
        print(f"Name: {f['name']}, ID: {f['id']}")

    print("\n--- Potential Sprint Fields ---")
    for f in sprint_fields:
        print(f"Name: {f['name']}, ID: {f['id']}")


if __name__ == "__main__":
    main()
