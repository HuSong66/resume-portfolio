"""
Database management for Agent Cluster Dashboard.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Agent, Task, Alert, AgentStatus, TaskStatus


class DatabaseManager:
    def __init__(self, db_path: str = "data/dashboard.db"):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine with SQLite
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize database
        self.init_db()
    
    def init_db(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)
        
        # Initialize default agents if not exist
        self._init_default_agents()
    
    def _init_default_agents(self):
        """Initialize default agents."""
        with self.get_session() as session:
            # Check if agents exist
            result = session.execute(select(func.count(Agent.id)))
            if result.scalar() == 0:
                default_agents = [
                    {"name": "chief", "display_name": "Chief", "description": "主管智能体，负责任务分配和协调"},
                    {"name": "coder", "display_name": "Coder", "description": "程序员智能体，负责代码开发"},
                    {"name": "hr", "display_name": "HR", "description": "人力资源智能体，负责招聘和人员管理"},
                    {"name": "analyst", "display_name": "Analyst", "description": "分析师智能体，负责数据分析和报告"},
                    {"name": "ops", "display_name": "Ops", "description": "运维智能体，负责系统运维和监控"},
                ]
                for agent_data in default_agents:
                    agent = Agent(
                        name=agent_data["name"],
                        display_name=agent_data["display_name"],
                        description=agent_data["description"],
                        status=AgentStatus.IDLE
                    )
                    session.add(agent)
                session.commit()
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    # Agent operations
    def get_all_agents(self) -> List[Agent]:
        """Get all agents."""
        with self.get_session() as session:
            return session.execute(select(Agent)).scalars().all()
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        with self.get_session() as session:
            return session.execute(
                select(Agent).where(Agent.name == name)
            ).scalar_one_or_none()
    
    def update_agent_status(self, name: str, status: str, current_task_id: Optional[str] = None):
        """Update agent status."""
        with self.get_session() as session:
            agent = session.execute(
                select(Agent).where(Agent.name == name)
            ).scalar_one_or_none()
            
            if agent:
                agent.status = status
                if current_task_id:
                    agent.current_task_id = current_task_id
                agent.updated_at = datetime.utcnow()
                session.commit()
    
    def update_agent_stats(self, name: str, **kwargs):
        """Update agent statistics."""
        with self.get_session() as session:
            agent = session.execute(
                select(Agent).where(Agent.name == name)
            ).scalar_one_or_none()
            
            if agent:
                for key, value in kwargs.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)
                session.commit()
    
    # Task operations
    def create_task(self, task_id: str, title: str, agent_name: Optional[str] = None,
                    description: Optional[str] = None, priority: str = "normal",
                    requester: Optional[str] = None) -> Task:
        """Create a new task."""
        with self.get_session() as session:
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                agent_name=agent_name,
                priority=priority,
                requester=requester,
                status=TaskStatus.PENDING
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
    
    def update_task_status(self, task_id: str, status: str, 
                          started_at: Optional[datetime] = None,
                          completed_at: Optional[datetime] = None,
                          error_message: Optional[str] = None):
        """Update task status."""
        with self.get_session() as session:
            task = session.execute(
                select(Task).where(Task.task_id == task_id)
            ).scalar_one_or_none()
            
            if task:
                task.status = status
                if started_at:
                    task.started_at = started_at
                if completed_at:
                    task.completed_at = completed_at
                    if task.started_at:
                        task.duration = (completed_at - task.started_at).total_seconds()
                if error_message:
                    task.error_message = error_message
                session.commit()
                
                # Update agent stats if task completed
                if agent_name := task.agent_name:
                    self._update_agent_task_stats(agent_name, status)
    
    def _update_agent_task_stats(self, agent_name: str, status: str):
        """Update agent task statistics."""
        with self.get_session() as session:
            agent = session.execute(
                select(Agent).where(Agent.name == agent_name)
            ).scalar_one_or_none()
            
            if agent:
                agent.total_tasks += 1
                if status == TaskStatus.COMPLETED:
                    agent.completed_tasks += 1
                elif status == TaskStatus.FAILED:
                    agent.failed_tasks += 1
                session.commit()
    
    def get_tasks(self, agent_name: Optional[str] = None, status: Optional[str] = None,
                  limit: int = 100) -> List[Task]:
        """Get tasks with optional filters."""
        with self.get_session() as session:
            query = select(Task)
            
            if agent_name:
                query = query.where(Task.agent_name == agent_name)
            if status:
                query = query.where(Task.status == status)
            
            query = query.order_by(Task.created_at.desc()).limit(limit)
            return session.execute(query).scalars().all()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by task_id."""
        with self.get_session() as session:
            return session.execute(
                select(Task).where(Task.task_id == task_id)
            ).scalar_one_or_none()
    
    # Alert operations
    def create_alert(self, alert_type: str, title: str, message: Optional[str] = None,
                     severity: str = "info", agent_name: Optional[str] = None,
                     task_id: Optional[str] = None) -> Alert:
        """Create a new alert."""
        with self.get_session() as session:
            alert = Alert(
                alert_type=alert_type,
                title=title,
                message=message,
                severity=severity,
                agent_name=agent_name,
                task_id=task_id
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert
    
    def get_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        with self.get_session() as session:
            return session.execute(
                select(Alert).order_by(Alert.created_at.desc()).limit(limit)
            ).scalars().all()
    
    def mark_alert_sent(self, alert_id: int):
        """Mark alert as sent."""
        with self.get_session() as session:
            alert = session.get(Alert, alert_id)
            if alert:
                alert.is_sent = True
                alert.sent_at = datetime.utcnow()
                session.commit()
    
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        with self.get_session() as session:
            # Task stats
            total_tasks = session.execute(select(func.count(Task.id))).scalar()
            completed_tasks = session.execute(
                select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED)
            ).scalar()
            failed_tasks = session.execute(
                select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED)
            ).scalar()
            running_tasks = session.execute(
                select(func.count(Task.id)).where(Task.status == TaskStatus.RUNNING)
            ).scalar()
            
            # Token stats
            total_input_tokens = session.execute(
                select(func.sum(Task.input_tokens))
            ).scalar() or 0
            total_output_tokens = session.execute(
                select(func.sum(Task.output_tokens))
            ).scalar() or 0
            
            # Alert stats
            total_alerts = session.execute(select(func.count(Alert.id))).scalar()
            unsent_alerts = session.execute(
                select(func.count(Alert.id)).where(Alert.is_sent == False)
            ).scalar()
            
            # Agent stats
            total_agents = session.execute(select(func.count(Agent.id))).scalar()
            active_agents = session.execute(
                select(func.count(Agent.id)).where(Agent.status == AgentStatus.BUSY)
            ).scalar()
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "success_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_alerts": total_alerts,
                "unsent_alerts": unsent_alerts,
                "total_agents": total_agents,
                "active_agents": active_agents
            }
