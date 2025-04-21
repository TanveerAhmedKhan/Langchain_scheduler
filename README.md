# Scout Agent - Proof of Concept

A lightweight, automated monitoring assistant that watches web pages for changes based on user instructions.

## Overview

Scout Agent is a proof of concept for an automated monitoring assistant. It accepts natural language instructions from users, parses them to understand what to monitor, and periodically checks web pages for changes. When changes are detected, it notifies the user.

### Key Features

- **Natural Language Instructions**: Tell Scout what to monitor in plain English
- **Automated Monitoring**: Scout checks web pages at the specified intervals
- **Change Detection**: Identifies when content changes on monitored pages
- **Simple Interface**: Easy-to-use Streamlit interface for managing monitoring tasks

## Architecture

The Scout Agent PoC consists of several components:

1. **Agent (agent.py)**: Uses LangChain to parse natural language instructions
2. **Database (db.py)**: Thread-safe SQLite storage for tasks and page snapshots
3. **Scraper (scraper.py)**: Handles web page fetching and content comparison
4. **Scheduler (scheduler.py)**: Manages periodic task execution
5. **Main App (main.py)**: Streamlit interface for user interaction with auto-refresh

### Thread Safety

The application is designed to be thread-safe, which is important because:

- Streamlit runs different parts of the app in different threads
- The scheduler runs tasks in background threads
- SQLite connections created in one thread can only be used in that same thread

To address these challenges:

- The database module creates a new connection for each operation
- Notifications are handled carefully to avoid cross-thread session state issues
- The UI auto-refreshes periodically to ensure state consistency

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- OpenAI API key (for LangChain)

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd scout_agent_poc
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Running the Application

Start the Streamlit interface:

```
streamlit run main.py
```

The application will be available at http://localhost:8501

## Usage

1. **Create a Monitoring Task**:
   - Enter a natural language instruction like "Check https://example.com/careers every 4 hours for new job postings"
   - Click "Create Task"
   - Review and confirm the task details

2. **View Active Tasks**:
   - Active monitoring tasks are displayed in the sidebar
   - You can pause tasks if needed

3. **Check Notifications**:
   - When changes are detected, notifications appear in the right panel
   - Notifications include details about what changed

## Example Use Cases

1. **Job Page Monitoring**:
   "Check https://company.com/careers every 6 hours and tell me if new jobs appear"

2. **News Monitoring**:
   "Monitor https://news.example.com every hour for articles about AI"

3. **Product Price Tracking**:
   "Watch https://store.example.com/product every day and tell me if the price changes"

## Troubleshooting

### Common Issues

1. **SQLite Threading Errors**
   - Error: `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`
   - Solution: This is handled by the thread-safe database implementation. If you still encounter this error, restart the application.

2. **OpenAI API Key Issues**
   - Error: `openai.error.AuthenticationError: Incorrect API key provided`
   - Solution: Make sure you've set the correct API key in your `.env` file.

3. **Streamlit Session State Issues**
   - Symptom: UI not updating or showing inconsistent state
   - Solution: The app auto-refreshes every 30 seconds, but you can manually refresh the page if needed.

4. **Scheduler Not Running Tasks**
   - Symptom: Tasks are created but never executed
   - Solution: Check the logs for any errors. Make sure the frequency is set correctly.

## Future Extensions

This proof of concept could be extended in several ways:

1. **Messaging Integration**: Connect to platforms like Slack, Discord, or email for notifications
2. **Advanced Content Analysis**: Use LLMs to better understand page content and changes
3. **User Authentication**: Add multi-user support with authentication
4. **Improved Diff Visualization**: Better visualization of what changed on monitored pages
5. **Custom Notification Rules**: Allow users to specify conditions for when to be notified
6. **Persistent Storage**: Replace SQLite with a more robust database for production use

## License

[MIT License](LICENSE)

## Acknowledgements

- Built with [LangChain](https://github.com/langchain-ai/langchain)
- Interface created with [Streamlit](https://streamlit.io/)
