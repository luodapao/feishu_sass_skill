"""
admin/main.py —— 房产SaaS 租户管理技能入口

租户用户管理与角色管理，租户管理员使用。

- 认证：复用共享认证内核 auth_core（凭证共享同一 cred.json，由根 auth_core 统一管理），
  与 sale/finance 一致，不再内联重复认证逻辑。
- URL：BASE_URL + admin 私有接口常量（见 admin.config）。
- 返回：直接透传 authenticated_request 的原始响应（成功 code=0）。
"""
import os
import sys

# 将项目根加入搜索路径，确保 auth_core / 根 config / admin 包均可导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from auth_core import (
    load_cred, clear_cred,
    do_login, do_logout, do_refresh_token,
    do_change_password, get_login_user, authenticated_request
)
from config import BASE_URL  # noqa: F401
from admin.config import API_TENANT_USER, API_ROLE


# ===================== 展示辅助 =====================
def _mask_secret(secret: str) -> str:
    """密码脱敏展示：仅保留末位可见，其余以 * 代替，空值返回占位"""
    if not secret:
        return "（空）"
    if len(secret) <= 2:
        return "*" * len(secret)
    return "*" * (len(secret) - 1) + secret[-1]


def _current_account():
    """读取本地凭证中的登录账号/姓名，未登录返回 None"""
    cred = load_cred()
    if not cred or not cred.get("access_token"):
        return None
    info = cred.get("user_info", {}) or {}
    return info.get("account") or info.get("name") or info.get("username") or "当前用户"


def _need_confirm(title, summary_lines, confirm_call, warn=False):
    """
    生成「二次确认」结构化返回：展示将执行的操作摘要，请用户确认后再调用 confirm_call。
    :param title: 操作标题
    :param summary_lines: 摘要行列表（每行 "字段：值"）
    :param confirm_call: 提示用户确认后应调用的函数签名字符串
    :param warn: 是否为高危操作（删除类）
    """
    tip = "此操作不可恢复，" if warn else ""
    body = "\n".join(summary_lines)
    message = f"请确认操作 · {title}\n{body}\n{tip}确认无误后继续。\n（确认后请调用 {confirm_call}）"
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
    message = f"请补充信息 · {title}\n还需要以下必填信息：{fields_txt}\n（补齐后我会先与你确认，再执行；对应调用 {retry_call}）"
    return {
        "code": 4001,
        "message": message,
        "action": "need_input",
        "data": {"required_fields": required_fields, "next": retry_call},
    }


# ===================== 飞书互动卡片 =====================
def _result_card(title, subtitle, template, content):
    """
    构建结果展示卡片（仅展示，无交互回调）。
    :param title: 卡片标题
    :param subtitle: 副标题
    :param template: 头部配色模板（blue/red/green/turquoise/...）
    :param content: 内容行列表，每项 (字段名, 值)
    """
    columns = []
    for label, value in content:
        columns.append({
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**{label}**\n{value}"
                }
            ],
            "vertical_spacing": "8px",
            "horizontal_align": "left",
            "vertical_align": "top"
        })
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
            "template": template,
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "elements": [
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": columns
                }
            ]
        }
    }


def _input_form_card(title, subtitle, template, fields, submit_text, submit_action, cancel_text="取消"):
    """
    构建飞书输入表单卡片（通用）：支持多个输入字段，提交按钮回调，取消按钮清空表单。
    :param title: 卡片标题
    :param subtitle: 副标题
    :param template: 头部配色（blue/red/green/orange/...）
    :param fields: 字段列表，每项 {name, placeholder, element_id, required, default_value}
    :param submit_text: 提交按钮文本（如"登录"/"确认修改"）
    :param submit_action: 提交回调 action（如"tenant_login"/"tenant_change_password"）
    :param cancel_text: 取消按钮文本（默认"取消"）
    """
    input_elements = []
    for f in fields:
        input_elements.append({
            "tag": "input",
            "placeholder": {"tag": "plain_text", "content": f.get("placeholder", "")},
            "default_value": f.get("default_value", ""),
            "width": "fill",
            "required": f.get("required", True),
            "name": f["name"],
            "element_id": f["element_id"]
        })

    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
            "template": template,
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "horizontal_align": "left",
            "vertical_align": "top",
            "elements": [
                {
                    "tag": "form",
                    "name": f"{submit_action}_form",
                    "direction": "vertical",
                    "vertical_spacing": "8px",
                    "horizontal_align": "left",
                    "vertical_align": "top",
                    "padding": "12px 12px 12px 12px",
                    "elements": input_elements + [
                        {
                            "tag": "column_set",
                            "flex_mode": "flow",
                            "horizontal_spacing": "8px",
                            "horizontal_align": "left",
                            "columns": [
                                {
                                    "tag": "column",
                                    "width": "auto",
                                    "elements": [
                                        {
                                            "tag": "button",
                                            "text": {"tag": "plain_text", "content": submit_text},
                                            "type": "primary_filled",
                                            "width": "100px",
                                            "behaviors": [
                                                {
                                                    "type": "callback",
                                                    "value": {
                                                        "action": submit_action,
                                                    }
                                                }
                                            ],
                                            "form_action_type": "submit",
                                            "name": "submit_btn",
                                            "margin": "4px 42px 4px 0px",
                                            "element_id": f"{submit_action}_submit"
                                        }
                                    ],
                                    "vertical_spacing": "8px",
                                    "horizontal_align": "left",
                                    "vertical_align": "top"
                                },
                                {
                                    "tag": "column",
                                    "width": "auto",
                                    "elements": [
                                        {
                                            "tag": "button",
                                            "text": {"tag": "plain_text", "content": cancel_text},
                                            "type": "danger_filled",
                                            "width": "100px",
                                            "form_action_type": "reset",
                                            "name": "reset_btn",
                                            "margin": "4px 0px 4px 0px",
                                            "element_id": f"{submit_action}_reset"
                                        }
                                    ],
                                    "vertical_spacing": "8px",
                                    "horizontal_align": "left",
                                    "vertical_align": "top"
                                }
                            ],
                            "margin": "12px 0px 0px 0px"
                        }
                    ]
                }
            ]
        }
    }


# ===================== 认证接口（复用共享登录，凭证共享）=====================
def tenant_login(account: str = None, password: str = None):
    """
    租户用户登录（租户管理员和普通用户通用）。

    一次登录：
    1）已登录 → 返回友好提示，无需重复登录；
    2）未提供账号或密码 → 返回 action=need_login 附飞书登录表单卡片，
       用户填写账号密码后提交回调触发 tenant_login(account, password) 直接登录。

    :param account: 登录账号（可选；缺省时触发引导输入）
    :param password: 登录密码（可选；缺省时触发引导输入）
    """
    # 1) 已登录：友好提示，避免重复登录
    logged_in = _current_account()
    if logged_in:
        return {
            "code": 200,
            "message": f"当前已登录账号：{logged_in}\n如需切换账号，请先执行 tenant_logout 退出登录。",
            "action": "already_logged_in",
            "data": {"account": logged_in},
        }

    # 2) 缺少账号或密码：返回飞书登录表单卡片
    if not account or not password:
        return {
            "code": 4001,
            "message": "请通过卡片输入账号与密码",
            "action": "need_login",
            "card": _input_form_card(
                title="房产SaaS租户管理系统 · 登录",
                subtitle="请输入账号与密码",
                template="blue",
                fields=[
                    {"name": "account", "placeholder": "请输入登录账号", "element_id": "login_account", "required": True},
                    {"name": "password", "placeholder": "请输入登录密码", "element_id": "login_password", "required": True},
                ],
                submit_text="登录",
                submit_action="tenant_login",
            ),
            "data": {
                "required_fields": ["account", "password"],
                "next": "用户提交表单后调用 tenant_login(account, password) 直接登录",
            },
        }

    # 3) 账号密码齐全：直接执行登录，自动持久化 token 到共享 cred.json
    res = do_login(account, password)
    if res.get("code") == 200:
        user_info = (res.get("data") or {}).get("user_info", {}) or {}
        who = user_info.get("account") or user_info.get("name") or account
        res["message"] = f"登录成功\n欢迎回来，{who}！\n凭证已安全保存，现在可以开始使用系统。"
        res["action"] = "login_success"
        res["card"] = _result_card(
            title="登录成功",
            subtitle=f"欢迎回来，{who}！",
            template="blue",
            content=[
                ("登录账号", who),
                ("凭证状态", "已安全保存"),
                ("下一步", "现在可以开始使用系统"),
            ],
        )
        return res

    # 登录失败：给出友好且清晰的提示
    reason = res.get("message", "登录失败")
    res["message"] = f"登录失败\n原因：{reason}\n请核对账号与密码后重试。"
    res["action"] = "login_failed"
    res["card"] = _result_card(
        title="登录失败",
        subtitle="请核对账号与密码后重试",
        template="red",
        content=[
            ("登录账号", account),
            ("失败原因", reason),
            ("建议", "检查账号是否正确、密码是否输入有误"),
        ],
    )
    return res


def _logout_confirm_card(who):
    """构建登出确认卡片：展示当前账号与退出影响，确认/取消按钮回调触发 tenant_logout"""
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": "确认退出登录"},
            "subtitle": {"tag": "plain_text", "content": "退出后需重新登录才能继续使用"},
            "template": "orange",
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "elements": [
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": f"**当前登录账号**\n{who}"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": "**退出影响**\n本地凭证将被清除"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ]
                },
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "button",
                                    "text": {"tag": "plain_text", "content": "确认退出"},
                                    "type": "danger_filled",
                                    "width": "100px",
                                    "behaviors": [
                                        {
                                            "type": "callback",
                                            "value": {
                                                "action": "tenant_logout",
                                                "confirmed": True
                                            }
                                        }
                                    ],
                                    "name": "confirm_btn",
                                    "margin": "4px 42px 4px 0px",
                                    "element_id": "logout_confirm_btn"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "button",
                                    "text": {"tag": "plain_text", "content": "取消"},
                                    "type": "default_filled",
                                    "width": "100px",
                                    "behaviors": [
                                        {
                                            "type": "callback",
                                            "value": {
                                                "action": "tenant_logout_cancel",
                                                "confirmed": False
                                            }
                                        }
                                    ],
                                    "name": "cancel_btn",
                                    "margin": "4px 0px 4px 0px",
                                    "element_id": "logout_cancel_btn"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ],
                    "margin": "12px 0px 0px 0px"
                }
            ]
        }
    }


def tenant_logout(confirmed: bool = False):
    """
    登出：为避免误操作，先返回飞书确认卡片与用户确认，确认后调用后端登出接口并删除本地凭证。

    :param confirmed: 是否已获得用户确认。默认 False：
        - False → 返回 action=need_confirm 附飞书确认卡片（确认退出/取消），
                  用户点选确认后回调触发 tenant_logout(confirmed=True)；
        - True  → 执行真正的登出，并礼貌地输出退出信息。
    """
    who = _current_account()

    # 本地无凭证：礼貌告知，无需再确认
    if not who:
        clear_cred()
        return {
            "code": 200,
            "message": "未处于登录状态\n本地暂无登录凭证，无需退出。\n如需使用系统，请先执行 tenant_login 登录。",
            "action": "not_logged_in",
            "card": _result_card(
                title="未处于登录状态",
                subtitle="本地暂无登录凭证，无需退出",
                template="grey",
                content=[
                    ("当前状态", "未登录"),
                    ("建议", "如需使用系统，请先执行 tenant_login 登录"),
                ],
            ),
            "data": None,
        }

    # 未确认：返回飞书确认卡片
    if not confirmed:
        return {
            "code": 4002,
            "message": (
                f"确认退出登录\n"
                f"当前登录账号：{who}\n"
                f"退出后需重新登录才能继续使用系统。\n"
                f"确定要退出登录吗？"
            ),
            "action": "need_confirm",
            "card": _logout_confirm_card(who),
            "data": {
                "account": who,
                "next": "用户点选确认后调用 tenant_logout(confirmed=True)",
            },
        }

    # 已确认：执行登出，礼貌道别
    do_logout()
    return {
        "code": 200,
        "message": f"已安全退出登录\n{who}，您已成功退出登录。\n本地凭证已清除，感谢您的使用，期待下次再见！",
        "action": "logout_success",
        "card": _result_card(
            title="已安全退出登录",
            subtitle=f"{who}，您已成功退出登录",
            template="green",
            content=[
                ("账号", who),
                ("凭证状态", "已清除"),
                ("感谢", "感谢您的使用，期待下次再见！"),
            ],
        ),
        "data": None,
    }


def tenant_refresh_token():
    """使用refresh_token刷新access_token，自动更新本地文件"""
    return do_refresh_token()


def tenant_change_password(old_password: str = None, new_password: str = None):
    """
    修改当前登录账号密码
    :param old_password: 原始旧密码（可选，缺省时触发卡片输入）
    :param new_password: 设置的新密码（可选，缺省时触发卡片输入）
    """
    # 缺少旧密码或新密码：返回飞书输入表单卡片
    if not old_password or not new_password:
        return {
            "code": 4001,
            "message": "请通过卡片输入旧密码与新密码",
            "action": "need_input",
            "card": _input_form_card(
                title="修改登录密码",
                subtitle="请输入旧密码与新密码",
                template="blue",
                fields=[
                    {"name": "old_password", "placeholder": "请输入原始旧密码", "element_id": "change_old_pwd", "required": True},
                    {"name": "new_password", "placeholder": "请输入新密码", "element_id": "change_new_pwd", "required": True},
                ],
                submit_text="确认修改",
                submit_action="tenant_change_password",
                cancel_text="取消修改",
            ),
            "data": {
                "required_fields": ["old_password", "new_password"],
                "next": "用户提交表单后调用 tenant_change_password(old_password, new_password)",
            },
        }

    # 参数齐备：执行修改密码
    res = do_change_password(old_password, new_password)
    if isinstance(res, dict) and res.get("code") in (0, 200):
        res["message"] = "密码修改成功\n请使用新密码重新登录。"
        res["action"] = "change_password_success"
        res["card"] = _result_card(
            title="密码修改成功",
            subtitle="请使用新密码重新登录",
            template="green",
            content=[
                ("操作", "修改密码"),
                ("结果", "成功"),
                ("建议", "请使用新密码重新登录"),
            ],
        )
        return res

    # 修改失败：给出失败提示卡片
    reason = res.get("message", "密码修改失败") if isinstance(res, dict) else "密码修改失败"
    if isinstance(res, dict):
        res["message"] = f"密码修改失败\n原因：{reason}\n请核对旧密码后重试。"
        res["action"] = "change_password_failed"
        res["card"] = _result_card(
            title="密码修改失败",
            subtitle="请核对旧密码后重试",
            template="red",
            content=[
                ("失败原因", reason),
                ("建议", "检查旧密码是否正确"),
            ],
        )
    return res


def tenant_get_login_user():
    """获取当前登录用户信息"""
    return get_login_user()


# ===================== 租户用户管理（仅租户管理员）=====================
_USER_STATUS = {1: "正常", 2: "禁用", 3: "锁定", 4: "待审核"}
_USER_TYPE = {1: "内部用户", 2: "分销渠道后台管理员", 3: "外部经纪人"}
_ROLE_TYPE = {1: "系统角色", 2: "自定义角色"}
_ROLE_STATUS = {1: "正常", 2: "禁用"}


def _create_user_form_card():
    """构建创建租户用户表单卡片：必填项 account/name/password，可选项 mobile/email/remark"""
    return _input_form_card(
        title="创建租户用户",
        subtitle="带 * 为必填项，填写完成后点击创建",
        template="blue",
        fields=[
            {"name": "account", "placeholder": "请输入登录账号 *", "element_id": "cu_account", "required": True},
            {"name": "name", "placeholder": "请输入用户姓名 *", "element_id": "cu_name", "required": True},
            {"name": "password", "placeholder": "请输入登录密码 *", "element_id": "cu_password", "required": True},
            {"name": "mobile", "placeholder": "请输入手机号（可选）", "element_id": "cu_mobile", "required": False},
            {"name": "email", "placeholder": "请输入邮箱（可选）", "element_id": "cu_email", "required": False},
            {"name": "remark", "placeholder": "请输入备注（可选）", "element_id": "cu_remark", "required": False},
        ],
        submit_text="创建",
        submit_action="tenant_create_user",
    )


def _create_user_confirm_card(account, name, password, mobile, email, status, user_type):
    """构建创建用户确认卡片：展示待创建用户信息摘要，确认后回调触发 tenant_create_user(confirmed=True)"""
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": "确认创建租户用户"},
            "subtitle": {"tag": "plain_text", "content": "请核对以下信息后确认创建"},
            "template": "blue",
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "elements": [
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**姓名**\n{name}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**账号**\n{account}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ]
                },
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**密码**\n{_mask_secret(password)}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**手机**\n{mobile or '—'}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ]
                },
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**邮箱**\n{email or '—'}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {"tag": "markdown", "content": f"**状态 / 类型**\n{_USER_STATUS.get(status, status)} / {_USER_TYPE.get(user_type, user_type)}"}
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ]
                },
                {
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "horizontal_spacing": "8px",
                    "horizontal_align": "left",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "button",
                                    "text": {"tag": "plain_text", "content": "确认创建"},
                                    "type": "primary_filled",
                                    "width": "100px",
                                    "behaviors": [
                                        {
                                            "type": "callback",
                                            "value": {
                                                "action": "tenant_create_user",
                                                "confirmed": True
                                            }
                                        }
                                    ],
                                    "name": "confirm_btn",
                                    "margin": "4px 42px 4px 0px",
                                    "element_id": "cu_confirm_btn"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        },
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "button",
                                    "text": {"tag": "plain_text", "content": "取消"},
                                    "type": "default_filled",
                                    "width": "100px",
                                    "behaviors": [
                                        {
                                            "type": "callback",
                                            "value": {
                                                "action": "tenant_create_user_cancel",
                                                "confirmed": False
                                            }
                                        }
                                    ],
                                    "name": "cancel_btn",
                                    "margin": "4px 0px 4px 0px",
                                    "element_id": "cu_cancel_btn"
                                }
                            ],
                            "vertical_spacing": "8px",
                            "horizontal_align": "left",
                            "vertical_align": "top"
                        }
                    ],
                    "margin": "12px 0px 0px 0px"
                }
            ]
        }
    }


def tenant_create_user(account: str = None, name: str = None, password: str = None,
                       mobile: str = "", email: str = "", avatar: str = "",
                       dept_id: int = None, status: int = 1,
                       user_type: int = 1, remark: str = "", confirmed: bool = False):
    """
    创建租户用户（仅租户管理员）—— 飞书卡片交互：缺必填→表单卡片；齐备未确认→确认卡片；confirmed=True→执行。
    :param account: 登录账号（必填）
    :param name: 用户姓名（必填）
    :param password: 登录密码（必填）
    :param mobile: 手机号（可选）
    :param email: 邮箱（可选）
    :param avatar: 头像（可选）
    :param dept_id: 部门ID（可选）
    :param status: 状态：1-正常，2-禁用，3-锁定，4-待审核（默认1）
    :param user_type: 用户类型：1-内部用户，2-分销渠道后台管理员、3-外部经纪人（默认1）
    :param remark: 备注（可选）
    :param confirmed: 是否已获用户确认（默认False先返回确认卡片）
    """
    missing = [f for f, v in (("account", account), ("name", name), ("password", password)) if not v]
    if missing:
        return {
            "code": 4001,
            "message": "请通过卡片填写必填信息",
            "action": "need_input",
            "card": _create_user_form_card(),
            "data": {
                "required_fields": ["account", "name", "password"],
                "next": "用户提交表单后调用 tenant_create_user(account, name, password, ...)",
            },
        }
    if not confirmed:
        return {
            "code": 4002,
            "message": (
                f"请确认创建租户用户\n"
                f"  姓名：{name}\n"
                f"  账号：{account}\n"
                f"  密码：{_mask_secret(password)}\n"
                f"  手机：{mobile or '—'}    邮箱：{email or '—'}\n"
                f"  状态：{_USER_STATUS.get(status, status)}    类型：{_USER_TYPE.get(user_type, user_type)}"
            ),
            "action": "need_confirm",
            "card": _create_user_confirm_card(account, name, password, mobile, email, status, user_type),
            "data": {
                "account": account,
                "name": name,
                "next": "用户确认后调用 tenant_create_user(..., confirmed=True)",
            },
        }
    url = f"{BASE_URL}{API_TENANT_USER}"
    cred = load_cred()
    tenant_id = cred.get("user_info", {}).get("tenant_id") if cred else None
    payload = {
        "tenant_id": tenant_id,
        "account": account,
        "name": name,
        "password": password,
        "mobile": mobile or None,
        "email": email or None,
        "avatar": avatar or None,
        "dept_id": dept_id,
        "status": status,
        "user_type": user_type,
        "remark": remark or None
    }
    res = authenticated_request("POST", url, json=payload)
    if isinstance(res, dict) and res.get("code") == 0:
        res["message"] = f"用户创建成功\n{name}（账号 {account}）已创建"
        res["action"] = "create_success"
        res["card"] = _result_card(
            title="用户创建成功",
            subtitle=f"{name}（账号 {account}）已创建",
            template="green",
            content=[
                ("姓名", name),
                ("账号", account),
                ("状态", _USER_STATUS.get(status, status)),
            ],
        )
    return res


def _user_table_card(rows, meta=None, title="租户用户列表"):
    """构建用户列表展示卡片：把行列表渲染为多列 Markdown 展示卡片"""
    if not rows:
        return _result_card(
            title=title,
            subtitle="没有查到符合条件的用户",
            template="grey",
            content=[("提示", "没有查到符合条件的用户")],
        )

    # 取所有行键的并集（保序）
    cols = []
    for row in rows:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in cols:
                    cols.append(k)
    if not cols:
        cols = ["值"]

    # 构建表头行 + 数据行，渲染为 Markdown 表格
    header_cells = [f"**{c}**" for c in cols]
    header_md = "| " + " | ".join(header_cells) + " |"
    sep_md = "| " + " | ".join([":--"] * len(cols)) + " |"
    body_lines = [header_md, sep_md]
    for row in rows[:20]:
        if isinstance(row, dict):
            cells = []
            for c in cols:
                v = row.get(c)
                if v is None or v == "":
                    cells.append("—")
                elif isinstance(v, (dict, list)):
                    import json as _json
                    cells.append(str(_json.dumps(v, ensure_ascii=False)).replace("|", "\\|").replace("\n", " "))
                else:
                    cells.append(str(v).replace("|", "\\|").replace("\n", " "))
            body_lines.append("| " + " | ".join(cells) + " |")
        else:
            body_lines.append(f"| {str(row).replace('|', '\\|')} |")

    table_md = "\n".join(body_lines)
    footer = ""
    if len(rows) > 20:
        footer += f"\n\n> 仅展示前 20 条，共 {len(rows)} 条。"
    if meta:
        parts = []
        if meta.get("total") is not None:
            parts.append(f"总数 {meta['total']}")
        if meta.get("page") is not None:
            parts.append(f"第 {meta['page']} 页")
        if meta.get("size") is not None:
            parts.append(f"每页 {meta['size']}")
        if parts:
            footer += "\n\n> " + " · ".join(parts)

    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": f"共 {len(rows)} 条记录" if not meta else f"共 {meta.get('total', len(rows))} 条记录"},
            "template": "turquoise",
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "elements": [
                {"tag": "markdown", "content": table_md + footer}
            ]
        }
    }


def _user_detail_card(user):
    """构建用户详情回显卡片：键值对双栏展示"""
    if not isinstance(user, dict) or not user:
        return _result_card(
            title="用户详情",
            subtitle="未找到该用户",
            template="grey",
            content=[("提示", "未找到该用户")],
        )

    # 两两配对渲染为双栏
    items = list(user.items())
    columns = []
    i = 0
    while i < len(items):
        k1, v1 = items[i]
        col1 = {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [
                {"tag": "markdown", "content": f"**{k1}**\n{_fmt_card_val(v1)}"}
            ],
            "vertical_spacing": "8px",
            "horizontal_align": "left",
            "vertical_align": "top"
        }
        if i + 1 < len(items):
            k2, v2 = items[i + 1]
            col2 = {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {"tag": "markdown", "content": f"**{k2}**\n{_fmt_card_val(v2)}"}
                ],
                "vertical_spacing": "8px",
                "horizontal_align": "left",
                "vertical_align": "top"
            }
            columns.append(col1)
            columns.append(col2)
            i += 2
        else:
            columns.append(col1)
            i += 1

    # 每两列组成一个 column_set
    column_sets = []
    for j in range(0, len(columns), 2):
        set_cols = columns[j:j + 2]
        column_sets.append({
            "tag": "column_set",
            "flex_mode": "flow",
            "horizontal_spacing": "8px",
            "horizontal_align": "left",
            "columns": set_cols
        })

    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": "用户详情"},
            "subtitle": {"tag": "plain_text", "content": f"用户 #{user.get('id', user.get('user_id', '?'))}"},
            "template": "turquoise",
            "padding": "12px 8px 12px 8px"
        },
        "body": {
            "direction": "vertical",
            "horizontal_spacing": "8px",
            "vertical_spacing": "8px",
            "elements": column_sets
        }
    }


def _fmt_card_val(v):
    """把字段值渲染为卡片单元格文本（None/空转占位，dict/list 转 JSON）"""
    if v is None or v == "":
        return "—"
    if isinstance(v, (dict, list)):
        import json as _json
        return _json.dumps(v, ensure_ascii=False)
    if isinstance(v, int) and v in _USER_STATUS:
        return _USER_STATUS[v]
    if isinstance(v, int) and v in _USER_TYPE:
        return _USER_TYPE[v]
    return str(v)


def _extract_rows(data):
    """从后端 data 中提取「列表行」与「分页信息」"""
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict):
        for key in ("list", "items", "records", "rows", "data"):
            arr = data.get(key)
            if isinstance(arr, list):
                meta = {k: data.get(k) for k in ("total", "page", "size", "pages")
                        if data.get(k) is not None}
                return arr, meta
    return None, {}


def _update_user_form_card(user_id, current=None):
    """
    构建更新用户表单卡片：先回显当前用户信息（从后端查询），用户在表单中修改后提交。
    :param user_id: 用户ID
    :param current: 当前用户信息 dict（来自 tenant_get_user 查询），None 时不预填
    """
    cur = current or {}
    return _input_form_card(
        title=f"更新租户用户 · #{user_id}",
        subtitle="修改字段后点击确认修改（留空表示不修改）",
        template="blue",
        fields=[
            {"name": "name", "placeholder": "用户姓名", "element_id": "uu_name",
             "required": False, "default_value": cur.get("name", "")},
            {"name": "mobile", "placeholder": "手机号", "element_id": "uu_mobile",
             "required": False, "default_value": cur.get("mobile", "")},
            {"name": "email", "placeholder": "邮箱", "element_id": "uu_email",
             "required": False, "default_value": cur.get("email", "")},
            {"name": "status", "placeholder": "状态：1-正常，2-禁用，3-锁定，4-待审核",
             "element_id": "uu_status", "required": False,
             "default_value": str(cur.get("status", "")) if cur.get("status") is not None else ""},
            {"name": "user_type", "placeholder": "类型：1-内部，2-分销后台，3-外部经纪人",
             "element_id": "uu_user_type", "required": False,
             "default_value": str(cur.get("user_type", "")) if cur.get("user_type") is not None else ""},
            {"name": "remark", "placeholder": "备注", "element_id": "uu_remark",
             "required": False, "default_value": cur.get("remark", "")},
        ],
        submit_text="确认修改",
        submit_action="tenant_update_user",
        cancel_text="取消修改",
    )


def tenant_get_user_list(user_name: str = "", login_name: str = "",
                         status: int = None, page: int = 1, size: int = 10):
    """
    分页查询租户用户列表（仅租户管理员），返回飞书展示卡片（Markdown 表格）。
    :param user_name: 用户姓名（可选，用于搜索）
    :param login_name: 登录账号（可选，用于搜索）
    :param status: 状态（可选）
    :param page: 页码（默认1）
    :param size: 每页数量（默认10）
    """
    url = f"{BASE_URL}{API_TENANT_USER}"
    params = {
        "page": page,
        "size": size
    }
    if user_name:
        params["user_name"] = user_name
    if login_name:
        params["login_name"] = login_name
    if status is not None:
        params["status"] = status
    res = authenticated_request("GET", url, params=params)
    if isinstance(res, dict) and res.get("code") == 0:
        rows, meta = _extract_rows(res.get("data"))
        if rows is not None:
            res["action"] = "query_result"
            res["card"] = _user_table_card(rows, meta, title="租户用户列表")
            res["message"] = f"查询完成，共 {meta.get('total', len(rows) if rows else 0)} 条记录"
        else:
            res["action"] = "query_result"
            res["card"] = _user_table_card([], title="租户用户列表")
            res["message"] = "没有查到符合条件的用户"
    return res


def tenant_get_user(user_id: int):
    """
    查询租户用户详情（仅租户管理员），返回飞书展示卡片（键值对回显）。
    :param user_id: 用户ID
    """
    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}"
    res = authenticated_request("GET", url)
    if isinstance(res, dict) and res.get("code") == 0:
        data = res.get("data")
        if isinstance(data, dict):
            res["action"] = "query_result"
            res["card"] = _user_detail_card(data)
            res["message"] = f"用户 #{user_id} 详情"
        else:
            res["action"] = "query_result"
            res["card"] = _user_detail_card(None)
            res["message"] = "未找到该用户"
    return res


def tenant_update_user(user_id: int, name: str = "", mobile: str = "",
                       email: str = "", avatar: str = "", dept_id: int = None,
                       status: int = None, user_type: int = None, remark: str = "",
                       confirmed: bool = False):
    """
    更新租户用户（仅租户管理员）—— 飞书卡片交互：先回显当前用户信息（可编辑表单），confirmed=True 时执行更新。
    :param user_id: 用户ID（必填）
    :param name: 用户姓名（可选）
    :param mobile: 手机号（可选）
    :param email: 邮箱（可选）
    :param avatar: 头像（可选）
    :param dept_id: 部门ID（可选）
    :param status: 状态（可选）
    :param user_type: 用户类型（可选）
    :param remark: 备注（可选）
    :param confirmed: 是否已获用户确认（默认False先返回回显可编辑卡片）
    """
    # 缺 user_id：引导输入
    if not user_id:
        return {
            "code": 4001,
            "message": "请提供要更新的用户ID",
            "action": "need_input",
            "card": _result_card(
                title="更新租户用户",
                subtitle="请提供要更新的用户ID",
                template="orange",
                content=[("提示", "请提供 user_id 后重试")],
            ),
            "data": {
                "required_fields": ["user_id"],
                "next": "调用 tenant_update_user(user_id, ...) 回显当前信息",
            },
        }

    # 未确认：先查询当前用户信息，回显到可编辑表单卡片
    if not confirmed:
        # 尝试查询当前用户信息用于回显
        current = None
        try:
            detail_url = f"{BASE_URL}{API_TENANT_USER}/{user_id}"
            detail_res = authenticated_request("GET", detail_url)
            if isinstance(detail_res, dict) and detail_res.get("code") == 0:
                current = detail_res.get("data") if isinstance(detail_res.get("data"), dict) else None
        except Exception:
            pass

        return {
            "code": 4002,
            "message": f"请修改需要更新的字段后点击确认修改\n当前编辑用户 #{user_id}",
            "action": "need_confirm",
            "card": _update_user_form_card(user_id, current),
            "data": {
                "user_id": user_id,
                "current": current,
                "next": "用户修改字段后调用 tenant_update_user(user_id, name=..., confirmed=True)",
            },
        }

    # 已确认：收集非空字段执行更新
    payload = {}
    if name:
        payload["name"] = name
    if mobile:
        payload["mobile"] = mobile
    if email:
        payload["email"] = email
    if avatar:
        payload["avatar"] = avatar
    if dept_id is not None:
        payload["dept_id"] = dept_id
    if status is not None:
        payload["status"] = status
    if user_type is not None:
        payload["user_type"] = user_type
    if remark:
        payload["remark"] = remark
    if not payload:
        return {
            "code": 4001,
            "message": "未提供任何要修改的字段",
            "action": "need_input",
            "card": _result_card(
                title="更新租户用户",
                subtitle="未提供任何要修改的字段",
                template="orange",
                content=[
                    ("用户ID", str(user_id)),
                    ("提示", "请至少修改一个字段"),
                ],
            ),
            "data": {
                "required_fields": ["name/mobile/email/status/... 至少一项"],
                "next": "tenant_update_user(user_id, name=..., ...)",
            },
        }

    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}"
    res = authenticated_request("PUT", url, json=payload)
    if isinstance(res, dict) and res.get("code") == 0:
        changes = []
        for k, v in payload.items():
            if k == "status":
                v = _USER_STATUS.get(v, v)
            elif k == "user_type":
                v = _USER_TYPE.get(v, v)
            changes.append((k, v))
        res["message"] = f"用户更新成功\n用户 #{user_id} 的信息已更新"
        res["action"] = "update_success"
        res["card"] = _result_card(
            title="用户更新成功",
            subtitle=f"用户 #{user_id} 的信息已更新",
            template="green",
            content=changes,
        )
    return res


def tenant_delete_user(user_id: int, confirmed: bool = False):
    """
    删除租户用户（仅租户管理员）—— 高危操作，需二次确认。
    :param user_id: 用户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回删除确认提示）
    """
    if not user_id:
        return _need_input("删除租户用户", ["user_id"], "tenant_delete_user(user_id)")
    if not confirmed:
        return _need_confirm(f"删除租户用户 · #{user_id}",
                             [f"即将删除用户 #{user_id}"],
                             "tenant_delete_user(user_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}"
    return authenticated_request("DELETE", url)


def tenant_reset_user_password(user_id: int, new_password: str = None, confirmed: bool = False):
    """
    重置租户用户密码（仅租户管理员）—— 结构化交互：缺密码→引导；未确认→确认（脱敏）。
    :param user_id: 用户ID（必填）
    :param new_password: 新密码（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("user_id", user_id), ("new_password", new_password)) if not v]
    if missing:
        return _need_input("重置用户密码", missing,
                           "tenant_reset_user_password(user_id, new_password)")
    if not confirmed:
        return _need_confirm(f"重置用户密码 · #{user_id}",
                             [f"用户 #{user_id} 新密码：{_mask_secret(new_password)}"],
                             "tenant_reset_user_password(user_id, new_password, confirmed=True)")
    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}/reset-password"
    payload = {
        "new_password": new_password
    }
    return authenticated_request("PUT", url, json=payload)


def tenant_unlock_user(user_id: int, confirmed: bool = False):
    """
    解锁租户用户（仅租户管理员）—— 结构化交互：未确认→确认。
    :param user_id: 用户ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not user_id:
        return _need_input("解锁用户", ["user_id"], "tenant_unlock_user(user_id)")
    if not confirmed:
        return _need_confirm(f"解锁用户 · #{user_id}",
                             [f"即将解锁用户 #{user_id}"],
                             "tenant_unlock_user(user_id, confirmed=True)")
    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}/unlock"
    return authenticated_request("PUT", url)


def tenant_grant_user_role(user_id: int = None, role_ids: list = None, confirmed: bool = False):
    """
    给租户用户分配角色（仅租户管理员）—— 结构化交互：缺参→引导；未确认→确认。
    :param user_id: 用户ID（必填）
    :param role_ids: 角色ID列表（必填）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = []
    if not user_id:
        missing.append("user_id")
    if not role_ids:
        missing.append("role_ids")
    if missing:
        return _need_input("分配用户角色", missing,
                           "tenant_grant_user_role(user_id, role_ids)")
    if not confirmed:
        return _need_confirm(f"分配用户角色 · 用户 #{user_id}",
                             [f"角色ID：{', '.join(str(r) for r in role_ids)}"],
                             "tenant_grant_user_role(user_id, role_ids, confirmed=True)")
    url = f"{BASE_URL}{API_TENANT_USER}/{user_id}/grant-role"
    payload = {
        "role_ids": role_ids
    }
    return authenticated_request("POST", url, json=payload)


# ===================== 角色管理 =====================
def tenant_create_role(role_name: str = None, role_code: str = None,
                       role_type: int = 1, status: int = 1, remark: str = "",
                       confirmed: bool = False):
    """
    创建角色（仅租户管理员）—— 结构化交互：缺必填→引导；齐备未确认→确认；confirmed=True→执行。
    :param role_name: 角色名称（必填）
    :param role_code: 角色编码（必填）
    :param role_type: 角色类型：1-系统角色，2-自定义角色（默认1）
    :param status: 状态：1-正常，2-禁用（默认1）
    :param remark: 备注（可选）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    missing = [f for f, v in (("role_name", role_name), ("role_code", role_code)) if not v]
    if missing:
        return _need_input("创建角色", missing,
                           "tenant_create_role(role_name, role_code, ...)")
    if not confirmed:
        return _need_confirm(
            "创建角色",
            [
                f"名称：{role_name}",
                f"编码：{role_code}",
                f"类型：{_ROLE_TYPE.get(role_type, role_type)}    状态：{_ROLE_STATUS.get(status, status)}",
            ],
            "tenant_create_role(..., confirmed=True)",
        )
    url = f"{BASE_URL}{API_ROLE}"
    payload = {
        "role_name": role_name,
        "role_code": role_code,
        "role_type": role_type,
        "status": status,
        "remark": remark or None
    }
    return authenticated_request("POST", url, json=payload)


def tenant_get_role_list(role_name: str = "", status: int = None,
                         page: int = 1, size: int = 10):
    """
    分页查询角色列表。
    :param role_name: 角色名称（可选，用于搜索）
    :param status: 状态（可选）
    :param page: 页码（默认1）
    :param size: 每页数量（默认10）
    """
    url = f"{BASE_URL}{API_ROLE}"
    params = {
        "page": page,
        "size": size
    }
    if role_name:
        params["role_name"] = role_name
    if status is not None:
        params["status"] = status
    return authenticated_request("GET", url, params=params)


def tenant_get_role(role_id: int):
    """
    查询角色详情。
    :param role_id: 角色ID
    """
    url = f"{BASE_URL}{API_ROLE}/{role_id}"
    return authenticated_request("GET", url)


def tenant_update_role(role_id: int, role_name: str = "",
                       role_code: str = "", status: int = None, remark: str = "",
                       confirmed: bool = False):
    """
    更新角色（仅租户管理员）—— 结构化交互：仅改动字段会展示确认摘要。
    :param role_id: 角色ID（必填）
    :param role_name: 角色名称（可选）
    :param role_code: 角色编码（可选）
    :param status: 状态（可选）
    :param remark: 备注（可选）
    :param confirmed: 是否已获用户确认（默认False先返回确认提示）
    """
    if not role_id:
        return _need_input("更新角色", ["role_id"], "tenant_update_role(role_id, ...)")
    payload = {}
    if role_name:
        payload["role_name"] = role_name
    if role_code:
        payload["role_code"] = role_code
    if status is not None:
        payload["status"] = status
    if remark:
        payload["remark"] = remark
    if not payload:
        return _need_input("更新角色（未提供任何要修改的字段）",
                           ["role_name/role_code/status/remark 至少一项"],
                           "tenant_update_role(role_id, role_name=..., ...)")
    if not confirmed:
        changes = []
        for k, v in payload.items():
            if k == "status":
                v = _ROLE_STATUS.get(v, v)
            changes.append(f"{k} → {v}")
        return _need_confirm(f"更新角色 · #{role_id}", changes,
                             "tenant_update_role(role_id, ..., confirmed=True)")
    url = f"{BASE_URL}{API_ROLE}/{role_id}"
    return authenticated_request("PUT", url, json=payload)


def tenant_delete_role(role_id: int, confirmed: bool = False):
    """
    删除角色（仅租户管理员）—— 高危操作，需二次确认。
    :param role_id: 角色ID（必填）
    :param confirmed: 是否已获用户确认（默认False先返回删除确认提示）
    """
    if not role_id:
        return _need_input("删除角色", ["role_id"], "tenant_delete_role(role_id)")
    if not confirmed:
        return _need_confirm(f"删除角色 · #{role_id}",
                             [f"即将删除角色 #{role_id}"],
                             "tenant_delete_role(role_id, confirmed=True)", warn=True)
    url = f"{BASE_URL}{API_ROLE}/{role_id}"
    return authenticated_request("DELETE", url)
