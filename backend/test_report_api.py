"""结果查看API测试脚本
测试报告生成和结果查看的API接口
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
        c.drawString(100, 750, "Report Test Document")
        c.drawString(100, 720, "This document is used for testing report generation.")
        c.drawString(100, 690, "Section 1: Introduction")
        c.drawString(100, 660, "This is a test document for RAG evaluation report testing.")
        c.save()
        buffer.seek(0)
        return buffer
    except ImportError:
        return None


class ReportAPITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        self.document_id = None
        self.testset_id = None
        self.evaluation_id = None
        self.username = f"reporter_{int(time.time())}"
    
    async def close(self):
        await self.client.aclose()
    
    def get_headers(self, with_auth=False):
        headers = {"Content-Type": "application/json"}
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def setup_test_data(self):
        """设置测试数据"""
        print("\n" + "=" * 60)
        print("准备测试数据...")
        print("=" * 60)
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@test.com",
                "password": "testpassword123"
            }
        )
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": self.username, "password": "testpassword123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print(f"  ✗ 登录失败: {response.text}")
            return False
        
        self.token = response.json().get("access_token")
        print("  ✓ 用户登录成功")
        
        pdf_buffer = create_test_pdf()
        if pdf_buffer:
            files = {"file": ("report_test.pdf", pdf_buffer, "application/pdf")}
            response = await self.client.post(
                f"{BASE_URL}/api/v1/documents/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                self.document_id = response.json().get("id")
                print("  ✓ 文档上传成功")
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/testsets/",
            json={
                "document_id": self.document_id,
                "name": f"Report Test Set {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "description": "Test set for report generation testing."
            },
            headers=self.get_headers(with_auth=True)
        )
        
        if response.status_code in [200, 201]:
            self.testset_id = response.json().get("id")
            print("  ✓ 测试集创建成功")
        
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
                "expected_answer": "This document is used for testing report generation functionality.",
                "context": "Report Test Document for testing."
            },
            {
                "question": "How many sections are in this document?",
                "question_type": "factual",
                "expected_answer": "The document has one section.",
                "context": "Section 1: Introduction"
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
        print("  ✓ 测试问题添加成功")
        
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
            self.evaluation_id = response.json().get("id")
            task_id = response.json().get("task_id")
            print("  ✓ 评估任务创建成功")
            
            for _ in range(30):
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/evaluations/task/{task_id}",
                    headers=self.get_headers(with_auth=True)
                )
                if response.status_code == 200:
                    status = response.json().get("status")
                    if status == "finished":
                        print("  ✓ 评估执行完成")
                        return True
                    elif status == "failed":
                        print(f"  ✗ 评估失败: {response.json().get('error')}")
                        return False
                await asyncio.sleep(2)
            
            print("  ✗ 评估超时")
            return False
        
        print(f"  ✗ 创建评估失败: {response.text}")
        return False
    
    async def test_list_reports(self):
        """测试获取报告列表"""
        print("\n" + "=" * 60)
        print("测试1: 获取报告列表")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  报告总数: {data.get('total', 0)}")
                if data.get('items'):
                    for item in data['items'][:3]:
                        score = item.get('overall_score', 0) or 0
                        print(f"    - {item.get('testset_name')}: 综合评分 {score:.3f}")
                print("  ✓ 获取报告列表成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_report_detail(self):
        """测试获取报告详情"""
        print("\n" + "=" * 60)
        print("测试2: 获取报告详情")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  测试集名称: {data.get('testset_name')}")
                print(f"  评估方法: {data.get('evaluation_method')}")
                print(f"  总问题数: {data.get('total_questions')}")
                print(f"  评估问题数: {data.get('evaluated_questions')}")
                print(f"  评估耗时: {data.get('evaluation_time')}秒")
                
                overall_metrics = data.get('overall_metrics', {})
                if overall_metrics:
                    print(f"  总体指标:")
                    for metric, values in overall_metrics.items():
                        if isinstance(values, dict) and 'mean' in values:
                            print(f"    {metric}: {values['mean']:.4f}")
                
                print("  ✓ 获取报告详情成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_report_summary(self):
        """测试获取报告摘要"""
        print("\n" + "=" * 60)
        print("测试3: 获取报告摘要")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/summary",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                score = data.get('overall_score')
                if score is not None:
                    print(f"  综合评分: {score:.4f}")
                else:
                    print(f"  综合评分: N/A")
                print(f"  性能等级: {data.get('performance_level', 'N/A')}")
                print(f"  关键发现: {data.get('key_findings', [])}")
                print(f"  建议: {data.get('recommendations', [])}")
                print("  ✓ 获取报告摘要成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_evaluation_metrics(self):
        """测试获取评估指标"""
        print("\n" + "=" * 60)
        print("测试4: 获取评估指标详情")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/metrics",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  质量指标:")
                for metric, values in data.get('quality_metrics', {}).items():
                    if isinstance(values, dict) and 'mean' in values:
                        print(f"    {metric}: {values['mean']:.4f}")
                
                print(f"  安全指标:")
                for metric, values in data.get('safety_metrics', {}).items():
                    if isinstance(values, dict) and 'mean' in values:
                        print(f"    {metric}: {values['mean']:.4f}")
                
                overall = data.get('overall_score', {})
                if overall:
                    mean = overall.get('mean')
                    if mean is not None:
                        print(f"  综合评分: {mean:.4f}")
                    else:
                        print(f"  综合评分: N/A")
                
                print("  ✓ 获取评估指标成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_generate_html_report(self):
        """测试生成HTML报告"""
        print("\n" + "=" * 60)
        print("测试5: 生成HTML报告")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/generate?format=html",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  报告路径: {data.get('report_path')}")
                print(f"  报告格式: {data.get('format')}")
                print("  ✓ HTML报告生成成功")
                return True
            else:
                print(f"  ✗ 生成失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_generate_pdf_report(self):
        """测试生成PDF报告"""
        print("\n" + "=" * 60)
        print("测试6: 生成PDF报告")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/generate?format=pdf",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  报告路径: {data.get('report_path')}")
                print(f"  报告格式: {data.get('format')}")
                print("  ✓ PDF报告生成成功")
                return True
            else:
                print(f"  ✗ 生成失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_download_report(self):
        """测试下载报告"""
        print("\n" + "=" * 60)
        print("测试7: 下载报告")
        print("=" * 60)
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/reports/{self.evaluation_id}/download?format=html",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                print(f"  内容类型: {content_type}")
                print(f"  内容长度: {len(response.content)} bytes")
                print("  ✓ 报告下载成功")
                return True
            else:
                print(f"  ✗ 下载失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("RAG评估系统 - 结果查看API测试")
        print("=" * 60)
        
        if not await self.setup_test_data():
            print("测试数据准备失败")
            return False
        
        results = {}
        
        results["获取报告列表"] = await self.test_list_reports()
        results["获取报告详情"] = await self.test_get_report_detail()
        results["获取报告摘要"] = await self.test_get_report_summary()
        results["获取评估指标"] = await self.test_get_evaluation_metrics()
        results["生成HTML报告"] = await self.test_generate_html_report()
        results["生成PDF报告"] = await self.test_generate_pdf_report()
        results["下载报告"] = await self.test_download_report()
        
        print("\n" + "=" * 60)
        print("测试结果汇总:")
        print("=" * 60)
        
        all_passed = True
        for name, passed in results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 所有测试通过!")
        else:
            print("⚠️ 部分测试失败，请检查上述错误信息。")
        print("=" * 60)
        
        return all_passed


async def main():
    tester = ReportAPITester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
