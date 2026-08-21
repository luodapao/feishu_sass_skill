"""
mcp_adapter_http.py —— 把 skill.json 工具暴露为 MCP Server（HTTP SSE / Streamable HTTP）。

共享给 mcp_admin_http.py / mcp_sale_http.py / mcp_finance_http.py 调用。

设计要点：
- 使用 FastMCP（mcp 1.x 官方推荐高层 API）
- 通过 FastMCP.add_tool 动态注册 skill.json 中声明的每个工具
- 用 FastMCP.streamable_http_app() 返回 Starlette ASGI app
- 业务逻辑完全复用现有 main.py 函数（auth_core 上下文认证、card 字段等不变）

飞书 AI Agent 接入：
- 协议：Streamable HTTP（POST /mcp + 可选 GET /mcp SSE 流）
- URL：http://云服务器IP:8081/mcp     （注意结尾的 /mcp）
- 工具列表自动从 skill.json 加载

使用：
    python mcp_admin_http.py --port 8081
    MCP_PORT=8081 python mcp_admin_http.py
"""
import os
import sys
import json
import argparse
import importlib
import traceback
from typing import Optional, Any

from mcp.server.fastmcp import FastMCP


# skill.json 中的 type 字段 -> JSON Schema type
_TYPE_MAP = {
    "string": "string", "str": "string",
    "integer": "integer", "int": "integer",
    "boolean": "boolean", "bool": "boolean",
    "number": "number", "float": "number",
    "array": "array", "list": "array",
    "object": "object", "dict": "object",
}


def _ensure_project_root(skill_json_path):
    """把项目根（skill.json 上一级目录）加入 sys.path，保证 auth_core / <domain>.config 可导入。"""
    domain_dir = os.path.dirname(os.path.abspath(skill_json_path))
    project_root = os.path.dirname(domain_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root


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


def _make_tool_wrapper(fn, spec):
    """
    为 skill.json 声明的工具生成一个 async 包装函数。
    - 仅保留 skill.json 声明的参数，过滤 AI 传入的多余字段
    - 剥离 access_token / refresh_token 注入 auth_core 请求级上下文
    - 调用结束立即清理，避免跨请求串号
    - 返回 JSON 文本（飞书 AI Agent 解析后取 card 字段发卡片）
    """
    declared = {p["name"] for p in (spec.get("parameters") if spec else []) or []}

    async def _wrapper(**kwargs):
        # 过滤未声明的参数
        if declared:
            kwargs = {k: v for k, v in kwargs.items() if k in declared}

        # 剥离认证参数到请求级上下文
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
                "tool": spec.get("tool_name"),
            }
        finally:
            clear_auth_context()

        # 统一序列化为 JSON 文本
        if isinstance(result, (dict, list)):
            if isinstance(result, dict) and result.get("code") not in (0, 200):
                result.setdefault("_mcp_error", True)
            return json.dumps(result, ensure_ascii=False)
        return str(result)

    # 设置函数元信息，FastMCP 会用这些生成 tool schema
    _wrapper.__name__ = spec.get("tool_name", "unknown_tool")
    _wrapper.__doc__ = spec.get("description", "")
    return _wrapper


def build_fastmcp_server(module_name, skill_json_path, server_name):
    """
    构建 FastMCP Server 并注册 skill.json 中的所有工具。

    :param module_name: 业务模块点路径，如 "admin.main" / "sale.main" / "finance.main"
    :param skill_json_path: skill.json 绝对路径
    :param server_name: MCP server 名称（用于客户端展示）
    :return: FastMCP 实例（已注册全部工具）
    """
    _ensure_project_root(skill_json_path)
    mod = importlib.import_module(module_name)

    with open(skill_json_path, encoding="utf-8") as f:
        skill = json.load(f)

    tools_spec = skill.get("tools", [])

    # 创建 FastMCP 实例
    mcp = FastMCP(
        name=server_name,
        instructions=skill.get("description", ""),
    )

    # 动态注册每个工具
    for spec in tools_spec:
        tool_name = spec.get("tool_name")
        if not tool_name:
            continue
        fn = getattr(mod, tool_name, None)
        if fn is None or not callable(fn) or tool_name.startswith("_"):
            print(f"[WARN] 跳过未实现或不可调用的工具: {tool_name}")
            continue

        wrapper = _make_tool_wrapper(fn, spec)
        mcp.add_tool(
            fn=wrapper,
            name=tool_name,
            description=spec.get("description", ""),
        )
        print(f"[OK] 注册工具: {tool_name}")

    return mcp


def run_http_server(
    module_name: str,
    skill_json_path: str,
    server_name: str,
    default_port: int = 8080,
    host: str = "0.0.0.0",
    extra_args: Optional[list] = None,
):
    """
    构建并启动 HTTP SSE / Streamable HTTP 的 MCP Server。

    :param module_name:    业务模块点路径，如 "admin.main"
    :param skill_json_path: skill.json 绝对路径
    :param server_name:    MCP server 名称（客户端展示用）
    :param default_port:   默认端口，可被 --port / MCP_PORT 覆盖
    :param host:           监听地址
    :param extra_args:     额外命令行参数（测试用）
    """
    # 端口解析优先级：CLI --port > 环境变量 MCP_PORT > default_port
    parser = argparse.ArgumentParser(description=f"MCP HTTP Server · {server_name}")
    parser.add_argument(
        "-p", "--port", type=int,
        default=int(os.environ.get("MCP_PORT", default_port)),
        help=f"监听端口（默认 {default_port}，环境变量 MCP_PORT 可覆盖）"
    )
    parser.add_argument(
        "--host", type=str, default=host,
        help=f"监听地址（默认 {host}）"
    )
    args = parser.parse_args(extra_args)

    # 构建 FastMCP Server
    mcp = build_fastmcp_server(module_name, skill_json_path, server_name)

    # 获取 Starlette ASGI app（Streamable HTTP 模式）
    app = mcp.streamable_http_app()

    # 用 uvicorn 启动
    try:
        import uvicorn
    except ImportError:
        print(
            "[ERROR] 缺少 uvicorn。请先：pip install -r requirements.txt\n"
            "        或手动：pip install 'uvicorn[standard]>=0.23.2'"
        )
        sys.exit(1)

    print(f"\n[MCP] Starting HTTP Server: {server_name}")
    print(f"[MCP] Listening on {args.host}:{args.port}")
    print(f"[MCP] Endpoint: http://{args.host}:{args.port}/mcp")
    print(f"[MCP] Backend: {module_name}  |  skill.json: {skill_json_path}")
    print(f"[MCP] 飞书 AI Agent 配置 URL: http://<云服务器IP>:{args.port}/mcp\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
