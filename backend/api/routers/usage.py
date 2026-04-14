import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config.database import get_db
from models.database import ApiUsageLog, User
from api.dependencies import get_current_user

router = APIRouter()

def calc_percentile(data: List[int], percentile: int) -> int:
    size = len(data)
    if not size:
        return 0
    return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]

def estimate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    # 估算价格 (元 / 1M tokens)，来源于当前常用模型单价
    prices = {
        # 常用模型
        "qwen3-max": {"in": 7.0, "out": 28.0},
        "qwen3.6-plus": {"in": 2.0, "out": 12.0},
        "qwen-flash": {"in": 0.6, "out": 6.0},
        "qwen3.5-flash": {"in": 0.8, "out": 8.0},
        # 兼容历史模型名
        "qwen-plus": {"in": 2.0, "out": 12.0},
        "qwen-turbo": {"in": 0.6, "out": 6.0}
    }
    # 未命中时给一个保守默认值（按 qwen-flash 估算）
    price = prices.get(model_name, {"in": 0.6, "out": 6.0})
    return (prompt_tokens / 1_000_000 * price["in"]) + (completion_tokens / 1_000_000 * price["out"])

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_usage_dashboard(
    start: Optional[datetime] = Query(None, description="开始时间（ISO8601）"),
    end: Optional[datetime] = Query(None, description="结束时间（ISO8601）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        end_dt = end or datetime.now()
        start_dt = start or (end_dt - timedelta(days=7))
        
        # 对比周期（前一周期）
        period_diff = end_dt - start_dt
        prev_start_dt = start_dt - period_diff
        prev_end_dt = start_dt
        
        # 当前周期查询
        q = db.query(ApiUsageLog).filter(ApiUsageLog.created_at >= start_dt, ApiUsageLog.created_at <= end_dt)
        logs = q.all()
        
        # 上一周期查询
        prev_q = db.query(ApiUsageLog).filter(ApiUsageLog.created_at >= prev_start_dt, ApiUsageLog.created_at <= prev_end_dt)
        prev_logs = prev_q.all()
        
        # Layer 1: 总览
        total_calls = len(logs)
        total_tokens = sum(l.total_tokens for l in logs)
        avg_latency = sum(l.latency_ms for l in logs) / total_calls if total_calls > 0 else 0
        calls_last_24h = len([l for l in logs if l.created_at >= (end_dt - timedelta(hours=24))])
        cost = sum(estimate_cost(l.model_name, l.prompt_tokens, l.completion_tokens) for l in logs)
        
        # Layer 1: 模块占比
        module_ratio = {}
        for l in logs:
            if l.module_name not in module_ratio:
                module_ratio[l.module_name] = {"module": l.module_name, "calls": 0, "tokens": 0}
            module_ratio[l.module_name]["calls"] += 1
            module_ratio[l.module_name]["tokens"] += l.total_tokens
            
        # Layer 2: 分位数
        latencies = [l.latency_ms for l in logs if l.latency_ms is not None]
        percentiles = {
            "p50": calc_percentile(latencies, 50),
            "p90": calc_percentile(latencies, 90),
            "p95": calc_percentile(latencies, 95)
        }
        
        # Layer 2: 异常统计
        error_logs = [l for l in logs if getattr(l, "is_error", False)]
        total_failures = len(error_logs)
        failure_rate = total_failures / total_calls if total_calls > 0 else 0
        
        failed_modules_count = {}
        for l in error_logs:
            failed_modules_count[l.module_name] = failed_modules_count.get(l.module_name, 0) + 1
        top_failed_modules = [{"module": k, "failures": v} for k, v in sorted(failed_modules_count.items(), key=lambda item: item[1], reverse=True)[:5]]
        
        # Layer 2: IO Token 结构
        avg_prompt_tokens = sum(l.prompt_tokens for l in logs) / total_calls if total_calls > 0 else 0
        avg_completion_tokens = sum(l.completion_tokens for l in logs) / total_calls if total_calls > 0 else 0
        
        # Layer 3: 模型对比
        model_stats = {}
        for l in logs:
            if l.model_name not in model_stats:
                model_stats[l.model_name] = {"model": l.model_name, "calls": 0, "tokens": 0, "latency": 0, "cost": 0.0}
            model_stats[l.model_name]["calls"] += 1
            model_stats[l.model_name]["tokens"] += l.total_tokens
            model_stats[l.model_name]["latency"] += l.latency_ms
            model_stats[l.model_name]["cost"] += estimate_cost(l.model_name, l.prompt_tokens, l.completion_tokens)
            
        for m in model_stats.values():
            m["avg_tokens"] = m["tokens"] / m["calls"]
            m["avg_latency"] = m["latency"] / m["calls"]
            
        # Layer 3: 趋势对比
        prev_calls = len(prev_logs)
        prev_tokens = sum(l.total_tokens for l in prev_logs)
        prev_cost = sum(estimate_cost(l.model_name, l.prompt_tokens, l.completion_tokens) for l in prev_logs)
        prev_error_logs = [l for l in prev_logs if getattr(l, "is_error", False)]
        prev_failure_rate = len(prev_error_logs) / prev_calls if prev_calls > 0 else 0
        
        return {
            "success": True,
            "data": {
                "overview": {
                    "total_calls": total_calls,
                    "total_tokens": total_tokens,
                    "avg_latency": round(avg_latency),
                    "calls_last_24h": calls_last_24h,
                    "estimated_cost": round(cost, 4)
                },
                "module_ratio": list(module_ratio.values()),
                "percentiles": percentiles,
                "errors": {
                    "total_failures": total_failures,
                    "failure_rate": round(failure_rate, 4),
                    "top_failed_modules": top_failed_modules
                },
                "io_ratio": {
                    "avg_prompt_tokens": round(avg_prompt_tokens),
                    "avg_completion_tokens": round(avg_completion_tokens)
                },
                "models": list(model_stats.values()),
                "trend_compare": {
                    "current_period": {
                        "calls": total_calls, "tokens": total_tokens, "cost": round(cost, 4), "failure_rate": round(failure_rate, 4)
                    },
                    "previous_period": {
                        "calls": prev_calls, "tokens": prev_tokens, "cost": round(prev_cost, 4), "failure_rate": round(prev_failure_rate, 4)
                    }
                }
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_usage_stats(
    days: int = Query(7, description="查询过去几天的统计数据"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取API调用的Token消耗统计"""
    try:
        # 计算时间范围
        start_date = datetime.now() - timedelta(days=days)
        
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
        end_dt = end or datetime.now()
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
