from typing import Any

from jira import JIRA

from shared import fetch_and_cache_tickets, save_config, CONFIG_FILE


def track_tickets(jira: JIRA, config: Any) -> None:
    print("Fetching open tickets assigned to you...")
    jql = "assignee = currentUser() AND statusCategory != Done"
    my_open_tickets = fetch_and_cache_tickets(jira, jql, config.jira.fields)

    untracked = [t for t in my_open_tickets if t.key not in config.tickets]

    if not untracked:
        print("No new untracked tickets found assigned to you.")
        return

    print("\nUntracked tickets assigned to you:")
    for i, ticket in enumerate(untracked):
        print(f"[{i}] {ticket.key}: {ticket.summary} ({ticket.status})")

    try:
        selection = input(
            "\nEnter the indices of tickets you want to track (comma-separated), or 'all', or press Enter to skip: "
        )
    except EOFError:
        return

    if not selection.strip():
        print("No tickets added.")
        return

    selected_tickets = []
    if selection.strip().lower() == "all":
        selected_tickets = untracked
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(",")]
            for idx in indices:
                if 0 <= idx < len(untracked):
                    selected_tickets.append(untracked[idx])
                else:
                    print(f"Invalid index: {idx}")
        except ValueError:
            print("Invalid input. Please enter numbers or 'all'.")
            return

    if not selected_tickets:
        print("No valid tickets selected.")
        return

    for ticket in selected_tickets:
        if ticket.key not in config.tickets:
            config.tickets.append(ticket.key)
            print(f"Added {ticket.key} to tracking.")

    save_config(config)
    print(f"Updated {CONFIG_FILE}")
