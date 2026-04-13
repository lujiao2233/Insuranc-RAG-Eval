from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List
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
            func.sum(ApiUsageLog.total_tokens).label("tokens")
        ).group_by(ApiUsageLog.module_name).all()
        
        # 3. 按天分组趋势统计 (最近days天)
        # 注意: SQLite 和 MySQL 的 date 函数不同。假设这里是 MySQL 或可以处理 func.date
        trend_stats = db.query(
            func.date(ApiUsageLog.created_at).label("date"),
            func.count(ApiUsageLog.id).label("calls"),
            func.sum(ApiUsageLog.total_tokens).label("tokens")
        ).filter(
            ApiUsageLog.created_at >= start_date
        ).group_by(
            func.date(ApiUsageLog.created_at)
        ).order_by(
            func.date(ApiUsageLog.created_at)
        ).all()
        
        # 格式化结果
        modules_data = [
            {"module": row.module_name, "calls": row.calls, "tokens": row.tokens or 0}
            for row in module_stats
        ]
        
        trend_data = [
            {"date": str(row.date), "calls": row.calls, "tokens": row.tokens or 0}
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
