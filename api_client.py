"""东吴人寿AI问答系统 - API客户端

该模块提供了与东吴人寿AI问答系统交互的客户端功能，包括：
- 短信验证码登录
- Token管理与缓存
- SSE (Server-Sent Events) 流处理
- 批量问答处理
- 评测集填充

主要功能：
1. 短信验证码登录与Token管理
2. SSE调试与实时数据处理
3. 批量问题处理与答案生成
4. 评测集填充与结果导出
"""

import os
import sys
import time
import json
import base64
import threading
import logging
from typing import Any, Dict, List

import requests
from requests.exceptions import ChunkedEncodingError
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 修复导入路径问题，支持不同运行方式
try:
    from config import BASE_URL, MOBILE, CHANNEL, BOT_ID, USER_TYPE
except ImportError:
    # 当直接运行脚本时，使用相对导入
    from .config import BASE_URL, MOBILE, CHANNEL, BOT_ID, USER_TYPE


logger = logging.getLogger(__name__)
urllib3.disable_warnings(InsecureRequestWarning)


def setup_logging() -> None:
    """配置日志系统
    
    设置日志级别为INFO，同时输出到文件和控制台
    日志文件路径：logs/run.log
    """
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    root = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "run.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


class TalkApiClient:
    """东吴人寿AI问答系统API客户端
    
    提供与东吴人寿AI问答系统交互的核心功能，包括登录、SSE流处理、
    批量问答处理等。
    """
    
    def __init__(self, session: requests.Session | None = None, mobile: str | None = None):
        """初始化API客户端
        
        Args:
            session: 可选的requests会话对象，如果为None则创建新会话
            mobile: 可选的手机号码，如果为None则使用配置文件中的默认值
        """
        setup_logging()
        self.session = session or requests.Session()
        self.session.verify = False
        self.base_url = BASE_URL.rstrip("/")
        override_mobile = os.getenv("MOBILE_OVERRIDE")
        if mobile:
            self.mobile = mobile
        else:
            self.mobile = override_mobile or MOBILE
        self.channel = CHANNEL
        self.bot_id = BOT_ID
        self.user_type = USER_TYPE
        self.token: str | None = None
        logger.info("TalkApiClient initialized for mobile %s", self.mobile)
        self._load_token_from_cache()

    def _url(self, path: str) -> str:
        """构建API请求URL
        
        Args:
            path: API路径，如 "/talk/chat"
            
        Returns:
            完整的API请求URL
        """
        return f"{self.base_url}{path}"

    def send_verify_code(self) -> Dict[str, Any]:
        """发送短信验证码
        
        Returns:
            API响应数据，包含发送结果
        """
        params = {
            "mobile": self.mobile,
            "channel": self.channel,
            "_t": str(int(time.time() * 1000)),
        }
        resp = self.session.get(self._url("/talk/sys/sendVerifyCodeChannel"), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def phone_login(self, verify_code: str) -> Dict[str, Any]:
        """手机号登录
        
        Args:
            verify_code: 短信验证码
            
        Returns:
            登录响应数据
            
        Raises:
            RuntimeError: 登录失败或未找到token
        """
        payload = {
            "mobile": self.mobile,
            "verifyCod": verify_code,
            "channel": self.channel,
        }
        resp = self.session.post(self._url("/talk/sys/phoneLoginChannel"), json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"登录失败: {data}")

        headers = resp.headers
        token = headers.get("x-access-token") or headers.get("X-Access-Token")
        if not token:
            token = (
                data.get("result", {}).get("token")
                or data.get("data", {}).get("token")
                or data.get("token")
                or data.get("result", {}).get("accessToken")
                or data.get("data", {}).get("accessToken")
                or data.get("accessToken")
            )
        if not token:
            raise RuntimeError(f"登录响应中未找到 token: {data}")

        self.token = str(token)
        self._save_token_to_cache(self.token)
        return data

    def _cache_file(self) -> str:
        """获取token缓存文件路径
        
        Returns:
            token缓存文件的完整路径
        """
        root = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(root, "token_cache.json")

    def _decode_token_exp(self, token: str) -> int | None:
        """解析JWT token的过期时间
        
        Args:
            token: JWT token字符串
            
        Returns:
            过期时间戳，如果解析失败则返回None
        """
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload_b64 = parts[1]
            padding = "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_bytes.decode("utf-8"))
            exp = payload.get("exp")
            if exp is None:
                return None
            return int(exp)
        except Exception:
            return None

    def _load_token_from_cache(self) -> None:
        """从缓存文件加载token
        
        检查缓存文件是否存在，token是否有效，以及是否与当前手机号匹配
        """
        path = self._cache_file()
        if not os.path.exists(path):
            logger.info("Token cache file not found at %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            logger.warning("Failed to read token cache file %s", path)
            return
        token = data.get("token")
        exp = data.get("exp")
        mobile = data.get("mobile")
        if not token or mobile != self.mobile:
            logger.info("Token cache invalid or for different mobile, current mobile %s", self.mobile)
            return
        now = int(time.time())
        if isinstance(exp, int) and now < exp - 60:
            self.token = str(token)
            logger.info("Loaded valid token from cache for mobile %s", self.mobile)

    def _save_token_to_cache(self, token: str) -> None:
        """保存token到缓存文件
        
        Args:
            token: 要保存的token
        """
        exp = self._decode_token_exp(token)
        path = self._cache_file()
        data = {
            "token": token,
            "exp": exp,
            "mobile": self.mobile,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            logger.warning("Failed to save token cache to %s", path)
            return
        logger.info("Saved token to cache for mobile %s", self.mobile)

    def _auth_headers(self) -> Dict[str, str]:
        """获取认证头
        
        Returns:
            包含token的认证头
            
        Raises:
            RuntimeError: 尚未登录，token为空
        """
        if not self.token:
            raise RuntimeError("尚未登录，token 为空")
        return {"x-access-token": self.token}

    def is_token_valid(self) -> bool:
        """检查token是否有效
        
        通过调用createSse接口来验证token的有效性
        
        Returns:
            token是否有效
        """
        if not self.token:
            return False
        try:
            logger.info("Checking token validity via createSse")
            resp = self.session.post(
                self._url("/talk/createSse"),
                json={"visitorBizId": self.mobile, "userType": self.user_type},
                headers=self._auth_headers(),
                timeout=10,
                stream=True,
            )
            status = resp.status_code
            resp.close()
            logger.info("Token validity check status %s", status)
            return status == 200
        except Exception:
            logger.exception("Token validity check failed")
            return False

    def ensure_login(self) -> None:
        """确保客户端已登录
        
        如果token有效则直接使用，否则发送验证码并登录
        """
        if self.is_token_valid():
            logger.info("Using existing valid token")
            return
        logger.info("Sending verify code to %s", self.mobile)
        send_resp = self.send_verify_code()
        if send_resp.get("code") not in (200, 0, "200", "0"):
            logger.error("Send verify code failed: %s", send_resp)
            raise RuntimeError(f"发送验证码失败: {send_resp}")
        verify_code = input("请输入短信验证码: ").strip()
        if not verify_code:
            raise RuntimeError("验证码不能为空")
        login_resp = self.phone_login(verify_code)
        if not login_resp.get("success"):
            logger.error("Login failed: %s", login_resp)
            raise RuntimeError(f"登录失败: {login_resp}")
        logger.info("Login success for mobile %s", self.mobile)

    def create_sse(self) -> Dict[str, Any]:
        """创建SSE连接
        
        Returns:
            包含状态码的字典
        """
        payload = {
            "visitorBizId": self.mobile,
            "userType": self.user_type,
        }
        resp = self.session.post(
            self._url("/talk/createSse"),
            json=payload,
            headers=self._auth_headers(),
            timeout=10,
            stream=True,
        )
        resp.raise_for_status()
        return {"status_code": resp.status_code}

    def open_sse_stream(self) -> requests.Response:
        """打开SSE流连接
        
        Returns:
            requests.Response对象，包含SSE流
        """
        payload = {
            "visitorBizId": self.mobile,
            "userType": self.user_type,
        }
        resp = self.session.post(
            self._url("/talk/createSse"),
            json=payload,
            headers=self._auth_headers(),
            timeout=None,
            stream=True,
        )
        resp.raise_for_status()
        return resp

    def chat(self, msg: str) -> Dict[str, Any]:
        """发送聊天消息
        
        Args:
            msg: 聊天消息内容
            
        Returns:
            聊天响应数据
        """
        payload = {
            "botId": self.bot_id,
            "visitorBizId": self.mobile,
            "userType": self.user_type,
            "sessionId": "",
            "newDialog": True,
            "msg": msg,
        }
        files = {
            "paramJsonStr": (None, json.dumps(payload, ensure_ascii=False)),
        }
        resp = self.session.post(
            self._url("/talk/chat"),
            files=files,
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def debug_sse_once(self, msg: str, listen_seconds: float = 120.0) -> List[str]:
        """调试SSE流
        
        打开SSE流，发送消息，接收并打印SSE数据，同时写入到sse_debug.txt文件
        
        Args:
            msg: 要发送的消息
            listen_seconds: 监听时间（秒）
            
        Returns:
            接收到的SSE数据行列表
        """
        resp = self.open_sse_stream()
        lines: List[str] = []
        
        # 覆盖写入SSE调试日志文件
        root_dir = os.path.dirname(os.path.dirname(__file__))
        sse_debug_path = os.path.join(root_dir, "sse_debug.txt")
        
        def reader():
            """SSE流读取器
            
            读取SSE流数据，打印到控制台，写入文件，并处理异常
            """
            start = time.time()
            # 覆盖写入SSE调试日志文件
            with open(sse_debug_path, "w", encoding="utf-8") as f:
                f.write(f"SSE调试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))}\n")
                f.write(f"问题: {msg}\n\n")
            
            try:
                try:
                    for raw in resp.iter_lines(decode_unicode=False):
                        if raw:
                            try:
                                text = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                text = raw.decode("latin1", errors="replace")
                            try:
                                print("SSE:", text)
                            except UnicodeEncodeError:
                                # 处理终端编码问题
                                safe_text = text.encode('utf-8', errors='replace').decode('utf-8')
                                print("SSE:", safe_text)
                            lines.append(text)
                            
                            # 实时写入SSE数据到文件
                            with open(sse_debug_path, "a", encoding="utf-8") as f:
                                f.write(f"SSE: {text}\n")
                            
                            if text.strip() == "data:END_OF_STREAM":
                                break
                        if time.time() - start > listen_seconds:
                            break
                except ChunkedEncodingError as e:
                    logger.warning("SSE debug stream ended prematurely: %s", e)
                    with open(sse_debug_path, "a", encoding="utf-8") as f:
                        f.write(f"SSE流提前结束: {e}\n")
                except Exception:
                    logger.exception("Unexpected error in SSE debug reader")
                    with open(sse_debug_path, "a", encoding="utf-8") as f:
                        f.write("SSE调试读取器发生意外错误\n")
            finally:
                resp.close()
                # 写入结束信息
                with open(sse_debug_path, "a", encoding="utf-8") as f:
                    f.write(f"\nSSE调试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
                    f.write(f"总共收到行数: {len(lines)}\n")

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        time.sleep(1.0)
        self.chat(msg)
        t.join(timeout=listen_seconds + 5)
        return lines

    def chat_with_answer_with_status(
        self, msg: str, listen_seconds: float = 120.0, max_retries: int = 1
    ) -> tuple[str, str, str]:
        """获取带状态的答案
        
        打开SSE流，发送消息，从SSE流中提取答案、状态和引用
        
        Args:
            msg: 要发送的消息
            listen_seconds: 监听时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            (答案, 状态, 引用) 的元组
        """
        for attempt in range(max_retries + 1):
            replies: List[str] = []
            got_knowledge = False
            had_stream_error = False
            timed_out = False
            ref_titles: List[str] = []

            resp = self.open_sse_stream()

            def reader():
                """SSE流读取器
                
                读取SSE流数据，提取答案、状态和引用
                """
                nonlocal got_knowledge, had_stream_error, timed_out
                start = time.time()
                try:
                    try:
                        for raw in resp.iter_lines(decode_unicode=False):
                            if not raw:
                                continue
                            try:
                                text = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                text = raw.decode("latin1", errors="replace")
                            if not text.startswith("data:"):
                                continue
                            payload = text[len("data:") :].strip()
                            if not payload or payload == "HEARTBEAT_STREAM":
                                continue
                            if payload == "END_OF_STREAM":
                                got_knowledge = True
                                break
                            try:
                                obj = json.loads(payload)
                            except json.JSONDecodeError:
                                continue
                            reply = obj.get("reply")
                            if isinstance(reply, str):
                                replies.append(reply)
                            for key in (
                                "title",
                                "docTitle",
                                "documentTitle",
                                "knowledgeTitle",
                                "knowledgeName",
                                "docName",
                                "sourceTitle",
                                "fileName",
                                "question",
                            ):
                                value = obj.get(key)
                                if (
                                    isinstance(value, str)
                                    and value.strip()
                                    and len(value.strip()) <= 120
                                    and value.strip() not in ref_titles
                                ):
                                    ref_titles.append(value.strip())
                                    break
                            knowledge = obj.get("knowledgeList")
                            if knowledge is not None:
                                if isinstance(knowledge, list):
                                    for item in knowledge:
                                        if not isinstance(item, dict):
                                            continue
                                        title_value = None
                                        for key in (
                                            "title",
                                            "docTitle",
                                            "documentTitle",
                                            "name",
                                            "question",
                                        ):
                                            value = item.get(key)
                                            if isinstance(value, str) and value.strip():
                                                title_value = value.strip()
                                                break
                                        if (
                                            title_value
                                            and title_value not in ref_titles
                                        ):
                                            ref_titles.append(title_value)
                                got_knowledge = True
                                break
                            if time.time() - start > listen_seconds:
                                timed_out = True
                                break
                    except ChunkedEncodingError as e:
                        had_stream_error = True
                        logger.warning("SSE chat stream ended prematurely: %s", e)
                    except Exception:
                        had_stream_error = True
                        logger.exception("Unexpected error in SSE chat reader")
                finally:
                    resp.close()

            t = threading.Thread(target=reader, daemon=True)
            t.start()
            time.sleep(1.0)
            try:
                self.chat(msg)
            except Exception:
                had_stream_error = True
                logger.exception("Chat request failed for message: %s", msg)
            t.join(timeout=listen_seconds + 5)

            answer = "".join(replies)
            refs = " | ".join(ref_titles)
            if got_knowledge and not had_stream_error and not timed_out:
                return answer, "ok", refs

            logger.warning(
                "Chat attempt %s incomplete for message '%s' "
                "(got_knowledge=%s, stream_error=%s, timed_out=%s)",
                attempt + 1,
                msg,
                got_knowledge,
                had_stream_error,
                timed_out,
            )
            if attempt == max_retries:
                return answer, "partial", refs

    def chat_with_answer(self, msg: str, listen_seconds: float = 120.0) -> str:
        """获取答案
        
        调用 `chat_with_answer_with_status` 获取答案，只返回答案部分
        
        Args:
            msg: 要发送的消息
            listen_seconds: 监听时间（秒）
            
        Returns:
            答案字符串
        """
        answer, _status, _refs = self.chat_with_answer_with_status(
            msg, listen_seconds=listen_seconds, max_retries=1
        )
        return answer

    def process_question_csv(self, input_path: str, output_path: str) -> None:
        """处理问题CSV文件
        
        读取输入CSV文件中的问题，获取答案，并写入输出CSV文件
        
        Args:
            input_path: 输入CSV文件路径
            output_path: 输出CSV文件路径
        """
        import csv

        existing_rows = 0
        header = None
        if os.path.exists(output_path):
            with open(output_path, mode="r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for _ in reader:
                    existing_rows += 1

        if header != ["question", "answer", "status", "refs"]:
            if header is not None:
                logger.info(
                    "Output CSV header changed or legacy format detected, restarting file: %s",
                    output_path,
                )
            existing_rows = 0

        logger.info("Existing answer rows in %s: %s", output_path, existing_rows)
        self.ensure_login()
        mode = "a" if existing_rows > 0 else "w"
        with open(input_path, mode="r", encoding="utf-8") as infile, open(
            output_path, mode=mode, newline="", encoding="utf-8-sig"
        ) as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            if existing_rows == 0:
                writer.writerow(["question", "answer", "status", "refs"])
            header = next(reader, None)
            for idx, row in enumerate(reader):
                if idx < existing_rows:
                    logger.info("Skipping already processed row index %s", idx)
                    continue
                if not row:
                    logger.info(
                        "Row index %s empty, writing empty question and answer with status",
                        idx,
                    )
                    writer.writerow(["", "", "empty_row", ""])
                    continue
                raw_question = row[0]
                question = raw_question.strip()
                if not question:
                    logger.info(
                        "Row index %s empty question, writing empty answer with status",
                        idx,
                    )
                    writer.writerow([raw_question, "", "empty_question", ""])
                    continue
                logger.info("Processing row index %s question: %s", idx, question)
                answer, status, refs = self.chat_with_answer_with_status(
                    question, listen_seconds=120.0, max_retries=1
                )
                writer.writerow([question, answer, status, refs])

    def fill_model_answers_csv(self, input_path: str, output_path: str) -> None:
        """填充模型答案CSV文件
        
        读取输入CSV文件中的问题，填充模型答案，并写入输出CSV文件
        
        Args:
            input_path: 输入CSV文件路径
            output_path: 输出CSV文件路径
            
        Raises:
            RuntimeError: CSV文件缺少“问题”或“模型答案”列
        """
        import csv

        logger.info("Filling model answers from %s to %s", input_path, output_path)
        self.ensure_login()
        with open(input_path, mode="r", encoding="utf-8") as infile, open(
            output_path, mode="w", newline="", encoding="utf-8-sig"
        ) as outfile:
            reader = csv.DictReader(infile)
            raw_fieldnames = reader.fieldnames or []
            if "问题" not in raw_fieldnames or "模型答案" not in raw_fieldnames:
                raise RuntimeError("CSV 必须包含“问题”和“模型答案”两列")
            fieldnames = list(raw_fieldnames)
            if "refs" not in fieldnames:
                fieldnames.append("refs")
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            for idx, row in enumerate(reader):
                question = (row.get("问题") or "").strip()
                model_answer = (row.get("模型答案") or "").strip()
                if not question:
                    logger.info("Row %s has empty question, skipping", idx + 2)
                    if "refs" in fieldnames and "refs" not in row:
                        row["refs"] = ""
                    writer.writerow(row)
                    continue
                if model_answer:
                    logger.info("Row %s already has model answer, skipping", idx + 2)
                    if "refs" in fieldnames and "refs" not in row:
                        row["refs"] = ""
                    writer.writerow(row)
                    continue
                logger.info("Asking question at row %s: %s", idx + 2, question)
                answer, status, refs = self.chat_with_answer_with_status(
                    question, listen_seconds=120.0, max_retries=1
                )
                row["模型答案"] = answer
                row["refs"] = refs
                writer.writerow(row)


if __name__ == "__main__":
    """主函数入口
    
    处理命令行参数，执行相应的功能：
    1. 调试SSE：`python src/api_client.py debug_sse [问题内容]`
    2. 填充问答：`python src/api_client.py fill_qa [输入CSV路径] [输出CSV路径] [手机号]`
    """
    root_dir = os.path.dirname(os.path.dirname(__file__))
    setup_logging()
    mobile_arg = None
    if len(sys.argv) > 1 and sys.argv[1] == "fill_qa" and len(sys.argv) > 4:
        mobile_arg = sys.argv[4]
    client = TalkApiClient(mobile=mobile_arg)
    if len(sys.argv) > 1 and sys.argv[1] == "debug_sse":
        client.ensure_login()
        if len(sys.argv) > 2:
            question = " ".join(sys.argv[2:])
        else:
            question = "重疾类理赔客户需要带哪些材料？"
        logger.info("Starting SSE debug for question: %s", question)
        lines = client.debug_sse_once(question, listen_seconds=120.0)
        logger.info("SSE debug finished, total lines: %s", len(lines))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "fill_qa":
        if len(sys.argv) > 2:
            input_csv = sys.argv[2]
        else:
            input_csv = os.path.join(root_dir, "data", "merged_testsets.csv")
        if len(sys.argv) > 3:
            output_csv = sys.argv[3]
        else:
            base_dir = os.path.dirname(input_csv)
            base_name = os.path.basename(input_csv)
            name, ext = os.path.splitext(base_name)
            output_csv = os.path.join(base_dir, f"{name}_filled{ext}")
        try:
            import csv

            with open(input_csv, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
        except Exception:
            fieldnames = []
        if "问题" in fieldnames and "模型答案" in fieldnames:
            logger.info("Detected merged_testsets format with 问题+模型答案, using fill_model_answers_csv")
            logger.info("Model answer filling started")
            client.fill_model_answers_csv(input_csv, output_csv)
            logger.info("Model answer filling finished, output: %s", output_csv)
        elif "questions" in fieldnames and "模型答案" not in fieldnames:
            logger.info("Detected questions.csv style format, using process_question_csv")
            logger.info("Batch question processing started")
            client.process_question_csv(input_csv, output_csv)
            logger.info("Batch question processing finished, output: %s", output_csv)
        else:
            raise RuntimeError("无法识别问题集格式：需要包含“问题”和“模型答案”字段，或只包含“questions”字段")
        sys.exit(0)
    input_csv = os.path.join(root_dir, "data", "questions.csv")
    output_csv = os.path.join(root_dir, "data", "answers.csv")
    logger.info("Batch question processing started")
    client.process_question_csv(input_csv, output_csv)
    logger.info("Batch question processing finished")
