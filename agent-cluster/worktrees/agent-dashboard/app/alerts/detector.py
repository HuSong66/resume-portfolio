"""
告警检测器 - Alert Detector
检测任务失败、执行超时等情况并生成告警
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.database import DatabaseManager
from app.models import Task, Alert, TaskStatus


@dataclass
class AlertConfig:
    """告警配置"""
    # 任务超时时间（分钟）
    task_timeout_minutes: int = 30
    
    # 是否启用任务失败告警
    enable_task_failure_alert: bool = True
    
    # 是否启用任务超时告警
    enable_task_timeout_alert: bool = True
    
    # 是否启用每日汇总
    enable_daily_summary: bool = True
    
    # 每日汇总发送时间 (小时, UTC)
    daily_summary_hour: int = 9
    
    # 每日汇总发送时间 (分钟)
    daily_summary_minute: int = 0


class AlertDetector:
    """告警检测器"""
    
    def __init__(self, db: DatabaseManager, config: Optional[AlertConfig] = None):
        self.db = db
        self.config = config or AlertConfig()
        # 记录已发送过的超时告警，避免重复发送
        self._timeout_alerts_sent: set = set()
    
    def check_task_failure(self, task: Task) -> Optional[Alert]:
        """
        检查任务是否失败并需要告警
        
        Args:
            task: 任务对象
        
        Returns:
            Alert 对象或 None
        """
        if not self.config.enable_task_failure_alert:
            return None
        
        if task.status == TaskStatus.FAILED.value:
            # 检查是否已存在未发送的相同告警
            existing_alerts = self.db.get_alerts(limit=100)
            for alert in existing_alerts:
                if alert.task_id == task.task_id and alert.alert_type == "task_failure" and not alert.is_sent:
                    return None  # 已有未发送的告警
            
            return self.db.create_alert(
                alert_type="task_failure",
                title=f"任务执行失败: {task.title[:50]}",
                message=task.error_message or "任务执行失败",
                severity="error",
                agent_name=task.agent_name,
                task_id=task.task_id
            )
        
        return None
    
    def check_task_timeout(self, task: Task) -> Optional[Alert]:
        """
        检查任务是否超时
        
        Args:
            task: 任务对象
        
        Returns:
            Alert 对象或 None
        """
        if not self.config.enable_task_timeout_alert:
            return None
        
        # 只检查正在运行的任务
        if task.status != TaskStatus.RUNNING.value:
            return None
        
        if not task.started_at:
            return None
        
        # 检查是否超时
        elapsed = datetime.utcnow() - task.started_at
        timeout_seconds = self.config.task_timeout_minutes * 60
        
        if elapsed.total_seconds() > timeout_seconds:
            # 检查是否已发送过超时告警
            if task.task_id in self._timeout_alerts_sent:
                return None
            
            # 记录已发送
            self._timeout_alerts_sent.add(task.task_id)
            
            return self.db.create_alert(
                alert_type="task_timeout",
                title=f"任务执行超时: {task.title[:50]}",
                message=f"任务已运行超过 {self.config.task_timeout_minutes} 分钟未完成",
                severity="warning",
                agent_name=task.agent_name,
                task_id=task.task_id
            )
        
        return None
    
    def check_all_tasks(self) -> List[Alert]:
        """
        检查所有任务并生成告警
        
        Returns:
            生成的告警列表
        """
        alerts = []
        
        # 获取所有任务
        tasks = self.db.get_tasks(limit=500)
        
        for task in tasks:
            # 检查失败
            failure_alert = self.check_task_failure(task)
            if failure_alert:
                alerts.append(failure_alert)
            
            # 检查超时
            timeout_alert = self.check_task_timeout(task)
            if timeout_alert:
                alerts.append(timeout_alert)
        
        return alerts
    
    def get_failed_tasks_for_summary(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取指定时间之后的失败任务"""
        if since is None:
            since = datetime.utcnow() - timedelta(days=1)
        
        tasks = self.db.get_tasks(status=TaskStatus.FAILED.value, limit=100)
        
        return [
            {
                "task_id": task.task_id,
                "title": task.title,
                "agent_name": task.agent_name,
                "error_message": task.error_message,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
            if task.completed_at and task.completed_at >= since
        ]
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """获取每日统计数据"""
        stats = self.db.get_stats()
        agents = self.db.get_all_agents()
        
        return {
            "total_tasks": stats.get("total_tasks", 0),
            "completed": stats.get("completed_tasks", 0),
            "failed": stats.get("failed_tasks", 0),
            "running": stats.get("running_tasks", 0),
            "failed_tasks": self.get_failed_tasks_for_summary(),
            "agent_stats": [
                {
                    "name": agent.name,
                    "display_name": agent.display_name,
                    "total": agent.total_tasks,
                    "completed": agent.completed_tasks,
                    "failed": agent.failed_tasks
                }
                for agent in agents
            ]
        }


def create_alert_detector(config: Optional[Dict[str, Any]] = None) -> AlertDetector:
    """
    创建告警检测器
    
    Args:
        config: 配置字典
    
    Returns:
        AlertDetector 实例
    """
    if config is None:
        # 从环境变量加载配置
        config = {
            "task_timeout_minutes": int(os.getenv("ALERT_TASK_TIMEOUT_MINUTES", "30")),
            "enable_task_failure_alert": os.getenv("ENABLE_TASK_FAILURE_ALERT", "true").lower() == "true",
            "enable_task_timeout_alert": os.getenv("ENABLE_TASK_TIMEOUT_ALERT", "true").lower() == "true",
            "enable_daily_summary": os.getenv("ENABLE_DAILY_SUMMARY", "true").lower() == "true",
            "daily_summary_hour": int(os.getenv("DAILY_SUMMARY_HOUR", "9")),
            "daily_summary_minute": int(os.getenv("DAILY_SUMMARY_MINUTE", "0")),
        }
    
    alert_config = AlertConfig(
        task_timeout_minutes=config.get("task_timeout_minutes", 30),
        enable_task_failure_alert=config.get("enable_task_failure_alert", True),
        enable_task_timeout_alert=config.get("enable_task_timeout_alert", True),
        enable_daily_summary=config.get("enable_daily_summary", True),
        daily_summary_hour=config.get("daily_summary_hour", 9),
        daily_summary_minute=config.get("daily_summary_minute", 0),
    )
    
    return AlertDetector(db=None, config=alert_config)
