"""
sale/config.py —— 销售技能 API 路径配置

复用根 config 的 BASE_URL / AUTH_FILE（即与 admin 共用同一后端、同一凭证文件）。
以下为 6 个业务子路由的基址常量，完整路径在 sale/main.py 中按
f"{BASE_URL}{API_SALE_XXX}/<route>" 拼接（与 admin 风格一致）。

对应后端：real_estate_agent_saas/sale/router/*
挂载点：main.py 中 app.include_router(sale_router, prefix="/api/sale")
"""
import os
import sys

# 将项目根加入搜索路径，确保可导入根 config
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import BASE_URL  # noqa: F401  复用同一后端与同一 AUTH_FILE

# ===================== 接口地址 - 销售业务子路由基址 =====================
API_SALE_PROJECT = "/api/sale/project"            # 楼盘销控
API_SALE_CUSTOMER = "/api/sale/customer"          # 客户管理
API_SALE_TRANSACTION = "/api/sale/transaction"    # 认购签约交易
API_SALE_COMMISSION = "/api/sale/commission"      # 分销渠道与佣金
API_SALE_PERFORMANCE = "/api/sale/performance"    # 销售业绩与考核
API_SALE_STATISTICS = "/api/sale/statistics"      # 数据统计报表
