"""
auth_core.py —— 共享认证内核（无状态版）

设计要点（v2.0 无状态改造）：
- 不再落盘 token。凭证由调用方（飞书 AI Agent）在对话上下文中持有，
  每次调用工具时通过 access_token / refresh_token 参数传入。
- mcp_adapter 在派发工具前，把 access_token / refresh_token 从参数中 pop 出来，
  通过 set_auth_context 注入本模块的请求级上下文；调用结束 clear_auth_context。
- admin / sale / finance 三端业务函数签名不变，仍调用本模块的
  authenticated_request / do_login / do_logout 等，内部从上下文取 token。
- 多用户天然隔离：每个飞书用户各自持有自己的 token，服务器无共享状态。

成功码约定：
- 后端成功返回 code=0，失败返回 code=5000；
- 本模块对外（业务函数）统一用 code=200 表示成功，code=5000 表示失败/未登录；
- token 过期返回 code=401 + action=token_expired，提示调用方刷新令牌后重试。
"""
import requests
from config import (
    BASE_URL, API_LOGIN, API_LOGOUT, API_REFRESH_TOKEN, API_CHANGE_PASSWORD
)

__version__ = "2.0.0"

# 复用连接的 Session（轻微优化：减少重复 TCP 握手）
_session = requests.Session()

# 请求级上下文：由 mcp_adapter 在每次工具调用前 set、调用后 clear。
# stdio MCP 单进程顺序处理请求，模块级变量即可；如未来切换 HTTP 并发，
# 可改为 threading.local()。
_auth_context = {"access_token": None, "refresh_token": None}


def set_auth_context(access_token=None, refresh_token=None):
    """设置当前请求的认证上下文（由 mcp_adapter 在派发工具前调用）。"""
    _auth_context["access_token"] = access_token
    _auth_context["refresh_token"] = refresh_token


def clear_auth_context():
    """清除当前请求的认证上下文（由 mcp_adapter 在工具调用后调用）。"""
    _auth_context["access_token"] = None
    _auth_context["refresh_token"] = None


# ===================== 兼容旧接口（供 admin/sale 业务函数过渡使用）=====================
def load_cred():
    """
    兼容旧接口：从当前上下文返回凭证。
    无状态模式下 user_info 不可用（仅返回 token），调用方如需 user_info 字段
    （如 tenant_id）应通过工具参数显式传入。
    """
    access_token = _auth_context.get("access_token")
    if not access_token:
        return None
    return {
        "access_token": access_token,
        "refresh_token": _auth_context.get("refresh_token"),
        "user_info": {}
    }


def clear_cred():
    """兼容旧接口：无状态模式下无文件可删，仅清当前上下文。"""
    clear_auth_context()


# ===================== 认证请求 =====================
def get_auth_headers():
    """获取认证请求头（从当前上下文取 access_token）"""
    access_token = _auth_context.get("access_token")
    if not access_token:
        return None
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def authenticated_request(method: str, url: str, **kwargs):
    """
    带认证的请求，统一返回格式。

    token 过期时不再自动刷新（无状态模式下 refresh_token 由调用方持有），
    而是返回 code=401 + action=token_expired，提示调用方先调用
    refresh_token 工具刷新令牌，再用新 token 重试原请求。
    """
    headers = kwargs.pop("headers", {})
    auth_headers = get_auth_headers()
    if not auth_headers:
        return {"code": 5000, "message": "未登录，请先执行登录", "data": None}
    headers.update(auth_headers)
    kwargs["headers"] = headers

    resp = _session.request(method, url, timeout=15, **kwargs)
    res = resp.json()

    # 后端对未登录/无权限返回 code=5000 + "系统内部错误"
    if res.get("code") == 5000 and res.get("message") in ("系统内部错误", "未登录"):
        return {
            "code": 401,
            "message": "访问令牌已过期或无效，请调用 refresh_token 工具刷新后重试",
            "action": "token_expired",
            "data": None
        }

    return res


# ===================== 认证接口 =====================
def do_login(account: str, password: str):
    """
    登录（租户管理员和普通用户通用）。
    无状态模式：不落盘 token，而是把 access_token / refresh_token / user_info
    放进响应 data 返回给调用方，由飞书 Agent 在对话上下文中持有。

    :param account: 登录账号
    :param password: 登录密码
    """
    url = f"{BASE_URL}{API_LOGIN}"
    payload = {
        "account": account,
        "password": password
    }
    resp = _session.post(url, json=payload, timeout=15)
    res = resp.json()
    # 后端成功返回 code=0，失败返回 code=5000
    if res.get("code") != 0:
        return {"code": 5000, "message": res.get("message", "登录失败"), "data": None}

    data = res["data"]
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    user_info = data.get("user", {})
    return {
        "code": 200,
        "message": "登录成功，请在后续工具调用中携带 access_token",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_info": user_info
        }
    }


def do_logout():
    """
    登出：使用当前上下文的 access_token 调用后端登出接口。
    无状态模式下不删除本地文件（本来就没有），仅调用后端销毁 token。
    """
    access_token = _auth_context.get("access_token")
    if not access_token:
        return {"code": 200, "message": "当前无登录凭证", "data": None}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{API_LOGOUT}"
    try:
        _session.post(url, headers=headers, timeout=10)
    except Exception:
        pass
    return {"code": 200, "message": "已完成登出，请丢弃本地保存的 access_token / refresh_token", "data": None}


def do_refresh_token():
    """
    使用当前上下文的 refresh_token 刷新 access_token。
    无状态模式：不落盘，把新的 access_token / refresh_token 放进响应 data 返回，
    调用方（飞书 Agent）需用新 token 替换旧 token 后重试原请求。
    """
    refresh_token = _auth_context.get("refresh_token")
    if not refresh_token:
        return {"code": 5000, "message": "无有效 refresh_token，请重新登录", "data": None}

    url = f"{BASE_URL}{API_REFRESH_TOKEN}"
    payload = {
        "refresh_token": refresh_token
    }
    resp = _session.post(url, json=payload, timeout=15)
    res = resp.json()
    # 后端成功返回 code=0，失败返回 code=5000
    if res.get("code") != 0:
        return {"code": 5000, "message": "刷新令牌失效，请重新登录", "data": None}

    data = res["data"]
    new_refresh_token = data.get("refresh_token", refresh_token)
    return {
        "code": 200,
        "message": "令牌刷新成功，请在后续调用中使用新的 access_token",
        "data": {
            "access_token": data["access_token"],
            "refresh_token": new_refresh_token
        }
    }


def do_change_password(old_password: str, new_password: str):
    """
    修改当前登录账号密码。
    成功后旧 token 失效，调用方需重新登录。

    :param old_password: 原始旧密码
    :param new_password: 设置的新密码
    """
    url = f"{BASE_URL}{API_CHANGE_PASSWORD}"
    payload = {
        "old_password": old_password,
        "new_password": new_password
    }
    res = authenticated_request("POST", url, json=payload)

    # 后端成功返回 code=0，失败返回 code=5000
    if res.get("code") == 0:
        return {"code": 200, "message": "密码修改成功，请重新登录获取新 token", "data": None}
    return res


def get_login_user():
    """
    查询当前登录状态。
    无状态模式下 user_info 已在 login 响应中返回给调用方，
    此处仅返回当前上下文 token 有效性，调用方可从对话上下文获取用户详情。
    """
    access_token = _auth_context.get("access_token")
    if not access_token:
        return {"code": 5000, "message": "暂未登录", "data": None}
    return {
        "code": 200,
        "message": "当前已登录，用户详情请参考登录响应中的 user_info",
        "data": {
            "has_valid_token": True
        }
    }
