"""
飞书通知服务 - Feishu Notification Service
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime

import httpx


class FeishuNotifier:
    """飞书机器人通知"""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None
    ):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人 webhook 地址
            app_id: 飞书应用 ID (用于获取 tenant_access_token)
            app_secret: 飞书应用密钥
        """
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")
        self.app_id = app_id or os.getenv("FEISHU_APP_ID", "")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET", "")
        self._tenant_access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def is_enabled(self) -> bool:
        """检查是否已配置飞书通知"""
        return bool(self.webhook_url)
    
    async def _get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        if not self.app_id or not self.app_secret:
            return None
        
        # 检查缓存的 token 是否有效
        if self._tenant_access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._tenant_access_token
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret
                    }
                )
                data = response.json()
                
                if data.get("code") == 0:
                    self._tenant_access_token = data.get("tenant_access_token")
                    # 提前5分钟过期
                    expires_in = data.get("expire", 7200) - 300
                    self._token_expires_at = datetime.now().timestamp() + expires_in
                    return self._tenant_access_token
                else:
                    print(f"Failed to get tenant_access_token: {data}")
                    return None
        except Exception as e:
            print(f"Error getting tenant_access_token: {e}")
            return None
    
    async def send_webhook(self, message: str) -> bool:
        """
        使用 webhook 发送消息
        
        Args:
            message: 消息内容
        
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            print("Feishu webhook URL not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={"msg_type": "text", "content": {"text": message}},
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Feishu webhook: {e}")
            return False
    
    async def send_card(self, title: str, content: str, color: str = "blue") -> bool:
        """
        发送卡片消息
        
        Args:
            title: 卡片标题
            content: 卡片内容
            color: 主题颜色 (blue/green/red/yellow/grey)
        
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            return False
        
        # 颜色映射
        color_map = {
            "blue": "blue",
            "green": "green", 
            "red": "red",
            "yellow": "yellow",
            "grey": "grey",
            "error": "red",
            "warning": "yellow",
            "info": "blue",
            "success": "green"
        }
        theme_color = color_map.get(color, "blue")
        
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": theme_color
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "查看详情"
                                },
                                "type": "primary",
                                "url": "http://localhost:8001"
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=card,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Feishu card: {e}")
            return False
    
    async def send_task_failed_alert(
        self,
        task_id: str,
        task_title: str,
        agent_name: str,
        error_message: Optional[str] = None
    ) -> bool:
        """发送任务失败告警"""
        emoji = "🔴"
        content = f"""**任务失败** {emoji}

**任务ID**: {task_id}
**任务标题**: {task_title}
**执行Agent**: {agent_name}
**失败时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        if error_message:
            content += f"""

**错误信息**:
```
{error_message[:500]}
```"""
        
        return await self.send_card(
            title="🚨 任务执行失败",
            content=content,
            color="red"
        )
    
    async def send_task_timeout_alert(
        self,
        task_id: str,
        task_title: str,
        agent_name: str,
        timeout_minutes: int,
        started_at: str
    ) -> bool:
        """发送任务超时告警"""
        emoji = "⚠️"
        content = f"""**任务执行超时** {emoji}

**任务ID**: {task_id}
**任务标题**: {task_title}
**执行Agent**: {agent_name}
**超时时间**: {timeout_minutes} 分钟
**开始时间**: {started_at}
**当前时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return await self.send_card(
            title="⏰ 任务执行超时",
            content=content,
            color="yellow"
        )
    
    async def send_daily_summary(
        self,
        total_tasks: int,
        completed: int,
        failed: int,
        running: int,
        failed_tasks: list,
        agent_stats: list
    ) -> bool:
        """发送每日汇总报告"""
        emoji = "📊"
        
        success_rate = round(completed / total_tasks * 100, 1) if total_tasks > 0 else 0
        
        # 失败任务列表
        failed_list = ""
        if failed_tasks:
            failed_list = "\n**失败任务:**\n"
            for task in failed_tasks[:5]:  # 最多显示5个
                failed_list += f"- {task['task_id']}: {task['title'][:50]}\n"
            if len(failed_tasks) > 5:
                failed_list += f"- ...还有 {len(failed_tasks) - 5} 个失败任务\n"
        
        # Agent 统计
        agent_summary = "\n**各智能体任务统计:**\n"
        for agent in agent_stats:
            rate = round(agent['completed'] / agent['total'] * 100, 1) if agent['total'] > 0 else 0
            agent_summary += f"- {agent['display_name']}: 完成 {agent['completed']}/{agent['total']} (成功率 {rate}%)\n"
        
        content = f"""**每日任务汇总报告** {emoji}

**汇总统计:**
- 总任务数: {total_tasks}
- ✅ 完成: {completed}
- 🔴 失败: {failed}
- 🔵 进行中: {running}
- 成功率: {success_rate}%

{failed_list}
{agent_summary}

**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return await self.send_card(
            title="📈 每日任务汇总报告",
            content=content,
            color="blue"
        )


def create_feishu_notifier(config: Optional[Dict[str, Any]] = None) -> FeishuNotifier:
    """
    创建飞书通知器
    
    Args:
        config: 配置字典，可以包含 webhook_url, app_id, app_secret
    
    Returns:
        FeishuNotifier 实例
    """
    if config is None:
        config = {}
    
    return FeishuNotifier(
        webhook_url=config.get("webhook_url"),
        app_id=config.get("app_id"),
        app_secret=config.get("app_secret")
    )
