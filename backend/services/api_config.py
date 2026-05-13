BASE_URL = "https://dwai.soochowlife.net:3000"
CHANNEL = "ZK"
USER_TYPE = "NQ"

# API路径配置
API_PATHS = {
    "default": {
        "name": "默认路径",
        "sse_path": "/talk/createSse",
        "chat_path": "/talk/chat",
    },
    "dwtsbuddy": {
        "name": "dwtsbuddy路径",
        "sse_path": "/dwtsbuddy/chat/sse",
        "chat_path": "/dwtsbuddy/chat",
    }
}

# 默认使用的路径类型
DEFAULT_API_TYPE = "dwtsbuddy"

