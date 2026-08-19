"""
sale 技能自检脚本：
1. 导入 sale/main.py，确认 104 个函数可正常加载
2. 对照 skill.json 的 tool_name 与 main.py 函数名一致性
3. 对照每个工具的参数名与函数签名的参数名一致性（顺序、是否齐全）
4. 检查 admin 技能未被破坏（导入根 main.py）
"""
import json
import inspect
import importlib
import sys
import os

SALE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SALE_DIR)  # 项目根 = sale 的父目录
sys.path.insert(0, ROOT)

errors = []
warnings = []

# ---- 1. 导入 sale.main ----
try:
    sale_main = importlib.import_module("sale.main")
except Exception as e:
    errors.append(f"[FATAL] 无法导入 sale.main: {e!r}")
    print("\n".join(errors))
    sys.exit(1)

# 收集 sale.main 中所有 sale_ 开头的公开函数
sale_funcs = {
    name: fn for name, fn in inspect.getmembers(sale_main, inspect.isfunction)
    if name.startswith("sale_") and fn.__module__ == "sale.main"
}
print(f"[1] sale.main 可导入，函数数：{len(sale_funcs)}")

# ---- 2. 加载 skill.json ----
with open(os.path.join(SALE_DIR, "skill.json"), encoding="utf-8") as f:
    skill = json.load(f)
tools = skill["tools"]
print(f"[2] skill.json 工具数：{len(tools)}")

tool_names = [t["tool_name"] for t in tools]

# ---- 3. 名称一致性 ----
fn_names = set(sale_funcs.keys())
tool_name_set = set(tool_names)

missing_in_json = fn_names - tool_name_set  # 函数有但 json 没有
missing_in_py = tool_name_set - fn_names    # json 有但函数没有
dup = [n for n in tool_names if tool_names.count(n) > 1]

if missing_in_json:
    errors.append(f"函数存在但 skill.json 缺失：{sorted(missing_in_json)}")
if missing_in_py:
    errors.append(f"skill.json 存在但 main.py 无对应函数：{sorted(missing_in_py)}")
if dup:
    errors.append(f"skill.json 存在重复工具名：{sorted(set(dup))}")
print(f"[3] 名称一致性：缺失json={len(missing_in_json)} 缺失py={len(missing_in_py)} 重复={len(set(dup))}")

# ---- 4. 参数一致性 ----
param_mismatch = 0
for t in tools:
    name = t["tool_name"]
    if name not in sale_funcs:
        continue
    sig = inspect.signature(sale_funcs[name])
    fn_params = [p for p in sig.parameters]
    tool_params = [p["name"] for p in t["parameters"]]
    if fn_params != tool_params:
        param_mismatch += 1
        # 区分：仅顺序不同 vs 内容不同
        if set(fn_params) == set(tool_params):
            warnings.append(f"{name}: 参数顺序不同 fn={fn_params} json={tool_params}")
        else:
            errors.append(f"{name}: 参数不一致 fn={fn_params} json={tool_params}")
print(f"[4] 参数一致性：不匹配工具数={param_mismatch}（其中仅顺序不同={len([w for w in warnings if '顺序' in w])}）")

# ---- 5. 参数类型推断校验（简单）----
# 检查 json 中 number 类型对应函数参数注解是否为 float/int
type_issues = []
for t in tools:
    name = t["tool_name"]
    if name not in sale_funcs:
        continue
    sig = inspect.signature(sale_funcs[name])
    for p in t["parameters"]:
        pname = p["name"]
        ptype_json = p["type"]
        if pname not in sig.parameters:
            continue
        ann = sig.parameters[pname].annotation
        if ann is inspect.Parameter.empty:
            continue
        # 简单映射检查
        ann_str = getattr(ann, "__name__", str(ann))
        if ptype_json == "integer" and ann_str not in ("int",):
            type_issues.append(f"{name}.{pname}: json=integer py={ann_str}")
        elif ptype_json == "number" and ann_str not in ("float", "int", "Decimal"):
            type_issues.append(f"{name}.{pname}: json=number py={ann_str}")
        elif ptype_json == "string" and ann_str not in ("str",):
            type_issues.append(f"{name}.{pname}: json=string py={ann_str}")
        elif ptype_json == "array" and ann_str not in ("list", "List"):
            type_issues.append(f"{name}.{pname}: json=array py={ann_str}")
        elif ptype_json == "object" and ann_str not in ("dict", "Dict"):
            type_issues.append(f"{name}.{pname}: json=object py={ann_str}")
print(f"[5] 类型推断：可疑类型不匹配={len(type_issues)}")
for ti in type_issues[:20]:
    warnings.append(ti)

# ---- 6. admin 回归：导入根 main.py ----
try:
    admin_main = importlib.import_module("main")
    admin_funcs = [n for n in dir(admin_main) if n.startswith("tenant_") or n.startswith("admin_")]
    print(f"[6] admin 回归：根 main.py 可导入，公开函数数={len(admin_funcs)}")
except Exception as e:
    errors.append(f"[FATAL] 无法导入根 main.py（admin回归失败）: {e!r}")

# ---- 汇总 ----
print("\n" + "=" * 60)
print("汇总")
print("=" * 60)
print(f"函数数(main.py): {len(sale_funcs)}")
print(f"工具数(skill.json): {len(tools)}")
print(f"错误数: {len(errors)}")
print(f"告警数: {len(warnings)}")

if errors:
    print("\n--- 错误 ---")
    for e in errors:
        print("  ✗", e)
if warnings:
    print("\n--- 告警（可接受，仅顺序/类型提示）---")
    for w in warnings[:15]:
        print("  ·", w)
    if len(warnings) > 15:
        print(f"  ... 还有 {len(warnings)-15} 条告警省略")

if not errors:
    print("\n✓ 全部检查通过（错误为0）")
sys.exit(1 if errors else 0)
