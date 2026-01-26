from jira import JIRA
from shared import Config, process_jira_issue, save_ticket_to_cache


def show_story(jira: JIRA, config: Config, key: str) -> None:
    try:
        issue = jira.issue(key)
        ticket = process_jira_issue(issue, config.jira.fields)
        save_ticket_to_cache(ticket)

        print(f"# {ticket.key}: {ticket.summary}\n")

        if ticket.description:
            print("## Description")
            print(f"{ticket.description}\n")

        if ticket.acceptance_criteria:
            print("## Acceptance Criteria")
            if isinstance(ticket.acceptance_criteria, list):
                for item in ticket.acceptance_criteria:
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        is_header = item.get("isHeader", False)
                    else:
                        text = str(item)
                        is_header = False

                    if is_header:
                        print(f"\n### {text}")
                    else:
                        # Indent multi-line items
                        lines = text.splitlines()
                        if lines:
                            print(f"- {lines[0]}")
                            for line in lines[1:]:
                                print(f"  {line}")
                print()
            else:
                print(f"{ticket.acceptance_criteria}\n")

    except Exception as e:
        print(f"Error fetching story {key}: {e}")


def run_with_args(args, config: Config) -> None:
    from jira import JIRA

    jira = JIRA(server=config.jira.url, token_auth=config.jira.token)
    show_story(jira, config, args.ticket)
