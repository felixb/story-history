from typing import Any, Optional

from jira import JIRA

from shared import fetch_and_cache_tickets, save_config, CONFIG_FILE, Ticket


def track_tickets(jira: JIRA, config: Any, ticket_key: Optional[str] = None) -> None:
    if ticket_key:
        __track_single_ticket(jira, config, ticket_key)
        return

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

    __add_tickets(config, selected_tickets)
    save_config(config)
    print(f"Updated {CONFIG_FILE}")


def __track_single_ticket(jira: JIRA, config: Any, ticket_key: str):
    if ticket_key in config.tickets:
        print(f"{ticket_key} is already being tracked.")
        return

    try:
        jql = f"key = {ticket_key}"
        tickets = fetch_and_cache_tickets(jira, jql, config.jira.fields)
        if not tickets:
            print(f"Ticket {ticket_key} not found in Jira.")
            return
        __add_tickets(config, [ticket_key])
        save_config(config)
    except Exception as e:
        print(f"Error fetching ticket {ticket_key}: {e}")


def __add_tickets(config, selected_tickets: list[Ticket] | list[str]):
    if not selected_tickets:
        return
    if isinstance(selected_tickets[0], Ticket):
        selected_ticket_keys = [ticket.key for ticket in selected_tickets]
    else:
        selected_ticket_keys = selected_tickets
    for ticket in selected_ticket_keys:
        if ticket not in config.tickets:
            config.tickets.append(ticket)
            print(f"Added {ticket} to tracking.")
