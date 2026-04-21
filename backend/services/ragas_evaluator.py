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




class RagasEvaluator:
    """RAG系统评估器
    
    提供对RAG系统输出结果进行全面评估的能力，支持多种评估指标和评估引擎。
    """
    
    def __init__(self):
        self.evaluation_config = self._load_evaluation_config()
        self.performance_thresholds = self._load_performance_thresholds()

    def _load_evaluation_config(self) -> Dict[str, Any]:
        return {
            "default_metrics": [
                "answer_relevance",
                "context_relevance",
                "context_precision",
                "faithfulness",
                "answer_correctness",
                "answer_similarity",
            ],
            "batch_size": 5,
            "timeout": 600,
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

            user_id = effective_config.get("user_id")
            db_session = effective_config.get("db_session")
            runtime_llm_config = self._configure_llm_environment(
                user_id=str(user_id) if user_id else None,
                db_session=db_session,
                require_db_config=True,
            )

            if "deepeval" in engine_normalized:
                if DEEPEVAL_AVAILABLE:
                    return self._evaluate_with_deepeval_rows(
                        rows, evaluation_metrics, start_time, run_config=effective_config, llm_config=runtime_llm_config
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

    def _configure_llm_environment(
        self,
        user_id: Optional[str] = None,
        db_session=None,
        require_db_config: bool = True,
    ) -> Dict[str, str]:
        """配置LLM环境变量（评估默认强制使用数据库配置，不回退环境变量）"""
        if require_db_config and (not user_id or db_session is None):
            raise RuntimeError("评估配置缺失：未提供用户上下文，无法从数据库读取Qwen配置")

        api_key = ""
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = "qwen-plus"

        if user_id and db_session is not None:
            from services.config_service import ConfigService

            config_service = ConfigService(db_session)
            db_api_key = config_service.get_api_key(user_id, "qwen")
            db_base_url = config_service.get_config_value(user_id, "qwen.api_endpoint", base_url)
            db_eval_model = config_service.get_config_value(user_id, "qwen.evaluation_model", None)
            db_gen_model = config_service.get_config_value(user_id, "qwen.generation_model", None)

            if db_api_key:
                api_key = str(db_api_key)
            if db_base_url:
                base_url = str(db_base_url)
            if db_eval_model:
                model = str(db_eval_model)
            elif db_gen_model:
                model = str(db_gen_model)

        if require_db_config and not api_key:
            raise RuntimeError("评估配置缺失：数据库未配置 qwen.api_key，请先在配置页面保存后重试")

        if not api_key:
            api_key = (
                os.getenv("DASHSCOPE_API_KEY")
                or os.getenv("QWEN_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or ""
            )
            base_url = os.getenv("OPENAI_BASE_URL") or base_url
            model = os.getenv("QWEN_MODEL", model)

        if not api_key:
            raise RuntimeError("评估配置缺失：未找到可用API密钥")

        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["QWEN_API_KEY"] = api_key
        os.environ["DASHSCOPE_API_KEY"] = api_key
        os.environ["OPENAI_BASE_URL"] = base_url
        os.environ["QWEN_MODEL"] = model

        return {"api_key": api_key, "base_url": base_url, "model": model}

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

        cfg = run_config or {}
        runtime_cfg = self._configure_llm_environment(
            user_id=str(cfg.get("user_id")) if cfg.get("user_id") else None,
            db_session=cfg.get("db_session"),
            require_db_config=True,
        )

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
                timeout = int(run_config.get("timeout", 600))
                max_workers = int(run_config.get("max_workers", 4))
                timeout = max(60, timeout)
                max_workers = max(1, max_workers)
                evaluate_kwargs["run_config"] = RunConfig(timeout=timeout, max_workers=max_workers)
                logger.info(f"Ragas RunConfig: timeout={timeout}, max_workers={max_workers}")
            except (ImportError, Exception) as e:
                logger.warning(f"构建 Ragas RunConfig 失败: {e}")

        llm_wrapper = None
        embeddings_wrapper = None

        # 强制注入评估LLM，避免RAGAS回退到默认OpenAI模型（如 gpt-4o-mini）
        try:
            from langchain_openai import ChatOpenAI
            from ragas.llms.base import LangchainLLMWrapper

            llm = ChatOpenAI(
                model=(runtime_cfg or {}).get("model") or os.getenv("QWEN_MODEL", "qwen-plus"),
                api_key=(runtime_cfg or {}).get("api_key") or os.getenv("OPENAI_API_KEY"),
                base_url=(runtime_cfg or {}).get("base_url") or os.getenv("OPENAI_BASE_URL"),
                temperature=0.0,
                max_retries=1,
                timeout=120,
            )
            llm_wrapper = LangchainLLMWrapper(llm)
            evaluate_kwargs["llm"] = llm_wrapper
            logger.info(
                f"RAGAS评估LLM已注入: model={(runtime_cfg or {}).get('model')}, base_url={(runtime_cfg or {}).get('base_url')}"
            )
        except Exception as e:
            logger.warning(f"构建RAGAS评估LLM失败，将使用RAGAS默认LLM: {e}")

        # 强制注入Embedding模型，避免RAGAS回退到 text-embedding-ada-002
        try:
            import dashscope
            from dashscope import TextEmbedding
            from ragas.embeddings import LangchainEmbeddingsWrapper

            embedding_model = (
                os.getenv("DASHSCOPE_EMBEDDING_MODEL")
                or os.getenv("EMBEDDING_MODEL")
                or "text-embedding-v3"
            )
            dashscope.api_key = (runtime_cfg or {}).get("api_key") or os.getenv("DASHSCOPE_API_KEY")

            class DashscopeLCEmbeddings:
                def __init__(self, model_name: str):
                    self.model = model_name

                def _parse_embedding(self, resp):
                    if hasattr(resp, "output") and resp.output and "embeddings" in resp.output:
                        return resp.output["embeddings"][0]["embedding"]
                    try:
                        return resp["data"][0]["embedding"]
                    except Exception:
                        code = getattr(resp, "code", None)
                        message = getattr(resp, "message", None)
                        raise RuntimeError(f"DashScope embedding error: code={code}, message={message}")

                def embed_query(self, text: str):
                    resp = TextEmbedding.call(model=self.model, input=text)
                    return self._parse_embedding(resp)

                async def aembed_query(self, text: str):
                    return self.embed_query(text)

                def embed_documents(self, texts):
                    out = []
                    for t in texts:
                        resp = TextEmbedding.call(model=self.model, input=t)
                        out.append(self._parse_embedding(resp))
                    return out

                async def aembed_documents(self, texts):
                    return self.embed_documents(texts)

            lc_embeddings = DashscopeLCEmbeddings(embedding_model)
            _ = lc_embeddings.embed_query("ping")
            embeddings_wrapper = LangchainEmbeddingsWrapper(lc_embeddings)
            evaluate_kwargs["embeddings"] = embeddings_wrapper
            logger.info(f"RAGAS评估Embeddings已注入: model={embedding_model}")
        except Exception as e:
            logger.warning(f"构建RAGAS评估Embeddings失败，将使用RAGAS默认Embeddings: {e}")

        # 对 ragas==0.1.x 显式回填到每个指标对象，避免其内部回退默认 OpenAI 工厂
        for metric in ragas_metrics:
            try:
                if llm_wrapper is not None and hasattr(metric, "llm"):
                    metric.llm = llm_wrapper
                if embeddings_wrapper is not None and hasattr(metric, "embeddings"):
                    metric.embeddings = embeddings_wrapper
            except Exception as e:
                logger.warning(f"绑定评估指标模型失败: metric={getattr(metric, 'name', metric.__class__.__name__)}, error={e}")

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
        logger.info(f"RAGAS评估完成，评估了{len(results)}个问题，耗时{evaluation_time:.2f}秒")
        return out

    def _evaluate_with_deepeval_rows(
        self,
        rows: List[Dict[str, Any]],
        evaluation_metrics: List[str],
        start_time: float,
        run_config: Dict[str, Any] = None,
        llm_config: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """使用DeepEval引擎执行评估"""
        if not DEEPEVAL_AVAILABLE:
            raise RuntimeError("DeepEval评估依赖未安装，请安装 deepeval 后重试")
        cfg = run_config or {}
        progress_callback = cfg.get("progress_callback") if isinstance(cfg, dict) else None
        runtime_cfg = llm_config or self._configure_llm_environment(
            user_id=str(cfg.get("user_id")) if cfg.get("user_id") else None,
            db_session=cfg.get("db_session"),
            require_db_config=True,
        )

        from openai import OpenAI
        from deepeval.test_case import LLMTestCase
        try:
            from deepeval.test_case import LLMTestCaseParams
        except Exception:
            LLMTestCaseParams = None
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            ContextualRelevancyMetric,
            HallucinationMetric,
            ToxicityMetric,
            BiasMetric,
        )
        try:
            from deepeval.metrics import ContextualPrecisionMetric
        except Exception:
            ContextualPrecisionMetric = None
        try:
            from deepeval.metrics import AnswerCorrectnessMetric
        except Exception:
            try:
                from deepeval.metrics.answer_correctness.answer_correctness import AnswerCorrectnessMetric
            except Exception:
                try:
                    from deepeval.metrics.answer_correctness import AnswerCorrectnessMetric
                except Exception:
                    AnswerCorrectnessMetric = None
        try:
            from deepeval.metrics import GEval
        except Exception:
            GEval = None
        from deepeval.models import DeepEvalBaseLLM

        class QwenDeepEvalLLM(DeepEvalBaseLLM):
            def __init__(self, runtime: Dict[str, str]):
                api_key = (runtime or {}).get("api_key") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("API密钥未配置")
                self.api_key = api_key
                self.base_url = (runtime or {}).get("base_url") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                self.model = (runtime or {}).get("model") or os.getenv("QWEN_MODEL", "qwen-plus")
                self.temperature = 0.0
                self.max_tokens = 2000
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            def load_model(self):
                return self.client

            def generate(self, prompt: str) -> str:
                import time
                start_time = time.time()
                try:
                    client = self.load_model()
                    completion = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are an evaluation assistant. Respond with only valid JSON. Ensure the `reason` field is written in Simplified Chinese (zh-CN)."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    if completion and completion.choices:
                        content = completion.choices[0].message.content or ""
                        # 记录Token使用情况
                        if hasattr(completion, "usage") and completion.usage:
                            try:
                                from services.llm_service import log_token_usage
                                import threading
                                usage_dict = {
                                    "prompt_tokens": completion.usage.prompt_tokens,
                                    "completion_tokens": completion.usage.completion_tokens,
                                    "total_tokens": completion.usage.total_tokens
                                }
                                # 使用线程异步记录
                                threading.Thread(
                                    target=log_token_usage,
                                    args=("evaluation", self.model, usage_dict, latency_ms),
                                    daemon=True
                                ).start()
                            except Exception as e:
                                logger.error(f"记录评估Token使用失败: {e}")
                        return self._ensure_valid_json(content.strip())
                    return self._ensure_valid_json("")
                except Exception as err:
                    latency_ms = int((time.time() - start_time) * 1000)
                    try:
                        from services.llm_service import log_token_usage
                        import threading
                        threading.Thread(
                            target=log_token_usage,
                            args=("evaluation", self.model, {}, latency_ms, True, str(err)),
                            daemon=True
                        ).start()
                    except Exception as le:
                        logger.error(f"记录评估错误Token使用失败: {le}")
                    raise err

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

        qwen_llm = QwenDeepEvalLLM(runtime_cfg)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        available_metrics: Dict[str, Any] = {
            "answer_relevance": AnswerRelevancyMetric,
            "faithfulness": FaithfulnessMetric,
            "context_relevance": ContextualRelevancyMetric,
            "hallucination": HallucinationMetric,
            "toxicity": ToxicityMetric,
            "bias": BiasMetric,
        }
        if ContextualPrecisionMetric is not None:
            available_metrics["context_precision"] = ContextualPrecisionMetric
        if AnswerCorrectnessMetric is not None:
            available_metrics["answer_correctness"] = AnswerCorrectnessMetric
        elif GEval is not None and LLMTestCaseParams is not None:
            class AnswerCorrectnessCompatMetric:
                def __init__(self, model, include_reason=True):
                    self._metric = GEval(
                        name="Answer Correctness",
                        criteria=(
                            "Assess whether the actual output is factually correct and consistent "
                            "with the expected output. Give a score between 0 and 1."
                        ),
                        evaluation_params=[
                            LLMTestCaseParams.INPUT,
                            LLMTestCaseParams.ACTUAL_OUTPUT,
                            LLMTestCaseParams.EXPECTED_OUTPUT,
                        ],
                        model=model,
                    )
                    self.score = 0.0
                    self.reason = None

                def measure(self, test_case):
                    self._metric.measure(test_case)
                    self.score = float(getattr(self._metric, "score", 0.0))
                    self.reason = getattr(self._metric, "reason", None)

            available_metrics["answer_correctness"] = AnswerCorrectnessCompatMetric

        metric_classes = self._map_deepeval_metrics(evaluation_metrics, available_metrics)
        if not metric_classes:
            raise RuntimeError("DeepEval评估指标加载失败")
        missing_metrics = [m for m in evaluation_metrics if m not in metric_classes]
        if missing_metrics:
            raise RuntimeError(f"DeepEval当前环境不支持以下指标: {', '.join(missing_metrics)}")

        def _contains_cjk(text: str) -> bool:
            return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))

        def _translate_reason_to_zh(reason_text: str) -> str:
            raw = str(reason_text or "").strip()
            if not raw or _contains_cjk(raw):
                return raw
            try:
                client = qwen_llm.load_model()
                completion = client.chat.completions.create(
                    model=qwen_llm.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是专业翻译助手。请将用户提供的评估理由翻译为简体中文，只输出译文，不要添加解释。",
                        },
                        {"role": "user", "content": raw},
                    ],
                    temperature=0.0,
                    max_tokens=1200,
                )
                if completion and completion.choices:
                    translated = (completion.choices[0].message.content or "").strip()
                    return translated or raw
            except Exception as translate_error:
                logger.warning(f"评估理由翻译失败，保留原文: {translate_error}")
            return raw

        def evaluate_single_row(row: Dict[str, Any]) -> Dict[str, Any]:
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
            
            if not a_val:
                raise ValueError(f"问题 '{q_val[:50]}...' 的答案为空，无法进行评估")
            
            test_case = LLMTestCase(
                input=q_val,
                actual_output=a_val,
                expected_output=gt_val,
                retrieval_context=retrieval_context,
                context=retrieval_context,
            )
            
            metrics_out: Dict[str, float] = {}
            reasons_out: Dict[str, str] = {}
            failed_metrics: List[str] = []
            
            for metric_name, metric_cls in metric_classes.items():
                try:
                    # 注入 include_reason=True 强制要求 LLM 输出评估理由
                    metric = metric_cls(model=qwen_llm, include_reason=True)
                except TypeError:
                    metric = metric_cls(model=qwen_llm)
                try:
                    metric.measure(test_case)
                    score_value = float(getattr(metric, "score", 0.0))
                    reason_value = getattr(metric, "reason", None)
                except Exception as e:
                    error_msg = str(e).lower()
                    # 对于严重错误（如网络断开、鉴权失败、限流等），直接向外抛出异常中断评估
                    if any(kw in error_msg for kw in ["api key", "unauthorized", "401", "403", "429", "connection", "timeout", "rate limit"]):
                        raise RuntimeError(f"大模型接口调用发生严重错误: {e}")
                    logger.warning(f"DeepEval metric {metric_name} 计算失败: {e}")
                    failed_metrics.append(metric_name)
                    score_value = 0.0
                    reason_value = f"评估失败: {str(e)}"
                
                metrics_out[metric_name] = score_value
                if reason_value:
                    reasons_out[metric_name] = _translate_reason_to_zh(str(reason_value))
            
            if len(failed_metrics) == len(metric_classes):
                raise RuntimeError(f"问题 '{q_val[:50]}...' 的所有指标评估均失败: {', '.join(failed_metrics)}")
            elif len(failed_metrics) > 0:
                logger.warning(f"问题 '{q_val[:50]}...' 的部分指标评估失败: {', '.join(failed_metrics)}")

            context_value = row.get("contexts", [])
            if isinstance(context_value, list):
                context_str = ", ".join(context_value)
            else:
                context_str = str(context_value) if context_value is not None else ""

            return {
                "question_id": row.get("question_id", ""),
                "question": row.get("question", ""),
                "expected_answer": row.get("ground_truth", ""),
                "generated_answer": row.get("answer", ""),
                "context": context_str,
                "metrics": metrics_out,
                "reasons": reasons_out,
                "evaluation_time": time.time() - start_time,
            }

        results: List[Dict[str, Any]] = []
        
        # 使用多线程并发评估各个题目，极大提升执行效率
        with ThreadPoolExecutor(max_workers=min(10, len(rows) or 1)) as executor:
            future_to_row = {executor.submit(evaluate_single_row, row): row for row in rows}
            completed_count = 0
            total_count = len(rows)
            for future in as_completed(future_to_row):
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    if callable(progress_callback):
                        try:
                            progress_callback(completed_count, total_count)
                        except Exception as cb_error:
                            logger.warning(f"进度回调执行失败: {cb_error}")
                except Exception as exc:
                    raise RuntimeError(f"DeepEval 并发执行时出错: {exc}")

        # 保持原有的返回顺序
        results_map = {r.get("question_id"): r for r in results if r.get("question_id")}
        ordered_results = []
        for row in rows:
            qid = row.get("question_id", "")
            if qid in results_map:
                ordered_results.append(results_map[qid])

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
                ContextPrecision,
            )

            class_map = {
                "answer_relevance": AnswerRelevancy,
                "context_relevance": ContextRecall,
                "context_precision": ContextPrecision,
                "faithfulness": Faithfulness,
                "answer_correctness": AnswerCorrectness,
                "answer_similarity": AnswerSimilarity,
            }
            out = []
            for m in metrics:
                cls = class_map.get(m)
                if cls:
                    if m in ("answer_relevance", "context_relevance", "context_precision"):
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
                    context_precision,
                )

                func_map = {
                    "answer_relevance": answer_relevancy,
                    "context_relevance": context_recall,
                    "context_precision": context_precision,
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
                "context_precision": 0.2,
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
        """获取评估历史记录 (已废弃)"""
        logger.warning("get_evaluation_history 方法已被废弃，评估结果应从数据库中读取。")
        return []
    
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
