"""
Data collector for Agent Cluster Dashboard.
Collects data from OpenClaw cron logs and active-tasks.json.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.database import DatabaseManager
from app.models import TaskStatus, AgentStatus


class DataCollector:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.agent_cluster_path = "C:\\Users\\husong\\clawd\\agent-cluster"
        self.active_tasks_file = os.path.join(self.agent_cluster_path, "active-tasks.json")
    
    def collect_from_active_tasks(self) -> Dict[str, Any]:
        """Collect data from active-tasks.json."""
        result = {"processed": 0, "errors": 0}
        
        try:
            if not os.path.exists(self.active_tasks_file):
                return result
            
            with open(self.active_tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            tasks = data.get("tasks", [])
            for task in tasks:
                try:
                    self._process_task(task)
                    result["processed"] += 1
                except Exception as e:
                    result["errors"] += 1
            
        except Exception as e:
            result["errors"] += 1
        
        return result
    
    def _process_task(self, task_data: Dict[str, Any]):
        """Process a single task from active-tasks.json."""
        task_id = task_data.get("id", "")
        if not task_id:
            return
        
        title = task_data.get("title", "")
        description = task_data.get("description")
        status = task_data.get("status", "pending")
        assignee = task_data.get("assignee")
        priority = task_data.get("priority", "normal")
        requester = task_data.get("requester")
        
        # Map status
        status_map = {
            "pending": TaskStatus.PENDING,
            "in_progress": TaskStatus.RUNNING,
            "completed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED
        }
        task_status = status_map.get(status, TaskStatus.PENDING)
        
        # Check if task exists
        existing_task = self.db.get_task(task_id)
        
        if existing_task:
            # Update existing task
            if existing_task.status != task_status:
                self.db.update_task_status(
                    task_id,
                    task_status.value,
                    completed_at=datetime.utcnow() if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED] else None
                )
        else:
            # Create new task
            self.db.create_task(
                task_id=task_id,
                title=title,
                description=description,
                agent_name=assignee,
                priority=priority,
                requester=requester
            )
            
            # Update task status if needed
            if task_status != TaskStatus.PENDING:
                self.db.update_task_status(
                    task_id,
                    task_status.value,
                    started_at=datetime.utcnow() if task_status == TaskStatus.RUNNING else None,
                    completed_at=datetime.utcnow() if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED] else None
                )
        
        # Update agent status
        if assignee:
            agent_status = AgentStatus.BUSY if task_status == TaskStatus.RUNNING else AgentStatus.IDLE
            self.db.update_agent_status(
                assignee,
                agent_status.value,
                current_task_id=task_id if task_status == TaskStatus.RUNNING else None
            )
    
    def collect_from_cron_logs(self, logs_dir: Optional[str] = None) -> Dict[str, Any]:
        """Collect data from OpenClaw cron logs."""
        result = {"processed": 0, "errors": 0}
        
        if logs_dir is None:
            logs_dir = os.path.join(self.agent_cluster_path, "logs")
        
        if not os.path.exists(logs_dir):
            return result
        
        # Process log files
        for filename in os.listdir(logs_dir):
            if filename.endswith(".log"):
                try:
                    log_path = os.path.join(logs_dir, filename)
                    with open(log_path, "r", encoding="utf-8") as f:
                        # Simple log processing - just count for now
                        lines = f.readlines()
                        result["processed"] += len(lines)
                except Exception:
                    result["errors"] += 1
        
        return result
    
    def sync_all(self) -> Dict[str, Any]:
        """Sync all data sources."""
        active_tasks_result = self.collect_from_active_tasks()
        cron_logs_result = self.collect_from_cron_logs()
        
        return {
            "active_tasks": active_tasks_result,
            "cron_logs": cron_logs_result,
            "timestamp": datetime.utcnow().isoformat()
        }
