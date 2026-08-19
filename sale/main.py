"""
sale/main.py —— 房产SaaS 销售管理技能入口

严格依据后端 real_estate_agent_saas/sale/router/* 的路由接口实现，
字段对照 sale/schemas/* 的 Pydantic 校验模型与 sale/model/sale_models.py 的列注释。

- 认证：复用共享认证内核 auth_core（凭证共享同一 cred.json，由根 auth_core 统一管理），
  与 admin/finance 一致，不再内联重复认证逻辑。
- URL：BASE_URL + /api/sale/<子路由>/<route>，路径常量见 sale.config。
- 请求构造：path 参数拼 URL；标量参数走 query（即使 POST）；dict body 走 json（schema 字段平铺）；
  customer/create 为多 body 参数，按 FastAPI 规则嵌套为 {customer_data, tags, demands}。
- 结构化输出（对齐 admin 模板）：
  · 查询类（list/detail/control/get-value/统计等）经 _beautify_query 渲染为 Markdown 表格；
  · 写操作（增/改/删等）遵循「缺必填→need_input 引导；齐备未确认→need_confirm 二次确认；
    confirmed=True→执行并经 _beautify_mutation 美化」的三段式交互；
  · 登录拆分为 sale_login（引导/确认）+ sale_login_confirm（执行）；登出带二次确认。
- 返回：成功透传 authenticated_request 的原始响应（code=0），并附加 action 与美观 message。
"""
import os
import sys

# 将项目根加入搜索路径，确保 auth_core / 根 config / sale 包均可导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from auth_core import (
    load_cred, clear_cred,
    do_login, do_logout, do_refresh_token,
    do_change_password, get_login_user, authenticated_request
)
from config import BASE_URL  # noqa: F401
from sale.config import (
    API_SALE_PROJECT, API_SALE_CUSTOMER, API_SALE_TRANSACTION,
    API_SALE_COMMISSION, API_SALE_PERFORMANCE, API_SALE_STATISTICS
)


def _compact(d: dict) -> dict:
    """剔除值为 None 的键（用 is not None，保留 0/False），让后端按 schema 默认值生效"""
    return {k: v for k, v in d.items() if v is not None}


# ===================== 展示辅助：为 arkclaw 输出美观提示 =====================
def _mask_secret(secret: str) -> str:
    """密码脱敏展示：仅保留末位可见，其余以 • 代替，空值返回占位"""
    if not secret:
        return "（空）"
    if len(secret) <= 2:
        return "•" * len(secret)
    return "•" * (len(secret) - 1) + secret[-1]


def _current_account():
    """读取本地凭证中的登录账号/姓名，未登录返回 None"""
    cred = load_cred()
    if not cred or not cred.get("access_token"):
        return None
    info = cred.get("user_info", {}) or {}
    return info.get("account") or info.get("name") or info.get("username") or "当前用户"


def _fmt_cell(v):
    """把单个字段值渲染为表格单元格文本（None/空转占位，转义竖线与换行）"""
    if v is None or v == "":
        return "—"
    if isinstance(v, (dict, list)):
        import json as _json
        v = _json.dumps(v, ensure_ascii=False)
    return str(v).replace("|", "\\|").replace("\n", " ")


def _extract_rows(data):
    """
    从后端 data 中尽力提取「列表行」与「分页信息」。
    兼容多种结构：data 直接是 list；或 data 是 dict 且含 list/items/records/rows 数组。
    返回 (rows: list|None, meta: dict) —— rows 为 None 表示不是列表结构。
    """
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict):
        for key in ("list", "items", "records", "rows", "data"):
            arr = data.get(key)
            if isinstance(arr, list):
                meta = {k: data.get(k) for k in ("total", "page", "page_size", "size", "pages")
                        if data.get(k) is not None}
                return arr, meta
    return None, {}


def _md_table_from_rows(rows, meta=None, max_rows=20):
    """把行列表渲染为 Markdown 表格；列取所有行键的并集（保序）"""
    if not rows:
        return "（暂无数据）"
    cols = []
    for row in rows:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in cols:
                    cols.append(k)
    if not cols:
        # 行不是 dict（如纯标量列表），退化为单列
        body = "\n".join(f"| {_fmt_cell(r)} |" for r in rows[:max_rows])
        table = "| 值 |\n|:--|\n" + body
    else:
        header = "| " + " | ".join(cols) + " |"
        sep = "| " + " | ".join([":--"] * len(cols)) + " |"
        lines = []
        for row in rows[:max_rows]:
            lines.append("| " + " | ".join(_fmt_cell(row.get(c)) for c in cols) + " |")
        table = "\n".join([header, sep] + lines)
    footer = ""
    if len(rows) > max_rows:
        footer += f"\n\n> 仅展示前 {max_rows} 条，共 {len(rows)} 条。"
    if meta:
        parts = []
        if meta.get("total") is not None:
            parts.append(f"总数 {meta['total']}")
        if meta.get("page") is not None:
            parts.append(f"第 {meta['page']} 页")
        size = meta.get("page_size") if meta.get("page_size") is not None else meta.get("size")
        if size is not None:
            parts.append(f"每页 {size}")
        if parts:
            footer += "\n\n> " + " · ".join(parts)
    return table + footer


def _md_kv_table(obj):
    """把单个详情对象渲染为两列 键/值 Markdown 表格"""
    if not isinstance(obj, dict) or not obj:
        return "（暂无详情数据）"
    lines = ["| 字段 | 值 |", "|:--|:--|"]
    for k, v in obj.items():
        lines.append(f"| {_fmt_cell(k)} | {_fmt_cell(v)} |")
    return "\n".join(lines)


def _beautify_query(res, title, empty_hint="没有查到符合条件的记录。"):
    """
    为查询类接口（list/detail/统计等）美化输出：把后端原始响应包装为带 Markdown 表格的 message，
    同时保留原始 code/data，附加 action=query_result。失败则原样透传。
    :param res: authenticated_request 的原始返回
    :param title: 面板标题（如“楼盘列表”）
    """
    if not isinstance(res, dict) or res.get("code") != 0:
        return res  # 失败/异常：交由上层统一透传，不强行美化

    data = res.get("data")
    rows, meta = _extract_rows(data)
    if rows is not None:
        body = _md_table_from_rows(rows, meta) if rows else f"_{empty_hint}_"
    elif isinstance(data, dict):
        body = _md_kv_table(data)
    else:
        body = f"_{empty_hint}_"

    res["message"] = f"### 📋 {title}\n\n{body}"
    res["action"] = "query_result"
    return res


def _need_confirm(title, summary_lines, confirm_call, warn=False):
    """
    生成「二次确认」结构化返回：展示将执行的操作摘要，请用户确认后再调用 confirm_call。
    :param title: 操作标题
    :param summary_lines: 摘要行列表（每行 "字段：值"）
    :param confirm_call: 提示用户确认后应调用的函数签名字符串
    :param warn: 是否为高危操作（删除/取消/冻结/终止/解散类），True 时使用醒目图标
    """
    icon = "🗑️" if warn else "📝"
    tip = "此操作影响较大，" if warn else ""
    body = "\n".join(f"│   {line}" for line in summary_lines)
    message = (
        f"╭──────────── {icon} 请确认操作 · {title} ────────────╮\n"
        f"{body}\n"
        "│                                            \n"
        f"│   {tip}确认无误后继续。\n"
        "╰────────────────────────────────────────────╯\n"
        f"（确认后请调用 {confirm_call}）"
    )
    return {
        "code": 4002,
        "message": message,
        "action": "need_confirm",
        "data": {"next": confirm_call},
    }


def _need_input(title, required_fields, retry_call):
    """
    生成「引导输入」结构化返回：告知缺少哪些必填字段，请用户补充后重试。
    :param title: 操作标题
    :param required_fields: 缺失的必填字段名列表
    :param retry_call: 补齐后应重新调用的函数签名字符串
    """
    fields_txt = "、".join(required_fields)
    lines = "\n".join(f"│     ▫ {f}：____________" for f in required_fields)
    message = (
        f"╭──────────── ✍️ 请补充信息 · {title} ────────────╮\n"
        "│                                                \n"
        f"│   还需要以下必填信息：{fields_txt}\n"
        f"{lines}\n"
        "│                                                \n"
        "╰────────────────────────────────────────────────╯\n"
        f"（补齐后我会先与你确认，再执行；对应调用 {retry_call}）"
    )
    return {
        "code": 4001,
        "message": message,
        "action": "need_input",
        "data": {"required_fields": required_fields, "next": retry_call},
    }


def _beautify_mutation(res, ok_title, ok_lines):
    """
    为写操作（增/改/删等）美化成功/失败输出，保留原始 code/data。
    :param res: authenticated_request 原始返回
    :param ok_title: 成功标题（如“楼盘创建成功”）
    :param ok_lines: 成功时展示的摘要行列表
    """
    if not isinstance(res, dict):
        return res
    if res.get("code") == 0:
        body = "\n".join(f"│   {line}" for line in ok_lines) if ok_lines else ""
        res["message"] = (
            f"╭──────────── ✅ {ok_title} ────────────╮\n"
            + (body + "\n" if body else "")
            + "╰────────────────────────────────────────────╯"
        )
        res["action"] = "mutation_success"
        return res
    reason = res.get("message", "操作失败")
    res["message"] = (
        f"╭──────────── ❌ 操作失败 ────────────╮\n"
        f"│   原因：{reason}\n"
        "│   请核对信息后重试。\n"
        "╰──────────────────────────────────────╯"
    )
    res["action"] = "mutation_failed"
    return res


# ===================== 认证接口（复用共享登录，凭证共享）=====================
def sale_login(account: str = None, password: str = None):
    """
    销售端登录（复用共享登录端点，凭证写入共享 cred.json）—— 分步交互。

    1）已登录 → 返回友好提示，无需重复登录；
    2）未提供账号或密码 → 返回 action=need_login，附带美观登录提示，请 Agent 引导用户输入；
    3）已提供账号与密码 → 返回 action=need_confirm（密码脱敏展示），
       请 Agent 与用户二次确认后调用 sale_login_confirm 完成登录。

    :param account: 登录账号（可选；缺省时触发引导输入）
    :param password: 登录密码（可选；缺省时触发引导输入）
    """
    logged_in = _current_account()
    if logged_in:
        message = (
            "╭──────────── 已处于登录状态 ────────────╮\n"
            f"│  ✅ 当前已登录账号：{logged_in}\n"
            "│  💡 如需切换账号，请先执行 sale_logout 退出登录。\n"
            "╰────────────────────────────────────────╯"
        )
        return {
            "code": 200,
            "message": message,
            "action": "already_logged_in",
            "data": {"account": logged_in},
        }

    if not account or not password:
        message = (
            "╭──────────── 🔐 房产SaaS销售管理系统 · 登录 ────────────╮\n"
            "│                                                \n"
            "│   欢迎使用房产SaaS销售管理系统                 \n"
            "│   检测到本地暂无有效登录凭证，请先登录。       \n"
            "│                                                \n"
            "│   请提供以下信息：                             \n"
            "│     👤 登录账号：____________                  \n"
            "│     🔑 登录密码：____________                  \n"
            "│                                                \n"
            "╰────────────────────────────────────────────────╯\n"
            "（请输入账号与密码，我会先与你确认再执行登录）"
        )
        return {
            "code": 4001,
            "message": message,
            "action": "need_login",
            "data": {
                "required_fields": ["account", "password"],
                "next": "收集账号密码后调用 sale_login(account, password) 进入确认环节",
            },
        }

    message = (
        "╭──────────── 📝 请确认登录信息 ────────────╮\n"
        f"│   👤 登录账号：{account}\n"
        f"│   🔑 登录密码：{_mask_secret(password)}\n"
        "│                                            \n"
        "│   确认无误后即可登录。                     \n"
        "╰────────────────────────────────────────────╯\n"
        "（确认后请调用 sale_login_confirm(account, password) 完成登录）"
    )
    return {
        "code": 4002,
        "message": message,
        "action": "need_confirm",
        "data": {
            "account": account,
            "password_masked": _mask_secret(password),
            "next": "用户确认后调用 sale_login_confirm(account, password)",
        },
    }


def sale_login_confirm(account: str, password: str):
    """
    确认并执行登录（在 sale_login 引导 + 用户确认之后调用）。
    登录成功自动持久化 token 到共享 cred.json。
    :param account: 登录账号
    :param password: 登录密码
    """
    res = do_login(account, password)
    if res.get("code") == 200:
        user_info = (res.get("data") or {}).get("user_info", {}) or {}
        who = user_info.get("account") or user_info.get("name") or account
        res["message"] = (
            "╭──────────── ✅ 登录成功 ────────────╮\n"
            f"│   欢迎回来，{who}！\n"
            "│   凭证已安全保存，现在可以开始使用系统。\n"
            "╰──────────────────────────────────────╯"
        )
        res["action"] = "login_success"
        return res

    reason = res.get("message", "登录失败")
    res["message"] = (
        "╭──────────── ❌ 登录失败 ────────────╮\n"
        f"│   原因：{reason}\n"
        "│   请核对账号与密码后重试。\n"
        "╰──────────────────────────────────────╯"
    )
    res["action"] = "login_failed"
    return res


def sale_logout(confirmed: bool = False):
    """
    销售端登出：为避免误操作，先与用户确认，再调用后端登出接口并删除本地凭证。

    :param confirmed: 是否已获得用户确认。默认 False：
        - False → 返回 action=need_confirm，请 Agent 与用户确认后再次调用 sale_logout(confirmed=True)；
        - True  → 执行真正的登出，并礼貌地输出退出信息。
    """
    who = _current_account()

    if not who:
        clear_cred()
        return {
            "code": 200,
            "message": (
                "╭──────────── 👋 未处于登录状态 ────────────╮\n"
                "│   本地暂无登录凭证，无需退出。\n"
                "│   如需使用系统，请先执行 sale_login 登录。\n"
                "╰────────────────────────────────────────────╯"
            ),
            "action": "not_logged_in",
            "data": None,
        }

    if not confirmed:
        return {
            "code": 4002,
            "message": (
                "╭──────────── ⚠️ 确认退出登录 ────────────╮\n"
                f"│   当前登录账号：{who}\n"
                "│                                          \n"
                "│   退出后需重新登录才能继续使用系统。     \n"
                "│   确定要退出登录吗？                     \n"
                "╰────────────────────────────────────────────╯\n"
                "（确认退出请调用 sale_logout(confirmed=True)）"
            ),
            "action": "need_confirm",
            "data": {
                "account": who,
                "next": "用户确认后调用 sale_logout(confirmed=True)",
            },
        }

    do_logout()
    return {
        "code": 200,
        "message": (
            "╭──────────── 👋 已安全退出登录 ────────────╮\n"
            f"│   {who}，您已成功退出登录。\n"
            "│   本地凭证已清除，感谢您的使用，期待下次再见！\n"
            "╰────────────────────────────────────────────╯"
        ),
        "action": "logout_success",
        "data": None,
    }


def sale_refresh_token():
    """自动刷新 access_token，无需传入参数"""
    return do_refresh_token()


def sale_change_password(old_password: str, new_password: str):
    """
    修改当前登录账号密码
    :param old_password: 原始旧密码
    :param new_password: 设置的新密码
    """
    return do_change_password(old_password, new_password)


def sale_get_login_user():
    """查询当前登录用户信息"""
    return get_login_user()


# ===================== 楼盘销控模块（/api/sale/project）=====================
def sale_project_create(project_code: str = None, project_name: str = None,
                        developer: str = None, region: str = None, address: str = None,
                        sale_status: int = None, status: int = None,
                        start_date: str = None, total_area: float = None,
                        total_buildings: int = None, total_houses: int = None,
                        confirmed: bool = False):
    """
    创建楼盘 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param project_code: 楼盘编码（必填）
    :param project_name: 楼盘名称（必填）
    :param developer: 开发商（必填）
    :param region: 区域（必填，如"广东省深圳市南山区"）
    :param address: 详细地址（必填）
    :param sale_status: 销售状态：1-未开盘 2-在售 3-售罄 4-停售
    :param status: 项目状态：1-正常 2-停用（默认1）
    :param start_date: 开盘日期
    :param total_area: 总建筑面积
    :param total_buildings: 总楼栋数
    :param total_houses: 总房源数
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("project_code", project_code), ("project_name", project_name),
                              ("developer", developer), ("region", region),
                              ("address", address)) if not v]
    if missing:
        return _need_input("创建楼盘", missing,
                           "sale_project_create(project_code, project_name, developer, region, address, ...)")
    if not confirmed:
        return _need_confirm(
            "创建楼盘",
            [
                f"🏢 名称：{project_name}（编码 {project_code}）",
                f"🏗️ 开发商：{developer}",
                f"📍 区域：{region}    地址：{address}",
            ],
            "sale_project_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_PROJECT}/create"
    payload = _compact({
        "project_code": project_code, "project_name": project_name,
        "developer": developer, "region": region, "address": address,
        "sale_status": sale_status, "status": status,
        "start_date": start_date, "total_area": total_area,
        "total_buildings": total_buildings, "total_houses": total_houses,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "楼盘创建成功", [f"🏢 {project_name}（编码 {project_code}）已创建"])


def sale_project_list(page: int = 1, page_size: int = 20,
                      project_name: str = None, project_status: int = None):
    """
    分页查询楼盘列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_name: 楼盘名称（可选，用于搜索）
    :param project_status: 项目状态（可选）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/list"
    params = _compact({"page": page, "page_size": page_size,
                       "project_name": project_name, "project_status": project_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "楼盘列表", empty_hint="没有查到符合条件的楼盘。")


def sale_project_detail(project_id: int):
    """
    查询楼盘详情，返回键/值 Markdown 表格。
    :param project_id: 楼盘ID
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/detail/{project_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"楼盘详情 · #{project_id}", empty_hint="未找到该楼盘。")


def sale_project_update(project_id: int, project_name: str = None,
                        developer: str = None, region: str = None,
                        address: str = None, sale_status: int = None,
                        status: int = None, start_date: str = None,
                        total_area: float = None, total_buildings: int = None,
                        total_houses: int = None, confirmed: bool = False):
    """
    更新楼盘 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称
    :param developer: 开发商
    :param region: 区域
    :param address: 详细地址
    :param sale_status: 销售状态
    :param status: 项目状态
    :param start_date: 开盘日期
    :param total_area: 总建筑面积
    :param total_buildings: 总楼栋数
    :param total_houses: 总房源数
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not project_id:
        return _need_input("更新楼盘", ["project_id"], "sale_project_update(project_id, ...)")
    payload = _compact({
        "project_name": project_name, "developer": developer, "region": region,
        "address": address, "sale_status": sale_status, "status": status,
        "start_date": start_date, "total_area": total_area,
        "total_buildings": total_buildings, "total_houses": total_houses,
    })
    if not payload:
        return _need_input("更新楼盘（未提供任何要修改的字段）",
                           ["project_name/developer/region/... 至少一项"],
                           "sale_project_update(project_id, project_name=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新楼盘 · #{project_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_project_update(project_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/update/{project_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "楼盘更新成功", [f"楼盘 #{project_id} 的信息已更新"])


def sale_project_delete(project_id: int, confirmed: bool = False):
    """
    删除楼盘 —— 高危操作，需二次确认。
    :param project_id: 楼盘ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回删除确认提示）
    """
    if not project_id:
        return _need_input("删除楼盘", ["project_id"], "sale_project_delete(project_id)")
    if not confirmed:
        return _need_confirm(f"删除楼盘 · #{project_id}",
                             [f"🗑️ 即将删除楼盘 #{project_id}"],
                             "sale_project_delete(project_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_PROJECT}/delete/{project_id}"
    res = authenticated_request("DELETE", url)
    return _beautify_mutation(res, "楼盘删除成功", [f"楼盘 #{project_id} 已删除"])


def sale_building_create(project_id: int = None, building_code: str = None,
                         building_name: str = None, total_floors: int = None,
                         status: int = None, confirmed: bool = False):
    """
    创建楼栋 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param project_id: 楼盘ID（必填）
    :param building_code: 楼栋编码（必填）
    :param building_name: 楼栋名称（必填）
    :param total_floors: 总楼层数
    :param status: 状态：1-正常 2-停用（默认1）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("project_id", project_id), ("building_code", building_code),
                              ("building_name", building_name)) if not v]
    if missing:
        return _need_input("创建楼栋", missing,
                           "sale_building_create(project_id, building_code, building_name, ...)")
    if not confirmed:
        return _need_confirm(
            "创建楼栋",
            [f"🏬 名称：{building_name}（编码 {building_code}）", f"🏢 所属楼盘：#{project_id}"],
            "sale_building_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_PROJECT}/building/create"
    payload = _compact({
        "project_id": project_id, "building_code": building_code,
        "building_name": building_name, "total_floors": total_floors,
        "status": status,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "楼栋创建成功", [f"🏬 {building_name}（编码 {building_code}）已创建"])


def sale_building_list(project_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询楼栋列表，返回 Markdown 表格。
    :param project_id: 楼盘ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/building/list"
    params = _compact({"project_id": project_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "楼栋列表", empty_hint="没有查到符合条件的楼栋。")


def sale_building_update(building_id: int, building_name: str = None,
                         total_floors: int = None, status: int = None,
                         confirmed: bool = False):
    """
    更新楼栋 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param building_id: 楼栋ID（必填）
    :param building_name: 楼栋名称
    :param total_floors: 总楼层数
    :param status: 状态
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not building_id:
        return _need_input("更新楼栋", ["building_id"], "sale_building_update(building_id, ...)")
    payload = _compact({
        "building_name": building_name, "total_floors": total_floors, "status": status,
    })
    if not payload:
        return _need_input("更新楼栋（未提供任何要修改的字段）",
                           ["building_name/total_floors/status 至少一项"],
                           "sale_building_update(building_id, building_name=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新楼栋 · #{building_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_building_update(building_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/building/update/{building_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "楼栋更新成功", [f"楼栋 #{building_id} 的信息已更新"])


def sale_unit_create(building_id: int = None, unit_code: str = None,
                     unit_name: str = None, status: int = None, confirmed: bool = False):
    """
    创建单元 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param building_id: 楼栋ID（必填）
    :param unit_code: 单元编码（必填）
    :param unit_name: 单元名称（必填）
    :param status: 状态（默认1）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("building_id", building_id), ("unit_code", unit_code),
                              ("unit_name", unit_name)) if not v]
    if missing:
        return _need_input("创建单元", missing,
                           "sale_unit_create(building_id, unit_code, unit_name, ...)")
    if not confirmed:
        return _need_confirm(
            "创建单元",
            [f"🚪 名称：{unit_name}（编码 {unit_code}）", f"🏬 所属楼栋：#{building_id}"],
            "sale_unit_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_PROJECT}/unit/create"
    payload = _compact({
        "building_id": building_id, "unit_code": unit_code, "unit_name": unit_name,
        "status": status,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "单元创建成功", [f"🚪 {unit_name}（编码 {unit_code}）已创建"])


def sale_unit_list(building_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询单元列表，返回 Markdown 表格。
    :param building_id: 楼栋ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/unit/list"
    params = _compact({"building_id": building_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "单元列表", empty_hint="没有查到符合条件的单元。")


def sale_unit_detail(unit_id: int):
    """
    查询单元详情，返回键/值 Markdown 表格。
    :param unit_id: 单元ID
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/unit/detail/{unit_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"单元详情 · #{unit_id}", empty_hint="未找到该单元。")


def sale_unit_update(unit_id: int, unit_name: str = None, status: int = None,
                     confirmed: bool = False):
    """
    更新单元 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param unit_id: 单元ID（必填）
    :param unit_name: 单元名称
    :param status: 状态
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not unit_id:
        return _need_input("更新单元", ["unit_id"], "sale_unit_update(unit_id, ...)")
    payload = _compact({"unit_name": unit_name, "status": status})
    if not payload:
        return _need_input("更新单元（未提供任何要修改的字段）",
                           ["unit_name/status 至少一项"],
                           "sale_unit_update(unit_id, unit_name=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新单元 · #{unit_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_unit_update(unit_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/unit/update/{unit_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "单元更新成功", [f"单元 #{unit_id} 的信息已更新"])


def sale_house_create(project_id: int = None, building_id: int = None,
                      house_code: str = None, house_name: str = None, floor: int = None,
                      room_type: str = None, building_area: float = None,
                      unit_price: float = None, unit_id: int = None,
                      usage_area: float = None, total_price: float = None,
                      house_status: int = None, orientation: str = None,
                      remark: str = None, confirmed: bool = False):
    """
    创建房源 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param project_id: 楼盘ID（必填）
    :param building_id: 楼栋ID（必填）
    :param house_code: 房源编码（必填）
    :param house_name: 房源名称（必填）
    :param floor: 楼层（必填）
    :param room_type: 户型（必填，如3室2厅1卫）
    :param building_area: 建筑面积㎡（必填）
    :param unit_price: 单价元/㎡（必填）
    :param unit_id: 单元ID（必填）
    :param usage_area: 使用面积㎡
    :param total_price: 总价元
    :param house_status: 房源状态：1-可售 2-已售 3-锁定 4-预定 5-停售（默认1）
    :param orientation: 朝向
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("project_id", project_id), ("building_id", building_id),
                              ("house_code", house_code), ("house_name", house_name),
                              ("floor", floor), ("room_type", room_type),
                              ("building_area", building_area),
                              ("unit_price", unit_price), ("unit_id", unit_id)) if not v]
    if missing:
        return _need_input("创建房源", missing,
                           "sale_house_create(project_id, building_id, house_code, house_name, floor, room_type, building_area, unit_price, unit_id, ...)")
    if not confirmed:
        return _need_confirm(
            "创建房源",
            [
                f"🏠 名称：{house_name}（编码 {house_code}）",
                f"🏢 楼盘 #{project_id} · 楼栋 #{building_id} · 单元 #{unit_id} · {floor}层",
                f"📐 户型：{room_type}    建面：{building_area}㎡    单价：{unit_price} 元/㎡",
            ],
            "sale_house_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/create"
    payload = _compact({
        "project_id": project_id, "building_id": building_id, "unit_id": unit_id,
        "house_code": house_code, "house_name": house_name, "floor": floor,
        "room_type": room_type, "building_area": building_area,
        "usage_area": usage_area, "unit_price": unit_price,
        "total_price": total_price, "house_status": house_status,
        "orientation": orientation, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "房源创建成功", [f"🏠 {house_name}（编码 {house_code}）已创建"])


def sale_house_list(project_id: int, page: int = 1, page_size: int = 20,
                    building_id: int = None, unit_id: int = None):
    """
    分页查询房源列表，返回 Markdown 表格。
    :param project_id: 楼盘ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param building_id: 楼栋ID（可选）
    :param unit_id: 单元ID（可选）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/list"
    params = _compact({
        "project_id": project_id, "building_id": building_id, "unit_id": unit_id,
        "page": page, "page_size": page_size,
    })
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "房源列表", empty_hint="没有查到符合条件的房源。")


def sale_house_detail(house_id: int):
    """
    查询房源详情，返回键/值 Markdown 表格。
    :param house_id: 房源ID
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/detail/{house_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"房源详情 · #{house_id}", empty_hint="未找到该房源。")


def sale_house_update(house_id: int, house_name: str = None, unit_price: float = None,
                      total_price: float = None, house_status: int = None,
                      orientation: str = None, usage_area: float = None,
                      remark: str = None, confirmed: bool = False):
    """
    更新房源 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param house_id: 房源ID（必填）
    :param house_name: 房源名称
    :param unit_price: 单价元/㎡
    :param total_price: 总价元
    :param house_status: 房源状态
    :param orientation: 朝向
    :param usage_area: 使用面积
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not house_id:
        return _need_input("更新房源", ["house_id"], "sale_house_update(house_id, ...)")
    payload = _compact({
        "house_name": house_name, "unit_price": unit_price,
        "total_price": total_price, "house_status": house_status,
        "orientation": orientation, "usage_area": usage_area, "remark": remark,
    })
    if not payload:
        return _need_input("更新房源（未提供任何要修改的字段）",
                           ["house_name/unit_price/house_status/... 至少一项"],
                           "sale_house_update(house_id, house_name=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新房源 · #{house_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_house_update(house_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/update/{house_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "房源更新成功", [f"房源 #{house_id} 的信息已更新"])


def sale_house_lock(house_id: int = None, customer_id: int = None,
                    expire_minutes: int = 30, confirmed: bool = False):
    """
    锁定房源（POST + query 参数）—— 缺必填→引导；未确认→确认；confirmed=True→执行。
    :param house_id: 房源ID（必填）
    :param customer_id: 客户ID（必填）
    :param expire_minutes: 过期时间分钟（默认30）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("house_id", house_id), ("customer_id", customer_id)) if not v]
    if missing:
        return _need_input("锁定房源", missing, "sale_house_lock(house_id, customer_id, ...)")
    if not confirmed:
        return _need_confirm(f"锁定房源 · #{house_id}",
                             [f"🔒 房源 #{house_id} 锁定给客户 #{customer_id}，有效 {expire_minutes} 分钟"],
                             "sale_house_lock(house_id, customer_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/lock"
    params = _compact({"house_id": house_id, "customer_id": customer_id,
                       "expire_minutes": expire_minutes})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "房源锁定成功", [f"房源 #{house_id} 已锁定给客户 #{customer_id}"])


def sale_house_unlock(house_id: int, confirmed: bool = False):
    """
    解锁房源（POST + query 参数）—— 未确认→确认；confirmed=True→执行。
    :param house_id: 房源ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not house_id:
        return _need_input("解锁房源", ["house_id"], "sale_house_unlock(house_id)")
    if not confirmed:
        return _need_confirm(f"解锁房源 · #{house_id}",
                             [f"🔓 即将解锁房源 #{house_id}"],
                             "sale_house_unlock(house_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/unlock"
    params = _compact({"house_id": house_id})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "房源解锁成功", [f"房源 #{house_id} 已解锁"])


def sale_house_control(project_id: int):
    """
    获取销控面板，返回 Markdown 表格/详情。
    :param project_id: 楼盘ID
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/house/control/{project_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"销控面板 · 楼盘 #{project_id}", empty_hint="暂无销控数据。")


def sale_project_rule_create(rule_key: str = None, rule_value: int = None,
                             project_id: int = None, rule_desc: str = None,
                             rule_status: int = None, confirmed: bool = False):
    """
    创建项目规则 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param rule_key: 规则键（必填）：visit_protect_days(到访保护期天数)/report_protect_days(报备保护期天数)
    :param rule_value: 规则值天数（必填）
    :param project_id: 楼盘ID（为空表示全局规则）
    :param rule_desc: 规则描述
    :param rule_status: 规则状态：1-启用 2-停用（默认1）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not rule_key:
        missing.append("rule_key")
    if rule_value is None:
        missing.append("rule_value")
    if missing:
        return _need_input("创建项目规则", missing,
                           "sale_project_rule_create(rule_key, rule_value, ...)")
    if not confirmed:
        return _need_confirm(
            "创建项目规则",
            [f"🔑 规则键：{rule_key} = {rule_value}",
             f"🏢 范围：{'楼盘 #' + str(project_id) if project_id else '全局'}"],
            "sale_project_rule_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/create"
    payload = _compact({
        "project_id": project_id, "rule_key": rule_key, "rule_value": rule_value,
        "rule_desc": rule_desc, "rule_status": rule_status,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "项目规则创建成功", [f"🔑 规则 {rule_key}={rule_value} 已创建"])


def sale_project_rule_list(page: int = 1, page_size: int = 20,
                           project_id: int = None, rule_key: str = None):
    """
    分页查询项目规则列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param rule_key: 规则键（可选）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/list"
    params = _compact({"project_id": project_id, "rule_key": rule_key,
                       "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "项目规则列表", empty_hint="没有查到符合条件的项目规则。")


def sale_project_rule_detail(rule_id: int):
    """
    查询项目规则详情，返回键/值 Markdown 表格。
    :param rule_id: 规则ID
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/detail/{rule_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"项目规则详情 · #{rule_id}", empty_hint="未找到该项目规则。")


def sale_project_rule_update(rule_id: int, rule_value: int = None,
                             rule_desc: str = None, rule_status: int = None,
                             confirmed: bool = False):
    """
    更新项目规则 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param rule_id: 规则ID（必填）
    :param rule_value: 规则值天数
    :param rule_desc: 规则描述
    :param rule_status: 规则状态：1-启用 2-停用
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not rule_id:
        return _need_input("更新项目规则", ["rule_id"], "sale_project_rule_update(rule_id, ...)")
    payload = _compact({"rule_value": rule_value, "rule_desc": rule_desc, "rule_status": rule_status})
    if not payload:
        return _need_input("更新项目规则（未提供任何要修改的字段）",
                           ["rule_value/rule_desc/rule_status 至少一项"],
                           "sale_project_rule_update(rule_id, rule_value=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新项目规则 · #{rule_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_project_rule_update(rule_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/update/{rule_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "项目规则更新成功", [f"项目规则 #{rule_id} 的信息已更新"])


def sale_project_rule_delete(rule_id: int, confirmed: bool = False):
    """
    删除项目规则 —— 高危操作，需二次确认。
    :param rule_id: 规则ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回删除确认提示）
    """
    if not rule_id:
        return _need_input("删除项目规则", ["rule_id"], "sale_project_rule_delete(rule_id)")
    if not confirmed:
        return _need_confirm(f"删除项目规则 · #{rule_id}",
                             [f"🗑️ 即将删除项目规则 #{rule_id}"],
                             "sale_project_rule_delete(rule_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/delete/{rule_id}"
    res = authenticated_request("DELETE", url)
    return _beautify_mutation(res, "项目规则删除成功", [f"项目规则 #{rule_id} 已删除"])


def sale_project_rule_get_value(project_id: int, rule_key: str):
    """
    获取规则值（GET + query 参数），返回键/值 Markdown 表格。
    :param project_id: 楼盘ID（必填）
    :param rule_key: 规则键（必填）
    """
    url = f"{BASE_URL}{API_SALE_PROJECT}/rule/get-value"
    params = _compact({"project_id": project_id, "rule_key": rule_key})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, f"规则值 · {rule_key}", empty_hint="未取到该规则值。")


# ===================== 客户管理模块（/api/sale/customer）=====================
def sale_customer_create(customer_name: str = None, mobile: str = None, gender: int = None,
                         id_card: str = None, customer_status: int = None,
                         customer_source: str = None, belong_user_id: int = None,
                         tags: list = None, demands: list = None, confirmed: bool = False):
    """
    创建客户（多 body 参数，FastAPI 嵌套为 {customer_data, tags, demands}）
    —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param customer_name: 客户姓名（必填）
    :param mobile: 手机号（必填）
    :param gender: 性别：1-男 2-女 3-未知（默认1）
    :param id_card: 身份证号
    :param customer_status: 客户状态：1-潜客 2-意向 3-认购 4-签约 5-成交 6-无效（默认1）
    :param customer_source: 客户来源（默认自然到访）
    :param belong_user_id: 归属销售ID
    :param tags: 标签列表（如 ["改善型", "首次到访"]）
    :param demands: 购房需求字典列表，如 [{"intent_room_type": "三室", "remark": "意向三室", "budget_min": 2000000, "budget_max": 3000000}]
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("customer_name", customer_name), ("mobile", mobile)) if not v]
    if missing:
        return _need_input("创建客户", missing, "sale_customer_create(customer_name, mobile, ...)")
    if not confirmed:
        return _need_confirm(
            "创建客户",
            [f"👤 姓名：{customer_name}", f"📱 手机：{mobile}",
             f"🏷️ 标签：{'、'.join(tags) if tags else '—'}"],
            "sale_customer_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/create"
    body = {"customer_data": _compact({
        "customer_name": customer_name, "mobile": mobile, "gender": gender,
        "id_card": id_card, "customer_status": customer_status,
        "customer_source": customer_source, "belong_sale_user_id": belong_user_id,
    })}
    if tags is not None:
        body["tags"] = tags
    if demands is not None:
        body["demands"] = demands
    res = authenticated_request("POST", url, json=body)
    return _beautify_mutation(res, "客户创建成功", [f"👤 {customer_name}（{mobile}）已创建"])


def sale_customer_list(page: int = 1, page_size: int = 20,
                       customer_name: str = None, mobile: str = None,
                       customer_status: int = None, belong_user_id: int = None):
    """
    分页查询客户列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param customer_name: 客户姓名（可选，用于搜索）
    :param mobile: 手机号（可选，用于搜索）
    :param customer_status: 客户状态（可选）
    :param belong_user_id: 归属销售ID（可选）
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/list"
    params = _compact({"page": page, "page_size": page_size, "customer_name": customer_name,
                       "mobile": mobile, "customer_status": customer_status,
                       "belong_sale_user_id": belong_user_id})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "客户列表", empty_hint="没有查到符合条件的客户。")


def sale_customer_detail(customer_id: int):
    """
    查询客户详情，返回键/值 Markdown 表格。
    :param customer_id: 客户ID
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/detail/{customer_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"客户详情 · #{customer_id}", empty_hint="未找到该客户。")


def sale_customer_update(customer_id: int, customer_name: str = None,
                         gender: int = None, id_card: str = None,
                         customer_status: int = None,
                         customer_source: str = None, belong_user_id: int = None,
                         confirmed: bool = False):
    """
    更新客户 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param customer_name: 客户姓名
    :param gender: 性别
    :param id_card: 身份证号
    :param customer_status: 客户状态
    :param customer_source: 客户来源
    :param belong_user_id: 归属销售ID
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not customer_id:
        return _need_input("更新客户", ["customer_id"], "sale_customer_update(customer_id, ...)")
    payload = _compact({
        "customer_name": customer_name, "gender": gender, "id_card": id_card,
        "customer_status": customer_status, "customer_source": customer_source,
        "belong_sale_user_id": belong_user_id,
    })
    if not payload:
        return _need_input("更新客户（未提供任何要修改的字段）",
                           ["customer_name/gender/customer_status/... 至少一项"],
                           "sale_customer_update(customer_id, customer_name=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新客户 · #{customer_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_customer_update(customer_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/update/{customer_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "客户更新成功", [f"客户 #{customer_id} 的信息已更新"])


def sale_customer_delete(customer_id: int, confirmed: bool = False):
    """
    删除客户 —— 高危操作，需二次确认。
    :param customer_id: 客户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回删除确认提示）
    """
    if not customer_id:
        return _need_input("删除客户", ["customer_id"], "sale_customer_delete(customer_id)")
    if not confirmed:
        return _need_confirm(f"删除客户 · #{customer_id}",
                             [f"🗑️ 即将删除客户 #{customer_id}"],
                             "sale_customer_delete(customer_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/delete/{customer_id}"
    res = authenticated_request("DELETE", url)
    return _beautify_mutation(res, "客户删除成功", [f"客户 #{customer_id} 已删除"])


def sale_customer_transfer(customer_id: int = None, target_user_id: int = None,
                           confirmed: bool = False):
    """
    转移客户归属（json body 参数）—— 缺必填→引导；未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param target_user_id: 目标销售ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("customer_id", customer_id), ("target_user_id", target_user_id)) if not v]
    if missing:
        return _need_input("转移客户归属", missing,
                           "sale_customer_transfer(customer_id, target_user_id)")
    if not confirmed:
        return _need_confirm(f"转移客户归属 · 客户 #{customer_id}",
                             [f"🔄 客户 #{customer_id} 转移至销售 #{target_user_id}"],
                             "sale_customer_transfer(customer_id, target_user_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/transfer"
    payload = _compact({"customer_id": customer_id, "target_user_id": target_user_id})
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "客户转移成功", [f"客户 #{customer_id} 已转移至销售 #{target_user_id}"])


def sale_report_create(customer_id: int = None, project_id: int = None,
                       customer_name: str = None, mobile: str = None,
                       report_time: str = None, broker_id: int = None,
                       channel_id: int = None, confirmed: bool = False):
    """
    创建报备 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param customer_name: 客户姓名（后端需要，建议传）
    :param mobile: 客户手机号（后端需要，建议传）
    :param report_time: 报备时间（可选，默认当前时间）
    :param broker_id: 经纪人ID（可选）
    :param channel_id: 渠道公司ID（可选）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("customer_id", customer_id), ("project_id", project_id)) if not v]
    if missing:
        return _need_input("创建报备", missing, "sale_report_create(customer_id, project_id, ...)")
    if not confirmed:
        return _need_confirm(
            "创建报备",
            [f"📝 客户 #{customer_id} 报备至楼盘 #{project_id}",
             f"👤 姓名：{customer_name or '—'}    📱 手机：{mobile or '—'}"],
            "sale_report_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/report/create"
    payload = _compact({
        "customer_id": customer_id, "project_id": project_id,
        "customer_name": customer_name, "mobile": mobile,
        "report_time": report_time, "broker_id": broker_id, "channel_id": channel_id,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "报备创建成功", [f"客户 #{customer_id} 已报备至楼盘 #{project_id}"])


def sale_report_list(page: int = 1, page_size: int = 20,
                     customer_id: int = None, project_id: int = None):
    """
    分页查询报备列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param customer_id: 客户ID（可选）
    :param project_id: 楼盘ID（可选）
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/report/list"
    params = _compact({"page": page, "page_size": page_size,
                       "customer_id": customer_id, "project_id": project_id})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "报备列表", empty_hint="没有查到符合条件的报备。")


def sale_visit_confirm(report_id: int = None, visit_time: str = None,
                       visit_type: str = None, receive_user_id: int = None,
                       confirmed: bool = False):
    """
    确认到访（json body 参数）—— 缺必填→引导；未确认→确认；confirmed=True→执行。
    :param report_id: 报备ID（必填，路径参数）
    :param visit_time: 到访时间
    :param visit_type: 到访类型（首次到访/多次到访，默认首次到访）
    :param receive_user_id: 接待销售ID
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not report_id:
        return _need_input("确认到访", ["report_id"], "sale_visit_confirm(report_id, ...)")
    if not confirmed:
        return _need_confirm(f"确认到访 · 报备 #{report_id}",
                             [f"🚶 报备 #{report_id} 到访确认",
                              f"⏰ 时间：{visit_time or '默认当前'}    类型：{visit_type or '首次到访'}"],
                             "sale_visit_confirm(report_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/visit/confirm/{report_id}"
    payload = _compact({
        "visit_time": visit_time, "visit_type": visit_type,
        "receive_user_id": receive_user_id,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "到访确认成功", [f"报备 #{report_id} 的到访已确认"])


def sale_visit_list(page: int = 1, page_size: int = 20,
                    customer_id: int = None, project_id: int = None):
    """
    分页查询到访列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param customer_id: 客户ID（可选）
    :param project_id: 楼盘ID（可选）
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/visit/list"
    params = _compact({"page": page, "page_size": page_size,
                       "customer_id": customer_id, "project_id": project_id})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "到访列表", empty_hint="没有查到符合条件的到访记录。")


def sale_follow_create(customer_id: int = None, follow_method: str = None,
                       follow_content: str = None, follow_time: str = None,
                       customer_intention: str = None, next_follow_time: str = None,
                       confirmed: bool = False):
    """
    创建跟进记录（json body 参数）—— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param follow_method: 跟进方式（必填：电话/微信/面谈/短信）
    :param follow_content: 跟进内容（必填）
    :param follow_time: 跟进时间
    :param customer_intention: 客户意向度
    :param next_follow_time: 下次跟进时间
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("customer_id", customer_id), ("follow_method", follow_method),
                              ("follow_content", follow_content)) if not v]
    if missing:
        return _need_input("创建跟进记录", missing,
                           "sale_follow_create(customer_id, follow_method, follow_content, ...)")
    if not confirmed:
        return _need_confirm(
            "创建跟进记录",
            [f"📇 客户 #{customer_id} · 方式：{follow_method}",
             f"📝 内容：{follow_content}"],
            "sale_follow_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/follow/create"
    payload = _compact({
        "customer_id": customer_id, "follow_method": follow_method,
        "follow_time": follow_time, "follow_content": follow_content,
        "customer_intention": customer_intention, "next_follow_time": next_follow_time,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "跟进记录创建成功", [f"客户 #{customer_id} 的跟进记录已创建"])


def sale_follow_list(customer_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询跟进记录列表，返回 Markdown 表格。
    :param customer_id: 客户ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/follow/list"
    params = _compact({"customer_id": customer_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "跟进记录列表", empty_hint="没有查到符合条件的跟进记录。")


def sale_sea_add(customer_id: int = None, confirmed: bool = False):
    """
    添加客户到公海（json body 参数）—— 未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not customer_id:
        return _need_input("添加客户到公海", ["customer_id"], "sale_sea_add(customer_id)")
    if not confirmed:
        return _need_confirm(f"添加客户到公海 · #{customer_id}",
                             [f"🌊 即将将客户 #{customer_id} 放入公海"],
                             "sale_sea_add(customer_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/sea/add"
    payload = _compact({"customer_id": customer_id})
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "已加入公海", [f"客户 #{customer_id} 已放入公海"])


def sale_sea_pick(customer_id: int = None, confirmed: bool = False):
    """
    从公海认领客户（json body 参数）—— 未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not customer_id:
        return _need_input("认领公海客户", ["customer_id"], "sale_sea_pick(customer_id)")
    if not confirmed:
        return _need_confirm(f"认领公海客户 · #{customer_id}",
                             [f"🙌 即将从公海认领客户 #{customer_id}"],
                             "sale_sea_pick(customer_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/sea/pick"
    payload = _compact({"customer_id": customer_id})
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "认领成功", [f"客户 #{customer_id} 已认领"])


def sale_sea_list(page: int = 1, page_size: int = 20):
    """
    分页查询公海客户列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_CUSTOMER}/sea/list"
    params = _compact({"page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "公海客户列表", empty_hint="公海暂无客户。")


# ===================== 认购签约交易模块（/api/sale/transaction）=====================
def sale_subscribe_create(customer_id: int = None, house_id: int = None,
                          subscribe_amount: float = None, deposit_amount: float = None,
                          discount_amount: float = None, subscribe_date: str = None,
                          sign_user_id: int = None, remark: str = None,
                          confirmed: bool = False):
    """
    创建认购单 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param customer_id: 客户ID（必填）
    :param house_id: 房源ID（必填）
    :param subscribe_amount: 认购金额（必填）
    :param deposit_amount: 定金金额（必填）
    :param discount_amount: 优惠金额（默认0）
    :param subscribe_date: 认购日期
    :param sign_user_id: 签约人ID
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not customer_id:
        missing.append("customer_id")
    if not house_id:
        missing.append("house_id")
    if subscribe_amount is None:
        missing.append("subscribe_amount")
    if deposit_amount is None:
        missing.append("deposit_amount")
    if missing:
        return _need_input("创建认购单", missing,
                           "sale_subscribe_create(customer_id, house_id, subscribe_amount, deposit_amount, ...)")
    if not confirmed:
        return _need_confirm(
            "创建认购单",
            [f"🧾 客户 #{customer_id} 认购房源 #{house_id}",
             f"💰 认购金额：{subscribe_amount}    定金：{deposit_amount}"],
            "sale_subscribe_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/subscribe/create"
    payload = _compact({
        "customer_id": customer_id, "house_id": house_id,
        "subscribe_amount": subscribe_amount, "deposit_amount": deposit_amount,
        "discount_amount": discount_amount, "subscribe_date": subscribe_date,
        "sign_user_id": sign_user_id, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "认购单创建成功", [f"客户 #{customer_id} 认购房源 #{house_id} 已创建"])


def sale_subscribe_list(page: int = 1, page_size: int = 20,
                        project_id: int = None, customer_id: int = None,
                        subscribe_status: int = None):
    """
    分页查询认购单列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param customer_id: 客户ID（可选）
    :param subscribe_status: 认购状态（可选）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/subscribe/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "customer_id": customer_id, "subscribe_status": subscribe_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "认购单列表", empty_hint="没有查到符合条件的认购单。")


def sale_subscribe_detail(subscribe_id: int):
    """
    查询认购单详情，返回键/值 Markdown 表格。
    :param subscribe_id: 认购ID
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/subscribe/detail/{subscribe_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"认购单详情 · #{subscribe_id}", empty_hint="未找到该认购单。")


def sale_subscribe_update(subscribe_id: int, subscribe_amount: float = None,
                          deposit_amount: float = None, discount_amount: float = None,
                          sign_user_id: int = None, remark: str = None,
                          confirmed: bool = False):
    """
    更新认购单 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param subscribe_id: 认购ID（必填）
    :param subscribe_amount: 认购金额
    :param deposit_amount: 定金金额
    :param discount_amount: 优惠金额
    :param sign_user_id: 签约人ID
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not subscribe_id:
        return _need_input("更新认购单", ["subscribe_id"], "sale_subscribe_update(subscribe_id, ...)")
    payload = _compact({
        "subscribe_amount": subscribe_amount, "deposit_amount": deposit_amount,
        "discount_amount": discount_amount, "sign_user_id": sign_user_id, "remark": remark,
    })
    if not payload:
        return _need_input("更新认购单（未提供任何要修改的字段）",
                           ["subscribe_amount/deposit_amount/... 至少一项"],
                           "sale_subscribe_update(subscribe_id, subscribe_amount=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新认购单 · #{subscribe_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_subscribe_update(subscribe_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/subscribe/update/{subscribe_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "认购单更新成功", [f"认购单 #{subscribe_id} 的信息已更新"])


def sale_subscribe_cancel(subscribe_id: int = None, cancel_reason: str = None,
                          confirmed: bool = False):
    """
    取消认购单（POST + query 参数）—— 高危操作：缺必填→引导；未确认→确认；confirmed=True→执行。
    :param subscribe_id: 认购ID（必填，路径参数）
    :param cancel_reason: 取消原因（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("subscribe_id", subscribe_id), ("cancel_reason", cancel_reason)) if not v]
    if missing:
        return _need_input("取消认购单", missing, "sale_subscribe_cancel(subscribe_id, cancel_reason)")
    if not confirmed:
        return _need_confirm(f"取消认购单 · #{subscribe_id}",
                             [f"🗑️ 即将取消认购单 #{subscribe_id}", f"原因：{cancel_reason}"],
                             "sale_subscribe_cancel(subscribe_id, cancel_reason, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/subscribe/cancel/{subscribe_id}"
    params = _compact({"cancel_reason": cancel_reason})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "认购单已取消", [f"认购单 #{subscribe_id} 已取消"])


def sale_contract_create(subscribe_id: int = None, contract_no: str = None,
                         contract_amount: float = None, contract_date: str = None,
                         sale_user_id: int = None, confirmed: bool = False):
    """
    创建签约合同 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param subscribe_id: 认购单ID（必填，路径参数）
    :param contract_no: 合同编号（必填）
    :param contract_amount: 签约金额（必填）
    :param contract_date: 签约日期（必填）
    :param sale_user_id: 销售ID
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not subscribe_id:
        missing.append("subscribe_id")
    if not contract_no:
        missing.append("contract_no")
    if contract_amount is None:
        missing.append("contract_amount")
    if not contract_date:
        missing.append("contract_date")
    if missing:
        return _need_input("创建签约合同", missing,
                           "sale_contract_create(subscribe_id, contract_no, contract_amount, contract_date, ...)")
    if not confirmed:
        return _need_confirm(
            "创建签约合同",
            [f"📄 合同号：{contract_no}（认购单 #{subscribe_id}）",
             f"💰 签约金额：{contract_amount}    日期：{contract_date}"],
            "sale_contract_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/contract/create/{subscribe_id}"
    payload = _compact({
        "subscribe_id": subscribe_id, "contract_no": contract_no,
        "contract_amount": contract_amount, "contract_date": contract_date,
        "sale_user_id": sale_user_id,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "合同创建成功", [f"📄 合同 {contract_no} 已创建"])


def sale_contract_list(page: int = 1, page_size: int = 20,
                       project_id: int = None, customer_id: int = None,
                       contract_status: int = None):
    """
    分页查询签约合同列表，返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param customer_id: 客户ID（可选）
    :param contract_status: 合同状态（可选）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/contract/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "customer_id": customer_id, "contract_status": contract_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "签约合同列表", empty_hint="没有查到符合条件的合同。")


def sale_contract_detail(contract_id: int):
    """
    查询签约合同详情，返回键/值 Markdown 表格。
    :param contract_id: 合同ID
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/contract/detail/{contract_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"合同详情 · #{contract_id}", empty_hint="未找到该合同。")


def sale_contract_update(contract_id: int, contract_amount: float = None,
                         contract_date: str = None, sale_user_id: int = None,
                         confirmed: bool = False):
    """
    更新签约合同 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param contract_id: 合同ID（必填）
    :param contract_amount: 签约金额
    :param contract_date: 签约日期
    :param sale_user_id: 销售ID
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not contract_id:
        return _need_input("更新签约合同", ["contract_id"], "sale_contract_update(contract_id, ...)")
    payload = _compact({
        "contract_amount": contract_amount, "contract_date": contract_date,
        "sale_user_id": sale_user_id,
    })
    if not payload:
        return _need_input("更新签约合同（未提供任何要修改的字段）",
                           ["contract_amount/contract_date/sale_user_id 至少一项"],
                           "sale_contract_update(contract_id, contract_amount=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新签约合同 · #{contract_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_contract_update(contract_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/contract/update/{contract_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "合同更新成功", [f"合同 #{contract_id} 的信息已更新"])


def sale_contract_record(contract_id: int = None, record_date: str = None,
                         confirmed: bool = False):
    """
    合同备案（POST + query 参数）—— 缺必填→引导；未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填，路径参数）
    :param record_date: 备案日期（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("contract_id", contract_id), ("record_date", record_date)) if not v]
    if missing:
        return _need_input("合同备案", missing, "sale_contract_record(contract_id, record_date)")
    if not confirmed:
        return _need_confirm(f"合同备案 · #{contract_id}",
                             [f"📑 合同 #{contract_id} 备案日期：{record_date}"],
                             "sale_contract_record(contract_id, record_date, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/contract/record/{contract_id}"
    params = _compact({"record_date": record_date})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "合同备案成功", [f"合同 #{contract_id} 已于 {record_date} 备案"])


def sale_payment_create(contract_id: int = None, payment_type: str = None,
                        payment_amount: float = None, payment_date: str = None,
                        remark: str = None, confirmed: bool = False):
    """
    创建回款记录 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填）
    :param payment_type: 回款类型（必填：首付/按揭/尾款）
    :param payment_amount: 回款金额（必填）
    :param payment_date: 回款日期
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not contract_id:
        missing.append("contract_id")
    if not payment_type:
        missing.append("payment_type")
    if payment_amount is None:
        missing.append("payment_amount")
    if missing:
        return _need_input("创建回款记录", missing,
                           "sale_payment_create(contract_id, payment_type, payment_amount, ...)")
    if not confirmed:
        return _need_confirm(
            "创建回款记录",
            [f"💵 合同 #{contract_id} · 类型：{payment_type}    金额：{payment_amount}"],
            "sale_payment_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/payment/create"
    payload = _compact({
        "contract_id": contract_id, "payment_type": payment_type,
        "payment_amount": payment_amount, "payment_date": payment_date,
        "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "回款记录创建成功", [f"合同 #{contract_id} 的回款记录已创建"])


def sale_payment_list(contract_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询回款记录列表，返回 Markdown 表格。
    :param contract_id: 合同ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/payment/list"
    params = _compact({"contract_id": contract_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "回款记录列表", empty_hint="没有查到符合条件的回款记录。")


def sale_payment_update(payment_id: int, payment_type: str = None,
                        payment_amount: float = None, payment_date: str = None,
                        remark: str = None, confirmed: bool = False):
    """
    更新回款记录 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param payment_id: 回款ID（必填）
    :param payment_type: 回款类型
    :param payment_amount: 回款金额
    :param payment_date: 回款日期
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not payment_id:
        return _need_input("更新回款记录", ["payment_id"], "sale_payment_update(payment_id, ...)")
    payload = _compact({
        "payment_type": payment_type, "payment_amount": payment_amount,
        "payment_date": payment_date, "remark": remark,
    })
    if not payload:
        return _need_input("更新回款记录（未提供任何要修改的字段）",
                           ["payment_type/payment_amount/... 至少一项"],
                           "sale_payment_update(payment_id, payment_type=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新回款记录 · #{payment_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_payment_update(payment_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/payment/update/{payment_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "回款记录更新成功", [f"回款记录 #{payment_id} 的信息已更新"])


def sale_payment_confirm(payment_id: int, confirmed: bool = False):
    """
    确认回款 —— 未确认→确认；confirmed=True→执行。
    :param payment_id: 回款ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not payment_id:
        return _need_input("确认回款", ["payment_id"], "sale_payment_confirm(payment_id)")
    if not confirmed:
        return _need_confirm(f"确认回款 · #{payment_id}",
                             [f"✅ 即将确认回款 #{payment_id}"],
                             "sale_payment_confirm(payment_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/payment/confirm/{payment_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "回款确认成功", [f"回款 #{payment_id} 已确认"])


def sale_loan_create(contract_id: int = None, loan_bank: str = None,
                     loan_amount: float = None, loan_rate: float = None,
                     loan_period: int = None, loan_type: str = None,
                     loan_status: int = None, remark: str = None,
                     confirmed: bool = False):
    """
    创建贷款记录 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填）
    :param loan_bank: 贷款银行（必填）
    :param loan_amount: 贷款金额（必填）
    :param loan_rate: 贷款利率%
    :param loan_period: 贷款期限月
    :param loan_type: 贷款类型（商业贷款/公积金贷款/组合贷款，默认商业贷款）
    :param loan_status: 贷款状态：1-申请中 2-已批贷 3-已放款 4-已结清（默认1）
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not contract_id:
        missing.append("contract_id")
    if not loan_bank:
        missing.append("loan_bank")
    if loan_amount is None:
        missing.append("loan_amount")
    if missing:
        return _need_input("创建贷款记录", missing,
                           "sale_loan_create(contract_id, loan_bank, loan_amount, ...)")
    if not confirmed:
        return _need_confirm(
            "创建贷款记录",
            [f"🏦 合同 #{contract_id} · 银行：{loan_bank}    金额：{loan_amount}"],
            "sale_loan_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/loan/create"
    payload = _compact({
        "contract_id": contract_id, "loan_bank": loan_bank, "loan_amount": loan_amount,
        "loan_rate": loan_rate, "loan_period": loan_period, "loan_type": loan_type,
        "loan_status": loan_status, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "贷款记录创建成功", [f"合同 #{contract_id} 的贷款记录已创建"])


def sale_loan_list(contract_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询贷款记录列表，返回 Markdown 表格。
    :param contract_id: 合同ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/loan/list"
    params = _compact({"contract_id": contract_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "贷款记录列表", empty_hint="没有查到符合条件的贷款记录。")


def sale_loan_update(loan_id: int, loan_bank: str = None, loan_amount: float = None,
                     loan_rate: float = None, loan_period: int = None,
                     loan_type: str = None, loan_status: int = None,
                     remark: str = None, confirmed: bool = False):
    """
    更新贷款记录 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param loan_id: 贷款ID（必填）
    :param loan_bank: 贷款银行
    :param loan_amount: 贷款金额
    :param loan_rate: 贷款利率
    :param loan_period: 贷款期限月
    :param loan_type: 贷款类型
    :param loan_status: 贷款状态
    :param remark: 备注
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not loan_id:
        return _need_input("更新贷款记录", ["loan_id"], "sale_loan_update(loan_id, ...)")
    payload = _compact({
        "loan_bank": loan_bank, "loan_amount": loan_amount, "loan_rate": loan_rate,
        "loan_period": loan_period, "loan_type": loan_type, "loan_status": loan_status,
        "remark": remark,
    })
    if not payload:
        return _need_input("更新贷款记录（未提供任何要修改的字段）",
                           ["loan_bank/loan_amount/loan_status/... 至少一项"],
                           "sale_loan_update(loan_id, loan_bank=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新贷款记录 · #{loan_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_loan_update(loan_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/loan/update/{loan_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "贷款记录更新成功", [f"贷款记录 #{loan_id} 的信息已更新"])


def sale_receipt_create(contract_id: int = None, receipt_type: str = None,
                        receipt_amount: float = None, receipt_status: int = None,
                        confirmed: bool = False):
    """
    创建发票记录 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填）
    :param receipt_type: 发票类型（必填：普通发票/专用发票）
    :param receipt_amount: 发票金额（必填）
    :param receipt_status: 发票状态：1-待开票 2-已开票 3-已作废（默认1）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not contract_id:
        missing.append("contract_id")
    if not receipt_type:
        missing.append("receipt_type")
    if receipt_amount is None:
        missing.append("receipt_amount")
    if missing:
        return _need_input("创建发票记录", missing,
                           "sale_receipt_create(contract_id, receipt_type, receipt_amount, ...)")
    if not confirmed:
        return _need_confirm(
            "创建发票记录",
            [f"🧾 合同 #{contract_id} · 类型：{receipt_type}    金额：{receipt_amount}"],
            "sale_receipt_create(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/receipt/create"
    payload = _compact({
        "contract_id": contract_id, "receipt_type": receipt_type,
        "receipt_amount": receipt_amount, "receipt_status": receipt_status,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "发票记录创建成功", [f"合同 #{contract_id} 的发票记录已创建"])


def sale_receipt_list(contract_id: int, page: int = 1, page_size: int = 20):
    """
    分页查询发票记录列表，返回 Markdown 表格。
    :param contract_id: 合同ID（必填）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/receipt/list"
    params = _compact({"contract_id": contract_id, "page": page, "page_size": page_size})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "发票记录列表", empty_hint="没有查到符合条件的发票记录。")


def sale_receipt_update(receipt_id: int, receipt_type: str = None,
                        receipt_amount: float = None, receipt_status: int = None,
                        confirmed: bool = False):
    """
    更新发票记录 —— 仅改动字段会展示确认摘要；confirmed=True→执行。
    :param receipt_id: 发票ID（必填）
    :param receipt_type: 发票类型
    :param receipt_amount: 发票金额
    :param receipt_status: 发票状态
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not receipt_id:
        return _need_input("更新发票记录", ["receipt_id"], "sale_receipt_update(receipt_id, ...)")
    payload = _compact({
        "receipt_type": receipt_type, "receipt_amount": receipt_amount,
        "receipt_status": receipt_status,
    })
    if not payload:
        return _need_input("更新发票记录（未提供任何要修改的字段）",
                           ["receipt_type/receipt_amount/receipt_status 至少一项"],
                           "sale_receipt_update(receipt_id, receipt_type=..., ...)")
    if not confirmed:
        return _need_confirm(f"更新发票记录 · #{receipt_id}",
                             [f"✏️ {k} → {v}" for k, v in payload.items()],
                             "sale_receipt_update(receipt_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/receipt/update/{receipt_id}"
    res = authenticated_request("PUT", url, json=payload)
    return _beautify_mutation(res, "发票记录更新成功", [f"发票记录 #{receipt_id} 的信息已更新"])


def sale_receipt_status_update(receipt_id: int = None, new_status: int = None,
                               confirmed: bool = False):
    """
    更新发票状态（PUT + query 参数）—— 缺必填→引导；未确认→确认；confirmed=True→执行。
    :param receipt_id: 发票ID（必填，路径参数）
    :param new_status: 新状态（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not receipt_id:
        missing.append("receipt_id")
    if new_status is None:
        missing.append("new_status")
    if missing:
        return _need_input("更新发票状态", missing,
                           "sale_receipt_status_update(receipt_id, new_status)")
    if not confirmed:
        return _need_confirm(f"更新发票状态 · #{receipt_id}",
                             [f"🔁 发票 #{receipt_id} 状态 → {new_status}"],
                             "sale_receipt_status_update(receipt_id, new_status, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/receipt/status/{receipt_id}"
    params = _compact({"new_status": new_status})
    res = authenticated_request("PUT", url, params=params)
    return _beautify_mutation(res, "发票状态更新成功", [f"发票 #{receipt_id} 状态已更新为 {new_status}"])


def sale_transaction_list(page: int = 1, page_size: int = 20, filters: dict = None):
    """
    获取交易综合列表（filters 为 body 参数），返回 Markdown 表格。
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param filters: 过滤条件（可选，dict，作为 body 透传）
    """
    url = f"{BASE_URL}{API_SALE_TRANSACTION}/transaction/list"
    kwargs = {"params": _compact({"page": page, "page_size": page_size})}
    if filters is not None:
        kwargs["json"] = filters
    res = authenticated_request("GET", url, **kwargs)
    return _beautify_query(res, "交易综合列表", empty_hint="没有查到符合条件的交易记录。")


# ===================== 分销渠道与佣金模块（/api/sale/commission）=====================
def sale_channel_create(channel_code: str = None, channel_name: str = None,
                        contact_person: str = None, contact_mobile: str = None,
                        channel_level: str = None, province: str = None, city: str = None,
                        district: str = None, address: str = None, start_date: str = None,
                        end_date: str = None, cooperation_status: int = None,
                        remark: str = None, confirmed: bool = False):
    """
    创建渠道公司 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param channel_code: 渠道编码（必填）
    :param channel_name: 渠道名称（必填）
    :param contact_person: 联系人（必填）
    :param contact_mobile: 联系电话（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("channel_code", channel_code), ("channel_name", channel_name),
                              ("contact_person", contact_person), ("contact_mobile", contact_mobile))
               if not v]
    if missing:
        return _need_input("创建渠道公司", missing,
                           "sale_channel_create(channel_code, channel_name, contact_person, contact_mobile)")
    if not confirmed:
        return _need_confirm(f"创建渠道公司 · {channel_name}",
                             [f"渠道编码：{channel_code}", f"渠道名称：{channel_name}",
                              f"联系人：{contact_person}", f"联系电话：{contact_mobile}"],
                             "sale_channel_create(..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/channel/create"
    payload = _compact({
        "channel_code": channel_code, "channel_name": channel_name,
        "contact_person": contact_person, "contact_mobile": contact_mobile,
        "channel_level": channel_level, "province": province, "city": city,
        "district": district, "address": address, "start_date": start_date,
        "end_date": end_date, "cooperation_status": cooperation_status, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "渠道公司创建成功", [f"渠道「{channel_name}」已创建"])


def sale_channel_list(page: int = 1, page_size: int = 20, channel_name: str = None,
                      cooperation_status: int = None):
    """分页查询渠道公司列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/channel/list"
    params = _compact({"page": page, "page_size": page_size,
                       "channel_name": channel_name, "cooperation_status": cooperation_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "渠道公司列表", empty_hint="没有查到符合条件的渠道公司。")


def sale_channel_detail(channel_id: int = None):
    """查询渠道公司详情，返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/channel/detail/{channel_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"渠道公司详情 · #{channel_id}", empty_hint="未查询到该渠道公司。")


def sale_channel_update(channel_id: int = None, channel_name: str = None,
                        contact_person: str = None, contact_mobile: str = None,
                        channel_level: str = None, address: str = None, end_date: str = None,
                        cooperation_status: int = None, remark: str = None,
                        confirmed: bool = False):
    """
    更新渠道公司 —— 缺 channel_id 或无改动→引导；有改动未确认→确认；confirmed=True→执行。
    :param channel_id: 渠道ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    changes = _compact({
        "channel_name": channel_name, "contact_person": contact_person,
        "contact_mobile": contact_mobile, "channel_level": channel_level,
        "address": address, "end_date": end_date,
        "cooperation_status": cooperation_status, "remark": remark,
    })
    if not channel_id:
        return _need_input("更新渠道公司", ["channel_id"], "sale_channel_update(channel_id, ...)")
    if not changes:
        return _need_input("更新渠道公司", ["至少一个待修改字段"],
                           "sale_channel_update(channel_id, channel_name/contact_person/...)")
    if not confirmed:
        return _need_confirm(f"更新渠道公司 · #{channel_id}",
                             [f"{k}：{v}" for k, v in changes.items()],
                             "sale_channel_update(channel_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/channel/update/{channel_id}"
    res = authenticated_request("PUT", url, json=changes)
    return _beautify_mutation(res, "渠道公司更新成功", [f"渠道 #{channel_id} 已更新"])


def sale_channel_terminate(channel_id: int = None, confirmed: bool = False):
    """
    终止渠道合作（POST）—— 高危操作：缺 channel_id→引导；未确认→确认；confirmed=True→执行。
    :param channel_id: 渠道ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not channel_id:
        return _need_input("终止渠道合作", ["channel_id"], "sale_channel_terminate(channel_id)")
    if not confirmed:
        return _need_confirm(f"终止渠道合作 · #{channel_id}",
                             [f"🗑️ 即将终止渠道 #{channel_id} 的合作关系"],
                             "sale_channel_terminate(channel_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_COMMISSION}/channel/terminate/{channel_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "渠道合作已终止", [f"渠道 #{channel_id} 合作已终止"])


def sale_broker_create(channel_id: int = None, broker_code: str = None,
                       broker_name: str = None, mobile: str = None, id_card: str = None,
                       gender: int = None, broker_level: str = None,
                       commission_rate: float = None, work_status: int = None,
                       entry_date: str = None, remark: str = None, confirmed: bool = False):
    """
    创建经纪人 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param channel_id: 渠道公司ID（必填）
    :param broker_code: 经纪人编码（必填）
    :param broker_name: 经纪人姓名（必填）
    :param mobile: 手机号（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("channel_id", channel_id), ("broker_code", broker_code),
                              ("broker_name", broker_name), ("mobile", mobile)) if not v]
    if missing:
        return _need_input("创建经纪人", missing,
                           "sale_broker_create(channel_id, broker_code, broker_name, mobile)")
    if not confirmed:
        return _need_confirm(f"创建经纪人 · {broker_name}",
                             [f"渠道公司ID：{channel_id}", f"经纪人编码：{broker_code}",
                              f"经纪人姓名：{broker_name}", f"手机号：{mobile}"],
                             "sale_broker_create(..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/broker/create"
    payload = _compact({
        "channel_id": channel_id, "broker_code": broker_code, "broker_name": broker_name,
        "mobile": mobile, "id_card": id_card, "gender": gender, "broker_level": broker_level,
        "commission_rate": commission_rate, "work_status": work_status,
        "entry_date": entry_date, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "经纪人创建成功", [f"经纪人「{broker_name}」已创建"])


def sale_broker_list(page: int = 1, page_size: int = 20, broker_name: str = None,
                     channel_id: int = None, work_status: int = None):
    """分页查询经纪人列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/broker/list"
    params = _compact({"page": page, "page_size": page_size, "broker_name": broker_name,
                       "channel_id": channel_id, "work_status": work_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "经纪人列表", empty_hint="没有查到符合条件的经纪人。")


def sale_broker_detail(broker_id: int = None):
    """查询经纪人详情，返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/broker/detail/{broker_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"经纪人详情 · #{broker_id}", empty_hint="未查询到该经纪人。")


def sale_broker_update(broker_id: int = None, broker_name: str = None, mobile: str = None,
                       id_card: str = None, gender: int = None, broker_level: str = None,
                       commission_rate: float = None, work_status: int = None,
                       remark: str = None, confirmed: bool = False):
    """
    更新经纪人 —— 缺 broker_id 或无改动→引导；有改动未确认→确认；confirmed=True→执行。
    :param broker_id: 经纪人ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    changes = _compact({
        "broker_name": broker_name, "mobile": mobile, "id_card": id_card, "gender": gender,
        "broker_level": broker_level, "commission_rate": commission_rate,
        "work_status": work_status, "remark": remark,
    })
    if not broker_id:
        return _need_input("更新经纪人", ["broker_id"], "sale_broker_update(broker_id, ...)")
    if not changes:
        return _need_input("更新经纪人", ["至少一个待修改字段"],
                           "sale_broker_update(broker_id, broker_name/mobile/...)")
    if not confirmed:
        return _need_confirm(f"更新经纪人 · #{broker_id}",
                             [f"{k}：{v}" for k, v in changes.items()],
                             "sale_broker_update(broker_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/broker/update/{broker_id}"
    res = authenticated_request("PUT", url, json=changes)
    return _beautify_mutation(res, "经纪人更新成功", [f"经纪人 #{broker_id} 已更新"])


def sale_commission_rule_create(project_id: int = None, room_type: str = None,
                                commission_rate: float = None, commission_amount: float = None,
                                rule_level: int = None, rule_status: int = None,
                                effective_date: str = None, expire_date: str = None,
                                remark: str = None, confirmed: bool = False):
    """
    创建佣金规则（字段均可选，由后端按 project_id 是否为空判定全局/楼盘专属）——
    未确认→确认；confirmed=True→执行。
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not confirmed:
        summary = [f"{k}：{v}" for k, v in _compact({
            "project_id": project_id, "room_type": room_type,
            "commission_rate": commission_rate, "commission_amount": commission_amount,
        }).items()] or ["（全局默认佣金规则）"]
        return _need_confirm("创建佣金规则", summary,
                             "sale_commission_rule_create(..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/rule/create"
    payload = _compact({
        "project_id": project_id, "room_type": room_type, "commission_rate": commission_rate,
        "commission_amount": commission_amount, "rule_level": rule_level,
        "rule_status": rule_status, "effective_date": effective_date,
        "expire_date": expire_date, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "佣金规则创建成功", ["新佣金规则已创建"])


def sale_commission_rule_list(page: int = 1, page_size: int = 20, project_id: int = None,
                              rule_type: str = None, rule_status: int = None):
    """分页查询佣金规则列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/rule/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "rule_type": rule_type, "rule_status": rule_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "佣金规则列表", empty_hint="没有查到符合条件的佣金规则。")


def sale_commission_rule_update(rule_id: int = None, room_type: str = None,
                                commission_rate: float = None, commission_amount: float = None,
                                rule_level: int = None, rule_status: int = None,
                                effective_date: str = None, expire_date: str = None,
                                remark: str = None, confirmed: bool = False):
    """
    更新佣金规则 —— 缺 rule_id 或无改动→引导；有改动未确认→确认；confirmed=True→执行。
    :param rule_id: 规则ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    changes = _compact({
        "room_type": room_type, "commission_rate": commission_rate,
        "commission_amount": commission_amount, "rule_level": rule_level,
        "rule_status": rule_status, "effective_date": effective_date,
        "expire_date": expire_date, "remark": remark,
    })
    if not rule_id:
        return _need_input("更新佣金规则", ["rule_id"], "sale_commission_rule_update(rule_id, ...)")
    if not changes:
        return _need_input("更新佣金规则", ["至少一个待修改字段"],
                           "sale_commission_rule_update(rule_id, commission_rate/...)")
    if not confirmed:
        return _need_confirm(f"更新佣金规则 · #{rule_id}",
                             [f"{k}：{v}" for k, v in changes.items()],
                             "sale_commission_rule_update(rule_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/rule/update/{rule_id}"
    res = authenticated_request("PUT", url, json=changes)
    return _beautify_mutation(res, "佣金规则更新成功", [f"佣金规则 #{rule_id} 已更新"])


def sale_bill_generate(contract_id: int = None, confirmed: bool = False):
    """
    生成佣金结算单（POST）—— 缺 contract_id→引导；未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not contract_id:
        return _need_input("生成佣金结算单", ["contract_id"], "sale_bill_generate(contract_id)")
    if not confirmed:
        return _need_confirm(f"生成佣金结算单 · 合同#{contract_id}",
                             [f"将为合同 #{contract_id} 生成佣金结算单"],
                             "sale_bill_generate(contract_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/bill/generate/{contract_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "佣金结算单已生成", [f"合同 #{contract_id} 的结算单已生成"])


def sale_bill_list(page: int = 1, page_size: int = 20, project_id: int = None,
                   channel_id: int = None, broker_id: int = None, bill_status: int = None):
    """分页查询佣金结算单列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_COMMISSION}/bill/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "channel_id": channel_id, "broker_id": broker_id, "bill_status": bill_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "佣金结算单列表", empty_hint="没有查到符合条件的结算单。")


def sale_bill_audit(bill_id: int = None, confirmed: bool = False):
    """
    审核佣金结算单（POST）—— 缺 bill_id→引导；未确认→确认；confirmed=True→执行。
    :param bill_id: 结算单ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not bill_id:
        return _need_input("审核佣金结算单", ["bill_id"], "sale_bill_audit(bill_id)")
    if not confirmed:
        return _need_confirm(f"审核佣金结算单 · #{bill_id}",
                             [f"将审核佣金结算单 #{bill_id}"],
                             "sale_bill_audit(bill_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_COMMISSION}/bill/audit/{bill_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "佣金结算单审核完成", [f"结算单 #{bill_id} 已审核"])


def sale_bill_freeze(bill_id: int = None, freeze_reason: str = None, confirmed: bool = False):
    """
    冻结佣金结算单（POST + query 参数）—— 高危操作：缺必填→引导；未确认→确认；confirmed=True→执行。
    :param bill_id: 结算单ID（必填，路径参数）
    :param freeze_reason: 冻结原因（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("bill_id", bill_id), ("freeze_reason", freeze_reason)) if not v]
    if missing:
        return _need_input("冻结佣金结算单", missing, "sale_bill_freeze(bill_id, freeze_reason)")
    if not confirmed:
        return _need_confirm(f"冻结佣金结算单 · #{bill_id}",
                             [f"🗑️ 即将冻结结算单 #{bill_id}", f"原因：{freeze_reason}"],
                             "sale_bill_freeze(bill_id, freeze_reason, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_COMMISSION}/bill/freeze/{bill_id}"
    params = _compact({"freeze_reason": freeze_reason})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "佣金结算单已冻结", [f"结算单 #{bill_id} 已冻结"])


# ===================== 销售业绩与考核模块（/api/sale/performance）=====================
def sale_team_create(team_code: str = None, team_name: str = None, parent_team_id: int = None,
                     leader_id: int = None, team_level: int = None, team_status: int = None,
                     remark: str = None, confirmed: bool = False):
    """
    创建销售团队 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param team_code: 团队编码（必填）
    :param team_name: 团队名称（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("team_code", team_code), ("team_name", team_name)) if not v]
    if missing:
        return _need_input("创建销售团队", missing, "sale_team_create(team_code, team_name)")
    if not confirmed:
        return _need_confirm(f"创建销售团队 · {team_name}",
                             [f"团队编码：{team_code}", f"团队名称：{team_name}"],
                             "sale_team_create(..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/create"
    payload = _compact({
        "team_code": team_code, "team_name": team_name, "parent_team_id": parent_team_id,
        "leader_id": leader_id, "team_level": team_level, "team_status": team_status,
        "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "销售团队创建成功", [f"团队「{team_name}」已创建"])


def sale_team_list(page: int = 1, page_size: int = 20, team_name: str = None,
                   team_level: int = None):
    """分页查询销售团队列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/list"
    params = _compact({"page": page, "page_size": page_size,
                       "team_name": team_name, "team_level": team_level})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "销售团队列表", empty_hint="没有查到符合条件的团队。")


def sale_team_detail(team_id: int = None):
    """查询销售团队详情，返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/detail/{team_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"销售团队详情 · #{team_id}", empty_hint="未查询到该团队。")


def sale_team_update(team_id: int = None, team_name: str = None, leader_id: int = None,
                     team_status: int = None, remark: str = None, confirmed: bool = False):
    """
    更新销售团队 —— 缺 team_id 或无改动→引导；有改动未确认→确认；confirmed=True→执行。
    :param team_id: 团队ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    changes = _compact({
        "team_name": team_name, "leader_id": leader_id,
        "team_status": team_status, "remark": remark,
    })
    if not team_id:
        return _need_input("更新销售团队", ["team_id"], "sale_team_update(team_id, ...)")
    if not changes:
        return _need_input("更新销售团队", ["至少一个待修改字段"],
                           "sale_team_update(team_id, team_name/leader_id/...)")
    if not confirmed:
        return _need_confirm(f"更新销售团队 · #{team_id}",
                             [f"{k}：{v}" for k, v in changes.items()],
                             "sale_team_update(team_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/update/{team_id}"
    res = authenticated_request("PUT", url, json=changes)
    return _beautify_mutation(res, "销售团队更新成功", [f"团队 #{team_id} 已更新"])


def sale_team_dissolve(team_id: int = None, confirmed: bool = False):
    """
    解散销售团队（POST）—— 高危操作：缺 team_id→引导；未确认→确认；confirmed=True→执行。
    :param team_id: 团队ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not team_id:
        return _need_input("解散销售团队", ["team_id"], "sale_team_dissolve(team_id)")
    if not confirmed:
        return _need_confirm(f"解散销售团队 · #{team_id}",
                             [f"🗑️ 即将解散团队 #{team_id}"],
                             "sale_team_dissolve(team_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/dissolve/{team_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "销售团队已解散", [f"团队 #{team_id} 已解散"])


def sale_team_member_add(team_id: int = None, user_id: int = None, member_role: str = None,
                         confirmed: bool = False):
    """
    添加团队成员（POST，body 为 {team_id,user_id,member_role}）——
    缺必填→引导；未确认→确认；confirmed=True→执行。
    :param team_id: 团队ID（必填）
    :param user_id: 用户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("team_id", team_id), ("user_id", user_id)) if not v]
    if missing:
        return _need_input("添加团队成员", missing, "sale_team_member_add(team_id, user_id)")
    if not confirmed:
        return _need_confirm(f"添加团队成员 · 团队#{team_id}",
                             [f"团队ID：{team_id}", f"用户ID：{user_id}",
                              f"成员角色：{member_role or 'member'}"],
                             "sale_team_member_add(team_id, user_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team/member/add"
    payload = _compact({"team_id": team_id, "user_id": user_id, "member_role": member_role})
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "团队成员添加成功", [f"用户 #{user_id} 已加入团队 #{team_id}"])


def sale_target_create(project_id: int = None, target_type: str = None, time_type: str = None,
                       target_amount: float = None, target_user_id: int = None,
                       target_team_id: int = None, time_value: str = None,
                       target_sets: int = None, target_status: int = None,
                       remark: str = None, confirmed: bool = False):
    """
    创建业绩目标 —— 缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param project_id: 楼盘ID（必填）
    :param target_type: 目标类型（必填：个人/团队）
    :param time_type: 时间类型（必填：年/季/月/周/日/自定义）
    :param target_amount: 目标金额（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("project_id", project_id), ("target_type", target_type),
                              ("time_type", time_type), ("target_amount", target_amount)) if not v]
    if missing:
        return _need_input("创建业绩目标", missing,
                           "sale_target_create(project_id, target_type, time_type, target_amount)")
    if not confirmed:
        return _need_confirm("创建业绩目标",
                             [f"楼盘ID：{project_id}", f"目标类型：{target_type}",
                              f"时间类型：{time_type}", f"目标金额：{target_amount}"],
                             "sale_target_create(..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/target/create"
    payload = _compact({
        "project_id": project_id, "target_type": target_type, "time_type": time_type,
        "target_amount": target_amount, "target_user_id": target_user_id,
        "target_team_id": target_team_id, "time_value": time_value,
        "target_sets": target_sets, "target_status": target_status, "remark": remark,
    })
    res = authenticated_request("POST", url, json=payload)
    return _beautify_mutation(res, "业绩目标创建成功", ["新业绩目标已创建"])


def sale_target_list(page: int = 1, page_size: int = 20, project_id: int = None,
                     target_type: str = None, target_status: int = None):
    """分页查询业绩目标列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/target/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "target_type": target_type, "target_status": target_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "业绩目标列表", empty_hint="没有查到符合条件的业绩目标。")


def sale_target_update(target_id: int = None, target_amount: float = None,
                       target_sets: int = None, target_status: int = None,
                       remark: str = None, confirmed: bool = False):
    """
    更新业绩目标 —— 缺 target_id 或无改动→引导；有改动未确认→确认；confirmed=True→执行。
    :param target_id: 目标ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    changes = _compact({
        "target_amount": target_amount, "target_sets": target_sets,
        "target_status": target_status, "remark": remark,
    })
    if not target_id:
        return _need_input("更新业绩目标", ["target_id"], "sale_target_update(target_id, ...)")
    if not changes:
        return _need_input("更新业绩目标", ["至少一个待修改字段"],
                           "sale_target_update(target_id, target_amount/...)")
    if not confirmed:
        return _need_confirm(f"更新业绩目标 · #{target_id}",
                             [f"{k}：{v}" for k, v in changes.items()],
                             "sale_target_update(target_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/target/update/{target_id}"
    res = authenticated_request("PUT", url, json=changes)
    return _beautify_mutation(res, "业绩目标更新成功", [f"业绩目标 #{target_id} 已更新"])


def sale_performance_personal(user_id: int = None, project_id: int = None,
                              time_type: str = "month", time_value: str = None):
    """获取个人销售业绩（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/personal"
    params = _compact({"user_id": user_id, "project_id": project_id,
                       "time_type": time_type, "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "个人销售业绩", empty_hint="暂无个人业绩数据。")


def sale_performance_team(team_id: int = None, project_id: int = None,
                          time_type: str = "month", time_value: str = None):
    """获取团队销售业绩（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/team"
    params = _compact({"team_id": team_id, "project_id": project_id,
                       "time_type": time_type, "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "团队销售业绩", empty_hint="暂无团队业绩数据。")


def sale_sales_commission_calculate(contract_id: int = None, confirmed: bool = False):
    """
    计算销售提成（POST）—— 缺 contract_id→引导；未确认→确认；confirmed=True→执行。
    :param contract_id: 合同ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not contract_id:
        return _need_input("计算销售提成", ["contract_id"],
                           "sale_sales_commission_calculate(contract_id)")
    if not confirmed:
        return _need_confirm(f"计算销售提成 · 合同#{contract_id}",
                             [f"将为合同 #{contract_id} 计算销售提成"],
                             "sale_sales_commission_calculate(contract_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/sales/commission/calculate/{contract_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "销售提成已计算", [f"合同 #{contract_id} 的销售提成已计算"])


def sale_sales_commission_list(page: int = 1, page_size: int = 20, project_id: int = None,
                               sale_user_id: int = None, commission_status: int = None):
    """分页查询销售提成列表，返回 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/sales/commission/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "sale_user_id": sale_user_id, "commission_status": commission_status})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "销售提成列表", empty_hint="没有查到符合条件的销售提成。")


def sale_sales_commission_audit(commission_id: int = None, confirmed: bool = False):
    """
    审核销售提成（POST）—— 缺 commission_id→引导；未确认→确认；confirmed=True→执行。
    :param commission_id: 提成ID（必填，路径参数）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not commission_id:
        return _need_input("审核销售提成", ["commission_id"],
                           "sale_sales_commission_audit(commission_id)")
    if not confirmed:
        return _need_confirm(f"审核销售提成 · #{commission_id}",
                             [f"将审核销售提成 #{commission_id}"],
                             "sale_sales_commission_audit(commission_id, confirmed=True)")
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/sales/commission/audit/{commission_id}"
    res = authenticated_request("POST", url)
    return _beautify_mutation(res, "销售提成审核完成", [f"提成 #{commission_id} 已审核"])


def sale_sales_commission_freeze(commission_id: int = None, freeze_reason: str = None,
                                 confirmed: bool = False):
    """
    冻结销售提成（POST + query 参数）—— 高危操作：缺必填→引导；未确认→确认；confirmed=True→执行。
    :param commission_id: 提成ID（必填，路径参数）
    :param freeze_reason: 冻结原因（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("commission_id", commission_id),
                              ("freeze_reason", freeze_reason)) if not v]
    if missing:
        return _need_input("冻结销售提成", missing,
                           "sale_sales_commission_freeze(commission_id, freeze_reason)")
    if not confirmed:
        return _need_confirm(f"冻结销售提成 · #{commission_id}",
                             [f"🗑️ 即将冻结提成 #{commission_id}", f"原因：{freeze_reason}"],
                             "sale_sales_commission_freeze(commission_id, freeze_reason, confirmed=True)",
                             warn=True)
    url = f"{BASE_URL}{API_SALE_PERFORMANCE}/sales/commission/freeze/{commission_id}"
    params = _compact({"freeze_reason": freeze_reason})
    res = authenticated_request("POST", url, params=params)
    return _beautify_mutation(res, "销售提成已冻结", [f"提成 #{commission_id} 已冻结"])


# ===================== 数据统计报表模块（/api/sale/statistics）=====================
def sale_statistics_overview(project_id: int = None):
    """获取项目总览统计-首页大屏，返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/overview/{project_id}"
    res = authenticated_request("GET", url)
    return _beautify_query(res, f"项目总览统计 · #{project_id}", empty_hint="暂无总览统计数据。")


def sale_statistics_project(project_id: int = None, time_type: str = "month",
                            time_value: str = None):
    """获取项目维度统计（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/project"
    params = _compact({"project_id": project_id, "time_type": time_type,
                       "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "项目维度统计", empty_hint="暂无项目维度统计数据。")


def sale_statistics_personal(user_id: int = None, project_id: int = None,
                             time_type: str = "month", time_value: str = None):
    """获取个人维度统计（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/personal"
    params = _compact({"user_id": user_id, "project_id": project_id,
                       "time_type": time_type, "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "个人维度统计", empty_hint="暂无个人维度统计数据。")


def sale_statistics_team(team_id: int = None, project_id: int = None,
                         time_type: str = "month", time_value: str = None):
    """获取团队维度统计（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/team"
    params = _compact({"team_id": team_id, "project_id": project_id,
                       "time_type": time_type, "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "团队维度统计", empty_hint="暂无团队维度统计数据。")


def sale_statistics_channel(channel_id: int = None, project_id: int = None,
                            time_type: str = "month", time_value: str = None):
    """获取渠道维度统计（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/channel"
    params = _compact({"channel_id": channel_id, "project_id": project_id,
                       "time_type": time_type, "time_value": time_value})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "渠道维度统计", empty_hint="暂无渠道维度统计数据。")


def sale_statistics_custom(project_id: int = None, start_date: str = None,
                           end_date: str = None):
    """获取自定义时段统计（参数走 query），返回键/值 Markdown 表格。"""
    url = f"{BASE_URL}{API_SALE_STATISTICS}/custom"
    params = _compact({"project_id": project_id, "start_date": start_date,
                       "end_date": end_date})
    res = authenticated_request("GET", url, params=params)
    return _beautify_query(res, "自定义时段统计", empty_hint="暂无自定义时段统计数据。")
