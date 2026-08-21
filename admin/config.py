"""
admin/config.py —— 租户管理技能 API 路径配置

复用根 config 的 BASE_URL（即与 sale/finance 共用同一后端）。无状态模式下凭证由调用方持有，不再共享凭证文件。
以下为 admin 私有的业务接口常量（租户用户管理、角色管理），
完整路径在 admin/main.py 中按 f"{BASE_URL}{API_XXX}" 拼接（与 sale/finance 风格一致）。

对应后端：real_estate_agent_saas/admin/router/*
"""
import os
import sys

# 将项目根加入搜索路径，确保可导入根 config
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import BASE_URL  # noqa: F401  复用同一后端

# ===================== 接口地址 - admin 业务接口 =====================
API_TENANT_USER = "/api/admin/tenant/users"  # 租户用户管理
API_ROLE = "/api/admin/role"                 # 角色管理
