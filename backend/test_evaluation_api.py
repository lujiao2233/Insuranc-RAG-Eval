"""评估API测试脚本
测试评估执行流程的API接口
"""
import httpx
import asyncio
import sys
import time
from io import BytesIO

BASE_URL = "http://localhost:8000"


def create_test_pdf():
    """创建测试PDF文件"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Test Document for Evaluation Testing")
        c.drawString(100, 720, "This document is used to test evaluation functionality.")
        c.drawString(100, 690, "Content includes:")
        c.drawString(120, 660, "- RAG system evaluation")
        c.drawString(120, 630, "- API integration testing")
        c.drawString(120, 600, "- Performance metrics calculation")
        c.save()
        buffer.seek(0)
        return buffer
    except ImportError:
        return None


class EvaluationAPITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.document_id = None
        self.testset_id = None
        self.evaluation_id = None
        self.task_id = None
        self.username = f"evaluser_{int(time.time())}"
    
    async def close(self):
        await self.client.aclose()
    
    def get_headers(self, with_auth=False):
        headers = {"Content-Type": "application/json"}
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def test_health(self):
        """测试健康检查"""
        print("\n" + "=" * 50)
        print("测试健康检查...")
        
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            print(f"  状态码: {response.status_code}")
            print(f"  响应: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_register_and_login(self):
        """测试注册和登录"""
        print("\n" + "=" * 50)
        print("测试用户注册和登录...")
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "username": self.username,
                    "email": f"{self.username}@test.com",
                    "password": "testpassword123",
                    "full_name": "Evaluation Tester"
                }
            )
            if response.status_code not in [200, 201, 400]:
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
                print(f"  ✓ 登录成功")
                return True
            else:
                print(f"  登录失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_upload_document(self):
        """测试上传文档"""
        print("\n" + "=" * 50)
        print("测试文档上传...")
        
        pdf_buffer = create_test_pdf()
        if not pdf_buffer:
            print("  跳过: 无法创建测试PDF")
            return False
        
        try:
            files = {"file": ("eval_test.pdf", pdf_buffer, "application/pdf")}
            response = await self.client.post(
                f"{BASE_URL}/api/v1/documents/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.document_id = data.get("id")
                print(f"  文档ID: {self.document_id}")
                print("  ✓ 上传成功")
                return True
            else:
                print(f"  上传失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_create_testset(self):
        """测试创建测试集"""
        print("\n" + "=" * 50)
        print("测试创建测试集...")
        
        if not self.document_id:
            print("  跳过: 没有文档ID")
            return False
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/testsets/",
                json={
                    "document_id": self.document_id,
                    "name": f"Test Set {int(time.time())}",
                    "description": "Test set for evaluation testing",
                    "generation_method": "qwen_model"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.testset_id = data.get("id")
                print(f"  测试集ID: {self.testset_id}")
                print("  ✓ 创建成功")
                return True
            else:
                print(f"  创建失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_list_evaluations(self):
        """测试获取评估列表"""
        print("\n" + "=" * 50)
        print("测试获取评估列表...")
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/evaluations/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  评估总数: {data.get('total', 0)}")
                print("  ✓ 获取成功")
                return True
            else:
                print(f"  获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_create_evaluation(self):
        """测试创建评估任务"""
        print("\n" + "=" * 50)
        print("测试创建评估任务...")
        
        if not self.testset_id:
            print("  跳过: 没有测试集ID")
            return False
        
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
                print(f"  评估ID: {self.evaluation_id}")
                print(f"  任务ID: {self.task_id}")
                print("  ✓ 创建成功")
                return True
            else:
                print(f"  创建失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_task_status(self):
        """测试获取任务状态"""
        print("\n" + "=" * 50)
        print("测试获取任务状态...")
        
        if not self.task_id:
            print("  跳过: 没有任务ID")
            return False
        
        try:
            for i in range(10):
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/evaluations/task/{self.task_id}",
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    message = data.get("message", "")
                    print(f"  状态: {status}, 进度: {progress:.0%}, 消息: {message}")
                    
                    if status in ["finished", "failed"]:
                        return status == "finished"
                else:
                    print(f"  获取失败: {response.text}")
                    return False
                
                await asyncio.sleep(2)
            
            print("  超时: 任务未完成")
            return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_evaluation(self):
        """测试获取评估详情"""
        print("\n" + "=" * 50)
        print("测试获取评估详情...")
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/evaluations/{self.evaluation_id}",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  状态: {data.get('status')}")
                print(f"  评估问题数: {data.get('evaluated_questions')}")
                print(f"  评估耗时: {data.get('evaluation_time')}秒")
                if data.get('overall_metrics'):
                    print(f"  总体指标: {data.get('overall_metrics')}")
                print("  ✓ 获取成功")
                return True
            else:
                print(f"  获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_evaluation_results(self):
        """测试获取评估结果"""
        print("\n" + "=" * 50)
        print("测试获取评估结果...")
        
        if not self.evaluation_id:
            print("  跳过: 没有评估ID")
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/evaluations/{self.evaluation_id}/results",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  结果总数: {data.get('total', 0)}")
                if data.get('items'):
                    item = data['items'][0]
                    print(f"  示例问题: {item.get('question_text', '')[:50]}...")
                    print(f"  示例指标: {item.get('metrics', {})}")
                print("  ✓ 获取成功")
                return True
            else:
                print(f"  获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("RAG评估系统 - 评估API测试")
        print("=" * 60)
        
        results = {}
        
        results["健康检查"] = await self.test_health()
        results["注册登录"] = await self.test_register_and_login()
        results["文档上传"] = await self.test_upload_document()
        results["创建测试集"] = await self.test_create_testset()
        results["评估列表"] = await self.test_list_evaluations()
        results["创建评估"] = await self.test_create_evaluation()
        results["任务状态"] = await self.test_get_task_status()
        results["评估详情"] = await self.test_get_evaluation()
        results["评估结果"] = await self.test_get_evaluation_results()
        
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
            print("所有测试通过!")
        else:
            print("部分测试失败，请检查上述错误信息。")
        print("=" * 60)
        
        return all_passed


async def main():
    tester = EvaluationAPITester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
