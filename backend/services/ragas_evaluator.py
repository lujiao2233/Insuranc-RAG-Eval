"""RAGAS评估器模块
实现RAG系统的评估功能，支持RAGAS和DeepEval两种评估引擎
"""
from typing import List, Dict, Any, Optional
import os
import time
from datetime import datetime
import json

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger("ragas_evaluator")

RAGAS_AVAILABLE = False
try:
    import ragas as _ragas_mod
    RAGAS_AVAILABLE = True
except Exception:
    RAGAS_AVAILABLE = False

DEEPEVAL_AVAILABLE = False
try:
    import deepeval as _deepeval_mod
    DEEPEVAL_AVAILABLE = True
except Exception:
    DEEPEVAL_AVAILABLE = False


def _mock_evaluate(rows: List[Dict[str, Any]], evaluation_metrics: List[str], start_time: float) -> Dict[str, Any]:
    """模拟评估（当RAGAS/DeepEval不可用时）"""
    import random
    
    results: List[Dict[str, Any]] = []
    for row in rows:
        metrics_out: Dict[str, float] = {}
        for metric in evaluation_metrics:
            metrics_out[metric] = round(random.uniform(0.6, 0.95), 4)
        
        ctx_value = row.get("contexts", [])
        if isinstance(ctx_value, list):
            context_str = ", ".join(str(c) for c in ctx_value)
        else:
            context_str = str(ctx_value) if ctx_value else ""
        
        results.append({
            "question_id": row.get("question_id", ""),
            "question": row.get("question", ""),
            "expected_answer": row.get("ground_truth", ""),
            "generated_answer": row.get("answer", ""),
            "context": context_str,
            "metrics": metrics_out,
            "evaluation_time": time.time() - start_time,
        })
    
    evaluation_time = time.time() - start_time
    
    all_metrics: Dict[str, List[float]] = {}
    for result in results:
        for metric, score in result.get("metrics", {}).items():
            if metric not in all_metrics:
                all_metrics[metric] = []
            all_metrics[metric].append(float(score))
    
    overall_metrics: Dict[str, Dict[str, float]] = {}
    for metric, scores in all_metrics.items():
        if scores:
            arr = np.array(scores, dtype=float)
            overall_metrics[metric] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "median": float(np.median(arr)),
            }
    
    if overall_metrics:
        weighted_score = sum(m["mean"] for m in overall_metrics.values()) / len(overall_metrics)
        overall_metrics["overall_score"] = {
            "mean": weighted_score,
            "interpretation": "良好" if weighted_score >= 0.8 else "一般" if weighted_score >= 0.7 else "较差"
        }
    
    return {
        "evaluation_id": f"eval_{int(time.time())}",
        "evaluation_method": "mock",
        "total_questions": len(rows),
        "evaluated_questions": len(results),
        "evaluation_time": evaluation_time,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "individual_results": results,
        "overall_metrics": overall_metrics,
        "evaluation_metrics": evaluation_metrics,
    }


class RagasEvaluator:
    """RAG系统评估器
    
    提供对RAG系统输出结果进行全面评估的能力，支持多种评估指标和评估引擎。
    """
    
    def __init__(self):
        self.evaluation_config = self._load_evaluation_config()
        self.performance_thresholds = self._load_performance_thresholds()
        self.evaluation_history: List[Dict[str, Any]] = []

    def _load_evaluation_config(self) -> Dict[str, Any]:
        return {
            "default_metrics": [
                "answer_relevance",
                "context_relevance",
                "faithfulness",
                "answer_correctness",
                "answer_similarity",
            ],
            "batch_size": 5,
            "timeout": 300,
            "max_workers": 4,
        }

    def _load_performance_thresholds(self) -> Dict[str, float]:
        return {
            "excellent": 0.9,
            "good": 0.8,
            "average": 0.7,
            "poor": 0.6,
        }

    def evaluate(
        self,
        questions: List[Dict[str, Any]],
        rag_system_func=None,
        evaluation_metrics: Optional[List[str]] = None,
        engine: Optional[str] = None,
        run_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行RAG系统评估"""
        if evaluation_metrics is None:
            evaluation_metrics = self.evaluation_config.get("default_metrics", [])

        try:
            logger.info(
                f"开始评估，问题数量: {len(questions)}, 指标: {evaluation_metrics}, 引擎: {engine or 'ragas'}"
            )
            start_time = time.time()

            rows: List[Dict[str, Any]] = []
            for i, q in enumerate(questions):
                q_text = getattr(q, "question", None) or q.get("question", "")
                q_id = getattr(q, "id", None) or q.get("id", f"q_{i}")
                gt = getattr(q, "expected_answer", None) or q.get("expected_answer", "")
                provided_answer = getattr(q, "answer", None) or q.get("answer", "")
                provided_context = getattr(q, "context", None) or q.get("context", "")

                ans = provided_answer
                ctx = provided_context
                if (not ans) and callable(rag_system_func):
                    rag = rag_system_func(q_text) or {}
                    ans = rag.get("answer", "")
                    ctx = rag.get("context", ctx or "")

                rows.append(
                    {
                        "question": q_text,
                        "answer": ans or "",
                        "response": ans or "",
                        "contexts": ([ctx] if ctx else []),
                        "ground_truth": gt or "",
                        "reference": gt or "",
                        "question_id": q_id,
                    }
                )

            engine_normalized = (engine or "").strip().lower()
            effective_config = self.evaluation_config.copy()
            if run_config:
                effective_config.update(run_config)

            if "deepeval" in engine_normalized:
                if DEEPEVAL_AVAILABLE:
                    return self._evaluate_with_deepeval_rows(
                        rows, evaluation_metrics, start_time
                    )
                else:
                    raise RuntimeError("DeepEval不可用，请确保已安装 deepeval 库并正确配置。")
            
            if RAGAS_AVAILABLE:
                return self._evaluate_with_ragas_rows(rows, evaluation_metrics, start_time, effective_config)
            else:
                raise RuntimeError("RAGAS不可用，请确保已安装 ragas 库并正确配置。")

        except Exception as e:
            logger.error(f"评估失败: {str(e)}")
            return {
                "error": str(e),
                "evaluation_id": f"eval_{int(time.time())}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

    def evaluate_batch(
        self, questions: List[Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """批量评估问题列表"""
        metrics = config.get("metrics") or self.evaluation_config.get("default_metrics", [])
        engine = config.get("engine")
        result = self.evaluate(
            questions=[
                {
                    "id": getattr(q, "id", None),
                    "question": getattr(q, "question", None),
                    "expected_answer": getattr(q, "expected_answer", None),
                    "answer": getattr(q, "answer", None),
                    "context": getattr(q, "context", None),
                    "question_type": getattr(q, "question_type", None),
                }
                for q in questions
            ],
            rag_system_func=None,
            evaluation_metrics=metrics,
            engine=engine,
            run_config=config,
        )

        if isinstance(result, dict) and result.get("error"):
            raise RuntimeError(result["error"])

        indiv = result.get("individual_results", [])
        out: List[Dict[str, Any]] = []
        for i, r in enumerate(indiv):
            qid = r.get("question_id")
            if (not qid) and i < len(questions):
                try:
                    qid = getattr(questions[i], "id", None)
                except Exception:
                    qid = None
            row: Dict[str, Any] = {
                "question_id": qid or "",
                "question": r.get("question", ""),
                "answer": r.get("generated_answer", ""),
                "context": r.get("context", ""),
            }
            expected_answer = r.get("expected_answer")
            if expected_answer is None and i < len(questions):
                src_q = questions[i]
                try:
                    expected_answer = getattr(src_q, "expected_answer", None)
                except Exception:
                    expected_answer = None
            if expected_answer is not None:
                row["expected_answer"] = expected_answer
            for m, s in (r.get("metrics") or {}).items():
                row[m] = s
            if i < len(questions):
                qt = getattr(questions[i], "question_type", None)
                if qt:
                    row["question_type"] = qt
            out.append(row)
        return out

    def _configure_llm_environment(self) -> None:
        """配置LLM环境变量"""
        api_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        base_url = os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url

    def _evaluate_with_ragas_rows(
        self,
        rows: List[Dict[str, Any]],
        evaluation_metrics: List[str],
        start_time: float,
        run_config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """使用RAGAS官方引擎执行评估"""
        if not RAGAS_AVAILABLE:
            raise RuntimeError("RAGAS评估依赖未安装，请安装 ragas 后重试")

        self._configure_llm_environment()

        ragas_metrics = self._map_ragas_metrics(evaluation_metrics)
        if not ragas_metrics:
            raise RuntimeError("RAGAS评估指标加载失败，请检查ragas安装")

        df = pd.DataFrame(rows)
        
        if "response" not in df.columns:
            df["response"] = df.get("answer", "")
        if "user_input" not in df.columns:
            df["user_input"] = df.get("question", "")
        if "retrieved_contexts" not in df.columns:
            df["retrieved_contexts"] = df.get("contexts", [])
        
        for col in ["response", "answer", "question", "user_input", "ground_truth", "reference"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        if "ground_truth" in df.columns and "reference" not in df.columns:
            df["reference"] = df["ground_truth"]
        
        from datasets import Dataset as HFDataset
        from ragas import evaluate as ragas_evaluate

        evaluate_kwargs: Dict[str, Any] = {"metrics": ragas_metrics}
        
        if run_config:
            try:
                from ragas.run_config import RunConfig
                timeout = int(run_config.get("timeout", 300))
                max_workers = int(run_config.get("max_workers", 4))
                timeout = max(60, timeout)
                max_workers = max(1, max_workers)
                evaluate_kwargs["run_config"] = RunConfig(timeout=timeout, max_workers=max_workers)
                logger.info(f"Ragas RunConfig: timeout={timeout}, max_workers={max_workers}")
            except (ImportError, Exception) as e:
                logger.warning(f"构建 Ragas RunConfig 失败: {e}")

        try:
            from services.llm_service import get_llm_service
            llm_service = get_llm_service(use_mock=False)
            if hasattr(llm_service, '_langchain_llm'):
                evaluate_kwargs["llm"] = llm_service._langchain_llm
        except Exception as e:
            logger.warning(f"LLM服务构建失败: {e}")

        ragas_result = ragas_evaluate(
            HFDataset.from_pandas(df),
            **evaluate_kwargs,
        )
        ragas_df = ragas_result.to_pandas()

        results: List[Dict[str, Any]] = []
        for idx, r in ragas_df.iterrows():
            base_row: Dict[str, Any] = {}
            if 0 <= int(idx) < len(rows):
                try:
                    base_row = rows[int(idx)] or {}
                except Exception:
                    base_row = {}
            
            metrics_out: Dict[str, float] = {}
            for m in ragas_metrics:
                name = getattr(m, "name", None) or m.__class__.__name__
                if name in r:
                    val = r[name]
                    try:
                        if pd.isna(val):
                            continue
                        metrics_out[name] = float(val)
                    except Exception:
                        continue
            
            question_id_val = r.get("question_id", "") or base_row.get("question_id", "")
            question_val = r.get("question", None) or base_row.get("question", "")
            gt_val = r.get("ground_truth", None) or base_row.get("ground_truth", "")
            ans_val = r.get("answer", None) or base_row.get("answer", "")
            ctx_val = r.get("contexts", None) or base_row.get("contexts") or base_row.get("context", "")
            
            if isinstance(ctx_val, list):
                ctx_str = ", ".join(ctx_val)
            else:
                ctx_str = str(ctx_val) if ctx_val is not None else ""
            
            results.append(
                {
                    "question_id": question_id_val,
                    "question": question_val or "",
                    "expected_answer": gt_val or "",
                    "generated_answer": ans_val or "",
                    "context": ctx_str,
                    "metrics": metrics_out,
                    "evaluation_time": time.time() - start_time,
                }
            )

        evaluation_time = time.time() - start_time
        overall_metrics = self._calculate_overall_metrics(results)
        out: Dict[str, Any] = {
            "evaluation_id": f"eval_{int(time.time())}",
            "evaluation_method": "ragas",
            "total_questions": len(rows),
            "evaluated_questions": len(results),
            "evaluation_time": evaluation_time,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "individual_results": results,
            "overall_metrics": overall_metrics,
            "evaluation_metrics": evaluation_metrics,
        }
        self.evaluation_history.append(out)
        logger.info(f"RAGAS评估完成，评估了{len(results)}个问题，耗时{evaluation_time:.2f}秒")
        return out

    def _evaluate_with_deepeval_rows(
        self,
        rows: List[Dict[str, Any]],
        evaluation_metrics: List[str],
        start_time: float,
    ) -> Dict[str, Any]:
        """使用DeepEval引擎执行评估"""
        if not DEEPEVAL_AVAILABLE:
            raise RuntimeError("DeepEval评估依赖未安装，请安装 deepeval 后重试")

        self._configure_llm_environment()

        from openai import OpenAI
        from deepeval.test_case import LLMTestCase
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            ContextualRelevancyMetric,
            HallucinationMetric,
            ToxicityMetric,
            BiasMetric,
        )
        from deepeval.models import DeepEvalBaseLLM

        class QwenDeepEvalLLM(DeepEvalBaseLLM):
            def __init__(self):
                api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("API密钥未配置")
                self.api_key = api_key
                self.base_url = os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                self.model = os.getenv("QWEN_MODEL", "qwen-plus")
                self.temperature = 0.0
                self.max_tokens = 2000
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            def load_model(self):
                return self.client

            def generate(self, prompt: str) -> str:
                client = self.load_model()
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an evaluation assistant. Respond with only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                if completion and completion.choices:
                    content = completion.choices[0].message.content or ""
                    return self._ensure_valid_json(content.strip())
                return self._ensure_valid_json("")

            async def a_generate(self, prompt: str) -> str:
                return self.generate(prompt)

            def get_model_name(self) -> str:
                return self.model

            def _ensure_valid_json(self, content: str) -> str:
                text = (content or "").strip()
                obj: Dict[str, Any] = {"score": 0.0, "reason": "No output"}
                if text:
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            obj = parsed
                    except Exception:
                        start = text.find("{")
                        end = text.rfind("}")
                        if start != -1 and end != -1 and end > start:
                            try:
                                parsed = json.loads(text[start:end+1])
                                if isinstance(parsed, dict):
                                    obj = parsed
                            except Exception:
                                pass
                if "score" not in obj:
                    obj["score"] = 0.0
                if "reason" not in obj:
                    obj["reason"] = "No reason provided"
                return json.dumps(obj, ensure_ascii=False)

        qwen_llm = QwenDeepEvalLLM()

        available_metrics: Dict[str, Any] = {
            "answer_relevance": AnswerRelevancyMetric,
            "faithfulness": FaithfulnessMetric,
            "context_relevance": ContextualRelevancyMetric,
            "hallucination": HallucinationMetric,
            "toxicity": ToxicityMetric,
            "bias": BiasMetric,
        }
        metric_classes = self._map_deepeval_metrics(evaluation_metrics, available_metrics)
        if not metric_classes:
            raise RuntimeError("DeepEval评估指标加载失败")

        results: List[Dict[str, Any]] = []
        for row in rows:
            ctx_value = row.get("contexts")
            if ctx_value is None:
                ctx_value = []
            if isinstance(ctx_value, list):
                retrieval_context = [str(c) for c in ctx_value if c is not None]
            else:
                retrieval_context = [str(ctx_value)]
            
            q_val = str(row.get("question", ""))
            a_val = str(row.get("answer", "")) if row.get("answer") else ""
            gt_val = str(row.get("ground_truth", "")) if row.get("ground_truth") else ""
            
            test_case = LLMTestCase(
                input=q_val,
                actual_output=a_val,
                expected_output=gt_val,
                retrieval_context=retrieval_context,
                context=retrieval_context,
            )
            
            metrics_out: Dict[str, float] = {}
            for metric_name, metric_cls in metric_classes.items():
                try:
                    metric = metric_cls(model=qwen_llm)
                except TypeError:
                    metric = metric_cls()
                try:
                    metric.measure(test_case)
                    score_value = float(getattr(metric, "score", 0.0))
                except Exception as e:
                    logger.warning(f"DeepEval metric {metric_name} 计算失败: {e}")
                    score_value = 0.0
                metrics_out[metric_name] = score_value

            context_value = row.get("contexts", [])
            if isinstance(context_value, list):
                context_str = ", ".join(context_value)
            else:
                context_str = str(context_value) if context_value is not None else ""

            results.append(
                {
                    "question_id": row.get("question_id", ""),
                    "question": row.get("question", ""),
                    "expected_answer": row.get("ground_truth", ""),
                    "generated_answer": row.get("answer", ""),
                    "context": context_str,
                    "metrics": metrics_out,
                    "evaluation_time": time.time() - start_time,
                }
            )

        evaluation_time = time.time() - start_time
        overall_metrics = self._calculate_overall_metrics(results)
        out: Dict[str, Any] = {
            "evaluation_id": f"eval_{int(time.time())}",
            "evaluation_method": "deepeval",
            "total_questions": len(rows),
            "evaluated_questions": len(results),
            "evaluation_time": evaluation_time,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "individual_results": results,
            "overall_metrics": overall_metrics,
            "evaluation_metrics": evaluation_metrics,
        }
        self.evaluation_history.append(out)
        logger.info(f"DeepEval评估完成，评估了{len(results)}个问题，耗时{evaluation_time:.2f}秒")
        return out

    def _map_ragas_metrics(self, metrics: List[str]):
        """将指标名称映射为RAGAS指标对象"""
        try:
            from ragas.metrics import (
                AnswerRelevancy,
                Faithfulness,
                AnswerCorrectness,
                AnswerSimilarity,
                ContextRecall,
            )

            class_map = {
                "answer_relevance": AnswerRelevancy,
                "context_relevance": ContextRecall,
                "faithfulness": Faithfulness,
                "answer_correctness": AnswerCorrectness,
                "answer_similarity": AnswerSimilarity,
            }
            out = []
            for m in metrics:
                cls = class_map.get(m)
                if cls:
                    if m in ("answer_relevance", "context_relevance"):
                        out.append(cls(name=m))
                    else:
                        out.append(cls())
            return out
        except Exception:
            try:
                from ragas.metrics import (
                    answer_relevancy,
                    faithfulness,
                    answer_correctness,
                    answer_similarity,
                    context_recall,
                )

                func_map = {
                    "answer_relevance": answer_relevancy,
                    "context_relevance": context_recall,
                    "faithfulness": faithfulness,
                    "answer_correctness": answer_correctness,
                    "answer_similarity": answer_similarity,
                }
                return [func_map[m] for m in metrics if m in func_map]
            except Exception as e:
                logger.warning(f"RAGAS指标导入失败: {e}")
                return []

    def _map_deepeval_metrics(
        self, metrics: List[str], available_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将指标名称映射为DeepEval指标类"""
        return {name: cls for name, cls in available_metrics.items() if name in metrics}

    def _calculate_overall_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算总体评估指标统计"""
        if not results:
            return {}
        
        all_metrics: Dict[str, List[float]] = {}
        for result in results:
            for metric, score in result.get("metrics", {}).items():
                try:
                    if score is None or (isinstance(score, float) and np.isnan(score)):
                        continue
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(float(score))
                except Exception:
                    pass
        
        overall_metrics: Dict[str, Dict[str, float]] = {}
        for metric, scores in all_metrics.items():
            if not scores:
                continue
            arr = np.array(scores, dtype=float)
            arr = arr[~np.isnan(arr)]
            if arr.size == 0:
                continue
            overall_metrics[metric] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "median": float(np.median(arr)),
            }
        
        if overall_metrics:
            weights = {
                "answer_relevance": 0.2,
                "context_relevance": 0.2,
                "faithfulness": 0.2,
                "answer_correctness": 0.2,
                "answer_similarity": 0.2,
            }
            
            weighted_score = 0.0
            total_weight = 0.0
            
            for metric, metric_data in overall_metrics.items():
                if metric in weights:
                    weighted_score += metric_data["mean"] * weights[metric]
                    total_weight += weights[metric]
            
            if total_weight > 0:
                overall_metrics["overall_score"] = {
                    "mean": weighted_score / total_weight,
                    "interpretation": self._interpret_score(weighted_score / total_weight)
                }
        
        return overall_metrics
    
    def _interpret_score(self, score: float) -> str:
        """解释评估分数"""
        if score >= 0.9:
            return "优秀"
        elif score >= 0.8:
            return "良好"
        elif score >= 0.7:
            return "一般"
        elif score >= 0.6:
            return "较差"
        else:
            return "很差"
    
    def get_evaluation_history(self) -> List[Dict[str, Any]]:
        """获取评估历史记录"""
        return self.evaluation_history
    
    def export_results_to_dataframe(self, evaluation_result: Dict[str, Any]) -> pd.DataFrame:
        """将评估结果导出为DataFrame"""
        try:
            data = []
            for result in evaluation_result.get("individual_results", []):
                row = {
                    "question_id": result.get("question_id", ""),
                    "question": result.get("question", ""),
                    "expected_answer": result.get("expected_answer", ""),
                    "generated_answer": result.get("generated_answer", ""),
                    "context": result.get("context", "")
                }
                
                for metric, score in result.get("metrics", {}).items():
                    row[metric] = score
                
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"导出结果为DataFrame失败: {str(e)}")
            return pd.DataFrame()


evaluator = RagasEvaluator()
