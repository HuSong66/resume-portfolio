"""
API routes for Agent Cluster Dashboard.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query

from app.database import DatabaseManager
from app.alerts import create_alert_manager


router = APIRouter(prefix="/api", tags=["api"])

# Global database manager instance
db_manager: DatabaseManager = None


def set_db_manager(db: DatabaseManager):
    """Set the global database manager."""
    global db_manager
    db_manager = db


# Agents endpoints
@router.get("/agents")
async def get_agents():
    """Get all agents with their status."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    agents = db_manager.get_all_agents()
    return [
        {
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "status": agent.status,
            "current_task_id": agent.current_task_id,
            "statistics": {
                "total_tasks": agent.total_tasks,
                "completed_tasks": agent.completed_tasks,
                "failed_tasks": agent.failed_tasks,
                "success_rate": round(agent.completed_tasks / agent.total_tasks * 100, 1) if agent.total_tasks > 0 else 0,
                "total_tokens": agent.total_tokens,
                "input_tokens": agent.input_tokens,
                "output_tokens": agent.output_tokens
            },
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
        }
        for agent in agents
    ]


@router.get("/agents/{name}")
async def get_agent(name: str):
    """Get specific agent by name."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    agent = db_manager.get_agent(name)
    if not agent:
        return {"error": f"Agent '{name}' not found"}
    
    return {
        "name": agent.name,
        "display_name": agent.display_name,
        "description": agent.description,
        "status": agent.status,
        "current_task_id": agent.current_task_id,
        "statistics": {
            "total_tasks": agent.total_tasks,
            "completed_tasks": agent.completed_tasks,
            "failed_tasks": agent.failed_tasks,
            "success_rate": round(agent.completed_tasks / agent.total_tasks * 100, 1) if agent.total_tasks > 0 else 0,
            "total_tokens": agent.total_tokens,
            "input_tokens": agent.input_tokens,
            "output_tokens": agent.output_tokens
        },
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }


# Tasks endpoints
@router.get("/tasks")
async def get_tasks(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500)
):
    """Get tasks with optional filters."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    tasks = db_manager.get_tasks(agent_name=agent_name, status=status, limit=limit)
    return [
        {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "agent_name": task.agent_name,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration": task.duration,
            "input_tokens": task.input_tokens,
            "output_tokens": task.output_tokens,
            "error_message": task.error_message,
            "requester": task.requester
        }
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get specific task by ID."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    task = db_manager.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}
    
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "agent_name": task.agent_name,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "duration": task.duration,
        "input_tokens": task.input_tokens,
        "output_tokens": task.output_tokens,
        "error_message": task.error_message,
        "requester": task.requester
    }


# History endpoint
@router.get("/tasks/history")
async def get_task_history(
    agent_name: Optional[str] = None,
    days: int = Query(7, le=30),
    limit: int = Query(50, le=200)
):
    """Get task history."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    # Get tasks from the last N days
    cutoff = datetime.utcnow() - timedelta(days=days)
    tasks = db_manager.get_tasks(agent_name=agent_name, limit=limit)
    
    # Filter by date
    filtered_tasks = [t for t in tasks if t.created_at and t.created_at >= cutoff]
    
    return [
        {
            "task_id": task.task_id,
            "title": task.title,
            "status": task.status,
            "agent_name": task.agent_name,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration": task.duration,
            "success": task.status == "completed"
        }
        for task in filtered_tasks
    ]


# Statistics endpoint
@router.get("/stats")
async def get_stats():
    """Get overall statistics."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    return db_manager.get_stats()


# Alerts endpoints
@router.get("/alerts")
async def get_alerts(limit: int = Query(50, le=200)):
    """Get recent alerts."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    alerts = db_manager.get_alerts(limit=limit)
    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "agent_name": alert.agent_name,
            "task_id": alert.task_id,
            "is_sent": alert.is_sent,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "sent_at": alert.sent_at.isoformat() if alert.sent_at else None
        }
        for alert in alerts
    ]


# Alert management endpoints
@router.post("/alerts/check")
async def trigger_alert_check():
    """Manually trigger alert check."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    alert_manager = create_alert_manager(db_manager)
    result = await alert_manager.check_and_alert()
    return {
        "success": True,
        "result": result
    }


@router.post("/alerts/summary")
async def trigger_daily_summary():
    """Manually trigger daily summary."""
    if not db_manager:
        return {"error": "Database not initialized"}
    
    alert_manager = create_alert_manager(db_manager)
    success = await alert_manager.send_daily_summary()
    return {
        "success": success
    }


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": db_manager is not None
    }
