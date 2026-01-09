#! /usr/bin/env uv run python3

from jira import JIRA

from shared import load_config, validate_jira_base_config


def main() -> None:
    config = load_config()
    validate_jira_base_config(config)

    jira = JIRA(server=config.jira.url, token_auth=config.jira.token)

    print("Fetching Jira fields...")
    fields = jira.fields()

    sp_fields = [f for f in fields if "Story Point" in f["name"]]
    sprint_fields = [f for f in fields if "Sprint" in f["name"]]

    print("\n--- Potential Story Points Fields ---")
    for f in sp_fields:
        print(f"Name: {f['name']}, ID: {f['id']}")

    print("\n--- Potential Sprint Fields ---")
    for f in sprint_fields:
        print(f"Name: {f['name']}, ID: {f['id']}")


if __name__ == "__main__":
    main()
