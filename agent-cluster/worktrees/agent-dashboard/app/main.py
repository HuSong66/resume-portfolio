"""
FastAPI application entry point for Agent Cluster Dashboard.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import DatabaseManager
from app.collector import DataCollector
from app.routers.api import router as api_router, set_db_manager


# Determine base directory
BASE_DIR = Path(__file__).parent.parent

# Database path
DB_PATH = os.path.join(BASE_DIR, "data", "dashboard.db")

# Global instances
db_manager: DatabaseManager = None
collector: DataCollector = None
scheduler: AsyncIOScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global db_manager, collector, scheduler
    
    # Initialize database
    print(f"Initializing database: {DB_PATH}")
    db_manager = DatabaseManager(DB_PATH)
    set_db_manager(db_manager)
    
    # Initialize collector
    collector = DataCollector(db_manager)
    
    # Initial data sync
    print("Running initial data sync...")
    sync_result = collector.sync_all()
    print(f"Sync result: {sync_result}")
    
    # Setup scheduled tasks
    scheduler = AsyncIOScheduler()
    
    # Schedule periodic data sync (every 30 seconds)
    scheduler.add_job(
        collector.sync_all,
        'interval',
        seconds=30,
        id='data_sync',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started with periodic data sync (every 30 seconds)")
    
    print("Application startup completed successfully")
    
    yield
    
    # Shutdown
    print("Shutting down application...")
    
    if scheduler:
        scheduler.shutdown(wait=False)
        print("Scheduler stopped")
    
    print("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Agent Cluster Dashboard",
    description="智能体集群监控面板 - 监控 Chief/Coder/HR/Analyst/Ops 五个智能体的任务执行情况",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(api_router)

# Mount static files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Root endpoint - serve dashboard."""
    index_path = BASE_DIR / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "Agent Cluster Dashboard API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/dashboard")
async def dashboard():
    """Serve web dashboard."""
    index_path = BASE_DIR / "static" / "index.html"
    return FileResponse(str(index_path))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": db_manager is not None,
        "scheduler": scheduler is not None and scheduler.running
    }


@app.post("/api/sync")
async def trigger_sync():
    """Manually trigger data sync."""
    if not collector:
        return {"error": "Collector not initialized"}
    
    result = collector.sync_all()
    return {
        "success": True,
        "result": result
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
