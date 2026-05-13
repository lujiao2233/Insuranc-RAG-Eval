"""配置管理API测试脚本
测试系统配置、API密钥管理等功能
"""
import httpx
import asyncio
import sys
import time
import json

BASE_URL = "http://localhost:8000"


class ConfigAPITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.username = f"config_tester_{int(time.time())}"
    
    async def close(self):
        await self.client.aclose()
    
    def get_headers(self, with_auth=False):
        headers = {"Content-Type": "application/json"}
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def setup(self):
        """设置测试环境"""
        print("\n" + "=" * 60)
        print("准备测试环境...")
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
        return True
    
    async def test_list_configurations(self):
        """测试获取配置列表"""
        print("\n" + "=" * 60)
        print("测试1: 获取配置列表")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  配置总数: {data.get('total', 0)}")
                print("  ✓ 获取配置列表成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_create_and_get_config(self):
        """测试创建和获取配置"""
        print("\n" + "=" * 60)
        print("测试2: 创建和获取配置")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/config/",
                json={
                    "config_key": "test.config_item",
                    "config_value": "test_value_123",
                    "description": "测试配置项"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code in [200, 201]:
                print("  ✓ 创建配置成功")
            else:
                print(f"  ✗ 创建失败: {response.text}")
                return False
            
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/test.config_item",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  配置键: {data.get('config_key')}")
                print(f"  配置值: {data.get('config_value')}")
                print("  ✓ 获取配置成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_update_config(self):
        """测试更新配置"""
        print("\n" + "=" * 60)
        print("测试3: 更新配置")
        print("=" * 60)
        
        try:
            response = await self.client.put(
                f"{BASE_URL}/api/v1/config/test.config_item",
                json={
                    "config_value": "updated_value_456",
                    "description": "更新后的测试配置项"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  更新后的值: {data.get('config_value')}")
                print("  ✓ 更新配置成功")
                return True
            else:
                print(f"  ✗ 更新失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_batch_update(self):
        """测试批量更新配置"""
        print("\n" + "=" * 60)
        print("测试4: 批量更新配置")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/config/batch",
                json={
                    "configs": {
                        "test.batch_item1": "value1",
                        "test.batch_item2": "value2",
                        "test.batch_item3": {"nested": "value"}
                    }
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  更新成功: {data.get('total_updated', 0)} 项")
                print("  ✓ 批量更新成功")
                return True
            else:
                print(f"  ✗ 批量更新失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_config_group(self):
        """测试获取配置组"""
        print("\n" + "=" * 60)
        print("测试5: 获取配置组")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/group/test",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  前缀: {data.get('prefix')}")
                print(f"  配置数量: {len(configs)}")
                for key, value in list(configs.items())[:3]:
                    print(f"    - {key}: {value}")
                print("  ✓ 获取配置组成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_api_key_management(self):
        """测试API密钥管理"""
        print("\n" + "=" * 60)
        print("测试6: API密钥管理")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/config/api/key",
                json={
                    "service": "qwen",
                    "api_key": "sk-test-api-key-12345"
                },
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                print("  ✓ 设置API密钥成功")
            else:
                print(f"  ✗ 设置失败: {response.text}")
                return False
            
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/api/status",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('api_status', {})
                print(f"  API状态: {status}")
                print("  ✓ 获取API状态成功")
                return True
            else:
                print(f"  ✗ 获取状态失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_qwen_config(self):
        """测试获取Qwen配置"""
        print("\n" + "=" * 60)
        print("测试7: 获取Qwen配置")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/qwen/all",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  Qwen配置数量: {len(configs)}")
                for key, value in list(configs.items())[:5]:
                    if 'api_key' not in key.lower():
                        print(f"    - {key}: {value}")
                print("  ✓ 获取Qwen配置成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_evaluation_config(self):
        """测试获取评估配置"""
        print("\n" + "=" * 60)
        print("测试8: 获取评估配置")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/evaluation/all",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  评估配置数量: {len(configs)}")
                for key, value in configs.items():
                    print(f"    - {key}: {value}")
                print("  ✓ 获取评估配置成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_get_thresholds(self):
        """测试获取性能阈值"""
        print("\n" + "=" * 60)
        print("测试9: 获取性能阈值配置")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/thresholds/all",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  阈值配置数量: {len(configs)}")
                for key, value in configs.items():
                    print(f"    - {key}: {value}")
                print("  ✓ 获取阈值配置成功")
                return True
            else:
                print(f"  ✗ 获取失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_export_import(self):
        """测试导出导入配置"""
        print("\n" + "=" * 60)
        print("测试10: 导出导入配置")
        print("=" * 60)
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/config/export",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get('configs', {})
                print(f"  导出配置数量: {len(configs)}")
                print("  ✓ 导出配置成功")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/v1/config/import",
                    json={
                        "configs": {"test.imported": "imported_value"},
                        "overwrite": True
                    },
                    headers=self.get_headers(with_auth=True)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  导入成功: {data.get('total_imported', 0)} 项")
                    print("  ✓ 导入配置成功")
                    return True
                else:
                    print(f"  ✗ 导入失败: {response.text}")
                    return False
            else:
                print(f"  ✗ 导出失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_delete_config(self):
        """测试删除配置"""
        print("\n" + "=" * 60)
        print("测试11: 删除配置")
        print("=" * 60)
        
        try:
            response = await self.client.delete(
                f"{BASE_URL}/api/v1/config/test.config_item",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                print("  ✓ 删除配置成功")
                return True
            else:
                print(f"  ✗ 删除失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def test_reset_defaults(self):
        """测试重置默认配置"""
        print("\n" + "=" * 60)
        print("测试12: 重置默认配置")
        print("=" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/config/reset?prefix=test",
                headers=self.get_headers(with_auth=True)
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  重置数量: {data.get('count', 0)}")
                print("  ✓ 重置默认配置成功")
                return True
            else:
                print(f"  ✗ 重置失败: {response.text}")
                return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("RAG评估系统 - 配置管理API测试")
        print("=" * 60)
        
        if not await self.setup():
            print("测试环境准备失败")
            return False
        
        results = {}
        
        results["获取配置列表"] = await self.test_list_configurations()
        results["创建和获取配置"] = await self.test_create_and_get_config()
        results["更新配置"] = await self.test_update_config()
        results["批量更新配置"] = await self.test_batch_update()
        results["获取配置组"] = await self.test_get_config_group()
        results["API密钥管理"] = await self.test_api_key_management()
        results["获取Qwen配置"] = await self.test_get_qwen_config()
        results["获取评估配置"] = await self.test_get_evaluation_config()
        results["获取性能阈值"] = await self.test_get_thresholds()
        results["导出导入配置"] = await self.test_export_import()
        results["删除配置"] = await self.test_delete_config()
        results["重置默认配置"] = await self.test_reset_defaults()
        
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
    tester = ConfigAPITester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
