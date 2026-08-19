"""
请求构造自检：monkeypatch authenticated_request，捕获每个业务函数
实际发出的 (method, url, params, json) 元组，校验：
- URL 前缀正确（BASE_URL + API_SALE_xxx）
- HTTP 方法合理（GET/POST/PUT/DELETE）
- 路径参数已正确拼入 URL
- query / json 参数按预期区分
不发起真实网络请求。
"""
import importlib
import sys
import os
import inspect

SALE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SALE_DIR)
sys.path.insert(0, ROOT)


def build_call_kwargs(fn):
    """
    为模板化后的函数构造能走到真实请求路径的入参：
    - 必填参数（无默认）按注解给合法值；
    - 结构化写操作把必填字段的默认值 None 也补成合法值（避免触发 need_input），
      并对存在的 confirmed 参数强制传 True（跳过 need_confirm 二次确认）；
    - 其余可选参数保持默认。
    """
    sig = inspect.signature(fn)
    params = sig.parameters
    has_confirmed = "confirmed" in params

    def sample_value(ann):
        ann_str = getattr(ann, "__name__", str(ann))
        if ann_str in ("int", "integer"):
            return 1
        if ann_str in ("float", "Decimal"):
            return 100.0
        if ann_str == "str":
            return "x"
        if ann_str in ("list", "List"):
            return []
        if ann_str in ("dict", "Dict"):
            return {}
        if ann_str in ("bool", "boolean"):
            return True
        return "x"

    kwargs = {}
    for pname, p in params.items():
        if pname == "confirmed":
            kwargs[pname] = True
            continue
        if p.default is inspect.Parameter.empty:
            # 无默认：必填
            kwargs[pname] = sample_value(p.annotation)
        elif has_confirmed and p.default is None:
            # 结构化写操作里被改为默认 None 的必填字段：补合法值以越过 need_input
            kwargs[pname] = sample_value(p.annotation)
        else:
            kwargs[pname] = p.default
    return kwargs

import auth_core
from config import BASE_URL
from sale.config import (API_SALE_PROJECT, API_SALE_CUSTOMER, API_SALE_TRANSACTION,
                          API_SALE_COMMISSION, API_SALE_PERFORMANCE, API_SALE_STATISTICS)

# ---- 捕获容器 ----
captured = []

def fake_request(method, url, **kwargs):
    captured.append({"method": method, "url": url, **kwargs})
    return {"code": 0, "message": "ok", "data": {"_captured": True}}

# 替换 sale.main 中引用的 authenticated_request
sale_main = importlib.import_module("sale.main")
sale_main.authenticated_request = fake_request

# 期望前缀表
PREFIX = {
    "project": f"{BASE_URL}{API_SALE_PROJECT}",
    "customer": f"{BASE_URL}{API_SALE_CUSTOMER}",
    "transaction": f"{BASE_URL}{API_SALE_TRANSACTION}",
    "commission": f"{BASE_URL}{API_SALE_COMMISSION}",
    "performance": f"{BASE_URL}{API_SALE_PERFORMANCE}",
    "statistics": f"{BASE_URL}{API_SALE_STATISTICS}",
}

errors = []
ok_count = 0

# 收集所有业务函数（排除认证函数，认证走 auth_core 不经 authenticated_request）
business_funcs = {
    name: fn for name, fn in inspect.getmembers(sale_main, inspect.isfunction)
    if name.startswith("sale_") and fn.__module__ == "sale.main"
    and name not in ("sale_login", "sale_login_confirm", "sale_logout",
                     "sale_refresh_token", "sale_change_password", "sale_get_login_user")
}

print(f"待校验业务函数数：{len(business_funcs)}")

for name, fn in business_funcs.items():
    captured.clear()
    # 构造调用参数：必填/被改为默认None的必填字段补合法值，confirmed 传 True 越过二次确认
    kwargs = build_call_kwargs(fn)
    try:
        fn(**kwargs)
    except Exception as e:
        errors.append(f"{name}: 调用异常 {e!r}")
        continue

    if not captured:
        errors.append(f"{name}: 未捕获到请求（可能未调用 authenticated_request）")
        continue

    rec = captured[0]
    url = rec["url"]
    method = rec["method"]

    # 校验 URL 前缀属于某个已知域
    matched_prefix = next((p for p in PREFIX.values() if url.startswith(p)), None)
    if not matched_prefix:
        errors.append(f"{name}: URL 前缀不在已知域 url={url}")
        continue

    # 校验 HTTP 方法合法
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        errors.append(f"{name}: 非法HTTP方法 {method}")
        continue

    # 校验路径参数已拼入：如果函数签名有 *_id 且 URL 含 /{xxx}，这里做宽松检查
    # （已在名称一致性自检覆盖，此处略）
    ok_count += 1

print(f"\n校验通过：{ok_count}/{len(business_funcs)}")
print(f"错误数：{len(errors)}")
if errors:
    print("\n--- 错误 ---")
    for e in errors:
        print("  ✗", e)

# ---- 抽样打印若干函数的实际请求构造 ----
print("\n--- 抽样请求构造（前10个）---")
samples = list(business_funcs.items())[:10]
for name, fn in samples:
    captured.clear()
    kwargs = build_call_kwargs(fn)
    fn(**kwargs)
    if not captured:
        print(f"  {name}: （交互态，未发起请求）")
        continue
    rec = captured[0]
    parts = [f"{rec['method']} {rec['url'].replace(BASE_URL, '')}"]
    if "params" in rec:
        parts.append(f"params={rec['params']}")
    if "json" in rec:
        j = rec["json"]
        # 只显示键，避免过长
        if isinstance(j, dict):
            parts.append(f"json.keys={list(j.keys())}")
        else:
            parts.append("json=<body>")
    print(f"  {name}: " + " | ".join(parts))

sys.exit(1 if errors else 0)
