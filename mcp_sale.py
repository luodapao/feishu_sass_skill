"""
mcp_sale.py —— Sale 域 MCP server 入口（stdio）。

把 sale/skill.json 的工具暴露为 MCP tools：飞书 AI Agent 调用 tool ->
Python 执行 sale.main 对应函数 -> 返回 JSON（含 card 字段）-> AI 提取 card 发卡片。

运行（需先 pip install -r requirements.txt）：
    python mcp_sale.py
"""
import os
import sys

# 项目根：优先环境变量 SAAS_SKILL_ROOT（aily 等环境可指定代码实际下载路径），
# 否则回退到本脚本所在目录。
_PROJECT_ROOT = os.environ.get("SAAS_SKILL_ROOT") or os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp_adapter import build_server, run

SKILL_JSON = os.path.join(_PROJECT_ROOT, "sale", "skill.json")
SERVER_NAME = "feishu-saas-sale"

server = build_server("sale.main", SKILL_JSON, SERVER_NAME)

if __name__ == "__main__":
    run(server)
