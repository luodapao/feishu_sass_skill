"""
mcp_adapter_http.py —— 把 skill.json 工具暴露为 MCP Server（HTTP SSE / Streamable HTTP）。

共享给 mcp_admin_http.py / mcp_sale_http.py / mcp_finance_http.py 调用。

设计要点：
- 业务逻辑复用 mcp_adapter.build_server 构建的 Server 对象（list_tools / call_tool 完全不变）
- 运行模式优先 mcp 库官方 Streamable HTTP（POST /messages + GET /sse，飞书 AI Agent 默认协议）；
  若当前 mcp 版本不支持，回退到纯 SSE 模式
- 通过 --port / -p 或环境变量 MCP_PORT 指定监听端口，默认 8080；host 默认 0.0.0.0

使用：
    python mcp_admin_http.py --port 8081
    # 或
    MCP_PORT=8081 python mcp_admin_http.py
"""
import os
import sys
import argparse
from typing import Optional

# MCP Server 对象构建复用 stdio 适配器里的 build_server
from mcp_adapter import build_server, _ensure_project_root  # noqa: F401


def _build_asgi_app(server):
    """
    用 mcp 官方提供的 HTTP 封装把 Server 对象包成 ASGI app。
    按优先级尝试：Streamable HTTP（推荐）→ SSE → 抛错。
    """
    # 1. Streamable HTTP：飞书 AI Agent 的 MCP HTTP 接入首选协议
    try:
        from mcp.server.streamable_http import streamable_http_server
        return streamable_http_server(server)
    except Exception:
        pass
    # 2. SSE：部分旧客户端支持
    try:
        from mcp.server.sse import sse_server
        return sse_server(server)
    except Exception:
        pass
    raise RuntimeError(
        "当前安装的 mcp 库不支持 Streamable HTTP 或 SSE 模式。\n"
        "请升级：pip install -U 'mcp>=1.2.0' 或指定：pip install 'mcp[http]>=1.2.0'"
    )


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

    # 构建业务 Server
    server = build_server(module_name, skill_json_path, server_name)
    # 包装为 ASGI app
    app = _build_asgi_app(server)

    # 用 uvicorn 启动
    try:
        import uvicorn
    except ImportError:
        print(
            "[ERROR] 缺少 uvicorn。请先：pip install -r requirements.txt\n"
            "        或手动：pip install 'uvicorn[standard]>=0.23.2'"
        )
        sys.exit(1)

    print(f"[MCP] Starting HTTP Server: {server_name}")
    print(f"[MCP] Listening on {args.host}:{args.port}")
    print(f"[MCP] Backend: {module_name}  |  skill.json: {skill_json_path}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
