"""
finance/config.py —— 财务技能 API 路径配置

复用根 config 的 BASE_URL / AUTH_FILE（即与 admin/sale 共用同一后端、同一凭证文件）。
以下为 10 个业务子路由的基址常量，完整路径在 finance/main.py 中按
f"{BASE_URL}{API_FINANCE_XXX}/<route>" 拼接（与 sale 风格一致）。

对应后端：real_estate_agent_saas/finance/router/*
挂载点：main.py 中 app.include_router(finance_router, prefix="/api/finance")
（各子路由自身 prefix 见下方常量，如 archive_router 的 prefix="/archive"）
"""
import os
import sys

# 将项目根加入搜索路径，确保可导入根 config
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import BASE_URL  # noqa: F401  复用同一后端与同一 AUTH_FILE

# ===================== 接口地址 - 财务业务子路由基址 =====================
API_FINANCE_ARCHIVE = "/api/finance/archive"                # 财务基础档案（配置/账户/科目/税率/银行/优惠规则）
API_FINANCE_PAYMENT = "/api/finance/payment"                # 房款收支（分期/差价/收款/退款/定金账户）
API_FINANCE_INVOICE = "/api/finance/invoice"                # 票据税务合规（蓝票/红票/收据/维修基金/纳税申报）
API_FINANCE_COMMISSION = "/api/finance/commission"          # 佣金支付（渠道佣金/扣款/销售提成/奖金）
API_FINANCE_COST = "/api/finance/cost"                      # 项目成本（费用/报销/付款/广告/工程）
API_FINANCE_AR_AP = "/api/finance/ar-ap"                    # 应收应付往来台账（应收/应付/预付/其他往来）
API_FINANCE_RECONCILIATION = "/api/finance/reconciliation"  # 资金对账（银行对账/每日现金/渠道对账）
API_FINANCE_VOUCHER = "/api/finance/voucher"                # 会计凭证（凭证主表/分录明细）
API_FINANCE_AUDIT = "/api/finance/audit"                    # 财务审计追溯（操作日志）
API_FINANCE_REPORT = "/api/finance/report"                  # 财务统计报表（现金流/应收/税务/佣金/利润/资产负债等）
