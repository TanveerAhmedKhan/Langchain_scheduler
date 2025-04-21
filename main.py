"""
Main module for Scout Agent PoC.
Provides a Streamlit interface for interacting with the Scout Agent.
"""

import os
import streamlit as st
import time
from datetime import datetime
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

from db import ScoutDatabase
from agent import ScoutAgent
from scraper import WebScraper
from scheduler import TaskScheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    if 'current_task' not in st.session_state:
        st.session_state.current_task = None
    if 'confirmation_stage' not in st.session_state:
        st.session_state.confirmation_stage = False
    if 'db' not in st.session_state:
        st.session_state.db = ScoutDatabase()
    if 'agent' not in st.session_state:
        st.session_state.agent = ScoutAgent()
    if 'scraper' not in st.session_state:
        st.session_state.scraper = WebScraper()
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = TaskScheduler(
            st.session_state.db,
            st.session_state.scraper,
            notification_callback=add_notification
        )
        # Schedule all active tasks
        st.session_state.scheduler.schedule_all_tasks()

def add_notification(notification: Dict[str, Any]):
    """Add a notification to the session state.

    Note: This function may be called from a background thread, so we need to be
    careful about how we modify session state. We'll use a file-based approach
    to store notifications that can be read by the main thread.
    """
    try:
        # Log the notification instead of directly modifying session state
        logger.info(f"Change notification received: {notification}")

        # In a production app, we would store this in a database or file
        # For this PoC, we'll just log it and let the UI poll for updates
        # from the database periodically

        # For demo purposes, we can still try to update the session state
        # but we need to be aware this might not always work across threads
        if 'notifications' in st.session_state:
            notifications = list(st.session_state.notifications)
            notifications.insert(0, notification)
            # Keep only the 50 most recent notifications
            if len(notifications) > 50:
                notifications = notifications[:50]
            st.session_state.notifications = notifications
    except Exception as e:
        logger.error(f"Error adding notification: {str(e)}")

def handle_instruction():
    """Handle the user's monitoring instruction."""
    instruction = st.session_state.instruction
    if not instruction:
        st.warning("Please enter an instruction.")
        return

    # Parse the instruction
    success, task_details = st.session_state.agent.parse_instruction(instruction)

    if not success:
        st.error(f"Failed to parse instruction: {task_details.get('error', 'Unknown error')}")
        return

    # Store the parsed task in session state
    st.session_state.current_task = task_details

    # Move to confirmation stage
    st.session_state.confirmation_stage = True

def confirm_task():
    """Confirm and save the monitoring task."""
    task = st.session_state.current_task

    # Add the task to the database
    task_id = st.session_state.db.add_task(
        url=task["url"],
        frequency=task["frequency_seconds"],
        task_prompt=task["task_description"]
    )

    # Schedule the task
    full_task = st.session_state.db.get_task(task_id)
    st.session_state.scheduler.schedule_task(full_task)

    # Reset the confirmation stage
    st.session_state.confirmation_stage = False
    st.session_state.current_task = None

    # Show success message
    st.success(f"Task created and scheduled! Task ID: {task_id}")

    # Clear the instruction input
    st.session_state.instruction = ""

def cancel_task():
    """Cancel the current task creation."""
    st.session_state.confirmation_stage = False
    st.session_state.current_task = None

def format_notification(notification: Dict[str, Any]) -> str:
    """Format a notification for display."""
    task_id = notification["task_id"]
    url = notification["url"]
    timestamp = notification["timestamp"]
    details = notification["details"]

    formatted_time = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    message = f"### Change detected for Task {task_id}\n"
    message += f"**URL:** {url}\n"
    message += f"**Time:** {formatted_time}\n"
    message += f"**Changes:** {details.get('additions', 0)} additions, {details.get('removals', 0)} removals\n"

    if "diff_sample" in details:
        message += f"\n**Sample of changes:**\n```diff\n{details['diff_sample']}\n```"

    return message

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Scout Agent PoC",
        page_icon="🔍",
        layout="wide"
    )

    # Initialize session state
    init_session_state()

    # Add auto-refresh for the UI
    # This helps with thread-safety by periodically refreshing the page
    # which recreates the session state in the main thread
    st.empty()
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    # Auto-refresh every 30 seconds
    if (datetime.now() - st.session_state.last_refresh).total_seconds() > 30:
        st.session_state.last_refresh = datetime.now()
        st.rerun()

    # Title and description
    st.title("🔍 Scout Agent")
    st.subheader("Your automated monitoring assistant")

    # Sidebar with active tasks
    with st.sidebar:
        st.header("Active Monitoring Tasks")
        active_tasks = st.session_state.db.get_all_tasks(status="active")

        if not active_tasks:
            st.info("No active tasks. Create one to get started!")

        for task in active_tasks:
            with st.expander(f"Task {task['task_id']}: {task['url'][:30]}..."):
                st.write(f"**URL:** {task['url']}")
                st.write(f"**Frequency:** Every {task['frequency'] // 60} minutes")
                st.write(f"**Monitoring for:** {task['task_prompt']}")
                st.write(f"**Created:** {task['created_at']}")

                if st.button("Pause", key=f"pause_{task['task_id']}"):
                    st.session_state.db.update_task_status(task['task_id'], "paused")
                    st.session_state.scheduler.remove_task(task['task_id'])
                    st.rerun()

    # Main content area
    col1, col2 = st.columns([3, 2])

    with col1:
        st.header("Create Monitoring Task")

        if not st.session_state.confirmation_stage:
            # Instruction input
            st.text_area(
                "What would you like me to monitor?",
                placeholder="Example: Check this https://example.com/careers page every 4 hours and tell me if a new job appears",
                height=100,
                key="instruction"
            )

            st.button("Create Task", on_click=handle_instruction)

            # Example instructions
            with st.expander("Example instructions"):
                st.markdown("""
                - Check this https://example.com/careers page every 4 hours and tell me if a new job appears
                - Monitor https://news.ycombinator.com/ every hour for posts about AI
                - Watch https://github.com/langchain-ai/langchain/releases every day for new releases
                """)
        else:
            # Confirmation stage
            st.subheader("Confirm Task Details")
            task = st.session_state.current_task

            st.markdown(f"""
            **URL:** {task['url']}
            **Check frequency:** Every {task['frequency_seconds'] // 60} minutes
            **What to monitor for:** {task['task_description']}
            """)

            col1a, col1b = st.columns(2)
            with col1a:
                st.button("Confirm", on_click=confirm_task, type="primary")
            with col1b:
                st.button("Cancel", on_click=cancel_task)

    with col2:
        st.header("Recent Change Notifications")

        if not st.session_state.notifications:
            st.info("No changes detected yet. Notifications will appear here.")

        for notification in st.session_state.notifications:
            st.markdown(format_notification(notification))
            st.divider()

if __name__ == "__main__":
    main()
