"""完整评估流程测试脚本
生成测试数据并执行完整的评估流程
"""
import httpx
import asyncio
import sys
import time
import uuid
from io import BytesIO
from datetime import datetime

BASE_URL = "http://localhost:8000"


def create_test_pdf():
    """创建测试PDF文件"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)
        
        c.drawString(100, 750, "RAG System Evaluation Test Document")
        c.drawString(100, 720, "This document contains test content for RAG evaluation.")
        c.drawString(100, 690, "")
        c.drawString(100, 660, "Section 1: Introduction")
        c.drawString(100, 630, "RAG (Retrieval-Augmented Generation) is a technique that combines")
        c.drawString(100, 600, "retrieval systems with generative AI models to produce more accurate")
        c.drawString(100, 570, "and contextually relevant responses.")
        c.drawString(100, 540, "")
        c.drawString(100, 510, "Section 2: Key Components")
        c.drawString(100, 480, "1. Document Store: Stores and indexes documents for retrieval")
        c.drawString(100, 450, "2. Retriever: Finds relevant documents based on queries")
        c.drawString(100, 420, "3. Generator: LLM that generates responses using retrieved context")
        c.drawString(100, 390, "")
        c.drawString(100, 360, "Section 3: Evaluation Metrics")
        c.drawString(100, 330, "- Answer Relevance: How well the answer addresses the question")
        c.drawString(100, 300, "- Faithfulness: How accurately the answer reflects the context")
        c.drawString(100, 270, "- Context Relevance: How relevant the retrieved context is")
        
        c.save()
        buffer.seek(0)
        return buffer
    except ImportError:
        return None


class FullEvaluationTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        self.user_id = None
        self.document_id = None
        self.testset_id = None
        self.evaluation_id = None
        self.task_id = None
        self.username = f"fulleval_{int(time.time())}"
        self.question_ids = []
    
    async def close(self):
        await self.client.aclose()
    
    def get_headers(self, with_auth=False):
        headers = {"Content-Type": "application/json"}
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def step1_register_login(self):
        """步骤1: 注册并登录"""
        print("\n" + "=" * 60)
        print("步骤1: 用户注册和登录")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "username": self.username,
                    "email": f"{self.username}@test.com",
                    "password": "testpassword123",
                    "full_name": "Full Evaluation Tester"
                }
            )
            
            if response.status_code not in [200, 201]:
                if "已被注册" not in response.text:
                    print(f"  注册失败: {response.text}")
                    return False
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                data={"username": self.username, "password": "testpassword123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"  ✓ 登录成功，用户: {self.username}")
                return True
            else:
                print(f"  登录失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def step2_upload_document(self):
        """步骤2: 上传测试文档"""
        print("\n" + "=" * 60)
        print("步骤2: 上传测试文档")
        print("=" * 60)
        
        pdf_buffer = create_test_pdf()
        if not pdf_buffer:
            print("  ✗ 无法创建测试PDF")
            return False
        
        try:
            files = {"file": ("rag_test_document.pdf", pdf_buffer, "application/pdf")}
            response = await self.client.post(
                f"{BASE_URL}/api/v1/documents/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.document_id = data.get("id")
                print(f"  ✓ 文档上传成功")
                print(f"    文档ID: {self.document_id}")
                return True
            else:
                print(f"  ✗ 上传失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def step3_create_testset(self):
        """步骤3: 创建测试集"""
        print("\n" + "=" * 60)
        print("步骤3: 创建测试集")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/testsets/",
                json={
                    "document_id": self.document_id,
                    "name": f"Evaluation Test Set {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "description": "Test set for complete evaluation flow testing",
                    "generation_method": "manual"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.testset_id = data.get("id")
                print(f"  ✓ 测试集创建成功")
                print(f"    测试集ID: {self.testset_id}")
                return True
            else:
                print(f"  ✗ 创建失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def step4_add_test_questions(self):
        """步骤4: 添加测试问题"""
        print("\n" + "=" * 60)
        print("步骤4: 添加测试问题")
        print("=" * 60)
        
        test_questions = [
            {
                "question": "What is RAG and how does it work?",
                "question_type": "factual",
                "expected_answer": "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval systems with generative AI models to produce more accurate and contextually relevant responses. It works by retrieving relevant documents and using them as context for generation.",
                "context": "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval systems with generative AI models to produce more accurate and contextually relevant responses."
            },
            {
                "question": "What are the key components of a RAG system?",
                "question_type": "factual",
                "expected_answer": "The key components of a RAG system are: 1. Document Store - stores and indexes documents for retrieval, 2. Retriever - finds relevant documents based on queries, 3. Generator - LLM that generates responses using retrieved context.",
                "context": "Key Components: 1. Document Store: Stores and indexes documents for retrieval. 2. Retriever: Finds relevant documents based on queries. 3. Generator: LLM that generates responses using retrieved context."
            },
            {
                "question": "What metrics are used to evaluate RAG systems?",
                "question_type": "factual",
                "expected_answer": "The main metrics used to evaluate RAG systems include: Answer Relevance (how well the answer addresses the question), Faithfulness (how accurately the answer reflects the context), and Context Relevance (how relevant the retrieved context is).",
                "context": "Evaluation Metrics: Answer Relevance: How well the answer addresses the question. Faithfulness: How accurately the answer reflects the context. Context Relevance: How relevant the retrieved context is."
            },
            {
                "question": "How does the retriever component function in a RAG system?",
                "question_type": "reasoning",
                "expected_answer": "The retriever component in a RAG system functions by finding relevant documents based on user queries. It searches through the document store, which stores and indexes documents, and retrieves the most relevant pieces of content to be used as context for the generator.",
                "context": "Retriever: Finds relevant documents based on queries. Document Store: Stores and indexes documents for retrieval."
            },
            {
                "question": "Why is faithfulness important in RAG evaluation?",
                "question_type": "reasoning",
                "expected_answer": "Faithfulness is important in RAG evaluation because it measures how accurately the generated answer reflects the retrieved context. A faithful answer ensures that the response is grounded in the actual source material, reducing hallucinations and increasing trustworthiness of the system.",
                "context": "Faithfulness: How accurately the answer reflects the context. This ensures responses are grounded in source material."
            }
        ]
        
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config.settings import settings
            from models.database import Question
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            try:
                for i, q in enumerate(test_questions):
                    question = Question(
                        id=str(uuid.uuid4()),
                        testset_id=self.testset_id,
                        question=q["question"],
                        question_type=q["question_type"],
                        expected_answer=q["expected_answer"],
                        context=q["context"],
                        category_major="RAG Evaluation",
                        category_minor="Test Question"
                    )
                    db.add(question)
                    self.question_ids.append(question.id)
                
                db.commit()
                print(f"  ✓ 添加了 {len(test_questions)} 个测试问题")
                for i, q in enumerate(test_questions):
                    print(f"    {i+1}. {q['question'][:50]}...")
                return True
            finally:
                db.close()
        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step5_create_evaluation(self):
        """步骤5: 创建评估任务"""
        print("\n" + "=" * 60)
        print("步骤5: 创建评估任务")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/evaluations/",
                json={
                    "testset_id": self.testset_id,
                    "evaluation_method": "ragas_official",
                    "evaluation_metrics": ["answer_relevance", "faithfulness"]
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.evaluation_id = data.get("id")
                self.task_id = data.get("task_id")
                print(f"  ✓ 评估任务创建成功")
                print(f"    评估ID: {self.evaluation_id}")
                print(f"    任务ID: {self.task_id}")
                return True
            else:
                print(f"  ✗ 创建失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def step6_monitor_task(self):
        """步骤6: 监控任务执行"""
        print("\n" + "=" * 60)
        print("步骤6: 监控评估任务执行")
        print("=" * 60)
        
        if not self.task_id:
            print("  ✗ 没有任务ID")
            return False
        
        try:
            max_wait = 120
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/evaluations/task/{self.task_id}",
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    message = data.get("message", "")
                    logs = data.get("logs", [])
                    
                    print(f"  状态: {status}, 进度: {progress:.0%}")
                    if message:
                        print(f"  消息: {message}")
                    if logs:
                        print(f"  最新日志: {logs[-1] if logs else '无'}")
                    
                    if status == "finished":
                        print(f"  ✓ 任务完成!")
                        return True
                    elif status == "failed":
                        error = data.get("error", "未知错误")
                        print(f"  ✗ 任务失败: {error}")
                        return False
                else:
                    print(f"  获取状态失败: {response.text}")
                    return False
                
                await asyncio.sleep(3)
            
            print(f"  ✗ 任务超时（等待超过{max_wait}秒）")
            return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def step7_get_results(self):
        """步骤7: 获取评估结果"""
        print("\n" + "=" * 60)
        print("步骤7: 获取评估结果")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  ✗ 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/evaluations/{self.evaluation_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  评估状态: {data.get('status')}")
                print(f"  评估问题数: {data.get('evaluated_questions')}")
                print(f"  评估耗时: {data.get('evaluation_time')}秒")
                
                overall_metrics = data.get('overall_metrics', {})
                if overall_metrics:
                    print(f"\n  总体指标:")
                    for metric, values in overall_metrics.items():
                        if isinstance(values, dict):
                            mean = values.get('mean', 0)
                            print(f"    {metric}: {mean:.4f}")
                        else:
                            print(f"    {metric}: {values}")
                
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/evaluations/{self.evaluation_id}/results",
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    results_data = response.json()
                    items = results_data.get('items', [])
                    print(f"\n  详细结果 ({len(items)} 条):")
                    for i, item in enumerate(items[:3]):
                        print(f"\n    问题 {i+1}: {item.get('question_text', '')[:60]}...")
                        metrics = item.get('metrics', {})
                        for m, v in metrics.items():
                            print(f"      {m}: {v:.4f}")
                
                print(f"\n  ✓ 结果获取成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def run_full_test(self):
        """运行完整测试流程"""
        print("\n" + "=" * 60)
        print("RAG评估系统 - 完整评估流程测试")
        print("=" * 60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {}
        
        results["步骤1: 注册登录"] = await self.step1_register_login()
        results["步骤2: 上传文档"] = await self.step2_upload_document()
        results["步骤3: 创建测试集"] = await self.step3_create_testset()
        results["步骤4: 添加测试问题"] = await self.step4_add_test_questions()
        results["步骤5: 创建评估任务"] = await self.step5_create_evaluation()
        results["步骤6: 监控任务执行"] = await self.step6_monitor_task()
        results["步骤7: 获取评估结果"] = await self.step7_get_results()
        
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        all_passed = True
        for name, passed in results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 所有测试通过! 完整评估流程验证成功!")
        else:
            print("⚠️ 部分测试失败，请检查上述错误信息。")
        print("=" * 60)
        
        return all_passed


async def main():
    tester = FullEvaluationTester()
    try:
        success = await tester.run_full_test()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
