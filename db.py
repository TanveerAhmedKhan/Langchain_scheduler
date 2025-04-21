"""
Database module for Scout Agent PoC.
Handles SQLite database operations for storing tasks and snapshots.
Thread-safe implementation using connection per operation.
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


class ScoutDatabase:
    def __init__(self, db_path: str = "scout_agent.db"):
        """Initialize the database path and create tables if they don't exist."""
        self.db_path = db_path
        # Create tables on initialization
        self._create_tables()

    def _get_connection(self):
        """Get a new database connection with row factory set."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create tasks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recruiter_id TEXT DEFAULT 'default_user',
                url TEXT NOT NULL,
                frequency INTEGER NOT NULL,  -- in seconds
                task_prompt TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create snapshots table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                raw_html TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id)
            )
            ''')

            conn.commit()
        finally:
            conn.close()

    def add_task(self, url: str, frequency: int, task_prompt: str,
                 recruiter_id: str = "default_user") -> int:
        """
        Add a new monitoring task to the database.

        Args:
            url: The URL to monitor
            frequency: How often to check (in seconds)
            task_prompt: Description of what to monitor
            recruiter_id: Identifier for the user (default: 'default_user')

        Returns:
            The ID of the newly created task
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO tasks (recruiter_id, url, frequency, task_prompt)
            VALUES (?, ?, ?, ?)
            ''', (recruiter_id, url, frequency, task_prompt))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a task by its ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
            task = cursor.fetchone()
            if task:
                return dict(task)
            return None
        finally:
            conn.close()

    def get_all_tasks(self, status: str = "active") -> List[Dict[str, Any]]:
        """Get all tasks with the specified status."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE status = ?', (status,))
            return [dict(task) for task in cursor.fetchall()]
        finally:
            conn.close()

    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update the status of a task."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE tasks SET status = ? WHERE task_id = ?
            ''', (status, task_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def add_snapshot(self, task_id: int, raw_html: str) -> Tuple[int, str]:
        """
        Add a new snapshot for a task.

        Args:
            task_id: The ID of the task
            raw_html: The raw HTML content of the page

        Returns:
            Tuple of (snapshot_id, content_hash)
        """
        # Generate a hash of the content
        content_hash = hashlib.sha256(raw_html.encode()).hexdigest()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO snapshots (task_id, content_hash, raw_html)
            VALUES (?, ?, ?)
            ''', (task_id, content_hash, raw_html))
            conn.commit()
            return cursor.lastrowid, content_hash
        finally:
            conn.close()

    def get_latest_snapshot(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for a task."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM snapshots
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            ''', (task_id,))
            snapshot = cursor.fetchone()
            if snapshot:
                return dict(snapshot)
            return None
        finally:
            conn.close()

    # No need for these methods anymore since we're creating and closing connections as needed
    def close(self):
        """This method is kept for backward compatibility but does nothing."""
        pass

    def __del__(self):
        """No need to close connections since they're closed after each operation."""
        pass
