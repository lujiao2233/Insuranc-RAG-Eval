from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config.database import get_db
from models.database import ApiUsageLog, User
from api.dependencies import get_current_user

router = APIRouter()

@router.get("/stats", response_model=Dict[str, Any])
async def get_usage_stats(
    days: int = Query(7, description="查询过去几天的统计数据"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取API调用的Token消耗统计"""
    try:
        # 计算时间范围
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 1. 获取总消耗和总次数
        total_stats = db.query(
            func.count(ApiUsageLog.id).label("total_calls"),
            func.sum(ApiUsageLog.total_tokens).label("total_tokens")
        ).first()
        
        # 2. 按模块分组统计
        module_stats = db.query(
            ApiUsageLog.module_name,
            func.count(ApiUsageLog.id).label("calls"),
            func.sum(ApiUsageLog.total_tokens).label("tokens"),
            func.avg(ApiUsageLog.latency_ms).label("avg_latency")
        ).group_by(ApiUsageLog.module_name).all()
        
        # 3. 按天分组趋势统计 (最近days天)
        # 注意: SQLite 和 MySQL 的 date 函数不同。假设这里是 MySQL 或可以处理 func.date
        trend_stats = db.query(
            func.date(ApiUsageLog.created_at).label("date"),
            func.count(ApiUsageLog.id).label("calls"),
            func.sum(ApiUsageLog.total_tokens).label("tokens"),
            func.avg(ApiUsageLog.latency_ms).label("avg_latency")
        ).filter(
            ApiUsageLog.created_at >= start_date
        ).group_by(
            func.date(ApiUsageLog.created_at)
        ).order_by(
            func.date(ApiUsageLog.created_at)
        ).all()
        
        # 格式化结果
        modules_data = [
            {
                "module": row.module_name, 
                "calls": row.calls, 
                "tokens": row.tokens or 0,
                "avg_latency": round(row.avg_latency or 0)
            }
            for row in module_stats
        ]
        
        trend_data = [
            {
                "date": str(row.date), 
                "calls": row.calls, 
                "tokens": row.tokens or 0,
                "avg_latency": round(row.avg_latency or 0)
            }
            for row in trend_stats
        ]
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_calls": total_stats.total_calls or 0,
                    "total_tokens": total_stats.total_tokens or 0,
                },
                "modules": modules_data,
                "trend": trend_data
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.get("/events", response_model=Dict[str, Any])
async def get_usage_events(
    start: Optional[datetime] = Query(None, description="开始时间（ISO8601）"),
    end: Optional[datetime] = Query(None, description="结束时间（ISO8601）"),
    limit: int = Query(2000, ge=1, le=20000, description="返回事件条数上限"),
    module_name: Optional[str] = Query(None, description="按模块过滤"),
    model_name: Optional[str] = Query(None, description="按模型过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        end_dt = end or datetime.utcnow()
        start_dt = start or (end_dt - timedelta(hours=24))

        q = db.query(ApiUsageLog).filter(
            ApiUsageLog.created_at >= start_dt,
            ApiUsageLog.created_at <= end_dt
        )
        if module_name:
            q = q.filter(ApiUsageLog.module_name == module_name)
        if model_name:
            q = q.filter(ApiUsageLog.model_name == model_name)

        rows = q.order_by(ApiUsageLog.created_at.asc()).limit(limit).all()

        data = [
            {
                "timestamp": row.created_at.isoformat(),
                "module": row.module_name,
                "model": row.model_name,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
                "latency_ms": row.latency_ms
            }
            for row in rows
        ]

        return {"success": True, "data": data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取调用明细失败: {str(e)}")
