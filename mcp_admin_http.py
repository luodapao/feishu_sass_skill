"""
mcp_admin_http.py —— Admin 域 MCP Server 入口（HTTP SSE / Streamable HTTP）。

房产 SaaS 后端为内网 192.168.0.79:8000，云服务器同内网可直接访问。

运行：
    pip install -r requirements.txt
    python mcp_admin_http.py --port 8081

飞书 AI Agent MCP 配置（HTTP SSE）：
    URL: http://云服务器IP:8081/sse     # 纯 SSE 模式
    URL: http://云服务器IP:8081          # Streamable HTTP（POST /messages + GET /sse，推荐）
"""
import os
import sys

_PROJECT_ROOT = os.environ.get("SAAS_SKILL_ROOT") or os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp_adapter_http import run_http_server

SKILL_JSON = os.path.join(_PROJECT_ROOT, "admin", "skill.json")
SERVER_NAME = "feishu-saas-admin"
DEFAULT_PORT = 8081

if __name__ == "__main__":
    run_http_server(
        module_name="admin.main",
        skill_json_path=SKILL_JSON,
        server_name=SERVER_NAME,
        default_port=DEFAULT_PORT,
    )
