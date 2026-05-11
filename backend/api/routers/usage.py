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
    """
    根据阿里云百炼阶梯计费规则估算成本（中国内地 普通调用）
    阶梯计费：单价取决于单次请求的输入 Token 总量，该请求所有 Token 均按对应阶梯单价结算
    """
    # 定义各模型的阶梯计费规则 (单位: 元/百万Token)
    tiered_prices = {
        # 千问Plus系列
        "qwen3.6-plus": {
            "tiers": [
                {"max_tokens": 256_000, "in": 2.0, "out": 12.0},
                {"max_tokens": 1_000_000, "in": 8.0, "out": 48.0},
            ]
        },
        "qwen3.6-plus-2026-04-02": {
            "tiers": [
                {"max_tokens": 256_000, "in": 2.0, "out": 12.0},
                {"max_tokens": 1_000_000, "in": 8.0, "out": 48.0},
            ]
        },
        "qwen3.5-plus": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 4.8},
                {"max_tokens": 256_000, "in": 2.0, "out": 12.0},
                {"max_tokens": 1_000_000, "in": 4.0, "out": 24.0},
            ]
        },
        "qwen3.5-plus-2026-02-15": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 4.8},
                {"max_tokens": 256_000, "in": 2.0, "out": 12.0},
                {"max_tokens": 1_000_000, "in": 4.0, "out": 24.0},
            ]
        },
        "qwen-plus": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 2.0},
                {"max_tokens": 256_000, "in": 2.4, "out": 20.0},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 48.0},
            ]
        },
        "qwen-plus-latest": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 2.0},
                {"max_tokens": 256_000, "in": 2.4, "out": 20.0},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 48.0},
            ]
        },
        "qwen-plus-2025-12-01": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 2.0},
                {"max_tokens": 256_000, "in": 2.4, "out": 20.0},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 48.0},
            ]
        },
        "qwen-plus-2025-09-11": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 2.0},
                {"max_tokens": 256_000, "in": 2.4, "out": 20.0},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 48.0},
            ]
        },
        "qwen-plus-2025-07-28": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.8, "out": 2.0},
                {"max_tokens": 256_000, "in": 2.4, "out": 20.0},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 48.0},
            ]
        },
        "qwen-plus-2025-07-14": {"in": 0.8, "out": 2.0},  # 无阶梯
        "qwen-plus-2025-04-28": {"in": 0.8, "out": 2.0},  # 无阶梯
        "qwen-plus-2025-01-25": {"in": 0.8, "out": 2.0},  # 无阶梯
        "qwen-plus-2025-01-12": {"in": 0.8, "out": 2.0},  # 无阶梯
        "qwen-plus-2024-12-20": {"in": 0.8, "out": 2.0},  # 无阶梯
        # 千问Max系列
        "qwen3.6-max-preview": {
            "tiers": [
                {"max_tokens": 128_000, "in": 9.0, "out": 54.0},
                {"max_tokens": 256_000, "in": 15.0, "out": 90.0},
            ]
        },
        "qwen3-max": {
            "tiers": [
                {"max_tokens": 32_000, "in": 2.5, "out": 10.0},
                {"max_tokens": 128_000, "in": 4.0, "out": 16.0},
                {"max_tokens": 252_000, "in": 7.0, "out": 28.0},
            ]
        },
        "qwen3-max-2026-01-23": {
            "tiers": [
                {"max_tokens": 32_000, "in": 2.5, "out": 10.0},
                {"max_tokens": 128_000, "in": 4.0, "out": 16.0},
                {"max_tokens": 252_000, "in": 7.0, "out": 28.0},
            ]
        },
        "qwen3-max-2025-09-23": {
            "tiers": [
                {"max_tokens": 32_000, "in": 6.0, "out": 24.0},
                {"max_tokens": 128_000, "in": 10.0, "out": 40.0},
                {"max_tokens": 252_000, "in": 15.0, "out": 60.0},
            ]
        },
        "qwen3-max-preview": {
            "tiers": [
                {"max_tokens": 32_000, "in": 6.0, "out": 24.0},
                {"max_tokens": 128_000, "in": 10.0, "out": 40.0},
                {"max_tokens": 252_000, "in": 15.0, "out": 60.0},
            ]
        },
        # 无阶梯的Max模型
        "qwen-max": {"in": 2.4, "out": 9.6},
        "qwen-max-latest": {"in": 2.4, "out": 9.6},
        "qwen-max-2025-01-25": {"in": 2.4, "out": 9.6},
        "qwen-max-2024-09-19": {"in": 20.0, "out": 60.0},
        "qwen-max-2024-04-28": {"in": 40.0, "out": 120.0},
        # 千问Flash系列
        "qwen3.6-flash": {
            "tiers": [
                {"max_tokens": 256_000, "in": 1.2, "out": 7.2},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 28.8},
            ]
        },
        "qwen3.6-flash-2026-04-16": {
            "tiers": [
                {"max_tokens": 256_000, "in": 1.2, "out": 7.2},
                {"max_tokens": 1_000_000, "in": 4.8, "out": 28.8},
            ]
        },
        "qwen3.5-flash": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.2, "out": 2.0},
                {"max_tokens": 256_000, "in": 0.8, "out": 8.0},
                {"max_tokens": 1_000_000, "in": 1.2, "out": 12.0},
            ]
        },
        "qwen3.5-flash-2026-02-23": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.2, "out": 2.0},
                {"max_tokens": 256_000, "in": 0.8, "out": 8.0},
                {"max_tokens": 1_000_000, "in": 1.2, "out": 12.0},
            ]
        },
        "qwen-flash": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.15, "out": 1.5},
                {"max_tokens": 256_000, "in": 0.6, "out": 6.0},
                {"max_tokens": 1_000_000, "in": 1.2, "out": 12.0},
            ]
        },
        "qwen-flash-2025-07-28": {
            "tiers": [
                {"max_tokens": 128_000, "in": 0.15, "out": 1.5},
                {"max_tokens": 256_000, "in": 0.6, "out": 6.0},
                {"max_tokens": 1_000_000, "in": 1.2, "out": 12.0},
            ]
        },
        # 千问Turbo系列 (无阶梯)
        "qwen-turbo": {"in": 0.3, "out": 0.6},
        "qwen-turbo-latest": {"in": 0.3, "out": 0.6},
        "qwen-turbo-2025-07-15": {"in": 0.3, "out": 0.6},
        "qwen-turbo-2025-04-28": {"in": 0.3, "out": 0.6},
        "qwen-turbo-2025-02-11": {"in": 0.3, "out": 0.6},
        "qwen-turbo-2024-11-01": {"in": 0.3, "out": 0.6},
        # QwQ 思考模型 (无阶梯)
        "qwq-plus": {"in": 1.6, "out": 4.0},
        "qwq-plus-latest": {"in": 1.6, "out": 4.0},
        "qwq-plus-2025-03-05": {"in": 1.6, "out": 4.0},
        # 第三方模型 (无阶梯)
        "deepseek-v3.2": {"in": 2.0, "out": 3.0},
        "deepseek-v3": {"in": 2.0, "out": 8.0},
        "glm-5": {"in": 1.0, "out": 4.0},
        "glm-5.1": {"in": 6.0, "out": 24.0},
        "glm-4-plus": {"in": 5.0, "out": 5.0},
        "glm-4-flash": {"in": 0.0, "out": 0.0},
    }

    # 获取该模型的价格配置
    price_config = tiered_prices.get(model_name, {"in": 0.15, "out": 1.5})  # 默认按 qwen-flash 最低价

    # 如果有阶梯计价，根据 prompt_tokens 选择对应阶梯
    if "tiers" in price_config:
        tiers = price_config["tiers"]
        # 找到 prompt_tokens 所在的阶梯
        selected_tier = tiers[-1]  # 默认使用最高阶梯
        for tier in tiers:
            if prompt_tokens <= tier["max_tokens"]:
                selected_tier = tier
                break
        
        price_in = selected_tier["in"]
        price_out = selected_tier["out"]
    else:
        # 无阶梯计价，直接使用固定单价
        price_in = price_config["in"]
        price_out = price_config["out"]

    return (prompt_tokens / 1_000_000 * price_in) + (completion_tokens / 1_000_000 * price_out)

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
