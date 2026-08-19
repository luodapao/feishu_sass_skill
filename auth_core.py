"""
auth_core.py —— 共享认证内核

抽取自 admin(main.py) 的凭证管理 / 认证请求 / token 刷新 / 登录登出改密逻辑，
采用中性命名（不带 tenant_ 前缀），供 sale 等技能复用。

设计要点：
- AUTH_FILE 解析为「项目根」绝对路径，确保 admin / sale / finance 无论从哪个 cwd 运行，
  都指向同一个 cred.json，落地「共用登录、凭证共享」语义。
- admin / sale / finance 三端均复用本模块认证逻辑，不再各自内联，消除重复。
"""
import os
import json
import requests
from config import (
    BASE_URL, AUTH_FILE, API_LOGIN, API_LOGOUT, API_REFRESH_TOKEN,
    API_CHANGE_PASSWORD
)

# 项目根（auth_core.py 所在目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# 凭证文件解析为根绝对路径，避免受 cwd 影响
AUTH_FILE_ABS = os.path.normpath(os.path.join(PROJECT_ROOT, AUTH_FILE))
AUTH_DIR_ABS = os.path.dirname(AUTH_FILE_ABS)

# 确保存储文件夹自动创建
if not os.path.exists(AUTH_DIR_ABS):
    os.makedirs(AUTH_DIR_ABS, exist_ok=True)


# ===================== 凭证文件读写通用方法 =====================
def save_cred(access_token: str, refresh_token: str, user_info: dict):
    """保存token信息到本地文件"""
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_info": user_info
    }
    with open(AUTH_FILE_ABS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cred():
    """读取本地凭证，未登录返回None"""
    if not os.path.exists(AUTH_FILE_ABS):
        return None
    try:
        with open(AUTH_FILE_ABS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_cred():
    """清空本地凭证文件（登出使用）"""
    if os.path.exists(AUTH_FILE_ABS):
        os.remove(AUTH_FILE_ABS)


def get_auth_headers():
    """获取认证请求头"""
    cred = load_cred()
    if not cred or not cred.get("access_token"):
        return None
    return {
        "Authorization": f"Bearer {cred['access_token']}",
        "Content-Type": "application/json"
    }


def authenticated_request(method: str, url: str, **kwargs):
    """带认证的请求，自动处理token刷新，统一返回格式"""
    headers = kwargs.pop("headers", {})
    auth_headers = get_auth_headers()
    if not auth_headers:
        return {"code": 5000, "message": "未登录，请先执行登录", "data": None}
    headers.update(auth_headers)
    kwargs["headers"] = headers

    resp = requests.request(method, url, timeout=15, **kwargs)
    res = resp.json()

    # 后端对未登录/无权限返回 code=5000 + "系统内部错误"
    if res.get("code") == 5000 and res.get("message") in ("系统内部错误", "未登录"):
        refresh_result = do_refresh_token()
        if refresh_result.get("code") == 200:
            new_auth_headers = get_auth_headers()
            if new_auth_headers:
                headers.update(new_auth_headers)
                kwargs["headers"] = headers
                try:
                    resp = requests.request(method, url, timeout=15, **kwargs)
                    res = resp.json()
                except Exception:
                    return {"code": 5000, "message": "请求失败，请重试", "data": None}
        else:
            clear_cred()
            return {"code": 5000, "message": "登录已失效，请重新登录", "data": None}

    return res


# ===================== 认证接口 =====================
def do_login(account: str, password: str):
    """
    登录（租户管理员和普通用户通用），登录成功自动持久化token
    :param account: 登录账号
    :param password: 登录密码
    """
    url = f"{BASE_URL}{API_LOGIN}"
    payload = {
        "account": account,
        "password": password
    }
    resp = requests.post(url, json=payload, timeout=15)
    res = resp.json()
    # 后端成功返回 code=0，失败返回 code=5000
    if res.get("code") != 0:
        return {"code": 5000, "message": res.get("message", "登录失败"), "data": None}

    data = res["data"]
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    user_info = data.get("user", {})
    save_cred(access_token, refresh_token, user_info)
    return {
        "code": 200,
        "message": "登录成功，凭证已保存",
        "data": {"user_info": user_info}
    }


def do_logout():
    """登出：调用后端登出接口 + 删除本地凭证"""
    cred = load_cred()
    if not cred or not cred.get("access_token"):
        clear_cred()
        return {"code": 200, "message": "本地无登录凭证，已清除", "data": None}

    headers = {
        "Authorization": f"Bearer {cred['access_token']}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{API_LOGOUT}"
    try:
        requests.post(url, headers=headers, timeout=10)
    except Exception:
        pass
    clear_cred()
    return {"code": 200, "message": "已完成登出，凭证清除", "data": None}


def do_refresh_token():
    """使用refresh_token刷新access_token，自动更新本地文件"""
    cred = load_cred()
    if not cred or not cred.get("refresh_token"):
        return {"code": 5000, "message": "无有效refresh_token，请重新登录", "data": None}

    url = f"{BASE_URL}{API_REFRESH_TOKEN}"
    payload = {
        "refresh_token": cred["refresh_token"]
    }
    resp = requests.post(url, json=payload, timeout=15)
    res = resp.json()
    # 后端成功返回 code=0，失败返回 code=5000
    if res.get("code") != 0:
        clear_cred()
        return {"code": 5000, "message": "刷新令牌失效，请重新登录", "data": None}

    data = res["data"]
    # 优先使用后端返回的新 refresh_token，如果没提供则保留旧的
    new_refresh_token = data.get("refresh_token", cred["refresh_token"])
    save_cred(
        access_token=data["access_token"],
        refresh_token=new_refresh_token,
        user_info=cred["user_info"]
    )
    return {"code": 200, "message": "令牌刷新成功", "data": None}


def do_change_password(old_password: str, new_password: str):
    """
    修改当前登录账号密码
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
        clear_cred()
        return {"code": 200, "message": "密码修改成功，请重新登录", "data": None}
    return res


def get_login_user():
    """获取当前登录用户信息"""
    cred = load_cred()
    if not cred:
        return {"code": 5000, "message": "暂未登录", "data": None}
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "user_info": cred["user_info"],
            "has_valid_token": bool(cred.get("access_token"))
        }
    }
