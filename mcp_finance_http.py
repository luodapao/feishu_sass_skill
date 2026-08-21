"""
mcp_finance_http.py —— Finance 域 MCP Server 入口（HTTP SSE / Streamable HTTP）。

运行：
    pip install -r requirements.txt
    python mcp_finance_http.py --port 8083

飞书 AI Agent MCP 配置：
    URL: http://云服务器IP:8083    # Streamable HTTP（推荐）
"""
import os
import sys

_PROJECT_ROOT = os.environ.get("SAAS_SKILL_ROOT") or os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp_adapter_http import run_http_server

SKILL_JSON = os.path.join(_PROJECT_ROOT, "finance", "skill.json")
SERVER_NAME = "feishu-saas-finance"
DEFAULT_PORT = 8083

if __name__ == "__main__":
    run_http_server(
        module_name="finance.main",
        skill_json_path=SKILL_JSON,
        server_name=SERVER_NAME,
        default_port=DEFAULT_PORT,
    )
