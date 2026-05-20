import requests
import json
import time
import os

BASE = "http://localhost:8001/api/v1"

def main():
    print("=== 1. 注册/登录 ===")
    r = requests.post(f"{BASE}/auth/register", json={
        "username": "diag_user",
        "email": "diag@test.com",
        "password": "diag123456"
    })
    if r.status_code == 201:
        print("注册成功")
    else:
        print(f"注册: {r.status_code} (可能已存在)")

    r = requests.post(f"{BASE}/auth/login", data={"username": "diag_user", "password": "diag123456"})
    if r.status_code != 200:
        print(f"登录失败: {r.status_code} {r.text[:200]}")
        return
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{BASE}/auth/me", headers=headers).json()
    user_id = me.get("id", "")
    print(f"登录成功, user_id={user_id}")

    print("\n=== 2. 上传测试文档 ===")
    dummy_path = r"d:\AIAI\AIAI\diag-test-doc.txt"
    with open(dummy_path, "w", encoding="utf-8") as f:
        f.write("诊断测试文档 - 用于验证多轮评估功能\n")
        f.write("产品名称: 荣耀鑫享终身寿险\n")
        f.write("缴费期限: 3年/5年/10年/20年\n")
        f.write("现金价值第5年: 已交保费45%\n")
        f.write("理赔材料: 身份证、保单、诊断证明、银行账户\n")
        f.write("审核时效: 5个工作日\n")
    
    with open(dummy_path, "rb") as f:
        files = {"file": ("diag-test-doc.txt", f, "text/plain")}
        data = {"category": "诊断测试", "analyze": "false"}
        r = requests.post(f"{BASE}/documents/upload", headers=headers, files=files, data=data)
    if r.status_code not in (200, 201):
        print(f"上传文档失败: {r.status_code} {r.text[:300]}")
        return
    doc = r.json()
    doc_id = doc.get("id")
    print(f"文档上传成功: id={doc_id}, name={doc.get('filename')}")

    print("\n=== 3. 导入诊断测试集CSV ===")
    with open(r"d:\AIAI\AIAI\diag-multi-turn.csv", "rb") as f:
        files = {"file": ("diag-multi-turn.csv", f, "text/csv")}
        data = {
            "name": "诊断-多轮知识保持度",
            "description": "最小化诊断测试集，验证知识保持度评估",
            "conversation_mode": "multi",
            "document_id": str(doc_id),
        }
        r = requests.post(f"{BASE}/testsets/import", headers=headers, files=files, data=data)
    if r.status_code not in (200, 201):
        print(f"导入失败: {r.status_code} {r.text[:500]}")
        return
    testset_data = r.json()
    ts = testset_data.get("testset", testset_data)
    testset_id = ts.get("id")
    print(f"导入成功: id={testset_id}, name={ts.get('name')}, questions={ts.get('question_count')}")

    print("\n=== 4. 触发多轮评估 ===")
    eval_payload = {
        "testset_id": testset_id,
        "evaluation_metrics": ["knowledge_retention", "conversation_relevancy", "conversation_completeness"],
    }
    r = requests.post(f"{BASE}/evaluations/conversation", headers=headers, json=eval_payload)
    if r.status_code not in (200, 201):
        print(f"评估启动失败: {r.status_code} {r.text[:500]}")
        return
    eval_result = r.json()
    eval_id = eval_result.get("id") or eval_result.get("evaluation_id")
    print(f"评估已启动: eval_id={eval_id}")

    print("\n=== 5. 等待评估完成(最多180s) ===")
    for i in range(60):
        time.sleep(3)
        try:
            r = requests.get(f"{BASE}/evaluations/{eval_id}", headers=headers)
            if r.status_code == 200:
                sd = r.json()
                st = sd.get("status", "")
                print(f"  [{i*3}s] status={st}")
                if st in ("completed", "failed", "error"):
                    break
        except Exception as e:
            print(f"  [{i*3}s] 查询异常: {e}")

    print("\n=== 6. 获取评估结果 ===")
    r = requests.get(f"{BASE}/evaluations/{eval_id}/results", headers=headers)
    if r.status_code == 200:
        results = r.json()
        results_list = results if isinstance(results, list) else results.get("results", [])
        print(f"\n共 {len(results_list)} 个结果:")
        for res in results_list[:10]:
            title = (res.get("question_text") or "")[:60]
            metrics = res.get("metrics") or {}
            reasons = res.get("reasons") or {}
            kr_score = metrics.get("knowledge_retention", "N/A")
            cr_score = metrics.get("conversation_relevancy", "N/A")
            cc_score = metrics.get("conversation_completeness", "N/A")
            kr_reason = str(reasons.get("knowledge_retention", ""))[:150]
            print(f"\n  Case: {title}")
            print(f"    KR={kr_score}  CR={cr_score}  CC={cc_score}")
            print(f"    KR_reason: {kr_reason}")

            turn_results = res.get("turn_results", [])
            for tr in turn_results[:5]:
                tm = tr.get("metrics") or {}
                trs = tr.get("reasons") or {}
                t_kr = tm.get("knowledge_retention", "N/A")
                t_kr_r = str(trs.get("knowledge_retention", ""))[:120]
                ti = tr.get("turn_index", "?")
                ga = str(tr.get("generated_answer", "") or "")[:60]
                print(f"      Turn[{ti}] ans={ga!r} | KR={t_kr}: {t_kr_r}")
    else:
        print(f"获取结果失败: {r.status_code} {r.text[:300]}")

if __name__ == "__main__":
    main()
