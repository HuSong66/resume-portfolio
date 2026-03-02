"""
告警管理器 - Alert Manager
协调告警检测和通知发送
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from app.database import DatabaseManager
from app.alerts.detector import AlertDetector, AlertConfig
from app.alerts.feishu import FeishuNotifier


class AlertManager:
    """告警管理器"""
    
    def __init__(
        self,
        db: DatabaseManager,
        notifier: Optional[FeishuNotifier] = None,
        config: Optional[AlertConfig] = None
    ):
        self.db = db
        self.notifier = notifier or FeishuNotifier()
        self.detector = AlertDetector(db, config)
        self._last_summary_time: Optional[datetime] = None
    
    async def check_and_alert(self) -> Dict[str, Any]:
        """
        检查所有任务并发送告警
        
        Returns:
            告警检查结果
        """
        results = {
            "alerts_generated": 0,
            "alerts_sent": 0,
            "errors": []
        }
        
        # 检查任务并生成告警
        alerts = self.detector.check_all_tasks()
        results["alerts_generated"] = len(alerts)
        
        # 发送告警
        if self.notifier.is_enabled():
            for alert in alerts:
                try:
                    success = await self._send_alert(alert)
                    if success:
                        # 标记为已发送
                        self.db.mark_alert_sent(alert.id)
                        results["alerts_sent"] += 1
                except Exception as e:
                    results["errors"].append(str(e))
        
        return results
    
    async def _send_alert(self, alert) -> bool:
        """发送单个告警"""
        if alert.alert_type == "task_failure":
            return await self.notifier.send_task_failed_alert(
                task_id=alert.task_id or "",
                task_title=alert.title,
                agent_name=alert.agent_name or "",
                error_message=alert.message
            )
        elif alert.alert_type == "task_timeout":
            return await self.notifier.send_task_timeout_alert(
                task_id=alert.task_id or "",
                task_title=alert.title,
                agent_name=alert.agent_name or "",
                timeout_minutes=self.detector.config.task_timeout_minutes,
                started_at=""  # 需要从任务中获取
            )
        else:
            # 通用告警
            return await self.notifier.send_card(
                title=alert.title,
                content=alert.message or "",
                color=alert.severity
            )
    
    async def send_daily_summary(self) -> bool:
        """
        发送每日汇总报告
        
        Returns:
            是否发送成功
        """
        if not self.notifier.is_enabled():
            return False
        
        if not self.detector.config.enable_daily_summary:
            return False
        
        # 获取昨日统计数据
        yesterday = datetime.utcnow() - timedelta(days=1)
        stats = self.detector.get_daily_stats()
        
        # 获取失败任务
        failed_tasks = [
            {
                "task_id": task["task_id"],
                "title": task["title"]
            }
            for task in stats.get("failed_tasks", [])
        ]
        
        success = await self.notifier.send_daily_summary(
            total_tasks=stats.get("total_tasks", 0),
            completed=stats.get("completed", 0),
            failed=stats.get("failed", 0),
            running=stats.get("running", 0),
            failed_tasks=failed_tasks,
            agent_stats=stats.get("agent_stats", [])
        )
        
        if success:
            self._last_summary_time = datetime.utcnow()
        
        return success
    
    async def trigger_sync_and_check(self) -> Dict[str, Any]:
        """
        触发同步并检查告警（由 scheduler 调用）
        
        Returns:
            检查结果
        """
        return await self.check_and_alert()


def create_alert_manager(
    db: DatabaseManager,
    config: Optional[Dict[str, Any]] = None
) -> AlertManager:
    """
    创建告警管理器
    
    Args:
        db: 数据库管理器
        config: 配置字典
    
    Returns:
        AlertManager 实例
    """
    # 创建飞书通知器
    notifier = FeishuNotifier(
        webhook_url=os.getenv("FEISHU_WEBHOOK_URL"),
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET")
    )
    
    # 创建告警配置
    alert_config = AlertConfig(
        task_timeout_minutes=int(os.getenv("ALERT_TASK_TIMEOUT_MINUTES", "30")),
        enable_task_failure_alert=os.getenv("ENABLE_TASK_FAILURE_ALERT", "true").lower() == "true",
        enable_task_timeout_alert=os.getenv("ENABLE_TASK_TIMEOUT_ALERT", "true").lower() == "true",
        enable_daily_summary=os.getenv("ENABLE_DAILY_SUMMARY", "true").lower() == "true",
        daily_summary_hour=int(os.getenv("DAILY_SUMMARY_HOUR", "9")),
        daily_summary_minute=int(os.getenv("DAILY_SUMMARY_MINUTE", "0")),
    )
    
    return AlertManager(db, notifier, alert_config)
