"""
Scheduler module for Scout Agent PoC.
Handles scheduling and executing monitoring tasks.
"""

import logging
from typing import Dict, Any, List, Callable
from datetime import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from db import ScoutDatabase
from scraper import WebScraper

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, db: ScoutDatabase, scraper: WebScraper, 
                 notification_callback: Callable[[Dict[str, Any]], None] = None):
        """
        Initialize the task scheduler.
        
        Args:
            db: Database instance
            scraper: WebScraper instance
            notification_callback: Function to call when changes are detected
        """
        self.db = db
        self.scraper = scraper
        self.notification_callback = notification_callback
        
        # Initialize the scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Dictionary to keep track of job IDs
        self.job_map = {}
        
        logger.info("Task scheduler initialized")
    
    def schedule_all_tasks(self):
        """Schedule all active tasks from the database."""
        active_tasks = self.db.get_all_tasks(status="active")
        for task in active_tasks:
            self.schedule_task(task)
        
        logger.info(f"Scheduled {len(active_tasks)} active tasks")
    
    def schedule_task(self, task: Dict[str, Any]):
        """
        Schedule a single task.
        
        Args:
            task: Task details dictionary
        """
        task_id = task["task_id"]
        
        # Remove any existing job for this task
        self.remove_task(task_id)
        
        # Add the new job
        job = self.scheduler.add_job(
            self.execute_task,
            IntervalTrigger(seconds=task["frequency"]),
            args=[task],
            id=f"task_{task_id}",
            replace_existing=True
        )
        
        self.job_map[task_id] = job.id
        logger.info(f"Scheduled task {task_id} to run every {task['frequency']} seconds")
    
    def remove_task(self, task_id: int):
        """
        Remove a scheduled task.
        
        Args:
            task_id: ID of the task to remove
        """
        job_id = self.job_map.get(task_id)
        if job_id:
            try:
                self.scheduler.remove_job(job_id)
                del self.job_map[task_id]
                logger.info(f"Removed scheduled task {task_id}")
            except JobLookupError:
                logger.warning(f"Job {job_id} for task {task_id} not found")
    
    def execute_task(self, task: Dict[str, Any]):
        """
        Execute a monitoring task.
        
        Args:
            task: Task details dictionary
        """
        task_id = task["task_id"]
        url = task["url"]
        task_prompt = task["task_prompt"]
        
        logger.info(f"Executing task {task_id} for URL: {url}")
        
        # Fetch the page
        success, content = self.scraper.fetch_page(url)
        if not success:
            logger.error(f"Failed to fetch {url}: {content}")
            return
        
        # Get the latest snapshot
        latest_snapshot = self.db.get_latest_snapshot(task_id)
        
        # If this is the first check, just save the snapshot
        if not latest_snapshot:
            snapshot_id, content_hash = self.db.add_snapshot(task_id, content)
            logger.info(f"Initial snapshot {snapshot_id} saved for task {task_id}")
            return
        
        # Compare with the previous snapshot
        changed, details = self.scraper.compare_content(latest_snapshot["raw_html"], content)
        
        if changed:
            # Save the new snapshot
            snapshot_id, content_hash = self.db.add_snapshot(task_id, content)
            logger.info(f"Change detected for task {task_id}, saved as snapshot {snapshot_id}")
            
            # Add task details to the notification
            notification = {
                "task_id": task_id,
                "url": url,
                "task_prompt": task_prompt,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            # Call the notification callback if provided
            if self.notification_callback:
                self.notification_callback(notification)
            else:
                logger.info(f"Change notification: {notification}")
        else:
            logger.info(f"No changes detected for task {task_id}")
    
    def shutdown(self):
        """Shut down the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler shut down")
    
    def __del__(self):
        """Ensure the scheduler is shut down when the object is deleted."""
        self.shutdown()
