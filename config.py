import os

# 后端基础地址
BASE_URL = "http://14.103.41.38:8000"

# 凭证存储目录与文件
AUTH_DIR = "./saas_tenant_auth"
AUTH_FILE = os.path.join(AUTH_DIR, "cred.json")

# 接口地址 - 认证接口（admin/sale/finance 共享）
API_LOGIN = "/api/admin/login"
API_LOGOUT = "/api/admin/logout"
API_REFRESH_TOKEN = "/api/admin/refresh-token"
API_CHANGE_PASSWORD = "/api/admin/change-password"

# 说明：admin 私有接口常量（租户用户管理 API_TENANT_USER、角色管理 API_ROLE）
# 已下沉至 admin/config.py，本文件仅保留三端共享配置（BASE_URL / AUTH_FILE / 认证接口）。

# 确保存储文件夹自动创建
if not os.path.exists(AUTH_DIR):
    os.makedirs(AUTH_DIR, exist_ok=True)
