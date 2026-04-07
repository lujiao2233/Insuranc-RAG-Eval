import httpx
import asyncio
import time
import os

BASE_URL = "http://localhost:8000"

async def test_generation():
    if not os.environ.get("DASHSCOPE_API_KEY") and not os.environ.get("QWEN_API_KEY"):
        print("Please set DASHSCOPE_API_KEY")
        # return
    
    client = httpx.AsyncClient(timeout=120.0)
    
    # 1. Register/Login
    username = f"testuser_{int(time.time())}"
    await client.post(f"{BASE_URL}/api/v1/auth/register", json={"username": username, "password": "password123", "email": f"{username}@test.com"})
    
    login_res = await client.post(f"{BASE_URL}/api/v1/auth/login", data={"username": username, "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upload Document
    with open("test_upload.txt", "rb") as f:
        upload_res = await client.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("test_upload.txt", f, "text/plain")}, headers=headers)
    
    if upload_res.status_code != 200:
        print("Upload failed:", upload_res.text)
        return
    
    doc_id = upload_res.json()["id"]
    print(f"Document uploaded: {doc_id}")
    
    # 3. Analyze Document
    analyze_res = await client.post(f"{BASE_URL}/api/v1/analysis/analyze/{doc_id}", headers=headers)
    print(analyze_res.json())
    
    # Wait for analysis
    # for _ in range(30):
    #     doc_res = await client.get(f"{BASE_URL}/api/v1/documents/{doc_id}", headers=headers)
    #     print("Doc:", doc_res.json())
    #     if doc_res.json().get("is_analyzed"):
    #         print("Analysis finished")
    #         break
    #     await asyncio.sleep(2)
        
    # Force is_analyzed=True for testing
    # import sqlite3
    # try:
    #     conn = sqlite3.connect("rag_eval.db")
    #     conn.execute("UPDATE documents SET is_analyzed = 1, doc_metadata = '{\"content\": \"This is a test document about RAG evaluation system.\"}' WHERE id = ?", (doc_id,))
    #     conn.commit()
    #     conn.close()
    # except Exception as e:
    #     print(e)

        
    # 4. Create Testset
    ts_res = await client.post(f"{BASE_URL}/api/v1/testsets/", json={"document_id": doc_id, "name": "Test Gen", "generation_method": "advanced"}, headers=headers)
    ts_id = ts_res.json()["id"]
    print(f"Testset created: {ts_id}")
    
    # 5. Generate Questions
    gen_res = await client.post(f"{BASE_URL}/api/v1/testsets/{ts_id}/generate", json={"num_questions": 2, "generation_mode": "advanced"}, headers=headers)
    print(gen_res.status_code)
    print(gen_res.text)
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_generation())
