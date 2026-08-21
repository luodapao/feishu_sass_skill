"""
mcp_adapter.py —— 把 skill.json 定义的工具自动暴露为 MCP tools（共享适配器）。

设计要点
- 函数不动：只在 main.py 外层包一层 MCP 适配，业务逻辑完全复用现有代码与卡片逻辑。
- schema 来自 skill.json：每条工具的入参 schema 直接取自 skill.json 的 parameters
  （显式 type/description），避免 pydantic 对 `list=None` / `dict=None` 这类签名的兼容问题。
- 动态派发：list_tools / call_tool 按工具名 getattr 到对应 main.py 函数并调用。
- 返回值透传：函数返回的 dict（含 code/message/action/data/card）序列化为 JSON 文本，
  飞书 AI Agent 调用 tool 后解析 JSON、提取 card 字段发卡片。

用法（见 mcp_admin.py / mcp_sale.py / mcp_finance.py）：
    from mcp_adapter import build_server, run
    server = build_server("admin.main", "/abs/admin/skill.json", "feishu-saas-admin")
    run(server)
"""
import os
import sys
import json
import importlib
import traceback

from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server


# skill.json 中的 type 字段 -> JSON Schema type
_TYPE_MAP = {
    "string": "string", "str": "string",
    "integer": "integer", "int": "integer",
    "boolean": "boolean", "bool": "boolean",
    "number": "number", "float": "number",
    "array": "array", "list": "array",
    "object": "object", "dict": "object",
}


def _build_input_schema(parameters):
    """把 skill.json 的 parameters 列表转为 JSON Schema（inputSchema）。"""
    properties = {}
    required = []
    for p in parameters or []:
        name = p.get("name")
        if not name:
            continue
        ptype = _TYPE_MAP.get(str(p.get("type", "string")).lower(), "string")
        properties[name] = {
            "type": ptype,
            "description": p.get("description", ""),
        }
        if p.get("required"):
            required.append(name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _ensure_project_root(skill_json_path):
    """把项目根（skill.json 上一级目录）加入 sys.path，保证 auth_core / <domain>.config 可导入。"""
    domain_dir = os.path.dirname(os.path.abspath(skill_json_path))
    project_root = os.path.dirname(domain_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root


def build_server(module_name, skill_json_path, server_name):
    """构建并返回配置好的 MCP Server（stdio）。

    :param module_name: 业务模块点路径，如 "admin.main" / "sale.main" / "finance.main"
    :param skill_json_path: skill.json 绝对路径
    :param server_name: MCP server 名称（用于客户端展示）
    :return: mcp.server.Server 实例
    """
    _ensure_project_root(skill_json_path)
    mod = importlib.import_module(module_name)

    with open(skill_json_path, encoding="utf-8") as f:
        skill = json.load(f)

    tools_spec = skill.get("tools", [])
    spec_map = {t["tool_name"]: t for t in tools_spec}

    server = Server(server_name)

    @server.list_tools()
    async def list_tools():
        out = []
        for t in tools_spec:
            out.append(types.Tool(
                name=t["tool_name"],
                description=t.get("description", ""),
                inputSchema=_build_input_schema(t.get("parameters", [])),
            ))
        return out

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None):
        spec = spec_map.get(name)
        fn = getattr(mod, name, None)

        # 未知工具或私有函数：拒绝派发
        if fn is None or not callable(fn) or name.startswith("_"):
            result = {
                "code": -1,
                "message": f"未知或不可调用的工具: {name}",
                "action": "error",
                "tool": name,
            }
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        # 仅保留 skill.json 声明的参数，过滤 AI 可能传入的多余字段
        kwargs = dict(arguments or {})
        declared = {p["name"] for p in (spec.get("parameters") if spec else []) or []}
        if declared:
            kwargs = {k: v for k, v in kwargs.items() if k in declared}

        # 无状态认证：把 access_token / refresh_token 从业务参数中剥离，
        # 注入 auth_core 请求级上下文，业务函数本身无需感知这两个参数。
        # 调用结束立即清理，避免跨请求串号。
        from auth_core import set_auth_context, clear_auth_context
        access_token = kwargs.pop("access_token", None)
        refresh_token = kwargs.pop("refresh_token", None)
        set_auth_context(access_token, refresh_token)

        try:
            result = fn(**kwargs)
        except Exception as e:
            result = {
                "code": -1,
                "_mcp_error": True,
                "message": f"执行异常: {e}",
                "traceback": traceback.format_exc(),
                "action": "error",
                "tool": name,
            }
        finally:
            clear_auth_context()

        # 统一序列化为 JSON 文本（飞书 AI Agent 解析后取 card 字段发卡片）
        if isinstance(result, (dict, list)):
            text = json.dumps(result, ensure_ascii=False)
            # 标注错误与正常：code != 0 且 != 200 视为异常，便于 AI 优先处理
            if isinstance(result, dict) and result.get("code") not in (0, 200):
                result.setdefault("_mcp_error", True)
                text = json.dumps(result, ensure_ascii=False)
        else:
            text = str(result)
        return [types.TextContent(type="text", text=text)]

    return server


def run(server):
    """以 stdio 模式运行 MCP server（阻塞，供入口脚本调用）。"""
    import asyncio

    async def _main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_main)
