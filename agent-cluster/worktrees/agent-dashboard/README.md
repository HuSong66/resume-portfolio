# Agent Cluster Dashboard

智能体集群监控面板，监控 Chief/Coder/HR/Analyst/Ops 五个智能体的任务执行情况。

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 访问 Dashboard
http://localhost:8001
```

## 项目结构

```
agent-dashboard/
├── app/
│   ├── main.py          # FastAPI 主程序
│   ├── models.py        # 数据模型
│   ├── collector.py     # 数据采集
│   ├── database.py      # 数据库管理
│   └── routers/
│       └── api.py       # API 接口
├── static/
│   └── index.html       # 前端页面
├── data/
│   └── dashboard.db     # SQLite 数据库
├── requirements.txt     # 依赖
└── README.md
```

## API 接口

- `GET /api/agents` - 获取所有智能体状态
- `GET /api/agents/{name}` - 获取指定智能体状态
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/history` - 获取历史记录
- `GET /api/stats` - 获取统计数据

## 智能体

| 智能体 | 说明 |
|--------|------|
| Chief | 主管智能体，负责任务分配 |
| Coder | 程序员智能体，负责代码开发 |
| HR | 人力资源智能体，负责招聘 |
| Analyst | 分析师智能体，负责数据分析 |
| Ops | 运维智能体，负责系统运维 |
