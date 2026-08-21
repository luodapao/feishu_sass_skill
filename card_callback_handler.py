"""
card_callback_handler.py —— 飞书卡片回调事件处理器。

配合 aily-cli 使用，接收卡片按钮点击 / 表单提交回调（card.action.trigger），
解析 action 与表单字段，派发到对应域的 main.py 函数，输出结果 JSON（含新 card）。

用法：
    # 方式1：aily-cli handler 模式（事件 JSON 从 stdin 传入）
    aily-cli auto --trigger-type event --event card_action \\
        --handler "python card_callback_handler.py"

    # 方式2：手动测试（事件 JSON 文件路径作为参数）
    python card_callback_handler.py event.json

    # 方式3：手动测试（事件 JSON 从 stdin 传入）
    echo '{"event_type":"card.action.trigger","action":{"value":{"action":"tenant_login"},"form_value":{"account":"u1","password":"p1"}}}' | python card_callback_handler.py

输出：结果 JSON（含 code/message/action/card）写到 stdout，供 aily-cli / AI 后续处理。
"""
import os
import sys
import json
import importlib
import traceback

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# action 名前缀 -> 业务域模块
_DOMAIN_MAP = {
    "tenant_": "admin.main",
    "sale_": "sale.main",
    "finance_": "finance.main",
}


def _resolve_module(action_name: str):
    """根据 action 名前缀定位业务域模块。"""
    for prefix, mod_name in _DOMAIN_MAP.items():
        if action_name.startswith(prefix):
            try:
                return importlib.import_module(mod_name)
            except Exception:
                return None
    return None


def _extract_action_and_args(payload: dict):
    """
    从飞书卡片回调 payload 中解析 action 名与参数。
    兼容多种 payload 结构（button callback / form submit）。
    """
    action_obj = payload.get("action") or payload.get("event", {}).get("action") or {}
    value = action_obj.get("value") or {}
    form_value = action_obj.get("form_value") or action_obj.get("formValue") or {}

    # action 名：优先 value.action，其次 action_obj.action
    action_name = value.get("action") or action_obj.get("action") or payload.get("action_name")
    if not action_name:
        return None, {}

    # 参数：合并 form_value（表单字段）+ value 里的额外参数（如 confirmed）
    args = {}
    args.update(form_value)
    for k, v in value.items():
        if k == "action":
            continue
        args.setdefault(k, v)
    return action_name, args


def handle_event(payload: dict) -> dict:
    """
    处理单个卡片回调事件，返回结果 dict（含 code/message/action/card）。
    """
    action_name, args = _extract_action_and_args(payload)
    if not action_name:
        return {
            "code": -1,
            "_mcp_error": True,
            "message": "无法从回调事件解析 action 名",
            "action": "error",
            "raw": payload,
        }

    # 跳过取消类回调（如 *_cancel），直接返回取消提示
    if action_name.endswith("_cancel"):
        return {
            "code": 200,
            "message": "用户已取消操作",
            "action": "cancelled",
        }

    mod = _resolve_module(action_name)
    if mod is None:
        return {
            "code": -1,
            "_mcp_error": True,
            "message": f"无法定位 action {action_name} 对应的业务模块",
            "action": "error",
        }

    fn = getattr(mod, action_name, None)
    if fn is None or not callable(fn) or action_name.startswith("_"):
        return {
            "code": -1,
            "_mcp_error": True,
            "message": f"未知或不可调用的 action: {action_name}",
            "action": "error",
        }

    # 类型转换：把 "true"/"false" 字符串转 bool（卡片表单值可能以字符串传回）
    for k, v in list(args.items()):
        if isinstance(v, str):
            low = v.lower()
            if low == "true":
                args[k] = True
            elif low == "false":
                args[k] = False

    try:
        result = fn(**args)
    except Exception as e:
        return {
            "code": -1,
            "_mcp_error": True,
            "message": f"执行异常: {e}",
            "traceback": traceback.format_exc(),
            "action": "error",
            "tool": action_name,
        }

    if isinstance(result, dict):
        # 标注错误与正常：code != 0 且 != 200 视为异常
        if result.get("code") not in (0, 200):
            result.setdefault("_mcp_error", True)
        return result
    return {"code": 200, "message": str(result), "action": "done"}


def _read_event():
    """从 argv[1]（文件路径）或 stdin 读取事件 JSON。"""
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], encoding="utf-8") as f:
            return json.load(f)
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


if __name__ == "__main__":
    try:
        event = _read_event()
        result = handle_event(event)
    except Exception as e:
        result = {
            "code": -1,
            "_mcp_error": True,
            "message": f"事件解析异常: {e}",
            "traceback": traceback.format_exc(),
            "action": "error",
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.write("\n")
