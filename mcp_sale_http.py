"""
mcp_sale_http.py —— Sale 域 MCP Server 入口（HTTP SSE / Streamable HTTP）。

运行：
    pip install -r requirements.txt
    python mcp_sale_http.py --port 8082

飞书 AI Agent MCP 配置：
    URL: http://云服务器IP:8082    # Streamable HTTP（推荐）
"""
import os
import sys

_PROJECT_ROOT = os.environ.get("SAAS_SKILL_ROOT") or os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp_adapter_http import run_http_server

SKILL_JSON = os.path.join(_PROJECT_ROOT, "sale", "skill.json")
SERVER_NAME = "feishu-saas-sale"
DEFAULT_PORT = 8082

if __name__ == "__main__":
    run_http_server(
        module_name="sale.main",
        skill_json_path=SKILL_JSON,
        server_name=SERVER_NAME,
        default_port=DEFAULT_PORT,
    )
