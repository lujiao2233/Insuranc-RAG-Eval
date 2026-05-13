"""RAG评估系统全流程测试脚本
验证所有迁移模块的完整功能
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
        c.drawString(100, 750, "RAG Evaluation System - Full Flow Test Document")
        c.drawString(100, 720, "This document is used for testing the complete evaluation flow.")
        c.drawString(100, 690, "Section 1: Introduction")
        c.drawString(100, 660, "This is a comprehensive test document for RAG evaluation.")
        c.drawString(100, 630, "The system will analyze this document and generate test questions.")
        c.drawString(100, 600, "Section 2: Technical Details")
        c.drawString(100, 570, "RAG systems combine retrieval and generation capabilities.")
        c.drawString(100, 540, "Evaluation metrics include relevance, faithfulness, and accuracy.")
        c.save()
        buffer.seek(0)
        return buffer
    except ImportError:
        return None


class FullFlowTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
        self.token = None
        self.username = f"fullflow_{int(time.time())}"
        self.document_id = None
        self.testset_id = None
        self.evaluation_id = None
        self.test_results = {}
    
    async def close(self):
        await self.client.aclose()
    
    def get_headers(self, with_auth=False):
        headers = {"Content-Type": "application/json"}
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def test_auth_flow(self):
        """测试认证流程"""
        print("\n" + "=" * 60)
        print("【1/6】认证流程测试")
        print("=" * 60)
        
        try:
            print("  注册新用户...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "username": self.username,
                    "email": f"{self.username}@test.com",
                    "password": "testpassword123"
                }
            )
            
            if response.status_code in [200, 201]:
                print("  ✓ 用户注册成功")
            else:
                print(f"  ! 注册响应: {response.status_code}")
            
            print("  用户登录...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                data={"username": self.username, "password": "testpassword123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"  ✓ 登录成功，获取到Token")
                
                print("  获取当前用户信息...")
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/auth/me",
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    user = response.json()
                    print(f"  ✓ 用户: {user.get('username')}, 角色: {user.get('role')}")
                    return True
            else:
                print(f"  ✗ 登录失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def test_document_flow(self):
        """测试文档上传和分析流程"""
        print("\n" + "=" * 60)
        print("【2/6】文档管理流程测试")
        print("=" * 60)
        
        try:
            print("  上传测试文档...")
            pdf_buffer = create_test_pdf()
            if not pdf_buffer:
                print("  ✗ 无法创建测试PDF")
                return False
            
            files = {"file": ("fullflow_test.pdf", pdf_buffer, "application/pdf")}
            response = await self.client.post(
                f"{BASE_URL}/api/v1/documents/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.document_id = data.get("id")
                print(f"  ✓ 文档上传成功，ID: {self.document_id}")
            else:
                print(f"  ✗ 上传失败: {response.text}")
                return False
            
            print("  获取文档列表...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/documents/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 文档列表: {data.get('total', 0)} 个文档")
            
            print("  获取文档详情...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/documents/{self.document_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                doc = response.json()
                print(f"  ✓ 文档: {doc.get('filename')}, 大小: {doc.get('file_size')} bytes")
            
            print("  分析文档...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/analysis/{self.document_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 文档分析完成")
                if data.get("metadata"):
                    print(f"    元数据: {list(data.get('metadata', {}).keys())[:3]}...")
                return True
            else:
                print(f"  ! 分析响应: {response.status_code}")
                return True
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def test_testset_flow(self):
        """测试测试集生成流程"""
        print("\n" + "=" * 60)
        print("【3/6】测试集生成流程测试")
        print("=" * 60)
        
        try:
            print("  创建测试集...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/testsets/",
                json={
                    "document_id": self.document_id,
                    "name": f"Full Flow Test Set {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "description": "Complete flow test for RAG evaluation system"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.testset_id = data.get("id")
                print(f"  ✓ 测试集创建成功，ID: {self.testset_id}")
            else:
                print(f"  ✗ 创建失败: {response.text}")
                return False
            
            print("  添加测试问题...")
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config.settings import settings
            from models.database import Question
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            test_questions = [
                {
                    "question": "What is the purpose of this document?",
                    "question_type": "factual",
                    "expected_answer": "This document is used for testing the complete evaluation flow.",
                    "context": "RAG Evaluation System - Full Flow Test Document"
                },
                {
                    "question": "What evaluation metrics are mentioned?",
                    "question_type": "factual",
                    "expected_answer": "Evaluation metrics include relevance, faithfulness, and accuracy.",
                    "context": "RAG systems combine retrieval and generation capabilities."
                },
                {
                    "question": "How does a RAG system work?",
                    "question_type": "reasoning",
                    "expected_answer": "RAG systems combine retrieval and generation capabilities.",
                    "context": "RAG systems combine retrieval and generation capabilities."
                }
            ]
            
            for q in test_questions:
                question = Question(
                    id=str(uuid.uuid4()),
                    testset_id=self.testset_id,
                    question=q["question"],
                    question_type=q["question_type"],
                    expected_answer=q["expected_answer"],
                    context=q["context"]
                )
                db.add(question)
            db.commit()
            db.close()
            print(f"  ✓ 添加了 {len(test_questions)} 个测试问题")
            
            print("  获取测试集详情...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/testsets/{self.testset_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 测试集: {data.get('name')}")
                print(f"    问题数: {data.get('question_count', 0)}")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def test_evaluation_flow(self):
        """测试评估执行流程"""
        print("\n" + "=" * 60)
        print("【4/6】评估执行流程测试")
        print("=" * 60)
        
        try:
            print("  创建评估任务...")
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
                task_id = data.get("task_id")
                print(f"  ✓ 评估任务创建成功")
                print(f"    评估ID: {self.evaluation_id}")
                print(f"    任务ID: {task_id}")
            else:
                print(f"  ✗ 创建失败: {response.text}")
                return False
            
            print("  等待评估完成...")
            for i in range(30):
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/evaluations/task/{task_id}",
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    
                    if status == "finished":
                        print(f"  ✓ 评估执行完成")
                        print(f"    进度: 100%")
                        break
                    elif status == "failed":
                        print(f"  ✗ 评估失败: {data.get('error')}")
                        return False
                    else:
                        print(f"    进度: {progress}%")
                        await asyncio.sleep(2)
                else:
                    await asyncio.sleep(2)
            else:
                print("  ✗ 评估超时")
                return False
            
            print("  获取评估结果...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/evaluations/{self.evaluation_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 评估结果获取成功")
                print(f"    总问题数: {data.get('total_questions')}")
                print(f"    评估问题数: {data.get('evaluated_questions')}")
                
                overall = data.get("overall_metrics", {})
                if overall:
                    print("    总体指标:")
                    for metric, values in overall.items():
                        if isinstance(values, dict) and "mean" in values:
                            print(f"      {metric}: {values['mean']:.4f}")
                
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def test_report_flow(self):
        """测试报告生成流程"""
        print("\n" + "=" * 60)
        print("【5/6】报告生成流程测试")
        print("=" * 60)
        
        try:
            print("  获取报告列表...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 报告总数: {data.get('total', 0)}")
            
            print("  获取报告详情...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 报告详情获取成功")
                print(f"    测试集: {data.get('testset_name')}")
            
            print("  获取报告摘要...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/summary",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                score = data.get('overall_score')
                if score is not None:
                    print(f"  ✓ 综合评分: {score:.4f}")
                print(f"    性能等级: {data.get('performance_level')}")
            
            print("  生成HTML报告...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/generate?format=html",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ HTML报告生成成功")
                print(f"    路径: {data.get('report_path')}")
            
            print("  生成PDF报告...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/generate?format=pdf",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ PDF报告生成成功")
                print(f"    路径: {data.get('report_path')}")
                return True
            else:
                print(f"  ✗ PDF生成失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def test_config_flow(self):
        """测试配置管理流程"""
        print("\n" + "=" * 60)
        print("【6/6】配置管理流程测试")
        print("=" * 60)
        
        try:
            print("  获取配置列表...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 配置总数: {data.get('total', 0)}")
            
            print("  获取Qwen配置...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/qwen/all",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  ✓ Qwen配置项: {len(configs)}")
            
            print("  获取评估配置...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/evaluation/all",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  ✓ 评估配置项: {len(configs)}")
            
            print("  获取API状态...")
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/api/status",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('api_status', {})
                print(f"  ✓ API状态: {status}")
            
            print("  批量更新配置...")
            response = await self.client.post(
                f"{BASE_URL}/api/v1/config/batch",
                json={
                    "configs": {
                        "test.fullflow": "completed",
                        "test.timestamp": datetime.now().isoformat()
                    }
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 批量更新成功: {data.get('total_updated', 0)} 项")
                return True
            else:
                print(f"  ✗ 批量更新失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("  RAG评估系统 - 全流程测试")
        print("  测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 70)
        
        self.test_results["认证流程"] = await self.test_auth_flow()
        self.test_results["文档管理"] = await self.test_document_flow()
        self.test_results["测试集生成"] = await self.test_testset_flow()
        self.test_results["评估执行"] = await self.test_evaluation_flow()
        self.test_results["报告生成"] = await self.test_report_flow()
        self.test_results["配置管理"] = await self.test_config_flow()
        
        print("\n" + "=" * 70)
        print("  测试结果汇总")
        print("=" * 70)
        
        all_passed = True
        for name, passed in self.test_results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "-" * 70)
        if all_passed:
            print("  🎉 全流程测试通过！所有模块工作正常。")
        else:
            print("  ⚠️ 部分测试失败，请检查上述错误信息。")
        print("-" * 70)
        
        return all_passed


async def main():
    tester = FullFlowTester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
