# 🤖 story-history

> A lightweight, AI-crafted personal story history tracker for Jira.

This tool maintains a localized view of your Jira tickets, providing quick insights into your progress and sprint
velocity without the heavy Jira UI.

### ✨ Key Features

- 📂 **Local Caching**: Minimizes Jira API requests by storing ticket data locally.
- 📋 **Ticket Reporting**:
    - **Open Tickets**: Lists your tracked tickets with direct browser links.
    - **Authored by Me**: Automatically finds and lists open tickets you've reported.
- 📊 **Sprint Analytics**: Sums up story points (SP) per sprint, distinguishing between closed and total capacity.
- 🔍 **Field Discovery**: Includes a utility to help find your Jira instance's specific custom field IDs.

## 🛠 Configuration

The tool uses a `config.yaml` file to connect to your Jira instance and track specific tickets.

```yaml
jira:
  url: https://your-jira-instance.com/jira # The base URL of your Jira instance
  token: your-jira-personal-access-token # Your Jira personal access token
  fields:
    story_points: customfield_10006 # The custom field ID for Story Points
    sprint: customfield_10000 # The custom field ID for Sprint
  closed_statuses: # Jira statuses considered "closed" for reporting
    - Done
    - Closed
tickets: # List of Jira ticket keys to track explicitly
  - PROJECT-123
  - PROJECT-456
```

> [!TIP]
> If you don't know the custom field IDs for Story Points and Sprint, run:
> `uv run python discover_fields.py`

## 🧪 Testing

To run the logic tests, use:

```bash
uv run pytest
```

## 🤝 Contribution

This project is an **AI-native** application, where the codebase is primarily maintained and evolved through AI-assisted
development.

**Policy:** Contributions are welcome! However, to preserve the project's heritage, we prefer contributions that are *
*AI-generated or AI-assisted**. We embrace the synergy between human guidance and machine execution.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.