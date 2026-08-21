# 后端基础地址
BASE_URL = "http://192.168.0.79:8000"

# 接口地址 - 认证接口（admin/sale/finance 共享）
# 无状态模式：不再持久化 token 到本地文件，凭证由调用方（飞书 Agent）持有，
# 每次工具调用通过 access_token 参数传入，由 auth_core 请求级上下文承载。
API_LOGIN = "/api/admin/login"
API_LOGOUT = "/api/admin/logout"
API_REFRESH_TOKEN = "/api/admin/refresh-token"
API_CHANGE_PASSWORD = "/api/admin/change-password"

# 说明：admin 私有接口常量（租户用户管理 API_TENANT_USER、角色管理 API_ROLE）
# 已下沉至 admin/config.py，本文件仅保留三端共享配置（BASE_URL / 认证接口）。
