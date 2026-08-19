"""
finance/main.py —— 房产SaaS 财务管理技能入口

严格依据后端 real_estate_agent_saas/finance/router/* 的路由接口实现，
字段对照 finance/schemas/* 的 Pydantic 校验模型（Create/Update）。

- 认证：复用 admin 登录体系，凭证共享同一 cred.json（由根 auth_core 统一管理）。
- URL：BASE_URL + /api/finance/<子路由>/<route>，路径常量见 finance.config。
- 请求构造：path 参数拼 URL；标量参数走 query（即使 POST/GET 列表）；
  schema body 走 json（字段平铺）；_compact() 剔除 None 值让后端默认值生效。
- 返回：直接透传 authenticated_request 的原始响应（成功 code=0）。

覆盖 10 大业务域：财务基础档案(archive)、房款收支(payment)、票据税务合规(invoice)、
佣金支付(commission)、项目成本(cost)、应收应付往来台账(ar_ap)、资金对账(reconciliation)、
会计凭证(voucher)、财务审计追溯(audit)、财务统计报表(report)。
"""
import os
import sys

# 将项目根加入搜索路径，确保 auth_core / 根 config / finance 包均可导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from auth_core import (
    do_login, do_logout, do_refresh_token,
    do_change_password, get_login_user, authenticated_request
)
from config import BASE_URL  # noqa: F401
from finance.config import (
    API_FINANCE_ARCHIVE, API_FINANCE_PAYMENT, API_FINANCE_INVOICE,
    API_FINANCE_COMMISSION, API_FINANCE_COST, API_FINANCE_AR_AP,
    API_FINANCE_RECONCILIATION, API_FINANCE_VOUCHER, API_FINANCE_AUDIT,
    API_FINANCE_REPORT
)


def _compact(d: dict) -> dict:
    """剔除值为 None 的键（用 is not None，保留 0/False），让后端按 schema 默认值生效"""
    return {k: v for k, v in d.items() if v is not None}


# ===================== 认证接口（复用 admin 登录，共享凭证）=====================
def finance_login(account: str, password: str):
    """
    财务端登录（复用 admin 登录端点，凭证写入共享 cred.json）
    :param account: 登录账号
    :param password: 登录密码
    """
    return do_login(account, password)


def finance_logout():
    """财务端登出，销毁本地共享凭证并调用后端登出接口"""
    return do_logout()


def finance_refresh_token():
    """自动刷新 access_token，无需传入参数"""
    return do_refresh_token()


def finance_change_password(old_password: str, new_password: str):
    """
    修改当前登录账号密码
    :param old_password: 原始旧密码
    :param new_password: 设置的新密码
    """
    return do_change_password(old_password, new_password)


def finance_get_login_user():
    """查询当前登录用户信息"""
    return get_login_user()


# =====================================================================
# 一、财务基础档案（/api/finance/archive）
# =====================================================================

# ---------- 项目财务配置（/archive/config）----------
def finance_archive_config_create(project_id: int, project_name: str,
                                  finance_status: int = None, calc_mode: int = None,
                                  default_tax_rate_id: int = None,
                                  default_income_subject_id: int = None,
                                  default_receive_account_id: int = None,
                                  default_mortgage_account_id: int = None,
                                  default_supervise_account_id: int = None,
                                  default_cap_cost_subject_id: int = None,
                                  default_market_subject_id: int = None,
                                  default_payable_subject_id: int = None,
                                  default_advance_subject_id: int = None,
                                  default_channel_subject_id: int = None,
                                  default_tax_subject_id: int = None,
                                  deposit_ratio: float = None,
                                  installment_rule: str = None,
                                  max_advance_ratio: float = None,
                                  settle_cycle_type: int = None,
                                  close_status: int = None, remark: str = None):
    """
    创建项目财务配置（POST /api/finance/archive/config/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param finance_status: 财务启用状态：1启用 2停用（默认1）
    :param calc_mode: 计税模式：1一般计税 2简易计税（默认1）
    :param default_tax_rate_id: 默认计税税率模板ID
    :param default_income_subject_id: 默认收入科目ID
    :param default_receive_account_id: 默认通用收款账户ID
    :param default_mortgage_account_id: 按揭回款专用收款账户ID
    :param default_supervise_account_id: 预售资金监管专户ID
    :param default_cap_cost_subject_id: 资本化开发成本默认科目ID
    :param default_market_subject_id: 广告营销费用默认科目ID
    :param default_payable_subject_id: 供应商应付账款科目ID
    :param default_advance_subject_id: 供应商预付账款科目ID
    :param default_channel_subject_id: 分销渠道佣金往来科目ID
    :param default_tax_subject_id: 应交税费总账科目ID
    :param deposit_ratio: 定金比例上限（默认0.0）
    :param installment_rule: 分期规则JSON配置
    :param max_advance_ratio: 供应商预付工程款比例上限（默认0.0）
    :param settle_cycle_type: 默认供应商结算周期：1月结 2季结 3竣工一次性结算（默认1）
    :param close_status: 项目财务归档状态：0在建未结账 1竣工已结账归档（默认0）
    :param remark: 财务配置备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/config/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "finance_status": finance_status, "calc_mode": calc_mode,
        "default_tax_rate_id": default_tax_rate_id,
        "default_income_subject_id": default_income_subject_id,
        "default_receive_account_id": default_receive_account_id,
        "default_mortgage_account_id": default_mortgage_account_id,
        "default_supervise_account_id": default_supervise_account_id,
        "default_cap_cost_subject_id": default_cap_cost_subject_id,
        "default_market_subject_id": default_market_subject_id,
        "default_payable_subject_id": default_payable_subject_id,
        "default_advance_subject_id": default_advance_subject_id,
        "default_channel_subject_id": default_channel_subject_id,
        "default_tax_subject_id": default_tax_subject_id,
        "deposit_ratio": deposit_ratio, "installment_rule": installment_rule,
        "max_advance_ratio": max_advance_ratio,
        "settle_cycle_type": settle_cycle_type, "close_status": close_status,
        "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_config_list(page: int = 1, page_size: int = 20, project_id: int = None):
    """
    获取项目财务配置列表（GET /api/finance/archive/config/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/config/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id})
    return authenticated_request("GET", url, params=params)


def finance_archive_config_get(config_id: int):
    """
    获取项目财务配置详情（GET /api/finance/archive/config/{id}）
    :param config_id: 项目财务配置ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/config/{config_id}"
    return authenticated_request("GET", url)


def finance_archive_config_update(config_id: int, finance_status: int = None,
                                  calc_mode: int = None, default_tax_rate_id: int = None,
                                  default_income_subject_id: int = None,
                                  default_receive_account_id: int = None,
                                  default_mortgage_account_id: int = None,
                                  default_supervise_account_id: int = None,
                                  default_cap_cost_subject_id: int = None,
                                  default_market_subject_id: int = None,
                                  default_payable_subject_id: int = None,
                                  default_advance_subject_id: int = None,
                                  default_channel_subject_id: int = None,
                                  default_tax_subject_id: int = None,
                                  deposit_ratio: float = None,
                                  installment_rule: str = None,
                                  max_advance_ratio: float = None,
                                  settle_cycle_type: int = None,
                                  close_status: int = None, remark: str = None):
    """
    更新项目财务配置（PUT /api/finance/archive/config/{id}）
    :param config_id: 项目财务配置ID
    :param finance_status: 财务启用状态：1启用 2停用
    :param calc_mode: 计税模式：1一般计税 2简易计税
    :param default_tax_rate_id: 默认计税税率模板ID
    :param default_income_subject_id: 默认收入科目ID
    :param default_receive_account_id: 默认通用收款账户ID
    :param default_mortgage_account_id: 按揭回款专用收款账户ID
    :param default_supervise_account_id: 预售资金监管专户ID
    :param default_cap_cost_subject_id: 资本化开发成本默认科目ID
    :param default_market_subject_id: 广告营销费用默认科目ID
    :param default_payable_subject_id: 供应商应付账款科目ID
    :param default_advance_subject_id: 供应商预付账款科目ID
    :param default_channel_subject_id: 分销渠道佣金往来科目ID
    :param default_tax_subject_id: 应交税费总账科目ID
    :param deposit_ratio: 定金比例上限
    :param installment_rule: 分期规则JSON配置
    :param max_advance_ratio: 供应商预付工程款比例上限
    :param settle_cycle_type: 默认供应商结算周期：1月结 2季结 3竣工一次性结算
    :param close_status: 项目财务归档状态：0在建未结账 1竣工已结账归档
    :param remark: 财务配置备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/config/{config_id}"
    payload = _compact({
        "finance_status": finance_status, "calc_mode": calc_mode,
        "default_tax_rate_id": default_tax_rate_id,
        "default_income_subject_id": default_income_subject_id,
        "default_receive_account_id": default_receive_account_id,
        "default_mortgage_account_id": default_mortgage_account_id,
        "default_supervise_account_id": default_supervise_account_id,
        "default_cap_cost_subject_id": default_cap_cost_subject_id,
        "default_market_subject_id": default_market_subject_id,
        "default_payable_subject_id": default_payable_subject_id,
        "default_advance_subject_id": default_advance_subject_id,
        "default_channel_subject_id": default_channel_subject_id,
        "default_tax_subject_id": default_tax_subject_id,
        "deposit_ratio": deposit_ratio, "installment_rule": installment_rule,
        "max_advance_ratio": max_advance_ratio,
        "settle_cycle_type": settle_cycle_type, "close_status": close_status,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_config_delete(config_id: int):
    """
    删除项目财务配置（DELETE /api/finance/archive/config/{id}）
    :param config_id: 项目财务配置ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/config/{config_id}"
    return authenticated_request("DELETE", url)


# ---------- 财务账户（/archive/account）----------
def finance_archive_account_create(account_name: str, account_type: int,
                                   account_code: str = None, bank_name: str = None,
                                   bank_account: str = None, cnaps_code: str = None,
                                   account_status: int = None, is_default: int = None,
                                   account_holder: str = None, mobile: str = None,
                                   remark: str = None):
    """
    创建财务账户（POST /api/finance/archive/account/create）
    :param account_name: 账户名称（必填）
    :param account_type: 账户类型：1现金 2银行存款 3支付宝 4微信（必填）
    :param account_code: 账户编码（自动生成，无需传入）
    :param bank_name: 开户银行名称
    :param bank_account: 银行账号（脱敏存储）
    :param cnaps_code: 联行号
    :param account_status: 账户状态：1启用 2停用（默认1）
    :param is_default: 是否默认账户：0否 1是（默认0）
    :param account_holder: 开户人姓名
    :param mobile: 联系电话
    :param remark: 账户备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/account/create"
    payload = _compact({
        "account_code": account_code, "account_name": account_name,
        "account_type": account_type, "bank_name": bank_name,
        "bank_account": bank_account, "cnaps_code": cnaps_code,
        "account_status": account_status, "is_default": is_default,
        "account_holder": account_holder, "mobile": mobile, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_account_list(page: int = 1, page_size: int = 20, account_type: int = None):
    """
    获取财务账户列表（GET /api/finance/archive/account/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param account_type: 账户类型：1现金 2银行存款 3支付宝 4微信（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/account/list"
    params = _compact({"page": page, "page_size": page_size, "account_type": account_type})
    return authenticated_request("GET", url, params=params)


def finance_archive_account_get(account_id: int):
    """
    获取财务账户详情（GET /api/finance/archive/account/{id}）
    :param account_id: 账户ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/account/{account_id}"
    return authenticated_request("GET", url)


def finance_archive_account_update(account_id: int, account_name: str = None,
                                   account_type: int = None, bank_name: str = None,
                                   bank_account: str = None, cnaps_code: str = None,
                                   account_status: int = None, is_default: int = None,
                                   account_holder: str = None, mobile: str = None,
                                   remark: str = None):
    """
    更新财务账户（PUT /api/finance/archive/account/{id}）
    :param account_id: 账户ID
    :param account_name: 账户名称
    :param account_type: 账户类型：1现金 2银行存款 3支付宝 4微信
    :param bank_name: 开户银行名称
    :param bank_account: 银行账号（脱敏存储）
    :param cnaps_code: 联行号
    :param account_status: 账户状态：1启用 2停用
    :param is_default: 是否默认账户：0否 1是
    :param account_holder: 开户人姓名
    :param mobile: 联系电话
    :param remark: 账户备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/account/{account_id}"
    payload = _compact({
        "account_name": account_name, "account_type": account_type,
        "bank_name": bank_name, "bank_account": bank_account,
        "cnaps_code": cnaps_code, "account_status": account_status,
        "is_default": is_default, "account_holder": account_holder,
        "mobile": mobile, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_account_delete(account_id: int):
    """
    删除财务账户（DELETE /api/finance/archive/account/{id}）
    :param account_id: 账户ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/account/{account_id}"
    return authenticated_request("DELETE", url)


# ---------- 财务科目（/archive/subject）----------
def finance_archive_subject_create(subject_name: str, subject_type: int, subject_nature: int,
                                   subject_code: str = None, subject_level: int = None,
                                   parent_id: int = None, is_leaf: int = None,
                                   is_enabled: int = None, account_id: int = None,
                                   remark: str = None):
    """
    创建财务科目（POST /api/finance/archive/subject/create）
    :param subject_name: 科目名称（必填）
    :param subject_type: 科目类型：1资产 2负债 3权益 4成本 5损益（必填）
    :param subject_nature: 科目性质：1借方 2贷方（必填）
    :param subject_code: 科目编码（自动生成，无需传入）
    :param subject_level: 科目级别：1-4（默认1）
    :param parent_id: 上级科目ID（默认0）
    :param is_leaf: 是否末级科目：1是 0否（默认1）
    :param is_enabled: 是否启用：1是 0否（默认1）
    :param account_id: 关联账户ID
    :param remark: 科目备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/subject/create"
    payload = _compact({
        "subject_code": subject_code, "subject_name": subject_name,
        "subject_level": subject_level, "parent_id": parent_id,
        "subject_type": subject_type, "subject_nature": subject_nature,
        "is_leaf": is_leaf, "is_enabled": is_enabled,
        "account_id": account_id, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_subject_list(page: int = 1, page_size: int = 20, subject_level: int = None):
    """
    获取财务科目列表（GET /api/finance/archive/subject/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param subject_level: 科目级别：1-4（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/subject/list"
    params = _compact({"page": page, "page_size": page_size, "subject_level": subject_level})
    return authenticated_request("GET", url, params=params)


def finance_archive_subject_get(subject_id: int):
    """
    获取财务科目详情（GET /api/finance/archive/subject/{id}）
    :param subject_id: 科目ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/subject/{subject_id}"
    return authenticated_request("GET", url)


def finance_archive_subject_update(subject_id: int, subject_name: str = None,
                                   subject_level: int = None, parent_id: int = None,
                                   subject_type: int = None, subject_nature: int = None,
                                   is_leaf: int = None, is_enabled: int = None,
                                   account_id: int = None, remark: str = None):
    """
    更新财务科目（PUT /api/finance/archive/subject/{id}）
    :param subject_id: 科目ID
    :param subject_name: 科目名称
    :param subject_level: 科目级别：1-4
    :param parent_id: 上级科目ID
    :param subject_type: 科目类型：1资产 2负债 3权益 4成本 5损益
    :param subject_nature: 科目性质：1借方 2贷方
    :param is_leaf: 是否末级科目：1是 0否
    :param is_enabled: 是否启用：1是 0否
    :param account_id: 关联账户ID
    :param remark: 科目备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/subject/{subject_id}"
    payload = _compact({
        "subject_name": subject_name, "subject_level": subject_level,
        "parent_id": parent_id, "subject_type": subject_type,
        "subject_nature": subject_nature, "is_leaf": is_leaf,
        "is_enabled": is_enabled, "account_id": account_id, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_subject_delete(subject_id: int):
    """
    删除财务科目（DELETE /api/finance/archive/subject/{id}）
    :param subject_id: 科目ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/subject/{subject_id}"
    return authenticated_request("DELETE", url)


# ---------- 税率配置（/archive/tax-rate）----------
def finance_archive_tax_rate_create(tax_rate_name: str, tax_rate_code: str = None,
                                    tax_type: int = None, rate_value: float = None,
                                    tax_status: int = None, is_default: int = None,
                                    calc_mode: int = None, bind_subject_id: int = None,
                                    biz_scope: str = None, create_user_id: int = None,
                                    remark: str = None):
    """
    创建税率配置（POST /api/finance/archive/tax-rate/create）
    :param tax_rate_name: 税率名称（必填）
    :param tax_rate_code: 税率编码（自动生成，无需传入）
    :param tax_type: 税种类型：1增值税 2企业所得税 3个人所得税（默认1）
    :param rate_value: 税率值（默认0.0）
    :param tax_status: 税率状态：1启用 2停用（默认1）
    :param is_default: 是否默认：0否 1是（默认0）
    :param calc_mode: 计税模式：1一般计税 2简易计税（默认1）
    :param bind_subject_id: 绑定的计税科目ID
    :param biz_scope: 适用业务范围JSON
    :param create_user_id: 创建人ID
    :param remark: 备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/tax-rate/create"
    payload = _compact({
        "tax_rate_code": tax_rate_code, "tax_rate_name": tax_rate_name,
        "tax_type": tax_type, "rate_value": rate_value,
        "tax_status": tax_status, "is_default": is_default,
        "calc_mode": calc_mode, "bind_subject_id": bind_subject_id,
        "biz_scope": biz_scope, "create_user_id": create_user_id, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_tax_rate_list(page: int = 1, page_size: int = 20, tax_type: int = None):
    """
    获取税率配置列表（GET /api/finance/archive/tax-rate/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param tax_type: 税种类型：1增值税 2企业所得税 3个人所得税（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/tax-rate/list"
    params = _compact({"page": page, "page_size": page_size, "tax_type": tax_type})
    return authenticated_request("GET", url, params=params)


def finance_archive_tax_rate_get(tax_rate_id: int):
    """
    获取税率配置详情（GET /api/finance/archive/tax-rate/{id}）
    :param tax_rate_id: 税率ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/tax-rate/{tax_rate_id}"
    return authenticated_request("GET", url)


def finance_archive_tax_rate_update(tax_rate_id: int, tax_rate_code: str = None,
                                    tax_rate_name: str = None, tax_type: int = None,
                                    rate_value: float = None, tax_status: int = None,
                                    is_default: int = None, calc_mode: int = None,
                                    bind_subject_id: int = None, biz_scope: str = None,
                                    remark: str = None):
    """
    更新税率配置（PUT /api/finance/archive/tax-rate/{id}）
    :param tax_rate_id: 税率ID
    :param tax_rate_code: 税率编码
    :param tax_rate_name: 税率名称
    :param tax_type: 税种类型：1增值税 2企业所得税 3个人所得税
    :param rate_value: 税率值
    :param tax_status: 税率状态：1启用 2停用
    :param is_default: 是否默认：0否 1是
    :param calc_mode: 计税模式：1一般计税 2简易计税
    :param bind_subject_id: 绑定的计税科目ID
    :param biz_scope: 适用业务范围JSON
    :param remark: 备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/tax-rate/{tax_rate_id}"
    payload = _compact({
        "tax_rate_code": tax_rate_code, "tax_rate_name": tax_rate_name,
        "tax_type": tax_type, "rate_value": rate_value,
        "tax_status": tax_status, "is_default": is_default,
        "calc_mode": calc_mode, "bind_subject_id": bind_subject_id,
        "biz_scope": biz_scope, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_tax_rate_delete(tax_rate_id: int):
    """
    删除税率配置（DELETE /api/finance/archive/tax-rate/{id}）
    :param tax_rate_id: 税率ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/tax-rate/{tax_rate_id}"
    return authenticated_request("DELETE", url)


# ---------- 银行信息（/archive/bank）----------
def finance_archive_bank_create(bank_name: str, bank_account: str, account_name: str,
                                company_type: int, bank_info_code: str = None,
                                cnaps_code: str = None, company_id: int = None,
                                bank_status: int = None, remark: str = None):
    """
    创建银行信息（POST /api/finance/archive/bank/create）
    :param bank_name: 开户银行名称（必填）
    :param bank_account: 银行账号（脱敏，必填）
    :param account_name: 账户名称（必填）
    :param company_type: 账户主体类型：1开发商 2渠道 3供应商（必填）
    :param bank_info_code: 银行档案编码（自动生成，无需传入）
    :param cnaps_code: 联行号
    :param company_id: 关联主体ID
    :param bank_status: 状态：1启用 2停用（默认1）
    :param remark: 备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/bank/create"
    payload = _compact({
        "bank_info_code": bank_info_code, "bank_name": bank_name,
        "bank_account": bank_account, "account_name": account_name,
        "cnaps_code": cnaps_code, "company_type": company_type,
        "company_id": company_id, "bank_status": bank_status, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_bank_list(page: int = 1, page_size: int = 20, bank_name: str = None):
    """
    获取银行信息列表（GET /api/finance/archive/bank/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param bank_name: 开户银行名称（可选，用于搜索）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/bank/list"
    params = _compact({"page": page, "page_size": page_size, "bank_name": bank_name})
    return authenticated_request("GET", url, params=params)


def finance_archive_bank_get(bank_id: int):
    """
    获取银行信息详情（GET /api/finance/archive/bank/{id}）
    :param bank_id: 银行信息ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/bank/{bank_id}"
    return authenticated_request("GET", url)


def finance_archive_bank_update(bank_id: int, bank_name: str = None,
                                bank_account: str = None, account_name: str = None,
                                cnaps_code: str = None, company_type: int = None,
                                company_id: int = None, bank_status: int = None,
                                remark: str = None):
    """
    更新银行信息（PUT /api/finance/archive/bank/{id}）
    :param bank_id: 银行信息ID
    :param bank_name: 开户银行名称
    :param bank_account: 银行账号（脱敏）
    :param account_name: 账户名称
    :param cnaps_code: 联行号
    :param company_type: 账户主体类型：1开发商 2渠道 3供应商
    :param company_id: 关联主体ID
    :param bank_status: 状态：1启用 2停用
    :param remark: 备注说明
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/bank/{bank_id}"
    payload = _compact({
        "bank_name": bank_name, "bank_account": bank_account,
        "account_name": account_name, "cnaps_code": cnaps_code,
        "company_type": company_type, "company_id": company_id,
        "bank_status": bank_status, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_bank_delete(bank_id: int):
    """
    删除银行信息（DELETE /api/finance/archive/bank/{id}）
    :param bank_id: 银行信息ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/bank/{bank_id}"
    return authenticated_request("DELETE", url)


# ---------- 优惠规则（/archive/preferential-rule）----------
def finance_archive_preferential_rule_create(project_id: int, project_name: str,
                                             discount_name: str, discount_type: int,
                                             property_type: str, start_time: str,
                                             discount_code: str = None,
                                             discount_rate: float = None,
                                             fixed_price: float = None,
                                             max_discount_amount: float = None,
                                             end_time: str = None, is_stack: int = None,
                                             offset_income: int = None,
                                             rule_status: int = None, remark: str = None):
    """
    创建优惠规则（POST /api/finance/archive/preferential-rule/create）
    :param project_id: 关联楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param discount_name: 优惠规则名称（必填）
    :param discount_type: 优惠类型：1折扣 2一口价 3减免 4组合（必填）
    :param property_type: 适用物业类型（必填）
    :param start_time: 规则生效时间（必填，如"2026-01-01 00:00:00"）
    :param discount_code: 优惠规则编码（自动生成，无需传入）
    :param discount_rate: 折扣比例（默认1.0）
    :param fixed_price: 一口价金额（默认0）
    :param max_discount_amount: 单房源最大优惠上限（默认0）
    :param end_time: 规则失效时间
    :param is_stack: 是否支持叠加：0否 1是（默认0）
    :param offset_income: 是否冲减收入：1是 0否（默认1）
    :param rule_status: 状态：1启用 2停用（默认1）
    :param remark: 优惠规则备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/preferential-rule/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "discount_code": discount_code, "discount_name": discount_name,
        "discount_type": discount_type, "property_type": property_type,
        "discount_rate": discount_rate, "fixed_price": fixed_price,
        "max_discount_amount": max_discount_amount, "start_time": start_time,
        "end_time": end_time, "is_stack": is_stack,
        "offset_income": offset_income, "rule_status": rule_status, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_archive_preferential_rule_list(page: int = 1, page_size: int = 20, rule_type: int = None):
    """
    获取优惠规则列表（GET /api/finance/archive/preferential-rule/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param rule_type: 规则类型（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/preferential-rule/list"
    params = _compact({"page": page, "page_size": page_size, "rule_type": rule_type})
    return authenticated_request("GET", url, params=params)


def finance_archive_preferential_rule_get(rule_id: int):
    """
    获取优惠规则详情（GET /api/finance/archive/preferential-rule/{id}）
    :param rule_id: 优惠规则ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/preferential-rule/{rule_id}"
    return authenticated_request("GET", url)


def finance_archive_preferential_rule_update(rule_id: int, discount_name: str = None,
                                             discount_type: int = None, property_type: str = None,
                                             discount_rate: float = None, fixed_price: float = None,
                                             max_discount_amount: float = None, end_time: str = None,
                                             is_stack: int = None, offset_income: int = None,
                                             rule_status: int = None, remark: str = None):
    """
    更新优惠规则（PUT /api/finance/archive/preferential-rule/{id}）
    :param rule_id: 优惠规则ID
    :param discount_name: 优惠规则名称
    :param discount_type: 优惠类型：1折扣 2一口价 3减免 4组合
    :param property_type: 适用物业类型
    :param discount_rate: 折扣比例
    :param fixed_price: 一口价金额
    :param max_discount_amount: 单房源最大优惠上限
    :param end_time: 规则失效时间
    :param is_stack: 是否支持叠加：0否 1是
    :param offset_income: 是否冲减收入：1是 0否
    :param rule_status: 状态：1启用 2停用
    :param remark: 优惠规则备注
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/preferential-rule/{rule_id}"
    payload = _compact({
        "discount_name": discount_name, "discount_type": discount_type,
        "property_type": property_type, "discount_rate": discount_rate,
        "fixed_price": fixed_price, "max_discount_amount": max_discount_amount,
        "end_time": end_time, "is_stack": is_stack,
        "offset_income": offset_income, "rule_status": rule_status, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_archive_preferential_rule_delete(rule_id: int):
    """
    删除优惠规则（DELETE /api/finance/archive/preferential-rule/{id}）
    :param rule_id: 优惠规则ID
    """
    url = f"{BASE_URL}{API_FINANCE_ARCHIVE}/preferential-rule/{rule_id}"
    return authenticated_request("DELETE", url)


# =====================================================================
# 二、房款收支（/api/finance/payment）
# =====================================================================

# ---------- 分期回款计划（/payment/installment）----------
def finance_payment_installment_create(order_id: int, customer_id: int, project_id: int,
                                       contract_amount: float, down_payment_ratio: float,
                                       down_payment_amount: float, down_payment_untax_amt: float,
                                       down_payment_tax: float, loan_amount: float,
                                       installment_count: int, payment_cycle: str,
                                       first_payment_date: str, plan_no: str = None,
                                       period_no: int = None):
    """
    创建分期回款计划（POST /api/finance/payment/installment/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param contract_amount: 合同金额（必填）
    :param down_payment_ratio: 首付比例（必填）
    :param down_payment_amount: 首付金额（必填）
    :param down_payment_untax_amt: 首付不含税金额（必填）
    :param down_payment_tax: 首付税额（必填）
    :param loan_amount: 贷款金额（必填）
    :param installment_count: 分期付款次数（必填）
    :param payment_cycle: 付款周期（月/季度/年，必填）
    :param first_payment_date: 首期付款日期（必填，如"2026-01-01 00:00:00"）
    :param plan_no: 分期计划编号（系统自动生成，无需传入）
    :param period_no: 期数编号（系统自动生成，无需传入）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/installment/create"
    payload = _compact({
        "order_id": order_id, "customer_id": customer_id, "project_id": project_id,
        "contract_amount": contract_amount, "down_payment_ratio": down_payment_ratio,
        "down_payment_amount": down_payment_amount,
        "down_payment_untax_amt": down_payment_untax_amt,
        "down_payment_tax": down_payment_tax, "loan_amount": loan_amount,
        "installment_count": installment_count, "payment_cycle": payment_cycle,
        "first_payment_date": first_payment_date, "plan_no": plan_no,
        "period_no": period_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_payment_installment_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取分期回款计划列表（GET /api/finance/payment/installment/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/installment/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_payment_installment_get(installment_id: int):
    """
    获取分期回款计划详情（GET /api/finance/payment/installment/{id}）
    :param installment_id: 分期回款计划ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/installment/{installment_id}"
    return authenticated_request("GET", url)


def finance_payment_installment_update(installment_id: int, down_payment_ratio: float = None,
                                       down_payment_amount: float = None,
                                       down_payment_untax_amt: float = None,
                                       down_payment_tax: float = None, loan_amount: float = None,
                                       installment_count: int = None, payment_cycle: str = None,
                                       first_payment_date: str = None):
    """
    更新分期回款计划（PUT /api/finance/payment/installment/{id}）
    :param installment_id: 分期回款计划ID
    :param down_payment_ratio: 首付比例
    :param down_payment_amount: 首付金额
    :param down_payment_untax_amt: 首付不含税金额
    :param down_payment_tax: 首付税额
    :param loan_amount: 贷款金额
    :param installment_count: 分期付款次数
    :param payment_cycle: 付款周期
    :param first_payment_date: 首期付款日期
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/installment/{installment_id}"
    payload = _compact({
        "down_payment_ratio": down_payment_ratio,
        "down_payment_amount": down_payment_amount,
        "down_payment_untax_amt": down_payment_untax_amt,
        "down_payment_tax": down_payment_tax, "loan_amount": loan_amount,
        "installment_count": installment_count, "payment_cycle": payment_cycle,
        "first_payment_date": first_payment_date,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_payment_installment_delete(installment_id: int):
    """
    删除分期回款计划（DELETE /api/finance/payment/installment/{id}）
    :param installment_id: 分期回款计划ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/installment/{installment_id}"
    return authenticated_request("DELETE", url)


# ---------- 面积差价调整（/payment/adjustment）----------
def finance_payment_adjustment_create(order_id: int, customer_id: int, house_id: int,
                                      original_area: float, actual_area: float, area_diff: float,
                                      unit_price: float, diff_amount: float, diff_untax_amt: float,
                                      diff_tax: float, diff_total_amt: float, diff_type: str,
                                      reason: str = None, diff_no: str = None):
    """
    创建面积差价调整（POST /api/finance/payment/adjustment/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param house_id: 房源ID（必填）
    :param original_area: 原合同面积（必填）
    :param actual_area: 实测面积（必填）
    :param area_diff: 面积差异（必填）
    :param unit_price: 单价（必填）
    :param diff_amount: 差价金额（必填）
    :param diff_untax_amt: 差价不含税金额（必填）
    :param diff_tax: 差价税额（必填）
    :param diff_total_amt: 差价含税总金额（必填）
    :param diff_type: 差价类型（补收/退还，必填）
    :param reason: 调整原因
    :param diff_no: 差价调整编号（系统自动生成，无需传入）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/adjustment/create"
    payload = _compact({
        "order_id": order_id, "customer_id": customer_id, "house_id": house_id,
        "original_area": original_area, "actual_area": actual_area,
        "area_diff": area_diff, "unit_price": unit_price,
        "diff_amount": diff_amount, "diff_untax_amt": diff_untax_amt,
        "diff_tax": diff_tax, "diff_total_amt": diff_total_amt,
        "diff_type": diff_type, "reason": reason, "diff_no": diff_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_payment_adjustment_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取面积差价调整列表（GET /api/finance/payment/adjustment/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/adjustment/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_payment_adjustment_get(adjustment_id: int):
    """
    获取面积差价调整详情（GET /api/finance/payment/adjustment/{id}）
    :param adjustment_id: 面积差价调整ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/adjustment/{adjustment_id}"
    return authenticated_request("GET", url)


def finance_payment_adjustment_update(adjustment_id: int, original_area: float = None,
                                      actual_area: float = None, unit_price: float = None,
                                      diff_amount: float = None, diff_untax_amt: float = None,
                                      diff_tax: float = None, diff_total_amt: float = None,
                                      reason: str = None):
    """
    更新面积差价调整（PUT /api/finance/payment/adjustment/{id}）
    :param adjustment_id: 面积差价调整ID
    :param original_area: 原合同面积
    :param actual_area: 实测面积
    :param unit_price: 单价
    :param diff_amount: 差价金额
    :param diff_untax_amt: 差价不含税金额
    :param diff_tax: 差价税额
    :param diff_total_amt: 差价含税总金额
    :param reason: 调整原因
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/adjustment/{adjustment_id}"
    payload = _compact({
        "original_area": original_area, "actual_area": actual_area,
        "unit_price": unit_price, "diff_amount": diff_amount,
        "diff_untax_amt": diff_untax_amt, "diff_tax": diff_tax,
        "diff_total_amt": diff_total_amt, "reason": reason,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_payment_adjustment_delete(adjustment_id: int):
    """
    删除面积差价调整（DELETE /api/finance/payment/adjustment/{id}）
    :param adjustment_id: 面积差价调整ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/adjustment/{adjustment_id}"
    return authenticated_request("DELETE", url)


# ---------- 收款记录（/payment/receipt）----------
def finance_payment_receipt_create(order_id: int, customer_id: int, project_id: int,
                                   receipt_type: str, receipt_amount: float,
                                   receipt_untax_amt: float, receipt_tax: float,
                                   receipt_total_amt: float, receipt_principal: float,
                                   receipt_agency_fee: float, account_id: int,
                                   payment_method: str, bank_account_no: str = None,
                                   payer_name: str = None, remark: str = None,
                                   receipt_no: str = None):
    """
    创建收款记录（POST /api/finance/payment/receipt/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param receipt_type: 收款类型（定金/首付/分期/面积补差/车位款/储藏室款/其他，必填）
    :param receipt_amount: 收款金额（必填）
    :param receipt_untax_amt: 收款不含税金额（必填）
    :param receipt_tax: 收款税额（必填）
    :param receipt_total_amt: 收款含税总金额（必填）
    :param receipt_principal: 不含税本金（必填）
    :param receipt_agency_fee: 代收款项（必填）
    :param account_id: 收款账户ID（必填）
    :param payment_method: 支付方式（现金/转账/微信/支付宝/POS刷卡/银行按揭/银行汇票，必填）
    :param bank_account_no: 付款人银行账号
    :param payer_name: 付款人姓名
    :param remark: 备注
    :param receipt_no: 收据编号（系统自动生成，无需传入）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/receipt/create"
    payload = _compact({
        "order_id": order_id, "customer_id": customer_id, "project_id": project_id,
        "receipt_type": receipt_type, "receipt_amount": receipt_amount,
        "receipt_untax_amt": receipt_untax_amt, "receipt_tax": receipt_tax,
        "receipt_total_amt": receipt_total_amt, "receipt_principal": receipt_principal,
        "receipt_agency_fee": receipt_agency_fee, "account_id": account_id,
        "payment_method": payment_method, "bank_account_no": bank_account_no,
        "payer_name": payer_name, "remark": remark, "receipt_no": receipt_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_payment_receipt_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取收款记录列表（GET /api/finance/payment/receipt/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/receipt/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_payment_receipt_get(receipt_id: int):
    """
    获取收款记录详情（GET /api/finance/payment/receipt/{id}）
    :param receipt_id: 收款记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/receipt/{receipt_id}"
    return authenticated_request("GET", url)


def finance_payment_receipt_update(receipt_id: int, receipt_no: str = None,
                                   receipt_type: int = None, receipt_amount: float = None,
                                   receipt_untax_amt: float = None, receipt_tax: float = None,
                                   receipt_total_amt: float = None, receipt_principal: float = None,
                                   receipt_agency_fee: float = None, account_id: int = None,
                                   payment_method: int = None, bank_account_no: str = None,
                                   payer_name: str = None, remark: str = None):
    """
    更新收款记录（PUT /api/finance/payment/receipt/{id}）
    :param receipt_id: 收款记录ID
    :param receipt_no: 收据编号
    :param receipt_type: 收款类型（int枚举，与创建时字符串对应）
    :param receipt_amount: 收款金额
    :param receipt_untax_amt: 收款不含税金额
    :param receipt_tax: 收款税额
    :param receipt_total_amt: 收款含税总金额
    :param receipt_principal: 不含税本金
    :param receipt_agency_fee: 代收款项
    :param account_id: 收款账户ID
    :param payment_method: 支付方式（int枚举，与创建时字符串对应）
    :param bank_account_no: 付款人银行账号
    :param payer_name: 付款人姓名
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/receipt/{receipt_id}"
    payload = _compact({
        "receipt_no": receipt_no, "receipt_type": receipt_type,
        "receipt_amount": receipt_amount, "receipt_untax_amt": receipt_untax_amt,
        "receipt_tax": receipt_tax, "receipt_total_amt": receipt_total_amt,
        "receipt_principal": receipt_principal, "receipt_agency_fee": receipt_agency_fee,
        "account_id": account_id, "payment_method": payment_method,
        "bank_account_no": bank_account_no, "payer_name": payer_name, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_payment_receipt_delete(receipt_id: int):
    """
    删除收款记录（DELETE /api/finance/payment/receipt/{id}）
    :param receipt_id: 收款记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/receipt/{receipt_id}"
    return authenticated_request("DELETE", url)


# ---------- 退款记录（/payment/refund）----------
def finance_payment_refund_create(order_id: int, customer_id: int, project_id: int,
                                  refund_type: str, refund_amount: float,
                                  untax_refund_principal: float, refund_tax: float,
                                  refund_total_amt: float, refund_agency_fee: float,
                                  refund_reason: str, account_id: int,
                                  remark: str = None, refund_no: str = None):
    """
    创建退款记录（POST /api/finance/payment/refund/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param refund_type: 退款类型（退房退款/其他，必填）
    :param refund_amount: 退款金额（必填）
    :param untax_refund_principal: 不含税退款本金（必填）
    :param refund_tax: 退款税额（必填）
    :param refund_total_amt: 退款含税总金额（必填）
    :param refund_agency_fee: 代退款项（必填）
    :param refund_reason: 退款原因（必填）
    :param account_id: 退款账户ID（必填）
    :param remark: 备注
    :param refund_no: 退款编号（系统自动生成，无需传入）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/refund/create"
    payload = _compact({
        "order_id": order_id, "customer_id": customer_id, "project_id": project_id,
        "refund_type": refund_type, "refund_amount": refund_amount,
        "untax_refund_principal": untax_refund_principal, "refund_tax": refund_tax,
        "refund_total_amt": refund_total_amt, "refund_agency_fee": refund_agency_fee,
        "refund_reason": refund_reason, "account_id": account_id,
        "remark": remark, "refund_no": refund_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_payment_refund_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取退款记录列表（GET /api/finance/payment/refund/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/refund/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_payment_refund_get(refund_id: int):
    """
    获取退款记录详情（GET /api/finance/payment/refund/{id}）
    :param refund_id: 退款记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/refund/{refund_id}"
    return authenticated_request("GET", url)


def finance_payment_refund_update(refund_id: int, refund_no: str = None,
                                  refund_type: int = None, refund_amount: float = None,
                                  untax_refund_principal: float = None, refund_tax: float = None,
                                  refund_total_amt: float = None, refund_agency_fee: float = None,
                                  refund_reason: str = None, account_id: int = None,
                                  remark: str = None):
    """
    更新退款记录（PUT /api/finance/payment/refund/{id}）
    :param refund_id: 退款记录ID
    :param refund_no: 退款编号
    :param refund_type: 退款类型（int枚举，与创建时字符串对应）
    :param refund_amount: 退款金额
    :param untax_refund_principal: 不含税退款本金
    :param refund_tax: 退款税额
    :param refund_total_amt: 退款含税总金额
    :param refund_agency_fee: 代退款项
    :param refund_reason: 退款原因
    :param account_id: 退款账户ID
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/refund/{refund_id}"
    payload = _compact({
        "refund_no": refund_no, "refund_type": refund_type,
        "refund_amount": refund_amount,
        "untax_refund_principal": untax_refund_principal, "refund_tax": refund_tax,
        "refund_total_amt": refund_total_amt, "refund_agency_fee": refund_agency_fee,
        "refund_reason": refund_reason, "account_id": account_id, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_payment_refund_delete(refund_id: int):
    """
    删除退款记录（DELETE /api/finance/payment/refund/{id}）
    :param refund_id: 退款记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/refund/{refund_id}"
    return authenticated_request("DELETE", url)


# ---------- 认筹定金台账（/payment/deposit）----------
def finance_payment_deposit_create(customer_id: int, project_id: int, deposit_type: str,
                                   deposit_total_amt: float, deposit_untax_amt: float,
                                   deposit_tax: float, account_id: int, payment_method: str,
                                   expire_date: str = None, remark: str = None,
                                   deposit_no: str = None):
    """
    创建认筹定金台账（POST /api/finance/payment/deposit/create）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param deposit_type: 定金类型（认筹金/购房定金，必填）
    :param deposit_total_amt: 定金含税总金额（必填）
    :param deposit_untax_amt: 定金不含税金额（必填）
    :param deposit_tax: 定金税额（必填）
    :param account_id: 账户ID（必填）
    :param payment_method: 支付方式（现金/银行卡/微信/支付宝/POS/银行转账，必填）
    :param expire_date: 有效期截止日期
    :param remark: 备注
    :param deposit_no: 定金编号（系统自动生成，无需传入）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/deposit/create"
    payload = _compact({
        "customer_id": customer_id, "project_id": project_id,
        "deposit_type": deposit_type, "deposit_total_amt": deposit_total_amt,
        "deposit_untax_amt": deposit_untax_amt, "deposit_tax": deposit_tax,
        "account_id": account_id, "payment_method": payment_method,
        "expire_date": expire_date, "remark": remark, "deposit_no": deposit_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_payment_deposit_list(page: int = 1, page_size: int = 20, customer_name: str = None):
    """
    获取认筹定金台账列表（GET /api/finance/payment/deposit/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param customer_name: 客户名称（可选，用于搜索）
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/deposit/list"
    params = _compact({"page": page, "page_size": page_size, "customer_name": customer_name})
    return authenticated_request("GET", url, params=params)


def finance_payment_deposit_get(deposit_id: int):
    """
    获取认筹定金台账详情（GET /api/finance/payment/deposit/{id}）
    :param deposit_id: 认筹定金台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/deposit/{deposit_id}"
    return authenticated_request("GET", url)


def finance_payment_deposit_update(deposit_id: int, deposit_total_amt: float = None,
                                   deposit_untax_amt: float = None, deposit_tax: float = None,
                                   expire_date: str = None, remark: str = None):
    """
    更新认筹定金台账（PUT /api/finance/payment/deposit/{id}）
    :param deposit_id: 认筹定金台账ID
    :param deposit_total_amt: 定金含税总金额
    :param deposit_untax_amt: 定金不含税金额
    :param deposit_tax: 定金税额
    :param expire_date: 有效期截止日期
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/deposit/{deposit_id}"
    payload = _compact({
        "deposit_total_amt": deposit_total_amt, "deposit_untax_amt": deposit_untax_amt,
        "deposit_tax": deposit_tax, "expire_date": expire_date, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_payment_deposit_delete(deposit_id: int):
    """
    删除认筹定金台账（DELETE /api/finance/payment/deposit/{id}）
    :param deposit_id: 认筹定金台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_PAYMENT}/deposit/{deposit_id}"
    return authenticated_request("DELETE", url)


# =====================================================================
# 三、票据税务合规（/api/finance/invoice）
# =====================================================================

# ---------- 蓝字发票（/invoice/blue）----------
def finance_invoice_blue_create(order_id: int, customer_id: int, project_id: int,
                                invoice_type: str, invoice_amount: float, tax_amount: float,
                                total_amount: float, tax_rate_id: int, invoice_date: str,
                                customer_name: str, customer_tax_no: str = None,
                                customer_address: str = None, customer_phone: str = None,
                                remark: str = None, invoice_no: str = None):
    """
    创建蓝字发票（POST /api/finance/invoice/blue/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param invoice_type: 发票类型（增值税普通发票/增值税专用发票，必填）
    :param invoice_amount: 发票金额（必填）
    :param tax_amount: 税额（必填）
    :param total_amount: 价税合计（必填）
    :param tax_rate_id: 税率ID（必填）
    :param invoice_date: 开票日期（必填，如 2026-01-01 00:00:00）
    :param customer_name: 客户名称（必填）
    :param customer_tax_no: 客户税号
    :param customer_address: 客户地址
    :param customer_phone: 客户电话
    :param remark: 备注
    :param invoice_no: 发票编号（不传则自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/blue/create"
    payload = _compact({
        "invoice_no": invoice_no, "order_id": order_id, "customer_id": customer_id,
        "project_id": project_id, "invoice_type": invoice_type,
        "invoice_amount": invoice_amount, "tax_amount": tax_amount,
        "total_amount": total_amount, "tax_rate_id": tax_rate_id,
        "invoice_date": invoice_date, "customer_name": customer_name,
        "customer_tax_no": customer_tax_no, "customer_address": customer_address,
        "customer_phone": customer_phone, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_invoice_blue_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取蓝字发票列表（GET /api/finance/invoice/blue/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/blue/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_invoice_blue_get(invoice_id: int):
    """
    获取蓝字发票详情（GET /api/finance/invoice/blue/{id}）
    :param invoice_id: 蓝字发票ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/blue/{invoice_id}"
    return authenticated_request("GET", url)


def finance_invoice_blue_update(invoice_id: int, invoice_amount: float = None,
                                tax_amount: float = None, total_amount: float = None,
                                customer_name: str = None, customer_tax_no: str = None,
                                customer_address: str = None, customer_phone: str = None,
                                remark: str = None):
    """
    更新蓝字发票（PUT /api/finance/invoice/blue/{id}）
    :param invoice_id: 蓝字发票ID
    :param invoice_amount: 发票金额
    :param tax_amount: 税额
    :param total_amount: 价税合计
    :param customer_name: 客户名称
    :param customer_tax_no: 客户税号
    :param customer_address: 客户地址
    :param customer_phone: 客户电话
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/blue/{invoice_id}"
    payload = _compact({
        "invoice_amount": invoice_amount, "tax_amount": tax_amount,
        "total_amount": total_amount, "customer_name": customer_name,
        "customer_tax_no": customer_tax_no, "customer_address": customer_address,
        "customer_phone": customer_phone, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_invoice_blue_delete(invoice_id: int):
    """
    删除蓝字发票（DELETE /api/finance/invoice/blue/{id}）
    :param invoice_id: 蓝字发票ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/blue/{invoice_id}"
    return authenticated_request("DELETE", url)


# ---------- 红字发票（/invoice/red）----------
def finance_invoice_red_create(original_invoice_id: int, red_reason: str,
                               invoice_amount: float, tax_amount: float,
                               total_amount: float, red_no: str = None):
    """
    创建红字发票（POST /api/finance/invoice/red/create）
    :param original_invoice_id: 原蓝字发票ID（必填）
    :param red_reason: 冲销原因（必填）
    :param invoice_amount: 冲销金额（必填）
    :param tax_amount: 冲销税额（必填）
    :param total_amount: 价税合计（必填）
    :param red_no: 红字发票编号（不传则自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/red/create"
    payload = _compact({
        "red_no": red_no, "original_invoice_id": original_invoice_id,
        "red_reason": red_reason, "invoice_amount": invoice_amount,
        "tax_amount": tax_amount, "total_amount": total_amount,
    })
    return authenticated_request("POST", url, json=payload)


def finance_invoice_red_list(page: int = 1, page_size: int = 20, original_invoice_id: int = None):
    """
    获取红字发票列表（GET /api/finance/invoice/red/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param original_invoice_id: 原蓝字发票ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/red/list"
    params = _compact({"page": page, "page_size": page_size,
                       "original_invoice_id": original_invoice_id})
    return authenticated_request("GET", url, params=params)


def finance_invoice_red_get(red_id: int):
    """
    获取红字发票详情（GET /api/finance/invoice/red/{id}）
    :param red_id: 红字发票ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/red/{red_id}"
    return authenticated_request("GET", url)


def finance_invoice_red_update(red_id: int, red_reason: str = None,
                               invoice_amount: float = None, tax_amount: float = None,
                               total_amount: float = None):
    """
    更新红字发票（PUT /api/finance/invoice/red/{id}）
    :param red_id: 红字发票ID
    :param red_reason: 冲销原因
    :param invoice_amount: 冲销金额
    :param tax_amount: 冲销税额
    :param total_amount: 价税合计
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/red/{red_id}"
    payload = _compact({
        "red_reason": red_reason, "invoice_amount": invoice_amount,
        "tax_amount": tax_amount, "total_amount": total_amount,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_invoice_red_delete(red_id: int):
    """
    删除红字发票（DELETE /api/finance/invoice/red/{id}）
    :param red_id: 红字发票ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/red/{red_id}"
    return authenticated_request("DELETE", url)


# ---------- 内部收据（/invoice/receipt）----------
def finance_invoice_receipt_create(order_id: int, customer_id: int, receipt_amount: float,
                                   receipt_type: str, payer_name: str,
                                   payer_phone: str = None, remark: str = None,
                                   receipt_no: str = None):
    """
    创建内部收据（POST /api/finance/invoice/receipt/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param receipt_amount: 收据金额（必填）
    :param receipt_type: 收据类型（必填）
    :param payer_name: 付款人（必填）
    :param payer_phone: 付款人电话
    :param remark: 备注
    :param receipt_no: 收据编号（不传则自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/receipt/create"
    payload = _compact({
        "receipt_no": receipt_no, "order_id": order_id, "customer_id": customer_id,
        "receipt_amount": receipt_amount, "receipt_type": receipt_type,
        "payer_name": payer_name, "payer_phone": payer_phone, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_invoice_receipt_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取内部收据列表（GET /api/finance/invoice/receipt/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/receipt/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_invoice_receipt_get(receipt_id: int):
    """
    获取内部收据详情（GET /api/finance/invoice/receipt/{id}）
    :param receipt_id: 内部收据ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/receipt/{receipt_id}"
    return authenticated_request("GET", url)


def finance_invoice_receipt_update(receipt_id: int, receipt_amount: float = None,
                                   payer_name: str = None, payer_phone: str = None,
                                   remark: str = None):
    """
    更新内部收据（PUT /api/finance/invoice/receipt/{id}）
    :param receipt_id: 内部收据ID
    :param receipt_amount: 收据金额
    :param payer_name: 付款人
    :param payer_phone: 付款人电话
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/receipt/{receipt_id}"
    payload = _compact({
        "receipt_amount": receipt_amount, "payer_name": payer_name,
        "payer_phone": payer_phone, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_invoice_receipt_delete(receipt_id: int):
    """
    删除内部收据（DELETE /api/finance/invoice/receipt/{id}）
    :param receipt_id: 内部收据ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/receipt/{receipt_id}"
    return authenticated_request("DELETE", url)


# ---------- 维修基金台账（/invoice/maintenance-fund）----------
def finance_invoice_maintenance_fund_create(order_id: int, customer_id: int, project_id: int,
                                            house_id: int, house_area: float, unit_price: float,
                                            total_amount: float, pay_status: str = None,
                                            remark: str = None, fund_no: str = None):
    """
    创建维修基金台账（POST /api/finance/invoice/maintenance-fund/create）
    :param order_id: 销售订单ID（必填）
    :param customer_id: 客户ID（必填）
    :param project_id: 楼盘ID（必填）
    :param house_id: 房源ID（必填）
    :param house_area: 房屋面积（必填）
    :param unit_price: 单价（必填）
    :param total_amount: 总金额（必填）
    :param pay_status: 缴纳状态（默认"未缴纳"）
    :param remark: 备注
    :param fund_no: 维修基金单据编号（不传则自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/maintenance-fund/create"
    payload = _compact({
        "fund_no": fund_no, "order_id": order_id, "customer_id": customer_id,
        "project_id": project_id, "house_id": house_id, "house_area": house_area,
        "unit_price": unit_price, "total_amount": total_amount,
        "pay_status": pay_status, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_invoice_maintenance_fund_list(page: int = 1, page_size: int = 20, contract_id: int = None):
    """
    获取维修基金台账列表（GET /api/finance/invoice/maintenance-fund/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param contract_id: 合同ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/maintenance-fund/list"
    params = _compact({"page": page, "page_size": page_size, "contract_id": contract_id})
    return authenticated_request("GET", url, params=params)


def finance_invoice_maintenance_fund_get(fund_id: int):
    """
    获取维修基金台账详情（GET /api/finance/invoice/maintenance-fund/{id}）
    :param fund_id: 维修基金台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/maintenance-fund/{fund_id}"
    return authenticated_request("GET", url)


def finance_invoice_maintenance_fund_update(fund_id: int, pay_status: str = None,
                                            remark: str = None):
    """
    更新维修基金台账（PUT /api/finance/invoice/maintenance-fund/{id}）
    :param fund_id: 维修基金台账ID
    :param pay_status: 缴纳状态
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/maintenance-fund/{fund_id}"
    payload = _compact({"pay_status": pay_status, "remark": remark})
    return authenticated_request("PUT", url, json=payload)


def finance_invoice_maintenance_fund_delete(fund_id: int):
    """
    删除维修基金台账（DELETE /api/finance/invoice/maintenance-fund/{id}）
    :param fund_id: 维修基金台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/maintenance-fund/{fund_id}"
    return authenticated_request("DELETE", url)


# ---------- 税务申报记录（/invoice/tax-declaration）----------
def finance_invoice_tax_declaration_create(project_id: int, declare_month: str,
                                           declare_type: str, invoice_total: float,
                                           tax_total: float, declare_amount: float,
                                           declare_date: str, remark: str = None,
                                           declare_no: str = None):
    """
    创建税务申报记录（POST /api/finance/invoice/tax-declaration/create）
    :param project_id: 楼盘ID（必填）
    :param declare_month: 申报月份（必填，如 2026-01）
    :param declare_type: 申报类型（必填）
    :param invoice_total: 开票总额（必填）
    :param tax_total: 税额总额（必填）
    :param declare_amount: 申报金额（必填）
    :param declare_date: 申报日期（必填，如 2026-01-15 00:00:00）
    :param remark: 备注
    :param declare_no: 申报编号（不传则自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/tax-declaration/create"
    payload = _compact({
        "declare_no": declare_no, "project_id": project_id,
        "declare_month": declare_month, "declare_type": declare_type,
        "invoice_total": invoice_total, "tax_total": tax_total,
        "declare_amount": declare_amount, "declare_date": declare_date, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_invoice_tax_declaration_list(page: int = 1, page_size: int = 20,
                                         year: int = None, month: int = None):
    """
    获取税务申报记录列表（GET /api/finance/invoice/tax-declaration/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param year: 申报年份（可选）
    :param month: 申报月份（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/tax-declaration/list"
    params = _compact({"page": page, "page_size": page_size, "year": year, "month": month})
    return authenticated_request("GET", url, params=params)


def finance_invoice_tax_declaration_get(declare_id: int):
    """
    获取税务申报记录详情（GET /api/finance/invoice/tax-declaration/{id}）
    :param declare_id: 税务申报记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/tax-declaration/{declare_id}"
    return authenticated_request("GET", url)


def finance_invoice_tax_declaration_update(declare_id: int, invoice_total: float = None,
                                           tax_total: float = None, declare_amount: float = None,
                                           declare_date: str = None, remark: str = None):
    """
    更新税务申报记录（PUT /api/finance/invoice/tax-declaration/{id}）
    :param declare_id: 税务申报记录ID
    :param invoice_total: 开票总额
    :param tax_total: 税额总额
    :param declare_amount: 申报金额
    :param declare_date: 申报日期
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/tax-declaration/{declare_id}"
    payload = _compact({
        "invoice_total": invoice_total, "tax_total": tax_total,
        "declare_amount": declare_amount, "declare_date": declare_date, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_invoice_tax_declaration_delete(declare_id: int):
    """
    删除税务申报记录（DELETE /api/finance/invoice/tax-declaration/{id}）
    :param declare_id: 税务申报记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_INVOICE}/tax-declaration/{declare_id}"
    return authenticated_request("DELETE", url)


# =====================================================================
# 四、佣金支付（/api/finance/commission）
# =====================================================================

# ---------- 佣金付款单（/commission/pay）----------
def finance_commission_pay_create(project_id: int, project_name: str, channel_id: int,
                                  channel_name: str, bank_info_id: int,
                                  project_fin_config_id: int, cost_subject_id: int,
                                  tax_tpl_id: int, pay_account_id: int, settle_cycle: str,
                                  settle_start: str, settle_end: str, settle_type: int,
                                  total_commission_untax: float, total_commission_tax: float,
                                  total_commission: float, actual_pay_untax: float,
                                  actual_pay_tax: float, actual_pay_amount: float,
                                  create_user_id: int, building_scope: str = None,
                                  refund_deduct_flag: int = None, deduct_amount: float = None,
                                  pay_file_url: str = None, remark: str = None):
    """
    创建佣金付款单（POST /api/finance/commission/pay/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param channel_id: 分销渠道ID（必填）
    :param channel_name: 渠道名称（必填）
    :param bank_info_id: 渠道对公收款账户ID（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 营销费用成本科目ID（必填）
    :param tax_tpl_id: 渠道服务费进项税率模板ID（必填）
    :param pay_account_id: 我方付款账户ID（必填）
    :param settle_cycle: 结算周期文本（必填）
    :param settle_start: 结算周期起始日（必填，如 2026-01-01）
    :param settle_end: 结算周期截止日（必填，如 2026-01-31）
    :param settle_type: 结算类型：1按月结算 2按回款结算（必填）
    :param total_commission_untax: 应付佣金不含税总额（必填）
    :param total_commission_tax: 渠道服务费进项税额（必填）
    :param total_commission: 应付佣金含税总金额（必填）
    :param actual_pay_untax: 实付不含税佣金（必填）
    :param actual_pay_tax: 实付对应进项税额（必填）
    :param actual_pay_amount: 实际含税应付付款金额（必填）
    :param create_user_id: 结算制单人ID（必填）
    :param building_scope: 结算覆盖楼栋ID，逗号分隔
    :param refund_deduct_flag: 是否包含退房扣佣：0不含 1包含（默认0）
    :param deduct_amount: 退房/违规扣减含税总额（默认0）
    :param pay_file_url: 结算单附件URL
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/pay/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_scope": building_scope, "channel_id": channel_id,
        "channel_name": channel_name, "bank_info_id": bank_info_id,
        "project_fin_config_id": project_fin_config_id, "cost_subject_id": cost_subject_id,
        "tax_tpl_id": tax_tpl_id, "pay_account_id": pay_account_id,
        "settle_cycle": settle_cycle, "settle_start": settle_start,
        "settle_end": settle_end, "settle_type": settle_type,
        "refund_deduct_flag": refund_deduct_flag,
        "total_commission_untax": total_commission_untax,
        "total_commission_tax": total_commission_tax,
        "total_commission": total_commission, "deduct_amount": deduct_amount,
        "actual_pay_untax": actual_pay_untax, "actual_pay_tax": actual_pay_tax,
        "actual_pay_amount": actual_pay_amount, "pay_file_url": pay_file_url,
        "remark": remark, "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_commission_pay_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                channel_id: int = None, audit_status: int = None,
                                pay_status: int = None):
    """
    获取佣金付款单列表（GET /api/finance/commission/pay/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param channel_id: 分销渠道ID（可选）
    :param audit_status: 审核状态：1待审核 2已通过 3已驳回 4作废（可选）
    :param pay_status: 付款状态：1待付款 2付款中 3付款完成 4付款失败退回（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/pay/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "channel_id": channel_id, "audit_status": audit_status,
                       "pay_status": pay_status})
    return authenticated_request("GET", url, params=params)


def finance_commission_pay_get(pay_id: int):
    """
    获取佣金付款单详情（GET /api/finance/commission/pay/{id}）
    :param pay_id: 佣金付款单ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/pay/{pay_id}"
    return authenticated_request("GET", url)


def finance_commission_pay_update(pay_id: int, building_scope: str = None,
                                  refund_deduct_flag: int = None, deduct_amount: float = None,
                                  actual_pay_untax: float = None, actual_pay_tax: float = None,
                                  actual_pay_amount: float = None, audit_status: int = None,
                                  pay_status: int = None, pay_time: str = None,
                                  audit_user_id: int = None, pay_user_id: int = None,
                                  bank_flow_id: int = None, bank_flow_no: str = None,
                                  voucher_no: str = None, pay_file_url: str = None,
                                  remark: str = None):
    """
    更新佣金付款单（PUT /api/finance/commission/pay/{id}）
    :param pay_id: 佣金付款单ID
    :param building_scope: 结算覆盖楼栋ID
    :param refund_deduct_flag: 是否包含退房扣佣
    :param deduct_amount: 扣减含税总额
    :param actual_pay_untax: 实付不含税佣金
    :param actual_pay_tax: 实付对应进项税额
    :param actual_pay_amount: 实际含税应付付款金额
    :param audit_status: 审核状态：1待审核 2已通过 3已驳回 4作废
    :param pay_status: 付款状态：1待付款 2付款中 3付款完成 4付款失败退回
    :param pay_time: 银行实际付款出账时间
    :param audit_user_id: 财务审核人ID
    :param pay_user_id: 出纳付款操作人ID
    :param bank_flow_id: 付款对应银行流水ID
    :param bank_flow_no: 银行流水单号
    :param voucher_no: 营销费用财务凭证编号
    :param pay_file_url: 结算单附件URL
    :param remark: 备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/pay/{pay_id}"
    payload = _compact({
        "building_scope": building_scope, "refund_deduct_flag": refund_deduct_flag,
        "deduct_amount": deduct_amount, "actual_pay_untax": actual_pay_untax,
        "actual_pay_tax": actual_pay_tax, "actual_pay_amount": actual_pay_amount,
        "audit_status": audit_status, "pay_status": pay_status, "pay_time": pay_time,
        "audit_user_id": audit_user_id, "pay_user_id": pay_user_id,
        "bank_flow_id": bank_flow_id, "bank_flow_no": bank_flow_no,
        "voucher_no": voucher_no, "pay_file_url": pay_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_commission_pay_delete(pay_id: int):
    """
    删除佣金付款单（DELETE /api/finance/commission/pay/{id}）
    :param pay_id: 佣金付款单ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/pay/{pay_id}"
    return authenticated_request("DELETE", url)


# ---------- 佣金扣罚记录（/commission/deduct）----------
def finance_commission_deduct_create(project_id: int, project_name: str, building_id: int,
                                     building_name: str, house_id: int, house_no: str,
                                     contract_id: int, sales_user_id: int, sales_user_name: str,
                                     channel_id: int, channel_name: str, deduct_type: int,
                                     relate_biz_id: int, deduct_untax_amt: float,
                                     deduct_tax_amt: float, deduct_amount: float,
                                     create_user_id: int, commission_pay_id: int = None,
                                     relate_biz_type: int = None, remark: str = None):
    """
    创建佣金扣罚记录（POST /api/finance/commission/deduct/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param building_id: 楼栋ID（必填）
    :param building_name: 楼栋名称（必填）
    :param house_id: 房源ID（必填）
    :param house_no: 房号（必填）
    :param contract_id: 对应退房购房合同ID（必填）
    :param sales_user_id: 成交置业顾问员工ID（必填）
    :param sales_user_name: 置业顾问姓名（必填）
    :param channel_id: 分销渠道ID（必填）
    :param channel_name: 渠道名称（必填）
    :param deduct_type: 扣罚类型：1客户退房 2业绩不达标 3渠道违规罚款（必填）
    :param relate_biz_id: 关联业务单据ID（必填）
    :param deduct_untax_amt: 扣罚不含税佣金金额（必填）
    :param deduct_tax_amt: 对应进项税额转出金额（必填）
    :param deduct_amount: 扣罚含税总金额（必填）
    :param create_user_id: 扣罚记录制单人ID（必填）
    :param commission_pay_id: 归属佣金汇总付款单ID
    :param relate_biz_type: 关联单据类型：1购房合同 2认购单（默认1）
    :param remark: 扣罚详细原因
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/deduct/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "house_id": house_id, "house_no": house_no, "contract_id": contract_id,
        "sales_user_id": sales_user_id, "sales_user_name": sales_user_name,
        "channel_id": channel_id, "channel_name": channel_name,
        "commission_pay_id": commission_pay_id, "deduct_type": deduct_type,
        "relate_biz_type": relate_biz_type, "relate_biz_id": relate_biz_id,
        "deduct_untax_amt": deduct_untax_amt, "deduct_tax_amt": deduct_tax_amt,
        "deduct_amount": deduct_amount, "remark": remark,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_commission_deduct_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                   channel_id: int = None, deduct_type: int = None,
                                   deduct_status: int = None):
    """
    获取佣金扣罚记录列表（GET /api/finance/commission/deduct/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param channel_id: 分销渠道ID（可选）
    :param deduct_type: 扣罚类型：1客户退房 2业绩不达标 3渠道违规罚款（可选）
    :param deduct_status: 扣罚状态：1待确认 2已确认抵扣佣金付款单（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/deduct/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "channel_id": channel_id, "deduct_type": deduct_type,
                       "deduct_status": deduct_status})
    return authenticated_request("GET", url, params=params)


def finance_commission_deduct_get(deduct_id: int):
    """
    获取佣金扣罚记录详情（GET /api/finance/commission/deduct/{id}）
    :param deduct_id: 佣金扣罚记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/deduct/{deduct_id}"
    return authenticated_request("GET", url)


def finance_commission_deduct_update(deduct_id: int, commission_pay_id: int = None,
                                     deduct_status: int = None, remark: str = None):
    """
    更新佣金扣罚记录（PUT /api/finance/commission/deduct/{id}）
    :param deduct_id: 佣金扣罚记录ID
    :param commission_pay_id: 归属佣金汇总付款单ID
    :param deduct_status: 扣罚状态：1待确认 2已确认抵扣佣金付款单
    :param remark: 扣罚详细原因
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/deduct/{deduct_id}"
    payload = _compact({
        "commission_pay_id": commission_pay_id, "deduct_status": deduct_status,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_commission_deduct_delete(deduct_id: int):
    """
    删除佣金扣罚记录（DELETE /api/finance/commission/deduct/{id}）
    :param deduct_id: 佣金扣罚记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/deduct/{deduct_id}"
    return authenticated_request("DELETE", url)


# ---------- 销售提成支付明细（/commission/sales）----------
def finance_commission_sales_create(project_id: int, project_name: str, building_id: int,
                                    building_name: str, house_id: int, house_no: str,
                                    contract_id: int, order_id: int, employee_id: int,
                                    employee_name: str, project_fin_config_id: int,
                                    cost_subject_id: int, commission_untax: float,
                                    commission_amount: float, create_user_id: int,
                                    commission_tax: float = None, remark: str = None):
    """
    创建销售提成支付明细（POST /api/finance/commission/sales/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param building_id: 楼栋ID（必填）
    :param building_name: 楼栋名称（必填）
    :param house_id: 房源ID（必填）
    :param house_no: 房号（必填）
    :param contract_id: 购房合同ID（必填）
    :param order_id: 认购订单ID（必填）
    :param employee_id: 成交销售员工ID（必填）
    :param employee_name: 销售姓名（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 销售提成费用科目ID（必填）
    :param commission_untax: 提成不含税金额（必填）
    :param commission_amount: 提成含税总金额（必填）
    :param create_user_id: 提成计算制单人ID（必填）
    :param commission_tax: 提成对应个税/服务费税额（默认0）
    :param remark: 提成计算规则备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/sales/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "house_id": house_id, "house_no": house_no, "contract_id": contract_id,
        "order_id": order_id, "employee_id": employee_id, "employee_name": employee_name,
        "project_fin_config_id": project_fin_config_id, "cost_subject_id": cost_subject_id,
        "commission_untax": commission_untax, "commission_tax": commission_tax,
        "commission_amount": commission_amount, "remark": remark,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_commission_sales_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                  employee_id: int = None, commission_status: int = None):
    """
    获取销售提成支付列表（GET /api/finance/commission/sales/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param employee_id: 销售员工ID（可选）
    :param commission_status: 提成状态：1待结算 2已汇总至付款单 3已完成代发支付（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/sales/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "employee_id": employee_id, "commission_status": commission_status})
    return authenticated_request("GET", url, params=params)


def finance_commission_sales_get(sales_id: int):
    """
    获取销售提成支付详情（GET /api/finance/commission/sales/{id}）
    :param sales_id: 销售提成支付明细ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/sales/{sales_id}"
    return authenticated_request("GET", url)


def finance_commission_sales_update(sales_id: int, bonus_pay_id: int = None,
                                    commission_status: int = None, settle_time: str = None,
                                    pay_time: str = None, remark: str = None):
    """
    更新销售提成支付明细（PUT /api/finance/commission/sales/{id}）
    :param sales_id: 销售提成支付明细ID
    :param bonus_pay_id: 归属月度提成汇总付款单ID
    :param commission_status: 提成状态：1待结算 2已汇总至付款单 3已完成代发支付
    :param settle_time: 提成汇总结算时间
    :param pay_time: 银行代发实际支付时间
    :param remark: 提成计算规则备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/sales/{sales_id}"
    payload = _compact({
        "bonus_pay_id": bonus_pay_id, "commission_status": commission_status,
        "settle_time": settle_time, "pay_time": pay_time, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_commission_sales_delete(sales_id: int):
    """
    删除销售提成支付明细（DELETE /api/finance/commission/sales/{id}）
    :param sales_id: 销售提成支付明细ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/sales/{sales_id}"
    return authenticated_request("DELETE", url)


# ---------- 内部销售提成付款单（/commission/bonus）----------
def finance_commission_bonus_create(project_id: int, project_name: str, staff_id: int,
                                    staff_name: str, project_fin_config_id: int,
                                    cost_subject_id: int, pay_account_id: int,
                                    settle_cycle: str, settle_start: str, settle_end: str,
                                    total_bonus_untax: float, total_bonus_tax: float,
                                    total_bonus: float, actual_pay_untax: float,
                                    actual_pay_tax: float, actual_pay_amount: float,
                                    create_user_id: int, building_scope: str = None,
                                    deduct_amount: float = None, remark: str = None):
    """
    创建内部销售提成付款单（POST /api/finance/commission/bonus/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param staff_id: 销售员工ID（必填）
    :param staff_name: 员工姓名（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 销售提成费用科目ID（必填）
    :param pay_account_id: 我方代发付款账户ID（必填）
    :param settle_cycle: 结算周期文本（必填）
    :param settle_start: 结算周期起始日（必填，如 2026-01-01）
    :param settle_end: 结算周期截止日（必填，如 2026-01-31）
    :param total_bonus_untax: 应付提成不含税总额（必填）
    :param total_bonus_tax: 代扣个人所得税总额（必填）
    :param total_bonus: 应付提成含税总额（必填）
    :param actual_pay_untax: 实发不含税提成（必填）
    :param actual_pay_tax: 实发对应代扣个税（必填）
    :param actual_pay_amount: 银行代发实际净额（必填）
    :param create_user_id: 提成汇总制单人ID（必填）
    :param building_scope: 代发覆盖楼栋ID，逗号分隔
    :param deduct_amount: 扣款（迟到/违规）含税总额（默认0）
    :param remark: 月度提成代发备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/bonus/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_scope": building_scope, "staff_id": staff_id, "staff_name": staff_name,
        "project_fin_config_id": project_fin_config_id, "cost_subject_id": cost_subject_id,
        "pay_account_id": pay_account_id, "settle_cycle": settle_cycle,
        "settle_start": settle_start, "settle_end": settle_end,
        "total_bonus_untax": total_bonus_untax, "total_bonus_tax": total_bonus_tax,
        "total_bonus": total_bonus, "deduct_amount": deduct_amount,
        "actual_pay_untax": actual_pay_untax, "actual_pay_tax": actual_pay_tax,
        "actual_pay_amount": actual_pay_amount, "remark": remark,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_commission_bonus_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                  staff_id: int = None, audit_status: int = None,
                                  pay_status: int = None):
    """
    获取内部销售提成付款单列表（GET /api/finance/commission/bonus/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 楼盘ID（可选）
    :param staff_id: 销售员工ID（可选）
    :param audit_status: 审核状态：1待审核 2已通过 3已驳回 4作废（可选）
    :param pay_status: 代发状态：1待代发 2付款中 3代发完成 4代发失败退回（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/bonus/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "staff_id": staff_id, "audit_status": audit_status,
                       "pay_status": pay_status})
    return authenticated_request("GET", url, params=params)


def finance_commission_bonus_get(bonus_id: int):
    """
    获取内部销售提成付款单详情（GET /api/finance/commission/bonus/{id}）
    :param bonus_id: 内部销售提成付款单ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/bonus/{bonus_id}"
    return authenticated_request("GET", url)


def finance_commission_bonus_update(bonus_id: int, building_scope: str = None,
                                    deduct_amount: float = None, actual_pay_untax: float = None,
                                    actual_pay_tax: float = None, actual_pay_amount: float = None,
                                    audit_status: int = None, pay_status: int = None,
                                    pay_time: str = None, audit_user_id: int = None,
                                    pay_user_id: int = None, bank_flow_id: int = None,
                                    bank_flow_no: str = None, voucher_no: str = None,
                                    remark: str = None):
    """
    更新内部销售提成付款单（PUT /api/finance/commission/bonus/{id}）
    :param bonus_id: 内部销售提成付款单ID
    :param building_scope: 代发覆盖楼栋ID
    :param deduct_amount: 扣款含税总额
    :param actual_pay_untax: 实发不含税提成
    :param actual_pay_tax: 实发对应代扣个税
    :param actual_pay_amount: 银行代发实际净额
    :param audit_status: 审核状态：1待审核 2已通过 3已驳回 4作废
    :param pay_status: 代发状态：1待代发 2付款中 3代发完成 4代发失败退回
    :param pay_time: 银行代发完成时间
    :param audit_user_id: 财务审核人ID
    :param pay_user_id: 出纳代发操作人ID
    :param bank_flow_id: 代发对应银行流水ID
    :param bank_flow_no: 银行流水单号
    :param voucher_no: 销售费用财务凭证编号
    :param remark: 月度提成代发备注
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/bonus/{bonus_id}"
    payload = _compact({
        "building_scope": building_scope, "deduct_amount": deduct_amount,
        "actual_pay_untax": actual_pay_untax, "actual_pay_tax": actual_pay_tax,
        "actual_pay_amount": actual_pay_amount, "audit_status": audit_status,
        "pay_status": pay_status, "pay_time": pay_time, "audit_user_id": audit_user_id,
        "pay_user_id": pay_user_id, "bank_flow_id": bank_flow_id,
        "bank_flow_no": bank_flow_no, "voucher_no": voucher_no, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_commission_bonus_delete(bonus_id: int):
    """
    删除内部销售提成付款单（DELETE /api/finance/commission/bonus/{id}）
    :param bonus_id: 内部销售提成付款单ID
    """
    url = f"{BASE_URL}{API_FINANCE_COMMISSION}/bonus/{bonus_id}"
    return authenticated_request("DELETE", url)


# =====================================================================
# 五、项目成本（/api/finance/cost）
# =====================================================================

# ---------- 通用费用申请（事前审批，/cost/expense）----------
def finance_cost_expense_create(apply_user_id: int, apply_user_name: str,
                                expense_subject_id: int, expense_type: int, apply_time: str,
                                expense_start_date: str, expense_end_date: str,
                                total_amount: float, untax_amount: float, create_user_id: int,
                                project_id: int = None, project_name: str = None,
                                building_id: int = None, building_name: str = None,
                                dept_id: int = None, project_fin_config_id: int = None,
                                tax_tpl_id: int = None, tax_amount: float = None,
                                reimburse_id: int = None, expense_file_url: str = None,
                                remark: str = None, expense_no: str = None):
    """
    创建通用费用申请（POST /api/finance/cost/expense/create）
    :param apply_user_id: 申请人员工ID（必填）
    :param apply_user_name: 申请人姓名冗余（必填）
    :param expense_subject_id: 费用归属会计科目ID（必填）
    :param expense_type: 费用类型：1办公费 2差旅费 3业务招待 4营销杂费 5行政水电（必填）
    :param apply_time: 申请提交时间（必填，如 2026-01-01 10:00:00）
    :param expense_start_date: 费用发生起始日期（必填，如 2026-01-01）
    :param expense_end_date: 费用发生截止日期（必填，如 2026-01-31）
    :param total_amount: 申请含税总金额（必填）
    :param untax_amount: 申请不含税成本金额（必填）
    :param create_user_id: 单据制单人ID（必填）
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param dept_id: 申请人部门ID
    :param project_fin_config_id: 楼盘财务配置ID
    :param tax_tpl_id: 预计进项税率模板ID
    :param tax_amount: 预计可抵扣进项税额（默认0）
    :param reimburse_id: 核销后关联报销单ID
    :param expense_file_url: 申请预算说明、报价单附件OSS链接
    :param remark: 费用用途、分摊楼栋说明
    :param expense_no: 费用申请单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/expense/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "apply_user_id": apply_user_id, "apply_user_name": apply_user_name,
        "dept_id": dept_id, "project_fin_config_id": project_fin_config_id,
        "expense_subject_id": expense_subject_id, "tax_tpl_id": tax_tpl_id,
        "expense_type": expense_type, "apply_time": apply_time,
        "expense_start_date": expense_start_date, "expense_end_date": expense_end_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "reimburse_id": reimburse_id,
        "expense_file_url": expense_file_url, "remark": remark,
        "create_user_id": create_user_id, "expense_no": expense_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_cost_expense_list(page: int = 1, page_size: int = 20, project_id: int = None,
                              expense_type: int = None, audit_status: int = None):
    """
    获取通用费用申请列表（GET /api/finance/cost/expense/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 归属楼盘ID（可选）
    :param expense_type: 费用类型：1办公费 2差旅费 3业务招待 4营销杂费 5行政水电（可选）
    :param audit_status: 审核状态（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/expense/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "expense_type": expense_type, "audit_status": audit_status})
    return authenticated_request("GET", url, params=params)


def finance_cost_expense_get(expense_id: int):
    """
    获取通用费用申请详情（GET /api/finance/cost/expense/{id}）
    :param expense_id: 通用费用申请ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/expense/{expense_id}"
    return authenticated_request("GET", url)


def finance_cost_expense_update(expense_id: int, project_id: int = None,
                                project_name: str = None, building_id: int = None,
                                building_name: str = None, dept_id: int = None,
                                expense_subject_id: int = None, tax_tpl_id: int = None,
                                expense_type: int = None, expense_start_date: str = None,
                                expense_end_date: str = None, total_amount: float = None,
                                untax_amount: float = None, tax_amount: float = None,
                                expense_file_url: str = None, remark: str = None):
    """
    更新通用费用申请（PUT /api/finance/cost/expense/{id}）
    :param expense_id: 通用费用申请ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param dept_id: 申请人部门ID
    :param expense_subject_id: 费用归属会计科目ID
    :param tax_tpl_id: 预计进项税率模板ID
    :param expense_type: 费用类型
    :param expense_start_date: 费用发生起始日期
    :param expense_end_date: 费用发生截止日期
    :param total_amount: 申请含税总金额
    :param untax_amount: 申请不含税成本金额
    :param tax_amount: 预计可抵扣进项税额
    :param expense_file_url: 申请预算说明、报价单附件OSS链接
    :param remark: 费用用途、分摊楼栋说明
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/expense/{expense_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name, "dept_id": dept_id,
        "expense_subject_id": expense_subject_id, "tax_tpl_id": tax_tpl_id,
        "expense_type": expense_type, "expense_start_date": expense_start_date,
        "expense_end_date": expense_end_date, "total_amount": total_amount,
        "untax_amount": untax_amount, "tax_amount": tax_amount,
        "expense_file_url": expense_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_cost_expense_delete(expense_id: int):
    """
    删除通用费用申请（DELETE /api/finance/cost/expense/{id}）
    :param expense_id: 通用费用申请ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/expense/{expense_id}"
    return authenticated_request("DELETE", url)


# ---------- 费用报销（事后核销，/cost/reimbursement）----------
def finance_cost_reimbursement_create(employee_id: int, employee_name: str,
                                      expense_subject_id: int, tax_tpl_id: int,
                                      expense_type: int, reimburse_date: str,
                                      total_amount: float, untax_amount: float,
                                      actual_reimburse_amount: float, create_user_id: int,
                                      project_id: int = None, project_name: str = None,
                                      building_id: int = None, building_name: str = None,
                                      dept_id: int = None, cost_expense_id: int = None,
                                      project_fin_config_id: int = None, invoice_no: str = None,
                                      invoice_date: str = None, tax_amount: float = None,
                                      deduct_amount: float = None, cost_pay_id: int = None,
                                      voucher_no: str = None, reimburse_file_url: str = None,
                                      remark: str = None, reimburse_no: str = None):
    """
    创建费用报销（POST /api/finance/cost/reimbursement/create）
    :param employee_id: 报销员工ID（必填）
    :param employee_name: 报销人姓名冗余（必填）
    :param expense_subject_id: 费用会计科目ID（必填）
    :param tax_tpl_id: 发票进项税率模板ID（必填）
    :param expense_type: 费用类型：1办公费 2差旅费 3业务招待 4营销杂费 5行政水电（必填）
    :param reimburse_date: 费用实际发生日期（必填，如 2026-01-15）
    :param total_amount: 报销含税总金额（必填）
    :param untax_amount: 报销不含税入账成本（必填）
    :param actual_reimburse_amount: 实际应报销净额（必填）
    :param create_user_id: 报销单制单人ID（必填）
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param dept_id: 报销人部门ID
    :param cost_expense_id: 关联事前费用申请单ID
    :param project_fin_config_id: 楼盘财务配置ID
    :param invoice_no: 增值税发票号码
    :param invoice_date: 发票开具日期
    :param tax_amount: 可抵扣增值税进项税额（默认0）
    :param deduct_amount: 不予抵扣/个人扣款金额（默认0）
    :param cost_pay_id: 核销后关联费用付款单ID
    :param voucher_no: 费用报销财务凭证编号
    :param reimburse_file_url: 发票、行程单、消费凭证多附件链接
    :param remark: 费用用途、楼栋分摊、发票特殊说明
    :param reimburse_no: 报销单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/reimbursement/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "employee_id": employee_id, "employee_name": employee_name, "dept_id": dept_id,
        "cost_expense_id": cost_expense_id, "project_fin_config_id": project_fin_config_id,
        "expense_subject_id": expense_subject_id, "tax_tpl_id": tax_tpl_id,
        "expense_type": expense_type, "reimburse_date": reimburse_date,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "deduct_amount": deduct_amount,
        "actual_reimburse_amount": actual_reimburse_amount, "cost_pay_id": cost_pay_id,
        "voucher_no": voucher_no, "reimburse_file_url": reimburse_file_url,
        "remark": remark, "create_user_id": create_user_id, "reimburse_no": reimburse_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_cost_reimbursement_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                    employee_id: int = None, expense_type: int = None,
                                    audit_status: int = None):
    """
    获取费用报销列表（GET /api/finance/cost/reimbursement/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 归属楼盘ID（可选）
    :param employee_id: 报销员工ID（可选）
    :param expense_type: 费用类型（可选）
    :param audit_status: 审核状态（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/reimbursement/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "employee_id": employee_id, "expense_type": expense_type,
                       "audit_status": audit_status})
    return authenticated_request("GET", url, params=params)


def finance_cost_reimbursement_get(reimbursement_id: int):
    """
    获取费用报销详情（GET /api/finance/cost/reimbursement/{id}）
    :param reimbursement_id: 费用报销ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/reimbursement/{reimbursement_id}"
    return authenticated_request("GET", url)


def finance_cost_reimbursement_update(reimbursement_id: int, project_id: int = None,
                                      project_name: str = None, building_id: int = None,
                                      building_name: str = None, expense_subject_id: int = None,
                                      tax_tpl_id: int = None, expense_type: int = None,
                                      reimburse_date: str = None, invoice_no: str = None,
                                      invoice_date: str = None, total_amount: float = None,
                                      untax_amount: float = None, tax_amount: float = None,
                                      deduct_amount: float = None,
                                      actual_reimburse_amount: float = None,
                                      reimburse_file_url: str = None, remark: str = None):
    """
    更新费用报销（PUT /api/finance/cost/reimbursement/{id}）
    :param reimbursement_id: 费用报销ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param expense_subject_id: 费用会计科目ID
    :param tax_tpl_id: 发票进项税率模板ID
    :param expense_type: 费用类型
    :param reimburse_date: 费用实际发生日期
    :param invoice_no: 增值税发票号码
    :param invoice_date: 发票开具日期
    :param total_amount: 报销含税总金额
    :param untax_amount: 报销不含税入账成本
    :param tax_amount: 可抵扣增值税进项税额
    :param deduct_amount: 不予抵扣/个人扣款金额
    :param actual_reimburse_amount: 实际应报销净额
    :param reimburse_file_url: 发票、行程单、消费凭证多附件链接
    :param remark: 费用用途、楼栋分摊、发票特殊说明
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/reimbursement/{reimbursement_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "expense_subject_id": expense_subject_id, "tax_tpl_id": tax_tpl_id,
        "expense_type": expense_type, "reimburse_date": reimburse_date,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "deduct_amount": deduct_amount,
        "actual_reimburse_amount": actual_reimburse_amount,
        "reimburse_file_url": reimburse_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_cost_reimbursement_delete(reimbursement_id: int):
    """
    删除费用报销（DELETE /api/finance/cost/reimbursement/{id}）
    :param reimbursement_id: 费用报销ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/reimbursement/{reimbursement_id}"
    return authenticated_request("DELETE", url)


# ---------- 费用付款（资金执行层，/cost/payment）----------
def finance_cost_payment_create(account_id: int, account_name: str, cost_subject_id: int,
                                total_pay_untax: float, total_pay_amount: float,
                                pay_amount: float, pay_target_type: int, target_name: str,
                                create_user_id: int, project_id: int = None,
                                project_name: str = None, building_scope: str = None,
                                project_fin_config_id: int = None, reimburse_ids: str = None,
                                expense_ids: str = None, ad_cost_ids: str = None,
                                eng_cost_ids: str = None, total_pay_tax: float = None,
                                deduct_total: float = None, target_bank_info_id: int = None,
                                target_bank_card: str = None, bank_flow_id: int = None,
                                bank_flow_no: str = None, voucher_no: str = None,
                                pay_file_url: str = None, remark: str = None, pay_no: str = None):
    """
    创建费用付款（POST /api/finance/cost/payment/create）
    :param account_id: 我方付款账户ID（必填）
    :param account_name: 账户名称冗余（必填）
    :param cost_subject_id: 费用付款对应总账科目ID（必填）
    :param total_pay_untax: 本次付款不含税总成本汇总（必填）
    :param total_pay_amount: 应付含税付款总额（必填）
    :param pay_amount: 银行实际出账净额（必填）
    :param pay_target_type: 1内部员工报销 2外部供应商对公付款（必填）
    :param target_name: 收款户名（必填）
    :param create_user_id: 付款单制单人ID（必填）
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_scope: 本次付款分摊楼栋ID，逗号分隔
    :param project_fin_config_id: 楼盘财务配置ID
    :param reimburse_ids: 批量付款关联报销单ID集合
    :param expense_ids: 批量付款关联费用申请单ID集合
    :param ad_cost_ids: 批量付款关联广告成本ID集合
    :param eng_cost_ids: 批量付款关联工程成本ID集合
    :param total_pay_tax: 本次付款进项税总额汇总（默认0）
    :param deduct_total: 扣款合计金额（默认0）
    :param target_bank_info_id: 外部供应商对公账户ID
    :param target_bank_card: 员工报销收款银行卡
    :param bank_flow_id: 对应银行资金流水ID
    :param bank_flow_no: 银行流水单号冗余
    :param voucher_no: 费用付款财务凭证编号
    :param pay_file_url: 付款审批单、网银回单、批量代发明细附件
    :param remark: 批量付款汇总说明、付款失败原因备注
    :param pay_no: 付款单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/payment/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_scope": building_scope, "account_id": account_id,
        "account_name": account_name, "project_fin_config_id": project_fin_config_id,
        "cost_subject_id": cost_subject_id, "reimburse_ids": reimburse_ids,
        "expense_ids": expense_ids, "ad_cost_ids": ad_cost_ids,
        "eng_cost_ids": eng_cost_ids, "total_pay_untax": total_pay_untax,
        "total_pay_tax": total_pay_tax, "total_pay_amount": total_pay_amount,
        "deduct_total": deduct_total, "pay_amount": pay_amount,
        "pay_target_type": pay_target_type, "target_name": target_name,
        "target_bank_info_id": target_bank_info_id, "target_bank_card": target_bank_card,
        "bank_flow_id": bank_flow_id, "bank_flow_no": bank_flow_no,
        "voucher_no": voucher_no, "pay_file_url": pay_file_url, "remark": remark,
        "create_user_id": create_user_id, "pay_no": pay_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_cost_payment_list(page: int = 1, page_size: int = 20, project_id: int = None,
                              pay_target_type: int = None, audit_status: int = None,
                              pay_status: int = None):
    """
    获取费用付款列表（GET /api/finance/cost/payment/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 归属楼盘ID（可选）
    :param pay_target_type: 1内部员工报销 2外部供应商对公付款（可选）
    :param audit_status: 审核状态（可选）
    :param pay_status: 资金执行状态（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/payment/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "pay_target_type": pay_target_type, "audit_status": audit_status,
                       "pay_status": pay_status})
    return authenticated_request("GET", url, params=params)


def finance_cost_payment_get(payment_id: int):
    """
    获取费用付款详情（GET /api/finance/cost/payment/{id}）
    :param payment_id: 费用付款ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/payment/{payment_id}"
    return authenticated_request("GET", url)


def finance_cost_payment_update(payment_id: int, project_id: int = None,
                                project_name: str = None, building_scope: str = None,
                                account_id: int = None, account_name: str = None,
                                cost_subject_id: int = None, total_pay_untax: float = None,
                                total_pay_tax: float = None, total_pay_amount: float = None,
                                deduct_total: float = None, pay_amount: float = None,
                                pay_target_type: int = None, target_name: str = None,
                                pay_status: int = None, pay_time: str = None,
                                bank_flow_id: int = None, bank_flow_no: str = None,
                                voucher_no: str = None, pay_file_url: str = None,
                                remark: str = None):
    """
    更新费用付款（PUT /api/finance/cost/payment/{id}）
    :param payment_id: 费用付款ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_scope: 本次付款分摊楼栋ID，逗号分隔
    :param account_id: 我方付款账户ID
    :param account_name: 账户名称冗余
    :param cost_subject_id: 费用付款对应总账科目ID
    :param total_pay_untax: 本次付款不含税总成本汇总
    :param total_pay_tax: 本次付款进项税总额汇总
    :param total_pay_amount: 应付含税付款总额
    :param deduct_total: 扣款合计金额
    :param pay_amount: 银行实际出账净额
    :param pay_target_type: 1内部员工报销 2外部供应商对公付款
    :param target_name: 收款户名
    :param pay_status: 资金执行状态
    :param pay_time: 银行实际出账时间
    :param bank_flow_id: 对应银行资金流水ID
    :param bank_flow_no: 银行流水单号冗余
    :param voucher_no: 费用付款财务凭证编号
    :param pay_file_url: 付款审批单、网银回单、批量代发明细附件
    :param remark: 批量付款汇总说明、付款失败原因备注
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/payment/{payment_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_scope": building_scope, "account_id": account_id,
        "account_name": account_name, "cost_subject_id": cost_subject_id,
        "total_pay_untax": total_pay_untax, "total_pay_tax": total_pay_tax,
        "total_pay_amount": total_pay_amount, "deduct_total": deduct_total,
        "pay_amount": pay_amount, "pay_target_type": pay_target_type,
        "target_name": target_name, "pay_status": pay_status, "pay_time": pay_time,
        "bank_flow_id": bank_flow_id, "bank_flow_no": bank_flow_no,
        "voucher_no": voucher_no, "pay_file_url": pay_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_cost_payment_delete(payment_id: int):
    """
    删除费用付款（DELETE /api/finance/cost/payment/{id}）
    :param payment_id: 费用付款ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/payment/{payment_id}"
    return authenticated_request("DELETE", url)


# ---------- 广告推广成本（/cost/advertising）----------
def finance_cost_advertising_create(project_id: int, project_name: str, supplier_id: int,
                                    supplier_name: str, project_fin_config_id: int,
                                    cost_subject_id: int, tax_tpl_id: int, ad_type: int,
                                    ad_start_date: str, ad_end_date: str, cost_date: str,
                                    total_amount: float, untax_amount: float,
                                    actual_cost_amount: float, create_user_id: int,
                                    building_id: int = None, building_name: str = None,
                                    bank_info_id: int = None, ad_channel: str = None,
                                    ad_contract_id: int = None, invoice_no: str = None,
                                    invoice_date: str = None, tax_amount: float = None,
                                    deduct_amount: float = None, relate_pay_id: int = None,
                                    voucher_no: str = None, ad_file_url: str = None,
                                    remark: str = None, cost_no: str = None):
    """
    创建广告推广成本（POST /api/finance/cost/advertising/create）
    :param project_id: 归属楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param supplier_id: 广告渠道供应商ID（必填）
    :param supplier_name: 供应商名称冗余（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 营销费用会计科目ID（必填）
    :param tax_tpl_id: 广告服务进项税率模板ID（必填）
    :param ad_type: 广告类型：1线上媒体 2线下活动 3户外大牌 4分销推广（必填）
    :param ad_start_date: 广告投放起始日期（必填，如 2026-01-01）
    :param ad_end_date: 广告投放结束日期（必填，如 2026-01-31）
    :param cost_date: 成本入账归属日期（必填，如 2026-01-31）
    :param total_amount: 广告含税总金额（必填）
    :param untax_amount: 广告不含税营销成本（必填）
    :param actual_cost_amount: 应付实际成本净额（必填）
    :param create_user_id: 广告成本录入制单人ID（必填）
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param bank_info_id: 供应商对公收款账户ID
    :param ad_channel: 投放渠道名称
    :param ad_contract_id: 广告合作合同ID
    :param invoice_no: 广告服务费发票号码
    :param invoice_date: 发票开具日期
    :param tax_amount: 可抵扣进项税额（默认0）
    :param deduct_amount: 扣款、违约金金额（默认0）
    :param relate_pay_id: 核销后关联费用付款单ID
    :param voucher_no: 广告成本财务凭证编号
    :param ad_file_url: 广告合同、投放排期、发票、验收单附件
    :param remark: 投放内容、楼栋分摊比例、结算特殊约定
    :param cost_no: 广告成本单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/advertising/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "supplier_id": supplier_id, "supplier_name": supplier_name,
        "bank_info_id": bank_info_id, "project_fin_config_id": project_fin_config_id,
        "cost_subject_id": cost_subject_id, "tax_tpl_id": tax_tpl_id, "ad_type": ad_type,
        "ad_channel": ad_channel, "ad_contract_id": ad_contract_id,
        "ad_start_date": ad_start_date, "ad_end_date": ad_end_date, "cost_date": cost_date,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "deduct_amount": deduct_amount,
        "actual_cost_amount": actual_cost_amount, "relate_pay_id": relate_pay_id,
        "voucher_no": voucher_no, "ad_file_url": ad_file_url, "remark": remark,
        "create_user_id": create_user_id, "cost_no": cost_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_cost_advertising_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                  supplier_id: int = None, ad_type: int = None,
                                  cost_status: int = None):
    """
    获取广告推广成本列表（GET /api/finance/cost/advertising/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 归属楼盘ID（可选）
    :param supplier_id: 广告渠道供应商ID（可选）
    :param ad_type: 广告类型：1线上媒体 2线下活动 3户外大牌 4分销推广（可选）
    :param cost_status: 成本状态（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/advertising/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "supplier_id": supplier_id, "ad_type": ad_type,
                       "cost_status": cost_status})
    return authenticated_request("GET", url, params=params)


def finance_cost_advertising_get(cost_id: int):
    """
    获取广告推广成本详情（GET /api/finance/cost/advertising/{id}）
    :param cost_id: 广告推广成本ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/advertising/{cost_id}"
    return authenticated_request("GET", url)


def finance_cost_advertising_update(cost_id: int, building_id: int = None,
                                    building_name: str = None, ad_type: int = None,
                                    ad_channel: str = None, ad_end_date: str = None,
                                    cost_date: str = None, invoice_no: str = None,
                                    invoice_date: str = None, total_amount: float = None,
                                    untax_amount: float = None, tax_amount: float = None,
                                    deduct_amount: float = None, actual_cost_amount: float = None,
                                    ad_file_url: str = None, remark: str = None):
    """
    更新广告推广成本（PUT /api/finance/cost/advertising/{id}）
    :param cost_id: 广告推广成本ID
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param ad_type: 广告类型
    :param ad_channel: 投放渠道名称
    :param ad_end_date: 广告投放结束日期
    :param cost_date: 成本入账归属日期
    :param invoice_no: 广告服务费发票号码
    :param invoice_date: 发票开具日期
    :param total_amount: 广告含税总金额
    :param untax_amount: 广告不含税营销成本
    :param tax_amount: 可抵扣进项税额
    :param deduct_amount: 扣款、违约金金额
    :param actual_cost_amount: 应付实际成本净额
    :param ad_file_url: 广告合同、投放排期、发票、验收单附件
    :param remark: 投放内容、楼栋分摊比例、结算特殊约定
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/advertising/{cost_id}"
    payload = _compact({
        "building_id": building_id, "building_name": building_name, "ad_type": ad_type,
        "ad_channel": ad_channel, "ad_end_date": ad_end_date, "cost_date": cost_date,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "deduct_amount": deduct_amount,
        "actual_cost_amount": actual_cost_amount, "ad_file_url": ad_file_url,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_cost_advertising_delete(cost_id: int):
    """
    删除广告推广成本（DELETE /api/finance/cost/advertising/{id}）
    :param cost_id: 广告推广成本ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/advertising/{cost_id}"
    return authenticated_request("DELETE", url)


# ---------- 工程建设成本（/cost/engineering）----------
def finance_cost_engineering_create(project_id: int, project_name: str, building_id: int,
                                    building_name: str, supplier_id: int, supplier_name: str,
                                    project_fin_config_id: int, cost_subject_id: int,
                                    tax_tpl_id: int, eng_type: int, eng_name: str,
                                    eng_contract_id: int, settle_cycle: str, settle_start: str,
                                    settle_end: str, cost_date: str, total_amount: float,
                                    untax_amount: float, actual_cost_amount: float,
                                    create_user_id: int, bank_info_id: int = None,
                                    invoice_no: str = None, invoice_date: str = None,
                                    tax_amount: float = None, deduct_amount: float = None,
                                    relate_pay_id: int = None, voucher_no: str = None,
                                    eng_file_url: str = None, remark: str = None,
                                    cost_no: str = None):
    """
    创建工程建设成本（POST /api/finance/cost/engineering/create）
    :param project_id: 归属楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param building_id: 分摊楼栋ID（必填）
    :param building_name: 分摊楼栋名称冗余（必填）
    :param supplier_id: 施工单位供应商ID（必填）
    :param supplier_name: 施工单位名称冗余（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 资本化开发成本科目ID（必填）
    :param tax_tpl_id: 工程建安进项税率模板ID（必填）
    :param eng_type: 工程类型：1土建总包 2园林景观 3配套道路管网 4水电安装 5监理设计（必填）
    :param eng_name: 分项工程名称（必填）
    :param eng_contract_id: 工程施工合同ID（必填）
    :param settle_cycle: 本期结算周期（必填）
    :param settle_start: 结算周期起始日（必填，如 2026-01-01）
    :param settle_end: 结算周期截止日（必填，如 2026-01-31）
    :param cost_date: 成本资本化入账日期（必填，如 2026-01-31）
    :param total_amount: 本期结算含税工程款总额（必填）
    :param untax_amount: 资本化不含税开发成本（必填）
    :param actual_cost_amount: 本期应付工程净额（必填）
    :param create_user_id: 工程成本录入制单人ID（必填）
    :param bank_info_id: 施工方对公收款账户ID
    :param invoice_no: 建安工程款增值税发票号码
    :param invoice_date: 发票开具日期
    :param tax_amount: 建安进项可抵扣税额（默认0）
    :param deduct_amount: 质保金、违约金扣款金额（默认0）
    :param relate_pay_id: 核销后关联费用付款单ID
    :param voucher_no: 开发成本资本化财务凭证编号
    :param eng_file_url: 工程合同、结算单、验收单、工程款发票附件
    :param remark: 工程内容、楼栋成本分摊比例、质保金约定说明
    :param cost_no: 工程成本单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/engineering/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "supplier_id": supplier_id, "supplier_name": supplier_name,
        "bank_info_id": bank_info_id, "project_fin_config_id": project_fin_config_id,
        "cost_subject_id": cost_subject_id, "tax_tpl_id": tax_tpl_id,
        "eng_type": eng_type, "eng_name": eng_name, "eng_contract_id": eng_contract_id,
        "settle_cycle": settle_cycle, "settle_start": settle_start,
        "settle_end": settle_end, "cost_date": cost_date, "invoice_no": invoice_no,
        "invoice_date": invoice_date, "total_amount": total_amount,
        "untax_amount": untax_amount, "tax_amount": tax_amount,
        "deduct_amount": deduct_amount, "actual_cost_amount": actual_cost_amount,
        "relate_pay_id": relate_pay_id, "voucher_no": voucher_no,
        "eng_file_url": eng_file_url, "remark": remark,
        "create_user_id": create_user_id, "cost_no": cost_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_cost_engineering_list(page: int = 1, page_size: int = 20, project_id: int = None,
                                  building_id: int = None, supplier_id: int = None,
                                  eng_type: int = None, cost_status: int = None):
    """
    获取工程建设成本列表（GET /api/finance/cost/engineering/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param project_id: 归属楼盘ID（可选）
    :param building_id: 分摊楼栋ID（可选）
    :param supplier_id: 施工单位供应商ID（可选）
    :param eng_type: 工程类型：1土建总包 2园林景观 3配套道路管网 4水电安装 5监理设计（可选）
    :param cost_status: 成本状态（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/engineering/list"
    params = _compact({"page": page, "page_size": page_size, "project_id": project_id,
                       "building_id": building_id, "supplier_id": supplier_id,
                       "eng_type": eng_type, "cost_status": cost_status})
    return authenticated_request("GET", url, params=params)


def finance_cost_engineering_get(cost_id: int):
    """
    获取工程建设成本详情（GET /api/finance/cost/engineering/{id}）
    :param cost_id: 工程建设成本ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/engineering/{cost_id}"
    return authenticated_request("GET", url)


def finance_cost_engineering_update(cost_id: int, eng_type: int = None, eng_name: str = None,
                                    settle_cycle: str = None, settle_start: str = None,
                                    settle_end: str = None, cost_date: str = None,
                                    invoice_no: str = None, invoice_date: str = None,
                                    total_amount: float = None, untax_amount: float = None,
                                    tax_amount: float = None, deduct_amount: float = None,
                                    actual_cost_amount: float = None, eng_file_url: str = None,
                                    remark: str = None):
    """
    更新工程建设成本（PUT /api/finance/cost/engineering/{id}）
    :param cost_id: 工程建设成本ID
    :param eng_type: 工程类型
    :param eng_name: 分项工程名称
    :param settle_cycle: 本期结算周期
    :param settle_start: 结算周期起始日
    :param settle_end: 结算周期截止日
    :param cost_date: 成本资本化入账日期
    :param invoice_no: 建安工程款增值税发票号码
    :param invoice_date: 发票开具日期
    :param total_amount: 本期结算含税工程款总额
    :param untax_amount: 资本化不含税开发成本
    :param tax_amount: 建安进项可抵扣税额
    :param deduct_amount: 质保金、违约金扣款金额
    :param actual_cost_amount: 本期应付工程净额
    :param eng_file_url: 工程合同、结算单、验收单、工程款发票附件
    :param remark: 工程内容、楼栋成本分摊比例、质保金约定说明
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/engineering/{cost_id}"
    payload = _compact({
        "eng_type": eng_type, "eng_name": eng_name, "settle_cycle": settle_cycle,
        "settle_start": settle_start, "settle_end": settle_end, "cost_date": cost_date,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "total_amount": total_amount, "untax_amount": untax_amount,
        "tax_amount": tax_amount, "deduct_amount": deduct_amount,
        "actual_cost_amount": actual_cost_amount, "eng_file_url": eng_file_url,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_cost_engineering_delete(cost_id: int):
    """
    删除工程建设成本（DELETE /api/finance/cost/engineering/{id}）
    :param cost_id: 工程建设成本ID
    """
    url = f"{BASE_URL}{API_FINANCE_COST}/engineering/{cost_id}"
    return authenticated_request("DELETE", url)


# ======================================================================
# 六、应收应付往来台账（/api/finance/ar-ap）
# ======================================================================

# ---------- 客户应收台账（/ar-ap/receivable）----------
def finance_arap_receivable_create(project_id: int, project_name: str, building_id: int,
                                   building_name: str, house_id: int, house_no: str,
                                   contract_id: int, customer_id: int, customer_name: str,
                                   project_fin_config_id: int, tax_tpl_id: int,
                                   receivable_subject_id: int, first_receivable_date: str,
                                   last_receivable_date: str, total_receivable: float,
                                   principal_receivable: float, tax_receivable: float,
                                   total_unpaid: float, create_user_id: int,
                                   customer_phone: str = None, total_received: float = None,
                                   remark: str = None):
    """
    创建客户应收台账（POST /api/finance/ar-ap/receivable/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param building_id: 楼栋ID，成本分摊核心维度（必填）
    :param building_name: 楼栋名称冗余（必填）
    :param house_id: 房源ID（必填）
    :param house_no: 房源房号冗余（必填）
    :param contract_id: 购房合同ID（必填）
    :param customer_id: 客户ID（必填）
    :param customer_name: 客户姓名冗余（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param tax_tpl_id: 房款销项税率模板ID（必填）
    :param receivable_subject_id: 应收账款会计科目ID（必填）
    :param first_receivable_date: 首期应收账期起始日（必填，如 2026-01-01）
    :param last_receivable_date: 尾款应收截止日（必填，如 2026-12-31）
    :param total_receivable: 应收含税总金额（必填）
    :param principal_receivable: 应收不含税房款本金（必填）
    :param tax_receivable: 应收增值税销项税额（必填）
    :param total_unpaid: 剩余未收含税金额（必填）
    :param create_user_id: 台账制单人ID（必填）
    :param customer_phone: 客户手机号冗余
    :param total_received: 累计已收含税金额（默认0）
    :param remark: 应收台账业务备注
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/receivable/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "house_id": house_id, "house_no": house_no, "contract_id": contract_id,
        "customer_id": customer_id, "customer_name": customer_name,
        "customer_phone": customer_phone, "project_fin_config_id": project_fin_config_id,
        "tax_tpl_id": tax_tpl_id, "receivable_subject_id": receivable_subject_id,
        "first_receivable_date": first_receivable_date,
        "last_receivable_date": last_receivable_date,
        "total_receivable": total_receivable,
        "principal_receivable": principal_receivable,
        "tax_receivable": tax_receivable, "total_received": total_received,
        "total_unpaid": total_unpaid, "remark": remark,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_arap_receivable_list(page: int = 1, page_size: int = 20, customer_id: int = None,
                                 project_id: int = None, building_id: int = None,
                                 account_status: int = None):
    """
    获取客户应收台账列表（GET /api/finance/ar-ap/receivable/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param customer_id: 客户ID（可选）
    :param project_id: 楼盘ID（可选）
    :param building_id: 楼栋ID（可选）
    :param account_status: 台账状态：1正常未结清 2全额结清 3部分逾期 4全部逾期 5作废红冲（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/receivable/list"
    params = _compact({"page": page, "page_size": page_size, "customer_id": customer_id,
                       "project_id": project_id, "building_id": building_id,
                       "account_status": account_status})
    return authenticated_request("GET", url, params=params)


def finance_arap_receivable_get(ar_id: int):
    """
    获取客户应收台账详情（GET /api/finance/ar-ap/receivable/{id}）
    :param ar_id: 客户应收台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/receivable/{ar_id}"
    return authenticated_request("GET", url)


def finance_arap_receivable_update(ar_id: int, project_id: int = None, project_name: str = None,
                                   building_id: int = None, building_name: str = None,
                                   customer_phone: str = None, total_received: float = None,
                                   total_unpaid: float = None, overdue_amount: float = None,
                                   overdue_interest: float = None, account_status: int = None,
                                   settle_time: str = None, voucher_no: str = None,
                                   settle_voucher_no: str = None, reconcile_remark: str = None,
                                   remark: str = None):
    """
    更新客户应收台账（PUT /api/finance/ar-ap/receivable/{id}）
    :param ar_id: 客户应收台账ID
    :param project_id: 楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 楼栋ID
    :param building_name: 楼栋名称冗余
    :param customer_phone: 客户手机号冗余
    :param total_received: 累计已收含税金额
    :param total_unpaid: 剩余未收含税金额
    :param overdue_amount: 当前逾期未收金额
    :param overdue_interest: 逾期罚息/违约金金额
    :param account_status: 1正常未结清 2全额结清 3部分逾期 4全部逾期 5作废红冲
    :param settle_time: 全款结清时间
    :param voucher_no: 应收入账凭证编号
    :param settle_voucher_no: 回款结清核销凭证编号
    :param reconcile_remark: 账龄差异、逾期特殊说明
    :param remark: 应收台账业务备注
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/receivable/{ar_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "customer_phone": customer_phone, "total_received": total_received,
        "total_unpaid": total_unpaid, "overdue_amount": overdue_amount,
        "overdue_interest": overdue_interest, "account_status": account_status,
        "settle_time": settle_time, "voucher_no": voucher_no,
        "settle_voucher_no": settle_voucher_no, "reconcile_remark": reconcile_remark,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_arap_receivable_delete(ar_id: int):
    """
    删除客户应收台账（DELETE /api/finance/ar-ap/receivable/{id}）
    :param ar_id: 客户应收台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/receivable/{ar_id}"
    return authenticated_request("DELETE", url)


# ---------- 供应商应付台账（/ar-ap/payable）----------
def finance_arap_payable_create(project_id: int, project_name: str, supplier_id: int,
                                supplier_name: str, supplier_type: int, relate_biz_type: int,
                                relate_biz_id: int, project_fin_config_id: int,
                                cost_subject_id: int, tax_tpl_id: int, bill_date: str,
                                due_date: str, payable_total_amt: float,
                                payable_untax_amt: float, payable_tax_amt: float,
                                unpaid_amount: float, create_user_id: int,
                                building_id: int = None, building_name: str = None,
                                contract_id: int = None, paid_amount: float = None,
                                payable_file_url: str = None, remark: str = None,
                                payable_no: str = None):
    """
    创建供应商应付台账（POST /api/finance/ar-ap/payable/create）
    :param project_id: 归属楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param supplier_id: 供应商ID（必填）
    :param supplier_name: 供应商名称冗余（必填）
    :param supplier_type: 供应商类型：1工程总包 2营销服务 3设计监理 4物资采购（必填）
    :param relate_biz_type: 关联业务类型：1工程成本 2广告营销 3通用费用（必填）
    :param relate_biz_id: 关联业务单据ID（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param cost_subject_id: 应付账款对应会计科目ID（必填）
    :param tax_tpl_id: 进项税税率模板ID（必填）
    :param bill_date: 应付账单入账日期（必填，如 2026-01-01）
    :param due_date: 付款到期日，账龄计算依据（必填，如 2026-02-01）
    :param payable_total_amt: 应付含税总金额（必填）
    :param payable_untax_amt: 应付不含税成本金额（必填）
    :param payable_tax_amt: 可抵扣进项税额（必填）
    :param unpaid_amount: 剩余未付余额（必填）
    :param create_user_id: 台账制单人ID（必填）
    :param building_id: 分摊楼栋ID，多楼栋逗号分隔
    :param building_name: 分摊楼栋名称冗余
    :param contract_id: 对应供应商合同ID
    :param paid_amount: 累计已付含税金额（默认0）
    :param payable_file_url: 结算单、发票、验收单附件
    :param remark: 应付台账业务备注
    :param payable_no: 应付台账单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/payable/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "supplier_id": supplier_id, "supplier_name": supplier_name,
        "supplier_type": supplier_type, "relate_biz_type": relate_biz_type,
        "relate_biz_id": relate_biz_id, "contract_id": contract_id,
        "project_fin_config_id": project_fin_config_id,
        "cost_subject_id": cost_subject_id, "tax_tpl_id": tax_tpl_id,
        "bill_date": bill_date, "due_date": due_date,
        "payable_total_amt": payable_total_amt, "payable_untax_amt": payable_untax_amt,
        "payable_tax_amt": payable_tax_amt, "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount, "payable_file_url": payable_file_url,
        "remark": remark, "create_user_id": create_user_id, "payable_no": payable_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_arap_payable_list(page: int = 1, page_size: int = 20, supplier_id: int = None,
                              project_id: int = None, payable_status: int = None,
                              supplier_type: int = None):
    """
    获取供应商应付台账列表（GET /api/finance/ar-ap/payable/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param supplier_id: 供应商ID（可选）
    :param project_id: 归属楼盘ID（可选）
    :param payable_status: 台账状态：1未结清 2已结清 3部分结清 4逾期挂账 5作废（可选）
    :param supplier_type: 供应商类型：1工程总包 2营销服务 3设计监理 4物资采购（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/payable/list"
    params = _compact({"page": page, "page_size": page_size, "supplier_id": supplier_id,
                       "project_id": project_id, "payable_status": payable_status,
                       "supplier_type": supplier_type})
    return authenticated_request("GET", url, params=params)


def finance_arap_payable_get(payable_id: int):
    """
    获取供应商应付台账详情（GET /api/finance/ar-ap/payable/{id}）
    :param payable_id: 供应商应付台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/payable/{payable_id}"
    return authenticated_request("GET", url)


def finance_arap_payable_update(payable_id: int, project_id: int = None, project_name: str = None,
                                building_id: int = None, building_name: str = None,
                                supplier_type: int = None, contract_id: int = None,
                                cost_subject_id: int = None, tax_tpl_id: int = None,
                                due_date: str = None, paid_amount: float = None,
                                unpaid_amount: float = None, deduct_amount: float = None,
                                payable_status: int = None, settle_time: str = None,
                                bank_flow_ids: str = None, voucher_no: str = None,
                                settle_voucher_no: str = None, payable_file_url: str = None,
                                reconcile_remark: str = None, remark: str = None):
    """
    更新供应商应付台账（PUT /api/finance/ar-ap/payable/{id}）
    :param payable_id: 供应商应付台账ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param supplier_type: 供应商类型
    :param contract_id: 对应供应商合同ID
    :param cost_subject_id: 应付账款对应会计科目ID
    :param tax_tpl_id: 进项税税率模板ID
    :param due_date: 付款到期日
    :param paid_amount: 累计已付含税金额
    :param unpaid_amount: 剩余未付余额
    :param deduct_amount: 质保金/违约金扣减总额
    :param payable_status: 1未结清 2已结清 3部分结清 4逾期挂账 5作废
    :param settle_time: 全额结清时间
    :param bank_flow_ids: 关联付款银行流水ID集合
    :param voucher_no: 应付入账凭证编号
    :param settle_voucher_no: 付款核销凭证编号
    :param payable_file_url: 结算单、发票、验收单附件
    :param reconcile_remark: 往来对账差异说明
    :param remark: 应付台账业务备注
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/payable/{payable_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "supplier_type": supplier_type, "contract_id": contract_id,
        "cost_subject_id": cost_subject_id, "tax_tpl_id": tax_tpl_id,
        "due_date": due_date, "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount, "deduct_amount": deduct_amount,
        "payable_status": payable_status, "settle_time": settle_time,
        "bank_flow_ids": bank_flow_ids, "voucher_no": voucher_no,
        "settle_voucher_no": settle_voucher_no, "payable_file_url": payable_file_url,
        "reconcile_remark": reconcile_remark, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_arap_payable_delete(payable_id: int):
    """
    删除供应商应付台账（DELETE /api/finance/ar-ap/payable/{id}）
    :param payable_id: 供应商应付台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/payable/{payable_id}"
    return authenticated_request("DELETE", url)


# ---------- 预付款台账（/ar-ap/prepayment）----------
def finance_arap_prepayment_create(project_id: int, project_name: str, supplier_id: int,
                                   supplier_name: str, advance_type: int,
                                   project_fin_config_id: int, advance_subject_id: int,
                                   tax_tpl_id: int, advance_date: str, advance_total_amt: float,
                                   advance_untax_amt: float, advance_tax_amt: float,
                                   balance_amount: float, relate_pay_id: int,
                                   create_user_id: int, building_id: int = None,
                                   building_name: str = None, expire_date: str = None,
                                   used_amount: float = None, invoice_no: str = None,
                                   invoice_date: str = None, advance_file_url: str = None,
                                   remark: str = None, advance_no: str = None):
    """
    创建预付款台账（POST /api/finance/ar-ap/prepayment/create）
    :param project_id: 归属楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param supplier_id: 供应商ID（必填）
    :param supplier_name: 供应商名称冗余（必填）
    :param advance_type: 1工程预付款 2营销预付款 3质保金预付 4其他预付（必填）
    :param project_fin_config_id: 楼盘财务配置ID（必填）
    :param advance_subject_id: 预付账款会计科目ID（必填）
    :param tax_tpl_id: 进项税税率模板ID（必填）
    :param advance_date: 预付付款日期（必填，如 2026-01-01）
    :param advance_total_amt: 预付含税总金额（必填）
    :param advance_untax_amt: 预付不含税成本金额（必填）
    :param advance_tax_amt: 预付可抵扣进项税额（必填）
    :param balance_amount: 剩余可核销余额（必填）
    :param relate_pay_id: 关联预付款付款单ID（必填）
    :param create_user_id: 台账制单人ID（必填）
    :param building_id: 成本分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param expire_date: 预付核销过期日期
    :param used_amount: 已核销含税金额（默认0）
    :param invoice_no: 核销对应发票号码
    :param invoice_date: 发票开具日期
    :param advance_file_url: 预付协议、付款回单、核销结算附件
    :param remark: 预付款业务备注
    :param advance_no: 预付款单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/prepayment/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "supplier_id": supplier_id, "supplier_name": supplier_name,
        "advance_type": advance_type, "project_fin_config_id": project_fin_config_id,
        "advance_subject_id": advance_subject_id, "tax_tpl_id": tax_tpl_id,
        "advance_date": advance_date, "expire_date": expire_date,
        "advance_total_amt": advance_total_amt, "advance_untax_amt": advance_untax_amt,
        "advance_tax_amt": advance_tax_amt, "used_amount": used_amount,
        "balance_amount": balance_amount, "relate_pay_id": relate_pay_id,
        "invoice_no": invoice_no, "invoice_date": invoice_date,
        "advance_file_url": advance_file_url, "remark": remark,
        "create_user_id": create_user_id, "advance_no": advance_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_arap_prepayment_list(page: int = 1, page_size: int = 20, supplier_id: int = None,
                                 project_id: int = None, advance_status: int = None,
                                 advance_type: int = None):
    """
    获取预付款台账列表（GET /api/finance/ar-ap/prepayment/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param supplier_id: 供应商ID（可选）
    :param project_id: 归属楼盘ID（可选）
    :param advance_status: 台账状态：1使用中可核销 2已全额核销 3过期作废 4红冲取消（可选）
    :param advance_type: 1工程预付款 2营销预付款 3质保金预付 4其他预付（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/prepayment/list"
    params = _compact({"page": page, "page_size": page_size, "supplier_id": supplier_id,
                       "project_id": project_id, "advance_status": advance_status,
                       "advance_type": advance_type})
    return authenticated_request("GET", url, params=params)


def finance_arap_prepayment_get(advance_id: int):
    """
    获取预付款台账详情（GET /api/finance/ar-ap/prepayment/{id}）
    :param advance_id: 预付款台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/prepayment/{advance_id}"
    return authenticated_request("GET", url)


def finance_arap_prepayment_update(advance_id: int, project_id: int = None,
                                   project_name: str = None, building_id: int = None,
                                   building_name: str = None, advance_type: int = None,
                                   expire_date: str = None, used_amount: float = None,
                                   balance_amount: float = None, relate_payable_ids: str = None,
                                   invoice_no: str = None, invoice_date: str = None,
                                   advance_status: int = None, settle_time: str = None,
                                   voucher_no: str = None, settle_voucher_no: str = None,
                                   advance_file_url: str = None, reconcile_remark: str = None,
                                   remark: str = None):
    """
    更新预付款台账（PUT /api/finance/ar-ap/prepayment/{id}）
    :param advance_id: 预付款台账ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 成本分摊楼栋ID
    :param building_name: 分摊楼栋名称冗余
    :param advance_type: 预付款类型
    :param expire_date: 预付核销过期日期
    :param used_amount: 已核销含税金额
    :param balance_amount: 剩余可核销余额
    :param relate_payable_ids: 核销关联应付台账ID集合
    :param invoice_no: 核销对应发票号码
    :param invoice_date: 发票开具日期
    :param advance_status: 1使用中可核销 2已全额核销 3过期作废 4红冲取消
    :param settle_time: 全额核销完成时间
    :param voucher_no: 预付入账凭证编号
    :param settle_voucher_no: 核销冲抵凭证编号
    :param advance_file_url: 预付协议、付款回单、核销结算附件
    :param reconcile_remark: 核销差异、过期说明
    :param remark: 预付款业务备注
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/prepayment/{advance_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "advance_type": advance_type, "expire_date": expire_date,
        "used_amount": used_amount, "balance_amount": balance_amount,
        "relate_payable_ids": relate_payable_ids, "invoice_no": invoice_no,
        "invoice_date": invoice_date, "advance_status": advance_status,
        "settle_time": settle_time, "voucher_no": voucher_no,
        "settle_voucher_no": settle_voucher_no, "advance_file_url": advance_file_url,
        "reconcile_remark": reconcile_remark, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_arap_prepayment_delete(advance_id: int):
    """
    删除预付款台账（DELETE /api/finance/ar-ap/prepayment/{id}）
    :param advance_id: 预付款台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/prepayment/{advance_id}"
    return authenticated_request("DELETE", url)


# ---------- 其他往来款台账（/ar-ap/other-loan）----------
def finance_arap_other_loan_create(loan_counterparty_type: int, counterparty_id: int,
                                   counterparty_name: str, loan_type: int, loan_direction: int,
                                   loan_subject_id: int, loan_date: str, loan_total_amt: float,
                                   loan_untax_amt: float, balance_amt: float,
                                   create_user_id: int, project_id: int = None,
                                   project_name: str = None, counterparty_dept: str = None,
                                   project_fin_config_id: int = None, due_date: str = None,
                                   loan_tax_amt: float = None, settle_amt: float = None,
                                   loan_file_url: str = None, remark: str = None,
                                   loan_no: str = None):
    """
    创建其他往来款台账（POST /api/finance/ar-ap/other-loan/create）
    :param loan_counterparty_type: 1内部员工 2外部供应商 3集团公司 4外部机构（必填）
    :param counterparty_id: 对方主体ID（必填）
    :param counterparty_name: 对方名称冗余（必填）
    :param loan_type: 1员工借款 2保证金 3集团拆借 4临时挂账 5押金（必填）
    :param loan_direction: 1其他应收 2其他应付（必填）
    :param loan_subject_id: 往来款对应会计科目ID（必填）
    :param loan_date: 往来挂账日期（必填，如 2026-01-01）
    :param loan_total_amt: 往来含税总金额（必填）
    :param loan_untax_amt: 往来不含税金额（必填）
    :param balance_amt: 剩余挂账余额（必填）
    :param create_user_id: 台账制单人ID（必填）
    :param project_id: 归属楼盘ID，集团总部往来为空
    :param project_name: 楼盘名称冗余
    :param counterparty_dept: 对方部门/所属单位
    :param project_fin_config_id: 楼盘财务配置ID
    :param due_date: 结清截止日期
    :param loan_tax_amt: 往来对应税额（默认0）
    :param settle_amt: 已结清金额（默认0）
    :param loan_file_url: 借款单、协议、收据附件
    :param remark: 往来款业务备注
    :param loan_no: 往来款单号（系统自动生成）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/other-loan/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "loan_counterparty_type": loan_counterparty_type,
        "counterparty_id": counterparty_id, "counterparty_name": counterparty_name,
        "counterparty_dept": counterparty_dept, "loan_type": loan_type,
        "loan_direction": loan_direction, "project_fin_config_id": project_fin_config_id,
        "loan_subject_id": loan_subject_id, "loan_date": loan_date, "due_date": due_date,
        "loan_total_amt": loan_total_amt, "loan_untax_amt": loan_untax_amt,
        "loan_tax_amt": loan_tax_amt, "settle_amt": settle_amt,
        "balance_amt": balance_amt, "loan_file_url": loan_file_url, "remark": remark,
        "create_user_id": create_user_id, "loan_no": loan_no,
    })
    return authenticated_request("POST", url, json=payload)


def finance_arap_other_loan_list(page: int = 1, page_size: int = 20, counterparty_id: int = None,
                                 project_id: int = None, loan_type: int = None,
                                 loan_direction: int = None):
    """
    获取其他往来款台账列表（GET /api/finance/ar-ap/other-loan/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param counterparty_id: 对方主体ID（可选）
    :param project_id: 归属楼盘ID（可选）
    :param loan_type: 1员工借款 2保证金 3集团拆借 4临时挂账 5押金（可选）
    :param loan_direction: 1其他应收 2其他应付（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/other-loan/list"
    params = _compact({"page": page, "page_size": page_size,
                       "counterparty_id": counterparty_id, "project_id": project_id,
                       "loan_type": loan_type, "loan_direction": loan_direction})
    return authenticated_request("GET", url, params=params)


def finance_arap_other_loan_get(loan_id: int):
    """
    获取其他往来款台账详情（GET /api/finance/ar-ap/other-loan/{id}）
    :param loan_id: 其他往来款台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/other-loan/{loan_id}"
    return authenticated_request("GET", url)


def finance_arap_other_loan_update(loan_id: int, project_id: int = None, project_name: str = None,
                                   loan_counterparty_type: int = None,
                                   counterparty_name: str = None, counterparty_dept: str = None,
                                   loan_type: int = None, loan_direction: int = None,
                                   loan_subject_id: int = None, due_date: str = None,
                                   settle_amt: float = None, balance_amt: float = None,
                                   loan_status: int = None, settle_time: str = None,
                                   relate_flow_id: int = None, voucher_no: str = None,
                                   settle_voucher_no: str = None, loan_file_url: str = None,
                                   reconcile_remark: str = None, remark: str = None):
    """
    更新其他往来款台账（PUT /api/finance/ar-ap/other-loan/{id}）
    :param loan_id: 其他往来款台账ID
    :param project_id: 归属楼盘ID
    :param project_name: 楼盘名称冗余
    :param loan_counterparty_type: 对方主体类型
    :param counterparty_name: 对方名称冗余
    :param counterparty_dept: 对方部门/所属单位
    :param loan_type: 往来类型
    :param loan_direction: 往来方向
    :param loan_subject_id: 往来款对应会计科目ID
    :param due_date: 结清截止日期
    :param settle_amt: 已结清金额
    :param balance_amt: 剩余挂账余额
    :param loan_status: 1挂账中 2部分结清 3全额结清 4作废红冲
    :param settle_time: 最终结清时间
    :param relate_flow_id: 关联银行流水ID
    :param voucher_no: 往来挂账凭证编号
    :param settle_voucher_no: 结清冲销凭证编号
    :param loan_file_url: 借款单、协议、收据附件
    :param reconcile_remark: 往来对账差异、结清说明
    :param remark: 往来款业务备注
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/other-loan/{loan_id}"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "loan_counterparty_type": loan_counterparty_type,
        "counterparty_name": counterparty_name, "counterparty_dept": counterparty_dept,
        "loan_type": loan_type, "loan_direction": loan_direction,
        "loan_subject_id": loan_subject_id, "due_date": due_date,
        "settle_amt": settle_amt, "balance_amt": balance_amt,
        "loan_status": loan_status, "settle_time": settle_time,
        "relate_flow_id": relate_flow_id, "voucher_no": voucher_no,
        "settle_voucher_no": settle_voucher_no, "loan_file_url": loan_file_url,
        "reconcile_remark": reconcile_remark, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_arap_other_loan_delete(loan_id: int):
    """
    删除其他往来款台账（DELETE /api/finance/ar-ap/other-loan/{id}）
    :param loan_id: 其他往来款台账ID
    """
    url = f"{BASE_URL}{API_FINANCE_AR_AP}/other-loan/{loan_id}"
    return authenticated_request("DELETE", url)


# ======================================================================
# 七、资金对账（/api/finance/reconciliation）
# ======================================================================

# ---------- 银行对账记录（/reconciliation/bank）----------
def finance_reconciliation_bank_create(account_id: int, account_name: str, check_date: str,
                                       bank_flow_no: str, bank_flow_type: int,
                                       bank_trade_time: str, bank_amount: float,
                                       relate_biz_type: int, create_user_id: int,
                                       check_no: str = None, account_bank: str = None,
                                       relate_biz_id: int = None, relate_biz_no: str = None,
                                       voucher_no: str = None, check_status: int = None,
                                       check_user_id: int = None, check_file_url: str = None,
                                       remark: str = None):
    """
    创建银行对账记录（POST /api/finance/reconciliation/bank/create）
    :param account_id: 银行账户ID（必填）
    :param account_name: 银行账户名称（必填）
    :param check_date: 对账所属日期（必填，如 2026-01-01）
    :param bank_flow_no: 银行官方流水号（必填）
    :param bank_flow_type: 流水类型：1收款 2付款 3退款 4手续费（必填）
    :param bank_trade_time: 银行交易发生时间（必填，如 2026-01-01 10:00:00）
    :param bank_amount: 银行流水交易金额（必填）
    :param relate_biz_type: 业务类型：1房款收款 2佣金付款 3费用报销 4工程付款 5渠道结算 6其他往来（必填）
    :param create_user_id: 单据制单人ID（必填）
    :param check_no: 银行对账单号，租户唯一，不传则自动生成
    :param account_bank: 开户银行
    :param relate_biz_id: 关联系统业务单据ID
    :param relate_biz_no: 关联系统业务单据编号
    :param voucher_no: 对应财务凭证编号
    :param check_status: 对账状态：1未匹配 2已匹配对账一致 3对账差异 4手动调平 5作废（默认1）
    :param check_user_id: 对账操作人ID
    :param check_file_url: 银行回单、对账调节表、差异处理附件
    :param remark: 对账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/create"
    payload = _compact({
        "check_no": check_no, "account_id": account_id, "account_name": account_name,
        "account_bank": account_bank, "check_date": check_date,
        "bank_flow_no": bank_flow_no, "bank_flow_type": bank_flow_type,
        "bank_trade_time": bank_trade_time, "bank_amount": bank_amount,
        "relate_biz_type": relate_biz_type, "relate_biz_id": relate_biz_id,
        "relate_biz_no": relate_biz_no, "voucher_no": voucher_no,
        "check_status": check_status, "check_user_id": check_user_id,
        "create_user_id": create_user_id, "check_file_url": check_file_url,
        "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_bank_match(account_id: int = None, check_date: str = None,
                                      amount_tolerance: float = None):
    """
    银行对账自动匹配（POST /api/finance/reconciliation/bank/match）
    :param account_id: 银行账户ID（可选）
    :param check_date: 对账日期（可选，如 2026-01-01）
    :param amount_tolerance: 金额容差范围（默认0.01）
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/match"
    payload = _compact({
        "account_id": account_id, "check_date": check_date,
        "amount_tolerance": amount_tolerance,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_bank_finish(check_id: int, system_amount: float, relate_biz_type: int,
                                       check_user_id: int, relate_biz_id: int = None,
                                       relate_biz_no: str = None, diff_reason: str = None,
                                       solve_remark: str = None):
    """
    完成银行对账（POST /api/finance/reconciliation/bank/finish）
    :param check_id: 银行对账记录ID（必填，映射请求体 id）
    :param system_amount: 系统匹配业务金额（必填）
    :param relate_biz_type: 业务类型（必填）
    :param check_user_id: 对账操作人ID（必填）
    :param relate_biz_id: 关联业务单据ID
    :param relate_biz_no: 关联业务单据编号
    :param diff_reason: 差异原因
    :param solve_remark: 处理方案
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/finish"
    payload = _compact({
        "id": check_id, "system_amount": system_amount, "relate_biz_type": relate_biz_type,
        "relate_biz_id": relate_biz_id, "relate_biz_no": relate_biz_no,
        "check_user_id": check_user_id, "diff_reason": diff_reason,
        "solve_remark": solve_remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_bank_list(page: int = 1, page_size: int = 20, account_id: int = None,
                                     check_date: str = None, bank_flow_type: int = None,
                                     relate_biz_type: int = None, check_status: int = None):
    """
    获取银行对账记录列表（GET /api/finance/reconciliation/bank/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param account_id: 银行账户ID（可选）
    :param check_date: 对账所属日期（可选，如 2026-01-01）
    :param bank_flow_type: 流水类型：1收款 2付款 3退款 4手续费（可选）
    :param relate_biz_type: 业务类型：1房款收款 2佣金付款 3费用报销 4工程付款 5渠道结算 6其他往来（可选）
    :param check_status: 对账状态：1未匹配 2已匹配对账一致 3对账差异 4手动调平 5作废（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/list"
    params = _compact({"page": page, "page_size": page_size, "account_id": account_id,
                       "check_date": check_date, "bank_flow_type": bank_flow_type,
                       "relate_biz_type": relate_biz_type, "check_status": check_status})
    return authenticated_request("GET", url, params=params)


def finance_reconciliation_bank_get(check_id: int):
    """
    获取银行对账记录详情（GET /api/finance/reconciliation/bank/{id}）
    :param check_id: 银行对账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/{check_id}"
    return authenticated_request("GET", url)


def finance_reconciliation_bank_update(check_id: int, check_finish_time: str = None,
                                       system_amount: float = None, relate_biz_type: int = None,
                                       relate_biz_id: int = None, relate_biz_no: str = None,
                                       voucher_no: str = None, check_status: int = None,
                                       diff_reason: str = None, solve_remark: str = None,
                                       check_user_id: int = None, check_file_url: str = None,
                                       remark: str = None):
    """
    更新银行对账记录（PUT /api/finance/reconciliation/bank/{id}）
    :param check_id: 银行对账记录ID
    :param check_finish_time: 对账完成时间
    :param system_amount: 系统匹配业务金额
    :param relate_biz_type: 业务类型
    :param relate_biz_id: 关联系统业务单据ID
    :param relate_biz_no: 关联系统业务单据编号
    :param voucher_no: 对应财务凭证编号
    :param check_status: 对账状态
    :param diff_reason: 对账差异原因说明
    :param solve_remark: 差异处理方案、调平备注
    :param check_user_id: 对账操作人ID
    :param check_file_url: 银行回单、对账调节表、差异处理附件
    :param remark: 对账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/{check_id}"
    payload = _compact({
        "check_finish_time": check_finish_time, "system_amount": system_amount,
        "relate_biz_type": relate_biz_type, "relate_biz_id": relate_biz_id,
        "relate_biz_no": relate_biz_no, "voucher_no": voucher_no,
        "check_status": check_status, "diff_reason": diff_reason,
        "solve_remark": solve_remark, "check_user_id": check_user_id,
        "check_file_url": check_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_reconciliation_bank_delete(check_id: int):
    """
    删除银行对账记录（DELETE /api/finance/reconciliation/bank/{id}）
    :param check_id: 银行对账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/bank/{check_id}"
    return authenticated_request("DELETE", url)


# ---------- 每日资金轧账记录（/reconciliation/daily）----------
def finance_reconciliation_daily_create(account_id: int, account_name: str, account_date: str,
                                        create_user_id: int, project_id: int = None,
                                        project_name: str = None, beginning_balance: float = None,
                                        total_receipt: float = None, house_receipt: float = None,
                                        other_receipt: float = None, total_refund: float = None,
                                        house_refund: float = None, total_pay: float = None,
                                        commission_pay: float = None, cost_pay: float = None,
                                        other_pay: float = None, bank_ending_balance: float = None,
                                        account_status: int = None, voucher_no: str = None,
                                        account_file_url: str = None, diff_remark: str = None,
                                        remark: str = None):
    """
    创建每日资金轧账记录（POST /api/finance/reconciliation/daily/create）
    :param account_id: 银行账户ID（必填）
    :param account_name: 账户名称（必填）
    :param account_date: 资金轧账日期（必填，如 2026-01-01）
    :param create_user_id: 轧账制单人ID（必填）
    :param project_id: 楼盘ID
    :param project_name: 楼盘名称
    :param beginning_balance: 当日期初账户余额（默认0）
    :param total_receipt: 当日收款总额（默认0）
    :param house_receipt: 当日房款收款（默认0）
    :param other_receipt: 当日其他收款（默认0）
    :param total_refund: 当日退款总额（默认0）
    :param house_refund: 当日房款退款（默认0）
    :param total_pay: 当日付款总额（默认0）
    :param commission_pay: 当日佣金提成付款（默认0）
    :param cost_pay: 当日费用/工程付款（默认0）
    :param other_pay: 当日其他付款（默认0）
    :param bank_ending_balance: 银行官方期末余额（默认0）
    :param account_status: 轧账状态：1未轧账 2轧账正常 3余额差异 4已审核归档 5作废重轧（默认1）
    :param voucher_no: 日结汇总凭证编号
    :param account_file_url: 日结报表、对账表附件
    :param diff_remark: 余额差异原因及处理说明
    :param remark: 轧账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/create"
    payload = _compact({
        "account_id": account_id, "account_name": account_name,
        "project_id": project_id, "project_name": project_name,
        "account_date": account_date, "beginning_balance": beginning_balance,
        "total_receipt": total_receipt, "house_receipt": house_receipt,
        "other_receipt": other_receipt, "total_refund": total_refund,
        "house_refund": house_refund, "total_pay": total_pay,
        "commission_pay": commission_pay, "cost_pay": cost_pay, "other_pay": other_pay,
        "bank_ending_balance": bank_ending_balance, "account_status": account_status,
        "create_user_id": create_user_id, "voucher_no": voucher_no,
        "account_file_url": account_file_url, "diff_remark": diff_remark, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_daily_audit(account_record_id: int, audit_user_id: int,
                                       audit_status: int, diff_remark: str = None):
    """
    审核每日资金轧账记录（POST /api/finance/reconciliation/daily/audit）
    :param account_record_id: 轧账记录ID（必填，映射请求体 id）
    :param audit_user_id: 审核人ID（必填）
    :param audit_status: 审核结果：2通过 5驳回（必填）
    :param diff_remark: 审核意见/差异说明
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/audit"
    payload = _compact({
        "id": account_record_id, "audit_user_id": audit_user_id,
        "audit_status": audit_status, "diff_remark": diff_remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_daily_list(page: int = 1, page_size: int = 20, account_id: int = None,
                                      project_id: int = None, account_date: str = None,
                                      account_status: int = None):
    """
    获取每日资金轧账记录列表（GET /api/finance/reconciliation/daily/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param account_id: 银行账户ID（可选）
    :param project_id: 楼盘ID（可选）
    :param account_date: 资金轧账日期（可选，如 2026-01-01）
    :param account_status: 轧账状态：1未轧账 2轧账正常 3余额差异 4已审核归档 5作废重轧（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/list"
    params = _compact({"page": page, "page_size": page_size, "account_id": account_id,
                       "project_id": project_id, "account_date": account_date,
                       "account_status": account_status})
    return authenticated_request("GET", url, params=params)


def finance_reconciliation_daily_get(account_record_id: int):
    """
    获取每日资金轧账记录详情（GET /api/finance/reconciliation/daily/{id}）
    :param account_record_id: 每日资金轧账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/{account_record_id}"
    return authenticated_request("GET", url)


def finance_reconciliation_daily_update(account_record_id: int, total_receipt: float = None,
                                        house_receipt: float = None, other_receipt: float = None,
                                        total_refund: float = None, house_refund: float = None,
                                        total_pay: float = None, commission_pay: float = None,
                                        cost_pay: float = None, other_pay: float = None,
                                        bank_ending_balance: float = None,
                                        account_status: int = None, audit_user_id: int = None,
                                        audit_time: str = None, voucher_no: str = None,
                                        account_file_url: str = None, diff_remark: str = None,
                                        remark: str = None):
    """
    更新每日资金轧账记录（PUT /api/finance/reconciliation/daily/{id}）
    :param account_record_id: 每日资金轧账记录ID
    :param total_receipt: 当日收款总额
    :param house_receipt: 当日房款收款
    :param other_receipt: 当日其他收款
    :param total_refund: 当日退款总额
    :param house_refund: 当日房款退款
    :param total_pay: 当日付款总额
    :param commission_pay: 当日佣金提成付款
    :param cost_pay: 当日费用/工程付款
    :param other_pay: 当日其他付款
    :param bank_ending_balance: 银行官方期末余额
    :param account_status: 轧账状态
    :param audit_user_id: 资金审核人ID
    :param audit_time: 审核归档时间
    :param voucher_no: 日结汇总凭证编号
    :param account_file_url: 日结报表、对账表附件
    :param diff_remark: 余额差异原因及处理说明
    :param remark: 轧账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/{account_record_id}"
    payload = _compact({
        "total_receipt": total_receipt, "house_receipt": house_receipt,
        "other_receipt": other_receipt, "total_refund": total_refund,
        "house_refund": house_refund, "total_pay": total_pay,
        "commission_pay": commission_pay, "cost_pay": cost_pay, "other_pay": other_pay,
        "bank_ending_balance": bank_ending_balance, "account_status": account_status,
        "audit_user_id": audit_user_id, "audit_time": audit_time, "voucher_no": voucher_no,
        "account_file_url": account_file_url, "diff_remark": diff_remark, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_reconciliation_daily_delete(account_record_id: int):
    """
    删除每日资金轧账记录（DELETE /api/finance/reconciliation/daily/{id}）
    :param account_record_id: 每日资金轧账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/daily/{account_record_id}"
    return authenticated_request("DELETE", url)


# ---------- 渠道月度对账记录（/reconciliation/channel）----------
def finance_reconciliation_channel_create(project_id: int, project_name: str, channel_id: int,
                                          channel_name: str, reconcile_month: str,
                                          settle_start: str, settle_end: str, create_user_id: int,
                                          reconcile_no: str = None, building_scope: str = None,
                                          channel_deal_num: int = None, system_deal_num: int = None,
                                          refund_num: int = None, channel_amount: float = None,
                                          system_amount: float = None, deduct_amount: float = None,
                                          commission_pay_id: int = None, voucher_no: str = None,
                                          reconcile_status: int = None, reconcile_user_id: int = None,
                                          diff_reason: str = None, solve_plan: str = None,
                                          reconcile_file_url: str = None, remark: str = None):
    """
    创建渠道月度对账记录（POST /api/finance/reconciliation/channel/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称（必填）
    :param channel_id: 分销渠道ID（必填）
    :param channel_name: 渠道名称（必填）
    :param reconcile_month: 对账月份（必填，如 2026-01）
    :param settle_start: 对账周期起始日（必填，如 2026-01-01）
    :param settle_end: 对账周期截止日（必填，如 2026-01-31）
    :param create_user_id: 制单人ID（必填）
    :param reconcile_no: 渠道对账单号，租户唯一，不传则自动生成
    :param building_scope: 本次对账覆盖楼栋ID，逗号分隔
    :param channel_deal_num: 渠道申报成交套数（默认0）
    :param system_deal_num: 系统审核成交套数（默认0）
    :param refund_num: 周期内退房套数（默认0）
    :param channel_amount: 渠道自主申报佣金金额（默认0）
    :param system_amount: 系统核算合规佣金金额（默认0）
    :param deduct_amount: 周期退房/违规扣减金额（默认0）
    :param commission_pay_id: 关联渠道佣金付款单ID
    :param voucher_no: 对账结算凭证编号
    :param reconcile_status: 对账状态：1待渠道确认 2已对账无差异 3对账存在差异 4差异已处理 5作废（默认1）
    :param reconcile_user_id: 对账负责人ID
    :param diff_reason: 金额/套数差异原因
    :param solve_plan: 差异调整方案、下期抵扣说明
    :param reconcile_file_url: 渠道对账表、结算明细、沟通回执附件
    :param remark: 月度对账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/create"
    payload = _compact({
        "reconcile_no": reconcile_no, "project_id": project_id,
        "project_name": project_name, "building_scope": building_scope,
        "channel_id": channel_id, "channel_name": channel_name,
        "reconcile_month": reconcile_month, "settle_start": settle_start,
        "settle_end": settle_end, "channel_deal_num": channel_deal_num,
        "system_deal_num": system_deal_num, "refund_num": refund_num,
        "channel_amount": channel_amount, "system_amount": system_amount,
        "deduct_amount": deduct_amount, "commission_pay_id": commission_pay_id,
        "voucher_no": voucher_no, "reconcile_status": reconcile_status,
        "reconcile_user_id": reconcile_user_id, "create_user_id": create_user_id,
        "diff_reason": diff_reason, "solve_plan": solve_plan,
        "reconcile_file_url": reconcile_file_url, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_channel_confirm(reconcile_id: int, reconcile_user_id: int,
                                           confirm_status: int, diff_reason: str = None,
                                           solve_plan: str = None):
    """
    确认渠道月度对账（POST /api/finance/reconciliation/channel/confirm）
    :param reconcile_id: 渠道对账记录ID（必填，映射请求体 id）
    :param reconcile_user_id: 确认人ID（必填）
    :param confirm_status: 确认状态：2无差异 3有差异（必填）
    :param diff_reason: 差异原因
    :param solve_plan: 解决方案
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/confirm"
    payload = _compact({
        "id": reconcile_id, "reconcile_user_id": reconcile_user_id,
        "confirm_status": confirm_status, "diff_reason": diff_reason,
        "solve_plan": solve_plan,
    })
    return authenticated_request("POST", url, json=payload)


def finance_reconciliation_channel_list(page: int = 1, page_size: int = 20, channel_id: int = None,
                                        project_id: int = None, reconcile_month: str = None,
                                        reconcile_status: int = None):
    """
    获取渠道月度对账记录列表（GET /api/finance/reconciliation/channel/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param channel_id: 分销渠道ID（可选）
    :param project_id: 楼盘ID（可选）
    :param reconcile_month: 对账月份（可选，如 2026-01）
    :param reconcile_status: 对账状态：1待渠道确认 2已对账无差异 3对账存在差异 4差异已处理 5作废（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/list"
    params = _compact({"page": page, "page_size": page_size, "channel_id": channel_id,
                       "project_id": project_id, "reconcile_month": reconcile_month,
                       "reconcile_status": reconcile_status})
    return authenticated_request("GET", url, params=params)


def finance_reconciliation_channel_get(reconcile_id: int):
    """
    获取渠道月度对账记录详情（GET /api/finance/reconciliation/channel/{id}）
    :param reconcile_id: 渠道月度对账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/{reconcile_id}"
    return authenticated_request("GET", url)


def finance_reconciliation_channel_update(reconcile_id: int, system_deal_num: int = None,
                                          refund_num: int = None, system_amount: float = None,
                                          deduct_amount: float = None, commission_pay_id: int = None,
                                          voucher_no: str = None, reconcile_status: int = None,
                                          reconcile_user_id: int = None, reconcile_time: str = None,
                                          diff_reason: str = None, solve_plan: str = None,
                                          reconcile_file_url: str = None, remark: str = None):
    """
    更新渠道月度对账记录（PUT /api/finance/reconciliation/channel/{id}）
    :param reconcile_id: 渠道月度对账记录ID
    :param system_deal_num: 系统审核成交套数
    :param refund_num: 周期内退房套数
    :param system_amount: 系统核算合规佣金金额
    :param deduct_amount: 周期退房/违规扣减金额
    :param commission_pay_id: 关联渠道佣金付款单ID
    :param voucher_no: 对账结算凭证编号
    :param reconcile_status: 对账状态
    :param reconcile_user_id: 对账负责人ID
    :param reconcile_time: 对账最终确认时间
    :param diff_reason: 金额/套数差异原因
    :param solve_plan: 差异调整方案、下期抵扣说明
    :param reconcile_file_url: 渠道对账表、结算明细、沟通回执附件
    :param remark: 月度对账通用备注
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/{reconcile_id}"
    payload = _compact({
        "system_deal_num": system_deal_num, "refund_num": refund_num,
        "system_amount": system_amount, "deduct_amount": deduct_amount,
        "commission_pay_id": commission_pay_id, "voucher_no": voucher_no,
        "reconcile_status": reconcile_status, "reconcile_user_id": reconcile_user_id,
        "reconcile_time": reconcile_time, "diff_reason": diff_reason,
        "solve_plan": solve_plan, "reconcile_file_url": reconcile_file_url,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_reconciliation_channel_delete(reconcile_id: int):
    """
    删除渠道月度对账记录（DELETE /api/finance/reconciliation/channel/{id}）
    :param reconcile_id: 渠道月度对账记录ID
    """
    url = f"{BASE_URL}{API_FINANCE_RECONCILIATION}/channel/{reconcile_id}"
    return authenticated_request("DELETE", url)


# ======================================================================
# 八、会计凭证（/api/finance/voucher）
# ======================================================================

# ---------- 会计凭证主表（/voucher）----------
def finance_voucher_create(voucher_type: int, voucher_year: int, voucher_month: str,
                           voucher_date: str, source_type: int, source_biz_id: int,
                           source_biz_no: str, summary: str, make_user_id: int,
                           voucher_no: str = None, voucher_word: str = None,
                           attach_num: int = None, is_red_flush: int = None,
                           red_flush_voucher_id: int = None, red_flush_reason: str = None,
                           is_manual: int = None, voucher_status: int = None,
                           audit_user_id: int = None, settle_user_id: int = None,
                           voucher_file_url: str = None, remark: str = None):
    """
    创建会计凭证（POST /api/finance/voucher/create）
    :param voucher_type: 凭证类型：1收款凭证 2付款凭证 3转账凭证（必填）
    :param voucher_year: 会计年度（必填）
    :param voucher_month: 会计月份（必填，如 2026-01）
    :param voucher_date: 凭证做账日期（必填，如 2026-01-31）
    :param source_type: 来源类型：1收款 2退款 3销售佣金 4费用报销 5工程成本 6广告成本 7应收应付 8预付核销 9往来款 10手工录入（必填）
    :param source_biz_id: 关联上游业务单据ID（必填）
    :param source_biz_no: 关联上游业务单据编号（必填）
    :param summary: 凭证总摘要（必填）
    :param make_user_id: 制单人ID（必填）
    :param voucher_no: 凭证编号，租户唯一，不传则自动生成
    :param voucher_word: 凭证字：收/付/转/记（默认"记"）
    :param attach_num: 附件张数（默认0）
    :param is_red_flush: 0正常凭证 1红字冲销凭证（默认0）
    :param red_flush_voucher_id: 对应被红冲的原凭证ID
    :param red_flush_reason: 红冲作废原因说明
    :param is_manual: 0系统自动生成 1财务手工录入（默认0）
    :param voucher_status: 凭证状态：1草稿 2已审核 3已结账 4已作废 5已红冲 6反结账（默认1）
    :param audit_user_id: 审核人ID
    :param settle_user_id: 月末结账人ID
    :param voucher_file_url: 凭证附件、单据扫描件、对账资料
    :param remark: 凭证备注、特殊账务处理说明
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/create"
    payload = _compact({
        "voucher_no": voucher_no, "voucher_word": voucher_word,
        "voucher_type": voucher_type, "voucher_year": voucher_year,
        "voucher_month": voucher_month, "voucher_date": voucher_date,
        "attach_num": attach_num, "source_type": source_type,
        "source_biz_id": source_biz_id, "source_biz_no": source_biz_no,
        "is_red_flush": is_red_flush, "red_flush_voucher_id": red_flush_voucher_id,
        "red_flush_reason": red_flush_reason, "is_manual": is_manual,
        "summary": summary, "voucher_status": voucher_status,
        "make_user_id": make_user_id, "audit_user_id": audit_user_id,
        "settle_user_id": settle_user_id, "voucher_file_url": voucher_file_url,
        "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_voucher_audit(voucher_id: int, audit_user_id: int, audit_status: int):
    """
    审核会计凭证（POST /api/finance/voucher/audit）
    :param voucher_id: 凭证ID（必填，映射请求体 id）
    :param audit_user_id: 审核人ID（必填）
    :param audit_status: 审核状态：2已审核 4已作废（必填）
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/audit"
    payload = _compact({
        "id": voucher_id, "audit_user_id": audit_user_id, "audit_status": audit_status,
    })
    return authenticated_request("POST", url, json=payload)


def finance_voucher_red_flush(voucher_id: int, red_flush_reason: str, make_user_id: int):
    """
    红字冲销会计凭证（POST /api/finance/voucher/red-flush）
    :param voucher_id: 凭证ID（必填，映射请求体 id）
    :param red_flush_reason: 红冲原因说明（必填）
    :param make_user_id: 制单人ID（必填）
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/red-flush"
    payload = _compact({
        "id": voucher_id, "red_flush_reason": red_flush_reason,
        "make_user_id": make_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_voucher_list(page: int = 1, page_size: int = 20, voucher_type: int = None,
                         voucher_date: str = None, voucher_status: int = None,
                         source_type: int = None, is_red_flush: int = None):
    """
    获取会计凭证列表（GET /api/finance/voucher/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param voucher_type: 凭证类型：1收款凭证 2付款凭证 3转账凭证（可选）
    :param voucher_date: 凭证做账日期（可选，如 2026-01-31）
    :param voucher_status: 凭证状态：1草稿 2已审核 3已结账 4已作废 5已红冲 6反结账（可选）
    :param source_type: 来源类型：1-10（可选）
    :param is_red_flush: 0正常凭证 1红字冲销凭证（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/list"
    params = _compact({"page": page, "page_size": page_size, "voucher_type": voucher_type,
                       "voucher_date": voucher_date, "voucher_status": voucher_status,
                       "source_type": source_type, "is_red_flush": is_red_flush})
    return authenticated_request("GET", url, params=params)


def finance_voucher_get(voucher_id: int):
    """
    获取会计凭证详情（GET /api/finance/voucher/{id}）
    :param voucher_id: 会计凭证ID
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/{voucher_id}"
    return authenticated_request("GET", url)


def finance_voucher_get_with_items(voucher_id: int):
    """
    获取会计凭证及明细（GET /api/finance/voucher/{id}/with-items）
    :param voucher_id: 会计凭证ID
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/{voucher_id}/with-items"
    return authenticated_request("GET", url)


def finance_voucher_update(voucher_id: int, voucher_word: str = None, voucher_date: str = None,
                           attach_num: int = None, source_type: int = None,
                           source_biz_id: int = None, source_biz_no: str = None,
                           is_red_flush: int = None, red_flush_voucher_id: int = None,
                           red_flush_reason: str = None, is_manual: int = None,
                           summary: str = None, voucher_status: int = None,
                           audit_user_id: int = None, audit_time: str = None,
                           settle_user_id: int = None, settle_time: str = None,
                           voucher_file_url: str = None, remark: str = None):
    """
    更新会计凭证（PUT /api/finance/voucher/{id}）
    :param voucher_id: 会计凭证ID
    :param voucher_word: 凭证字：收/付/转/记
    :param voucher_date: 凭证做账日期
    :param attach_num: 附件张数
    :param source_type: 来源类型
    :param source_biz_id: 关联上游业务单据ID
    :param source_biz_no: 关联上游业务单据编号
    :param is_red_flush: 0正常凭证 1红字冲销凭证
    :param red_flush_voucher_id: 对应被红冲的原凭证ID
    :param red_flush_reason: 红冲作废原因说明
    :param is_manual: 0系统自动生成 1财务手工录入
    :param summary: 凭证总摘要
    :param voucher_status: 凭证状态
    :param audit_user_id: 审核人ID
    :param audit_time: 凭证审核时间
    :param settle_user_id: 月末结账人ID
    :param settle_time: 月末结账时间
    :param voucher_file_url: 凭证附件、单据扫描件、对账资料
    :param remark: 凭证备注、特殊账务处理说明
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/{voucher_id}"
    payload = _compact({
        "voucher_word": voucher_word, "voucher_date": voucher_date,
        "attach_num": attach_num, "source_type": source_type,
        "source_biz_id": source_biz_id, "source_biz_no": source_biz_no,
        "is_red_flush": is_red_flush, "red_flush_voucher_id": red_flush_voucher_id,
        "red_flush_reason": red_flush_reason, "is_manual": is_manual,
        "summary": summary, "voucher_status": voucher_status,
        "audit_user_id": audit_user_id, "audit_time": audit_time,
        "settle_user_id": settle_user_id, "settle_time": settle_time,
        "voucher_file_url": voucher_file_url, "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_voucher_delete(voucher_id: int):
    """
    删除会计凭证（DELETE /api/finance/voucher/{id}）
    :param voucher_id: 会计凭证ID
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/{voucher_id}"
    return authenticated_request("DELETE", url)


# ---------- 凭证明细（/voucher/item）----------
def finance_voucher_item_create(voucher_id: int, subject_id: int, subject_code: str,
                                subject_name: str, subject_type: int, borrow_amount: float = None,
                                lend_amount: float = None, original_currency: str = None,
                                original_amount: float = None, exchange_rate: float = None,
                                project_id: int = None, project_name: str = None,
                                building_id: int = None, building_name: str = None,
                                customer_id: int = None, supplier_id: int = None,
                                channel_id: int = None, staff_id: int = None,
                                dept_id: int = None, item_summary: str = None,
                                item_sort: int = None, item_remark: str = None):
    """
    创建凭证明细（POST /api/finance/voucher/item/create）
    :param voucher_id: 关联凭证主表ID（必填）
    :param subject_id: 会计科目ID（必填）
    :param subject_code: 科目编码冗余（必填）
    :param subject_name: 科目名称冗余（必填）
    :param subject_type: 科目类型：1资产 2负债 3权益 4成本 5损益（必填）
    :param borrow_amount: 借方发生金额（默认0）
    :param lend_amount: 贷方发生金额（默认0）
    :param original_currency: 原币币种（默认CNY）
    :param original_amount: 原币金额（默认0）
    :param exchange_rate: 记账汇率（默认1.0000）
    :param project_id: 辅助核算-楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 辅助核算-楼栋ID
    :param building_name: 楼栋名称冗余
    :param customer_id: 辅助核算-购房客户ID
    :param supplier_id: 辅助核算-供应商ID
    :param channel_id: 辅助核算-分销渠道ID
    :param staff_id: 辅助核算-员工ID
    :param dept_id: 辅助核算-部门ID
    :param item_summary: 分录行明细摘要
    :param item_sort: 分录行排序号（默认0）
    :param item_remark: 分录明细备注、账务说明
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/item/create"
    payload = _compact({
        "voucher_id": voucher_id, "subject_id": subject_id,
        "subject_code": subject_code, "subject_name": subject_name,
        "subject_type": subject_type, "borrow_amount": borrow_amount,
        "lend_amount": lend_amount, "original_currency": original_currency,
        "original_amount": original_amount, "exchange_rate": exchange_rate,
        "project_id": project_id, "project_name": project_name,
        "building_id": building_id, "building_name": building_name,
        "customer_id": customer_id, "supplier_id": supplier_id,
        "channel_id": channel_id, "staff_id": staff_id, "dept_id": dept_id,
        "item_summary": item_summary, "item_sort": item_sort,
        "item_remark": item_remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_voucher_item_list(page: int = 1, page_size: int = 20, voucher_id: int = None,
                              subject_id: int = None, subject_type: int = None,
                              project_id: int = None):
    """
    获取凭证明细列表（GET /api/finance/voucher/item/list）
    :param page: 页码（默认1）
    :param page_size: 每页数量（默认20）
    :param voucher_id: 关联凭证主表ID（可选）
    :param subject_id: 会计科目ID（可选）
    :param subject_type: 科目类型：1资产 2负债 3权益 4成本 5损益（可选）
    :param project_id: 辅助核算-楼盘ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/item/list"
    params = _compact({"page": page, "page_size": page_size, "voucher_id": voucher_id,
                       "subject_id": subject_id, "subject_type": subject_type,
                       "project_id": project_id})
    return authenticated_request("GET", url, params=params)


def finance_voucher_item_get(item_id: int):
    """
    获取凭证明细详情（GET /api/finance/voucher/item/{id}）
    :param item_id: 凭证明细ID
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/item/{item_id}"
    return authenticated_request("GET", url)


def finance_voucher_item_update(item_id: int, subject_id: int = None, subject_code: str = None,
                                subject_name: str = None, subject_type: int = None,
                                borrow_amount: float = None, lend_amount: float = None,
                                original_currency: str = None, original_amount: float = None,
                                exchange_rate: float = None, project_id: int = None,
                                project_name: str = None, building_id: int = None,
                                building_name: str = None, customer_id: int = None,
                                supplier_id: int = None, channel_id: int = None,
                                staff_id: int = None, dept_id: int = None,
                                item_summary: str = None, item_sort: int = None,
                                item_remark: str = None):
    """
    更新凭证明细（PUT /api/finance/voucher/item/{id}）
    :param item_id: 凭证明细ID
    :param subject_id: 会计科目ID
    :param subject_code: 科目编码冗余
    :param subject_name: 科目名称冗余
    :param subject_type: 科目类型
    :param borrow_amount: 借方发生金额
    :param lend_amount: 贷方发生金额
    :param original_currency: 原币币种
    :param original_amount: 原币金额
    :param exchange_rate: 记账汇率
    :param project_id: 辅助核算-楼盘ID
    :param project_name: 楼盘名称冗余
    :param building_id: 辅助核算-楼栋ID
    :param building_name: 楼栋名称冗余
    :param customer_id: 辅助核算-购房客户ID
    :param supplier_id: 辅助核算-供应商ID
    :param channel_id: 辅助核算-分销渠道ID
    :param staff_id: 辅助核算-员工ID
    :param dept_id: 辅助核算-部门ID
    :param item_summary: 分录行明细摘要
    :param item_sort: 分录行排序号
    :param item_remark: 分录明细备注、账务说明
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/item/{item_id}"
    payload = _compact({
        "subject_id": subject_id, "subject_code": subject_code,
        "subject_name": subject_name, "subject_type": subject_type,
        "borrow_amount": borrow_amount, "lend_amount": lend_amount,
        "original_currency": original_currency, "original_amount": original_amount,
        "exchange_rate": exchange_rate, "project_id": project_id,
        "project_name": project_name, "building_id": building_id,
        "building_name": building_name, "customer_id": customer_id,
        "supplier_id": supplier_id, "channel_id": channel_id, "staff_id": staff_id,
        "dept_id": dept_id, "item_summary": item_summary, "item_sort": item_sort,
        "item_remark": item_remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_voucher_item_delete(item_id: int):
    """
    删除凭证明细（DELETE /api/finance/voucher/item/{id}）
    :param item_id: 凭证明细ID
    """
    url = f"{BASE_URL}{API_FINANCE_VOUCHER}/item/{item_id}"
    return authenticated_request("DELETE", url)


# ==================================================================================
# 九、财务审计追溯（/api/finance/audit）
# ==================================================================================

# ---------- 9.1 财务操作审计日志 operate-log ----------

def finance_audit_operate_log_create(
    operate_user_id: int,
    operate_user_name: str,
    biz_module: int,
    operate_type: int,
    operate_summary: str,
    operate_content: str,
    operate_no: str = None,
    operate_dept_id: int = None,
    operate_dept_name: str = None,
    operate_ip: str = None,
    operate_mac: str = None,
    terminal_type: int = None,
    request_url: str = None,
    biz_type: int = None,
    biz_id: int = None,
    biz_no: str = None,
    voucher_id: int = None,
    voucher_no: str = None,
    old_data: str = None,
    new_data: str = None,
    operate_status: int = None,
    error_msg: str = None,
):
    """
    创建财务操作审计日志（POST /api/finance/audit/operate-log/create）
    :param operate_user_id: 操作人ID（必填）
    :param operate_user_name: 操作人姓名冗余（必填）
    :param biz_module: 业务模块（必填）：1收款管理 2退款管理 3应付应收台账 4预付款管理 5其他往来款 6资金对账 7会计凭证 8佣金结算 9费用报销 10财务配置
    :param operate_type: 操作类型（必填）：1新增 2修改 3删除 4审核 5反审核 6作废 7红冲 8结账 9反结账 10配置变更 11批量操作
    :param operate_summary: 操作简短摘要（必填）
    :param operate_content: 操作详细描述、变更说明（必填）
    :param operate_no: 审计日志唯一编号，租户唯一，不传则自动生成（可选）
    :param operate_dept_id: 操作人所属部门ID（可选）
    :param operate_dept_name: 操作人所属部门名称冗余（可选）
    :param operate_ip: 操作客户端IP地址（可选）
    :param operate_mac: 设备MAC地址（可选）
    :param terminal_type: 操作终端（可选，默认1）：1PC端 2移动端 3后台管理端
    :param request_url: 操作请求接口地址（可选）
    :param biz_type: 业务单据类型（可选）：1收款单 2退款单 3应付台账 4应收台账 5预付款单 6往来款单 7会计凭证 8渠道对账 9资金轧账
    :param biz_id: 关联业务单据主ID（可选）
    :param biz_no: 关联业务单据编号（可选）
    :param voucher_id: 关联会计凭证ID，凭证操作专属溯源（可选）
    :param voucher_no: 关联会计凭证编号（可选）
    :param old_data: 操作前完整数据JSON快照（可选）
    :param new_data: 操作后完整数据JSON快照（可选）
    :param operate_status: 操作结果状态（可选，默认1）：1操作成功 2操作失败 3部分成功
    :param error_msg: 操作失败异常信息、报错详情（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AUDIT}/operate-log/create"
    payload = _compact({
        "operate_no": operate_no, "operate_user_id": operate_user_id,
        "operate_user_name": operate_user_name, "operate_dept_id": operate_dept_id,
        "operate_dept_name": operate_dept_name, "operate_ip": operate_ip,
        "operate_mac": operate_mac, "terminal_type": terminal_type,
        "request_url": request_url, "biz_module": biz_module,
        "operate_type": operate_type, "biz_type": biz_type, "biz_id": biz_id,
        "biz_no": biz_no, "voucher_id": voucher_id, "voucher_no": voucher_no,
        "operate_summary": operate_summary, "operate_content": operate_content,
        "old_data": old_data, "new_data": new_data,
        "operate_status": operate_status, "error_msg": error_msg,
    })
    return authenticated_request("POST", url, json=payload)


def finance_audit_operate_log_list(
    page: int = 1,
    page_size: int = 20,
    biz_module: int = None,
    operate_type: int = None,
    biz_type: int = None,
    biz_id: int = None,
    voucher_id: int = None,
    operate_user_id: int = None,
    operate_status: int = None,
):
    """
    获取财务操作审计日志列表（GET /api/finance/audit/operate-log/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param biz_module: 业务模块过滤（可选）
    :param operate_type: 操作类型过滤（可选）
    :param biz_type: 业务单据类型过滤（可选）
    :param biz_id: 关联业务单据主ID过滤（可选）
    :param voucher_id: 关联会计凭证ID过滤（可选）
    :param operate_user_id: 操作人ID过滤（可选）
    :param operate_status: 操作结果状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AUDIT}/operate-log/list"
    params = _compact({
        "page": page, "page_size": page_size, "biz_module": biz_module,
        "operate_type": operate_type, "biz_type": biz_type, "biz_id": biz_id,
        "voucher_id": voucher_id, "operate_user_id": operate_user_id,
        "operate_status": operate_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_audit_operate_log_get(log_id: int):
    """
    获取财务操作审计日志详情（GET /api/finance/audit/operate-log/{id}）
    :param log_id: 操作审计日志ID
    """
    url = f"{BASE_URL}{API_FINANCE_AUDIT}/operate-log/{log_id}"
    return authenticated_request("GET", url)


def finance_audit_operate_log_update(
    log_id: int,
    operate_user_id: int = None,
    operate_user_name: str = None,
    operate_dept_id: int = None,
    operate_dept_name: str = None,
    operate_ip: str = None,
    operate_mac: str = None,
    terminal_type: int = None,
    request_url: str = None,
    biz_module: int = None,
    operate_type: int = None,
    biz_type: int = None,
    biz_id: int = None,
    biz_no: str = None,
    voucher_id: int = None,
    voucher_no: str = None,
    operate_summary: str = None,
    operate_content: str = None,
    old_data: str = None,
    new_data: str = None,
    operate_status: int = None,
    error_msg: str = None,
):
    """
    更新财务操作审计日志（PUT /api/finance/audit/operate-log/{id}）
    :param log_id: 操作审计日志ID（路径参数，必填）
    :param operate_user_id: 操作人ID（可选）
    :param operate_user_name: 操作人姓名冗余（可选）
    :param operate_dept_id: 操作人所属部门ID（可选）
    :param operate_dept_name: 操作人所属部门名称冗余（可选）
    :param operate_ip: 操作客户端IP地址（可选）
    :param operate_mac: 设备MAC地址（可选）
    :param terminal_type: 操作终端（可选）
    :param request_url: 操作请求接口地址（可选）
    :param biz_module: 业务模块（可选）
    :param operate_type: 操作类型（可选）
    :param biz_type: 业务单据类型（可选）
    :param biz_id: 关联业务单据主ID（可选）
    :param biz_no: 关联业务单据编号（可选）
    :param voucher_id: 关联会计凭证ID（可选）
    :param voucher_no: 关联会计凭证编号（可选）
    :param operate_summary: 操作简短摘要（可选）
    :param operate_content: 操作详细描述、变更说明（可选）
    :param old_data: 操作前完整数据JSON快照（可选）
    :param new_data: 操作后完整数据JSON快照（可选）
    :param operate_status: 操作结果状态（可选）
    :param error_msg: 操作失败异常信息、报错详情（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_AUDIT}/operate-log/{log_id}"
    payload = _compact({
        "operate_user_id": operate_user_id, "operate_user_name": operate_user_name,
        "operate_dept_id": operate_dept_id, "operate_dept_name": operate_dept_name,
        "operate_ip": operate_ip, "operate_mac": operate_mac,
        "terminal_type": terminal_type, "request_url": request_url,
        "biz_module": biz_module, "operate_type": operate_type,
        "biz_type": biz_type, "biz_id": biz_id, "biz_no": biz_no,
        "voucher_id": voucher_id, "voucher_no": voucher_no,
        "operate_summary": operate_summary, "operate_content": operate_content,
        "old_data": old_data, "new_data": new_data,
        "operate_status": operate_status, "error_msg": error_msg,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_audit_operate_log_delete(log_id: int):
    """
    删除财务操作审计日志（DELETE /api/finance/audit/operate-log/{id}）
    :param log_id: 操作审计日志ID
    """
    url = f"{BASE_URL}{API_FINANCE_AUDIT}/operate-log/{log_id}"
    return authenticated_request("DELETE", url)


# ==================================================================================
# 十、财务统计报表（/api/finance/report）
# ==================================================================================

# ---------- 10.1 现金流统计 cash-flow-stat ----------

def finance_report_cash_flow_stat_create(
    project_id: int,
    project_name: str,
    stat_date: str,
    stat_month: str,
    create_user_id: int,
    stat_type: int = None,
    total_receipt=None,
    house_receipt=None,
    other_receipt=None,
    total_refund=None,
    house_refund=None,
    total_pay=None,
    commission_pay=None,
    cost_pay=None,
    admin_pay=None,
    other_pay=None,
    operating_net_cash=None,
    investing_net_cash=None,
    financing_net_cash=None,
    net_cash_flow=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    创建现金流统计（POST /api/finance/report/cash-flow-stat/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param stat_date: 统计日期，日统计维度，格式YYYY-MM-DD（必填）
    :param stat_month: 统计月份 YYYY-MM（必填）
    :param create_user_id: 统计生成人ID（必填）
    :param stat_type: 统计类型（可选，默认1）：1日统计 2月统计
    :param total_receipt: 收款总金额（可选，默认0）
    :param house_receipt: 房款销售收入（可选，默认0）
    :param other_receipt: 其他经营收款（可选，默认0）
    :param total_refund: 退款总金额（可选，默认0）
    :param house_refund: 房款退款金额（可选，默认0）
    :param total_pay: 付款总金额（可选，默认0）
    :param commission_pay: 渠道佣金支付金额（可选，默认0）
    :param cost_pay: 工程/营销费用支付（可选，默认0）
    :param admin_pay: 管理费用支付（可选，默认0）
    :param other_pay: 其他付款金额（可选，默认0）
    :param operating_net_cash: 经营活动净现金流（可选，默认0）
    :param investing_net_cash: 投资活动净现金流（可选，默认0）
    :param financing_net_cash: 筹资活动净现金流（可选，默认0）
    :param net_cash_flow: 当期总净现金流（可选，默认0）
    :param stat_status: 统计状态（可选，默认1）：1正常 2待重算 3数据异常
    :param stat_batch: 统计批次号，重算溯源（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow-stat/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "stat_date": stat_date, "stat_month": stat_month, "stat_type": stat_type,
        "total_receipt": total_receipt, "house_receipt": house_receipt,
        "other_receipt": other_receipt, "total_refund": total_refund,
        "house_refund": house_refund, "total_pay": total_pay,
        "commission_pay": commission_pay, "cost_pay": cost_pay,
        "admin_pay": admin_pay, "other_pay": other_pay,
        "operating_net_cash": operating_net_cash,
        "investing_net_cash": investing_net_cash,
        "financing_net_cash": financing_net_cash, "net_cash_flow": net_cash_flow,
        "stat_status": stat_status, "stat_batch": stat_batch,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_cash_flow_stat_list(
    page: int = 1,
    page_size: int = 20,
    project_id: int = None,
    stat_month: str = None,
    stat_type: int = None,
    stat_status: int = None,
):
    """
    获取现金流统计列表（GET /api/finance/report/cash-flow-stat/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param project_id: 楼盘ID过滤（可选）
    :param stat_month: 统计月份 YYYY-MM 过滤（可选）
    :param stat_type: 统计类型过滤（可选）
    :param stat_status: 统计状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow-stat/list"
    params = _compact({
        "page": page, "page_size": page_size, "project_id": project_id,
        "stat_month": stat_month, "stat_type": stat_type, "stat_status": stat_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_cash_flow_stat_get(stat_id: int):
    """
    获取现金流统计详情（GET /api/finance/report/cash-flow-stat/{id}）
    :param stat_id: 现金流统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow-stat/{stat_id}"
    return authenticated_request("GET", url)


def finance_report_cash_flow_stat_update(
    stat_id: int,
    stat_date: str = None,
    stat_month: str = None,
    stat_type: int = None,
    total_receipt=None,
    house_receipt=None,
    other_receipt=None,
    total_refund=None,
    house_refund=None,
    total_pay=None,
    commission_pay=None,
    cost_pay=None,
    admin_pay=None,
    other_pay=None,
    operating_net_cash=None,
    investing_net_cash=None,
    financing_net_cash=None,
    net_cash_flow=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    更新现金流统计（PUT /api/finance/report/cash-flow-stat/{id}）
    :param stat_id: 现金流统计ID（路径参数，必填）
    :param stat_date: 统计日期，格式YYYY-MM-DD（可选）
    :param stat_month: 统计月份 YYYY-MM（可选）
    :param stat_type: 统计类型（可选）
    :param total_receipt: 收款总金额（可选）
    :param house_receipt: 房款销售收入（可选）
    :param other_receipt: 其他经营收款（可选）
    :param total_refund: 退款总金额（可选）
    :param house_refund: 房款退款金额（可选）
    :param total_pay: 付款总金额（可选）
    :param commission_pay: 渠道佣金支付金额（可选）
    :param cost_pay: 工程/营销费用支付（可选）
    :param admin_pay: 管理费用支付（可选）
    :param other_pay: 其他付款金额（可选）
    :param operating_net_cash: 经营活动净现金流（可选）
    :param investing_net_cash: 投资活动净现金流（可选）
    :param financing_net_cash: 筹资活动净现金流（可选）
    :param net_cash_flow: 当期总净现金流（可选）
    :param stat_status: 统计状态（可选）
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow-stat/{stat_id}"
    payload = _compact({
        "stat_date": stat_date, "stat_month": stat_month, "stat_type": stat_type,
        "total_receipt": total_receipt, "house_receipt": house_receipt,
        "other_receipt": other_receipt, "total_refund": total_refund,
        "house_refund": house_refund, "total_pay": total_pay,
        "commission_pay": commission_pay, "cost_pay": cost_pay,
        "admin_pay": admin_pay, "other_pay": other_pay,
        "operating_net_cash": operating_net_cash,
        "investing_net_cash": investing_net_cash,
        "financing_net_cash": financing_net_cash, "net_cash_flow": net_cash_flow,
        "stat_status": stat_status, "stat_batch": stat_batch,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_cash_flow_stat_delete(stat_id: int):
    """
    删除现金流统计（DELETE /api/finance/report/cash-flow-stat/{id}）
    :param stat_id: 现金流统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow-stat/{stat_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.2 应收款统计 receivable-stat ----------

def finance_report_receivable_stat_create(
    project_id: int,
    project_name: str,
    stat_date: str,
    stat_month: str,
    create_user_id: int,
    stat_type: int = None,
    total_receivable=None,
    current_period_receivable=None,
    total_received=None,
    current_period_received=None,
    unpaid_amount=None,
    overdue_amount=None,
    overdue_count: int = None,
    max_overdue_days: int = None,
    receive_rate=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    创建应收款统计（POST /api/finance/report/receivable-stat/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param stat_date: 统计日期，格式YYYY-MM-DD（必填）
    :param stat_month: 统计月份 YYYY-MM（必填）
    :param create_user_id: 统计生成人ID（必填）
    :param stat_type: 统计类型（可选，默认1）：1日统计 2月统计
    :param total_receivable: 累计应收总额（可选，默认0）
    :param current_period_receivable: 当期新增应收（可选，默认0）
    :param total_received: 累计已收总额（可选，默认0）
    :param current_period_received: 当期回款金额（可选，默认0）
    :param unpaid_amount: 当前未收余额（可选，默认0）
    :param overdue_amount: 当前逾期总金额（可选，默认0）
    :param overdue_count: 逾期单据笔数（可选，默认0）
    :param max_overdue_days: 当期最大逾期天数（可选，默认0）
    :param receive_rate: 当期回款率（可选，默认0）
    :param stat_status: 统计状态（可选，默认1）：1正常 2待重算 3数据异常
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/receivable-stat/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "stat_date": stat_date, "stat_month": stat_month, "stat_type": stat_type,
        "total_receivable": total_receivable,
        "current_period_receivable": current_period_receivable,
        "total_received": total_received,
        "current_period_received": current_period_received,
        "unpaid_amount": unpaid_amount, "overdue_amount": overdue_amount,
        "overdue_count": overdue_count, "max_overdue_days": max_overdue_days,
        "receive_rate": receive_rate, "stat_status": stat_status,
        "stat_batch": stat_batch, "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_receivable_stat_list(
    page: int = 1,
    page_size: int = 20,
    project_id: int = None,
    stat_month: str = None,
    stat_type: int = None,
    stat_status: int = None,
):
    """
    获取应收款统计列表（GET /api/finance/report/receivable-stat/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param project_id: 楼盘ID过滤（可选）
    :param stat_month: 统计月份 YYYY-MM 过滤（可选）
    :param stat_type: 统计类型过滤（可选）
    :param stat_status: 统计状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/receivable-stat/list"
    params = _compact({
        "page": page, "page_size": page_size, "project_id": project_id,
        "stat_month": stat_month, "stat_type": stat_type, "stat_status": stat_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_receivable_stat_get(stat_id: int):
    """
    获取应收款统计详情（GET /api/finance/report/receivable-stat/{id}）
    :param stat_id: 应收款统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/receivable-stat/{stat_id}"
    return authenticated_request("GET", url)


def finance_report_receivable_stat_update(
    stat_id: int,
    stat_date: str = None,
    stat_month: str = None,
    stat_type: int = None,
    total_receivable=None,
    current_period_receivable=None,
    total_received=None,
    current_period_received=None,
    unpaid_amount=None,
    overdue_amount=None,
    overdue_count: int = None,
    max_overdue_days: int = None,
    receive_rate=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    更新应收款统计（PUT /api/finance/report/receivable-stat/{id}）
    :param stat_id: 应收款统计ID（路径参数，必填）
    :param stat_date: 统计日期，格式YYYY-MM-DD（可选）
    :param stat_month: 统计月份 YYYY-MM（可选）
    :param stat_type: 统计类型（可选）
    :param total_receivable: 累计应收总额（可选）
    :param current_period_receivable: 当期新增应收（可选）
    :param total_received: 累计已收总额（可选）
    :param current_period_received: 当期回款金额（可选）
    :param unpaid_amount: 当前未收余额（可选）
    :param overdue_amount: 当前逾期总金额（可选）
    :param overdue_count: 逾期单据笔数（可选）
    :param max_overdue_days: 当期最大逾期天数（可选）
    :param receive_rate: 当期回款率（可选）
    :param stat_status: 统计状态（可选）
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/receivable-stat/{stat_id}"
    payload = _compact({
        "stat_date": stat_date, "stat_month": stat_month, "stat_type": stat_type,
        "total_receivable": total_receivable,
        "current_period_receivable": current_period_receivable,
        "total_received": total_received,
        "current_period_received": current_period_received,
        "unpaid_amount": unpaid_amount, "overdue_amount": overdue_amount,
        "overdue_count": overdue_count, "max_overdue_days": max_overdue_days,
        "receive_rate": receive_rate, "stat_status": stat_status,
        "stat_batch": stat_batch,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_receivable_stat_delete(stat_id: int):
    """
    删除应收款统计（DELETE /api/finance/report/receivable-stat/{id}）
    :param stat_id: 应收款统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/receivable-stat/{stat_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.3 税务统计 tax-stat ----------

def finance_report_tax_stat_create(
    project_id: int,
    project_name: str,
    stat_month: str,
    stat_year: int,
    create_user_id: int,
    invoice_amount=None,
    invoice_untax_amount=None,
    output_tax=None,
    input_tax=None,
    deduct_tax=None,
    tax_amount=None,
    declare_amount=None,
    declared_status: int = None,
    tax_burden_rate=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    创建税务统计（POST /api/finance/report/tax-stat/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param stat_month: 统计月份 YYYY-MM（必填）
    :param stat_year: 统计年度（必填）
    :param create_user_id: 统计生成人ID（必填）
    :param invoice_amount: 当期含税开票总额（可选，默认0）
    :param invoice_untax_amount: 当期不含税开票金额（可选，默认0）
    :param output_tax: 销项税额（可选，默认0）
    :param input_tax: 进项税额（可选，默认0）
    :param deduct_tax: 当期抵扣税额（可选，默认0）
    :param tax_amount: 当期应缴税额（可选，默认0）
    :param declare_amount: 已申报税额（可选，默认0）
    :param declared_status: 申报状态（可选，默认1）：1未申报 2已申报 3申报异常
    :param tax_burden_rate: 当期税负率（可选，默认0）
    :param stat_status: 统计状态（可选，默认1）：1正常 2待重算 3数据异常
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/tax-stat/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "stat_month": stat_month, "stat_year": stat_year,
        "invoice_amount": invoice_amount,
        "invoice_untax_amount": invoice_untax_amount,
        "output_tax": output_tax, "input_tax": input_tax,
        "deduct_tax": deduct_tax, "tax_amount": tax_amount,
        "declare_amount": declare_amount, "declared_status": declared_status,
        "tax_burden_rate": tax_burden_rate, "stat_status": stat_status,
        "stat_batch": stat_batch, "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_tax_stat_list(
    page: int = 1,
    page_size: int = 20,
    project_id: int = None,
    stat_month: str = None,
    stat_year: str = None,
    declared_status: int = None,
    stat_status: int = None,
):
    """
    获取税务统计列表（GET /api/finance/report/tax-stat/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param project_id: 楼盘ID过滤（可选）
    :param stat_month: 统计月份 YYYY-MM 过滤（可选）
    :param stat_year: 统计年度过滤，字符串（可选）
    :param declared_status: 申报状态过滤（可选）
    :param stat_status: 统计状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/tax-stat/list"
    params = _compact({
        "page": page, "page_size": page_size, "project_id": project_id,
        "stat_month": stat_month, "stat_year": stat_year,
        "declared_status": declared_status, "stat_status": stat_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_tax_stat_get(stat_id: int):
    """
    获取税务统计详情（GET /api/finance/report/tax-stat/{id}）
    :param stat_id: 税务统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/tax-stat/{stat_id}"
    return authenticated_request("GET", url)


def finance_report_tax_stat_update(
    stat_id: int,
    stat_month: str = None,
    stat_year: int = None,
    invoice_amount=None,
    invoice_untax_amount=None,
    output_tax=None,
    input_tax=None,
    deduct_tax=None,
    tax_amount=None,
    declare_amount=None,
    declared_status: int = None,
    tax_burden_rate=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    更新税务统计（PUT /api/finance/report/tax-stat/{id}）
    :param stat_id: 税务统计ID（路径参数，必填）
    :param stat_month: 统计月份 YYYY-MM（可选）
    :param stat_year: 统计年度（可选）
    :param invoice_amount: 当期含税开票总额（可选）
    :param invoice_untax_amount: 当期不含税开票金额（可选）
    :param output_tax: 销项税额（可选）
    :param input_tax: 进项税额（可选）
    :param deduct_tax: 当期抵扣税额（可选）
    :param tax_amount: 当期应缴税额（可选）
    :param declare_amount: 已申报税额（可选）
    :param declared_status: 申报状态（可选）
    :param tax_burden_rate: 当期税负率（可选）
    :param stat_status: 统计状态（可选）
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/tax-stat/{stat_id}"
    payload = _compact({
        "stat_month": stat_month, "stat_year": stat_year,
        "invoice_amount": invoice_amount,
        "invoice_untax_amount": invoice_untax_amount,
        "output_tax": output_tax, "input_tax": input_tax,
        "deduct_tax": deduct_tax, "tax_amount": tax_amount,
        "declare_amount": declare_amount, "declared_status": declared_status,
        "tax_burden_rate": tax_burden_rate, "stat_status": stat_status,
        "stat_batch": stat_batch,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_tax_stat_delete(stat_id: int):
    """
    删除税务统计（DELETE /api/finance/report/tax-stat/{id}）
    :param stat_id: 税务统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/tax-stat/{stat_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.4 佣金统计 commission-stat ----------

def finance_report_commission_stat_create(
    project_id: int,
    project_name: str,
    channel_id: int,
    channel_name: str,
    channel_type: int,
    stat_month: str,
    stat_year: int,
    create_user_id: int,
    deal_num: int = None,
    deal_amount=None,
    total_commission=None,
    deduct_commission=None,
    real_commission=None,
    paid_amount=None,
    unpaid_amount=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    创建佣金统计（POST /api/finance/report/commission-stat/create）
    :param project_id: 楼盘ID（必填）
    :param project_name: 楼盘名称冗余（必填）
    :param channel_id: 渠道ID（必填）
    :param channel_name: 渠道名称冗余（必填）
    :param channel_type: 渠道类型（必填）：1全民分销 2中介渠道 3内部销售
    :param stat_month: 统计月份 YYYY-MM（必填）
    :param stat_year: 统计年度（必填）
    :param create_user_id: 统计生成人ID（必填）
    :param deal_num: 当期成交套数（可选，默认0）
    :param deal_amount: 当期成交总额（可选，默认0）
    :param total_commission: 当期应付佣金总额（可选，默认0）
    :param deduct_commission: 当期扣减佣金（退房/违规）（可选，默认0）
    :param real_commission: 当期实际应付佣金（可选，默认0）
    :param paid_amount: 当期已支付佣金（可选，默认0）
    :param unpaid_amount: 当期未付佣金余额（可选，默认0）
    :param stat_status: 统计状态（可选，默认1）：1正常 2待重算 3数据异常
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/commission-stat/create"
    payload = _compact({
        "project_id": project_id, "project_name": project_name,
        "channel_id": channel_id, "channel_name": channel_name,
        "channel_type": channel_type, "stat_month": stat_month,
        "stat_year": stat_year, "deal_num": deal_num,
        "deal_amount": deal_amount, "total_commission": total_commission,
        "deduct_commission": deduct_commission, "real_commission": real_commission,
        "paid_amount": paid_amount, "unpaid_amount": unpaid_amount,
        "stat_status": stat_status, "stat_batch": stat_batch,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_commission_stat_list(
    page: int = 1,
    page_size: int = 20,
    project_id: int = None,
    channel_id: int = None,
    channel_type: int = None,
    stat_month: str = None,
    stat_year: str = None,
    stat_status: int = None,
):
    """
    获取佣金统计列表（GET /api/finance/report/commission-stat/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param project_id: 楼盘ID过滤（可选）
    :param channel_id: 渠道ID过滤（可选）
    :param channel_type: 渠道类型过滤（可选）
    :param stat_month: 统计月份 YYYY-MM 过滤（可选）
    :param stat_year: 统计年度过滤，字符串（可选）
    :param stat_status: 统计状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/commission-stat/list"
    params = _compact({
        "page": page, "page_size": page_size, "project_id": project_id,
        "channel_id": channel_id, "channel_type": channel_type,
        "stat_month": stat_month, "stat_year": stat_year, "stat_status": stat_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_commission_stat_get(stat_id: int):
    """
    获取佣金统计详情（GET /api/finance/report/commission-stat/{id}）
    :param stat_id: 佣金统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/commission-stat/{stat_id}"
    return authenticated_request("GET", url)


def finance_report_commission_stat_update(
    stat_id: int,
    stat_month: str = None,
    stat_year: int = None,
    deal_num: int = None,
    deal_amount=None,
    total_commission=None,
    deduct_commission=None,
    real_commission=None,
    paid_amount=None,
    unpaid_amount=None,
    stat_status: int = None,
    stat_batch: str = None,
):
    """
    更新佣金统计（PUT /api/finance/report/commission-stat/{id}）
    :param stat_id: 佣金统计ID（路径参数，必填）
    :param stat_month: 统计月份 YYYY-MM（可选）
    :param stat_year: 统计年度（可选）
    :param deal_num: 当期成交套数（可选）
    :param deal_amount: 当期成交总额（可选）
    :param total_commission: 当期应付佣金总额（可选）
    :param deduct_commission: 当期扣减佣金（可选）
    :param real_commission: 当期实际应付佣金（可选）
    :param paid_amount: 当期已支付佣金（可选）
    :param unpaid_amount: 当期未付佣金余额（可选）
    :param stat_status: 统计状态（可选）
    :param stat_batch: 统计批次号（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/commission-stat/{stat_id}"
    payload = _compact({
        "stat_month": stat_month, "stat_year": stat_year, "deal_num": deal_num,
        "deal_amount": deal_amount, "total_commission": total_commission,
        "deduct_commission": deduct_commission, "real_commission": real_commission,
        "paid_amount": paid_amount, "unpaid_amount": unpaid_amount,
        "stat_status": stat_status, "stat_batch": stat_batch,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_commission_stat_delete(stat_id: int):
    """
    删除佣金统计（DELETE /api/finance/report/commission-stat/{id}）
    :param stat_id: 佣金统计ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/commission-stat/{stat_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.5 现金流量表（正式报表） cash-flow ----------

def finance_report_cash_flow_create(
    report_period: str,
    report_year: int,
    create_user_id: int,
    operating_cash_in=None,
    operating_cash_out=None,
    operating_cash_flow=None,
    investing_cash_in=None,
    investing_cash_out=None,
    investing_cash_flow=None,
    financing_cash_in=None,
    financing_cash_out=None,
    financing_cash_flow=None,
    net_cash_flow=None,
    last_period_net_flow=None,
    report_status: int = None,
):
    """
    创建现金流量表（POST /api/finance/report/cash-flow/create）
    :param report_period: 报表期间 YYYY-MM（必填）
    :param report_year: 报表年度（必填）
    :param create_user_id: 制表人ID（必填）
    :param operating_cash_in: 经营活动现金流入（可选，默认0）
    :param operating_cash_out: 经营活动现金流出（可选，默认0）
    :param operating_cash_flow: 经营活动净现金流（可选，默认0）
    :param investing_cash_in: 投资活动现金流入（可选，默认0）
    :param investing_cash_out: 投资活动现金流出（可选，默认0）
    :param investing_cash_flow: 投资活动净现金流（可选，默认0）
    :param financing_cash_in: 筹资活动现金流入（可选，默认0）
    :param financing_cash_out: 筹资活动现金流出（可选，默认0）
    :param financing_cash_flow: 筹资活动净现金流（可选，默认0）
    :param net_cash_flow: 当期净现金流量（可选，默认0）
    :param last_period_net_flow: 上期同期净现金流，对比分析（可选，默认0）
    :param report_status: 报表状态（可选，默认1）：1草稿 2已审核 3已归档 4作废
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow/create"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "operating_cash_in": operating_cash_in,
        "operating_cash_out": operating_cash_out,
        "operating_cash_flow": operating_cash_flow,
        "investing_cash_in": investing_cash_in,
        "investing_cash_out": investing_cash_out,
        "investing_cash_flow": investing_cash_flow,
        "financing_cash_in": financing_cash_in,
        "financing_cash_out": financing_cash_out,
        "financing_cash_flow": financing_cash_flow,
        "net_cash_flow": net_cash_flow,
        "last_period_net_flow": last_period_net_flow,
        "report_status": report_status, "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_cash_flow_list(
    page: int = 1,
    page_size: int = 20,
    report_period: str = None,
    report_type: int = None,
    report_status: int = None,
):
    """
    获取现金流量表列表（GET /api/finance/report/cash-flow/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param report_period: 报表期间 YYYY-MM 过滤（可选）
    :param report_type: 报表类型过滤（可选）
    :param report_status: 报表状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow/list"
    params = _compact({
        "page": page, "page_size": page_size, "report_period": report_period,
        "report_type": report_type, "report_status": report_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_cash_flow_get(report_id: int):
    """
    获取现金流量表详情（GET /api/finance/report/cash-flow/{id}）
    :param report_id: 现金流量表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow/{report_id}"
    return authenticated_request("GET", url)


def finance_report_cash_flow_update(
    report_id: int,
    report_period: str = None,
    report_year: int = None,
    operating_cash_in=None,
    operating_cash_out=None,
    operating_cash_flow=None,
    investing_cash_in=None,
    investing_cash_out=None,
    investing_cash_flow=None,
    financing_cash_in=None,
    financing_cash_out=None,
    financing_cash_flow=None,
    net_cash_flow=None,
    last_period_net_flow=None,
    report_status: int = None,
    audit_user_id: int = None,
):
    """
    更新现金流量表（PUT /api/finance/report/cash-flow/{id}）
    :param report_id: 现金流量表ID（路径参数，必填）
    :param report_period: 报表期间 YYYY-MM（可选）
    :param report_year: 报表年度（可选）
    :param operating_cash_in: 经营活动现金流入（可选）
    :param operating_cash_out: 经营活动现金流出（可选）
    :param operating_cash_flow: 经营活动净现金流（可选）
    :param investing_cash_in: 投资活动现金流入（可选）
    :param investing_cash_out: 投资活动现金流出（可选）
    :param investing_cash_flow: 投资活动净现金流（可选）
    :param financing_cash_in: 筹资活动现金流入（可选）
    :param financing_cash_out: 筹资活动现金流出（可选）
    :param financing_cash_flow: 筹资活动净现金流（可选）
    :param net_cash_flow: 当期净现金流量（可选）
    :param last_period_net_flow: 上期同期净现金流（可选）
    :param report_status: 报表状态（可选）
    :param audit_user_id: 审核人ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow/{report_id}"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "operating_cash_in": operating_cash_in,
        "operating_cash_out": operating_cash_out,
        "operating_cash_flow": operating_cash_flow,
        "investing_cash_in": investing_cash_in,
        "investing_cash_out": investing_cash_out,
        "investing_cash_flow": investing_cash_flow,
        "financing_cash_in": financing_cash_in,
        "financing_cash_out": financing_cash_out,
        "financing_cash_flow": financing_cash_flow,
        "net_cash_flow": net_cash_flow,
        "last_period_net_flow": last_period_net_flow,
        "report_status": report_status, "audit_user_id": audit_user_id,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_cash_flow_delete(report_id: int):
    """
    删除现金流量表（DELETE /api/finance/report/cash-flow/{id}）
    :param report_id: 现金流量表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/cash-flow/{report_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.6 利润表（正式报表） profit ----------

def finance_report_profit_create(
    report_period: str,
    report_year: int,
    create_user_id: int,
    revenue=None,
    other_business_revenue=None,
    cost=None,
    other_business_cost=None,
    business_tax=None,
    gross_profit=None,
    operating_expense=None,
    admin_expense=None,
    financial_expense=None,
    operating_profit=None,
    total_profit=None,
    income_tax=None,
    net_profit=None,
    last_period_net_profit=None,
    report_status: int = None,
):
    """
    创建利润表（POST /api/finance/report/profit/create）
    :param report_period: 报表期间 YYYY-MM（必填）
    :param report_year: 报表年度（必填）
    :param create_user_id: 制表人ID（必填）
    :param revenue: 营业收入（可选，默认0）
    :param other_business_revenue: 其他业务收入（可选，默认0）
    :param cost: 营业成本（可选，默认0）
    :param other_business_cost: 其他业务成本（可选，默认0）
    :param business_tax: 营业税金及附加（可选，默认0）
    :param gross_profit: 销售毛利润（可选，默认0）
    :param operating_expense: 营业费用（可选，默认0）
    :param admin_expense: 管理费用（可选，默认0）
    :param financial_expense: 财务费用（可选，默认0）
    :param operating_profit: 营业利润（可选，默认0）
    :param total_profit: 利润总额（可选，默认0）
    :param income_tax: 企业所得税（可选，默认0）
    :param net_profit: 净利润（可选，默认0）
    :param last_period_net_profit: 上期同期净利润（可选，默认0）
    :param report_status: 报表状态（可选，默认1）：1草稿 2已审核 3已归档 4作废
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/profit/create"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "revenue": revenue, "other_business_revenue": other_business_revenue,
        "cost": cost, "other_business_cost": other_business_cost,
        "business_tax": business_tax, "gross_profit": gross_profit,
        "operating_expense": operating_expense, "admin_expense": admin_expense,
        "financial_expense": financial_expense,
        "operating_profit": operating_profit, "total_profit": total_profit,
        "income_tax": income_tax, "net_profit": net_profit,
        "last_period_net_profit": last_period_net_profit,
        "report_status": report_status, "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_profit_list(
    page: int = 1,
    page_size: int = 20,
    report_period: str = None,
    report_type: int = None,
    report_status: int = None,
):
    """
    获取利润表列表（GET /api/finance/report/profit/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param report_period: 报表期间 YYYY-MM 过滤（可选）
    :param report_type: 报表类型过滤（可选）
    :param report_status: 报表状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/profit/list"
    params = _compact({
        "page": page, "page_size": page_size, "report_period": report_period,
        "report_type": report_type, "report_status": report_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_profit_get(report_id: int):
    """
    获取利润表详情（GET /api/finance/report/profit/{id}）
    :param report_id: 利润表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/profit/{report_id}"
    return authenticated_request("GET", url)


def finance_report_profit_update(
    report_id: int,
    report_period: str = None,
    report_year: int = None,
    revenue=None,
    other_business_revenue=None,
    cost=None,
    other_business_cost=None,
    business_tax=None,
    gross_profit=None,
    operating_expense=None,
    admin_expense=None,
    financial_expense=None,
    operating_profit=None,
    total_profit=None,
    income_tax=None,
    net_profit=None,
    last_period_net_profit=None,
    report_status: int = None,
    audit_user_id: int = None,
):
    """
    更新利润表（PUT /api/finance/report/profit/{id}）
    :param report_id: 利润表ID（路径参数，必填）
    :param report_period: 报表期间 YYYY-MM（可选）
    :param report_year: 报表年度（可选）
    :param revenue: 营业收入（可选）
    :param other_business_revenue: 其他业务收入（可选）
    :param cost: 营业成本（可选）
    :param other_business_cost: 其他业务成本（可选）
    :param business_tax: 营业税金及附加（可选）
    :param gross_profit: 销售毛利润（可选）
    :param operating_expense: 营业费用（可选）
    :param admin_expense: 管理费用（可选）
    :param financial_expense: 财务费用（可选）
    :param operating_profit: 营业利润（可选）
    :param total_profit: 利润总额（可选）
    :param income_tax: 企业所得税（可选）
    :param net_profit: 净利润（可选）
    :param last_period_net_profit: 上期同期净利润（可选）
    :param report_status: 报表状态（可选）
    :param audit_user_id: 审核人ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/profit/{report_id}"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "revenue": revenue, "other_business_revenue": other_business_revenue,
        "cost": cost, "other_business_cost": other_business_cost,
        "business_tax": business_tax, "gross_profit": gross_profit,
        "operating_expense": operating_expense, "admin_expense": admin_expense,
        "financial_expense": financial_expense,
        "operating_profit": operating_profit, "total_profit": total_profit,
        "income_tax": income_tax, "net_profit": net_profit,
        "last_period_net_profit": last_period_net_profit,
        "report_status": report_status, "audit_user_id": audit_user_id,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_profit_delete(report_id: int):
    """
    删除利润表（DELETE /api/finance/report/profit/{id}）
    :param report_id: 利润表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/profit/{report_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.7 资产负债表（正式报表） balance ----------

def finance_report_balance_create(
    report_period: str,
    report_year: int,
    create_user_id: int,
    current_assets=None,
    non_current_assets=None,
    total_assets=None,
    current_liabilities=None,
    non_current_liabilities=None,
    total_liabilities=None,
    owner_equity=None,
    asset_equity_balance=None,
    begin_total_assets=None,
    begin_total_liabilities=None,
    begin_equity=None,
    report_status: int = None,
):
    """
    创建资产负债表（POST /api/finance/report/balance/create）
    :param report_period: 报表期间 YYYY-MM（必填）
    :param report_year: 报表年度（必填）
    :param create_user_id: 制表人ID（必填）
    :param current_assets: 流动资产合计（可选，默认0）
    :param non_current_assets: 非流动资产合计（可选，默认0）
    :param total_assets: 资产总计（可选，默认0）
    :param current_liabilities: 流动负债合计（可选，默认0）
    :param non_current_liabilities: 非流动负债合计（可选，默认0）
    :param total_liabilities: 负债总计（可选，默认0）
    :param owner_equity: 所有者权益合计（可选，默认0）
    :param asset_equity_balance: 资产权益平衡差值，校验用（可选，默认0）
    :param begin_total_assets: 期初资产总额（可选，默认0）
    :param begin_total_liabilities: 期初负债总额（可选，默认0）
    :param begin_equity: 期初权益总额（可选，默认0）
    :param report_status: 报表状态（可选，默认1）：1草稿 2已审核 3已归档 4作废
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/balance/create"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "current_assets": current_assets,
        "non_current_assets": non_current_assets, "total_assets": total_assets,
        "current_liabilities": current_liabilities,
        "non_current_liabilities": non_current_liabilities,
        "total_liabilities": total_liabilities, "owner_equity": owner_equity,
        "asset_equity_balance": asset_equity_balance,
        "begin_total_assets": begin_total_assets,
        "begin_total_liabilities": begin_total_liabilities,
        "begin_equity": begin_equity, "report_status": report_status,
        "create_user_id": create_user_id,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_balance_list(
    page: int = 1,
    page_size: int = 20,
    report_period: str = None,
    report_type: int = None,
    report_status: int = None,
):
    """
    获取资产负债表列表（GET /api/finance/report/balance/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param report_period: 报表期间 YYYY-MM 过滤（可选）
    :param report_type: 报表类型过滤（可选）
    :param report_status: 报表状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/balance/list"
    params = _compact({
        "page": page, "page_size": page_size, "report_period": report_period,
        "report_type": report_type, "report_status": report_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_balance_get(report_id: int):
    """
    获取资产负债表详情（GET /api/finance/report/balance/{id}）
    :param report_id: 资产负债表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/balance/{report_id}"
    return authenticated_request("GET", url)


def finance_report_balance_update(
    report_id: int,
    report_period: str = None,
    report_year: int = None,
    current_assets=None,
    non_current_assets=None,
    total_assets=None,
    current_liabilities=None,
    non_current_liabilities=None,
    total_liabilities=None,
    owner_equity=None,
    asset_equity_balance=None,
    begin_total_assets=None,
    begin_total_liabilities=None,
    begin_equity=None,
    report_status: int = None,
    audit_user_id: int = None,
):
    """
    更新资产负债表（PUT /api/finance/report/balance/{id}）
    :param report_id: 资产负债表ID（路径参数，必填）
    :param report_period: 报表期间 YYYY-MM（可选）
    :param report_year: 报表年度（可选）
    :param current_assets: 流动资产合计（可选）
    :param non_current_assets: 非流动资产合计（可选）
    :param total_assets: 资产总计（可选）
    :param current_liabilities: 流动负债合计（可选）
    :param non_current_liabilities: 非流动负债合计（可选）
    :param total_liabilities: 负债总计（可选）
    :param owner_equity: 所有者权益合计（可选）
    :param asset_equity_balance: 资产权益平衡差值（可选）
    :param begin_total_assets: 期初资产总额（可选）
    :param begin_total_liabilities: 期初负债总额（可选）
    :param begin_equity: 期初权益总额（可选）
    :param report_status: 报表状态（可选）
    :param audit_user_id: 审核人ID（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/balance/{report_id}"
    payload = _compact({
        "report_period": report_period, "report_year": report_year,
        "current_assets": current_assets,
        "non_current_assets": non_current_assets, "total_assets": total_assets,
        "current_liabilities": current_liabilities,
        "non_current_liabilities": non_current_liabilities,
        "total_liabilities": total_liabilities, "owner_equity": owner_equity,
        "asset_equity_balance": asset_equity_balance,
        "begin_total_assets": begin_total_assets,
        "begin_total_liabilities": begin_total_liabilities,
        "begin_equity": begin_equity, "report_status": report_status,
        "audit_user_id": audit_user_id,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_balance_delete(report_id: int):
    """
    删除资产负债表（DELETE /api/finance/report/balance/{id}）
    :param report_id: 资产负债表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/balance/{report_id}"
    return authenticated_request("DELETE", url)


# ---------- 10.8 财务报表主表 financial ----------

def finance_report_financial_create(
    report_name: str,
    report_type: int,
    report_period: str,
    report_year: int,
    create_user_id: int,
    cash_flow_statement_id: int = None,
    profit_statement_id: int = None,
    balance_sheet_id: int = None,
    report_file_url: str = None,
    status: int = None,
    remark: str = None,
):
    """
    创建财务报表主表（POST /api/finance/report/financial/create）
    :param report_name: 报表名称（必填）
    :param report_type: 报表类型（必填）：1现金流量表 2利润表 3资产负债表 4综合财报
    :param report_period: 报表期间 YYYY-MM（必填）
    :param report_year: 报表年度（必填）
    :param create_user_id: 报表编制人ID（必填）
    :param cash_flow_statement_id: 现金流量表ID（可选）
    :param profit_statement_id: 利润表ID（可选）
    :param balance_sheet_id: 资产负债表ID（可选）
    :param report_file_url: 导出报表附件文件（可选）
    :param status: 报表状态（可选，默认1）：1草稿 2已编制 3已审核 4已归档 5作废
    :param remark: 报表编制说明、数据异常备注（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/financial/create"
    payload = _compact({
        "report_name": report_name, "report_type": report_type,
        "report_period": report_period, "report_year": report_year,
        "cash_flow_statement_id": cash_flow_statement_id,
        "profit_statement_id": profit_statement_id,
        "balance_sheet_id": balance_sheet_id,
        "report_file_url": report_file_url, "status": status,
        "create_user_id": create_user_id, "remark": remark,
    })
    return authenticated_request("POST", url, json=payload)


def finance_report_financial_list(
    page: int = 1,
    page_size: int = 20,
    report_period: str = None,
    report_type: int = None,
    report_status: int = None,
):
    """
    获取财务报表主表列表（GET /api/finance/report/financial/list）
    :param page: 页码，默认1（可选）
    :param page_size: 每页数量，默认20（可选）
    :param report_period: 报表期间 YYYY-MM 过滤（可选）
    :param report_type: 报表类型过滤（可选）
    :param report_status: 报表状态过滤（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/financial/list"
    params = _compact({
        "page": page, "page_size": page_size, "report_period": report_period,
        "report_type": report_type, "report_status": report_status,
    })
    return authenticated_request("GET", url, params=params)


def finance_report_financial_get(report_id: int):
    """
    获取财务报表主表详情（GET /api/finance/report/financial/{id}）
    :param report_id: 财务报表主表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/financial/{report_id}"
    return authenticated_request("GET", url)


def finance_report_financial_update(
    report_id: int,
    report_name: str = None,
    report_type: int = None,
    report_period: str = None,
    report_year: int = None,
    cash_flow_statement_id: int = None,
    profit_statement_id: int = None,
    balance_sheet_id: int = None,
    report_file_url: str = None,
    status: int = None,
    audit_user_id: int = None,
    archive_user_id: int = None,
    remark: str = None,
):
    """
    更新财务报表主表（PUT /api/finance/report/financial/{id}）
    :param report_id: 财务报表主表ID（路径参数，必填）
    :param report_name: 报表名称（可选）
    :param report_type: 报表类型（可选）
    :param report_period: 报表期间 YYYY-MM（可选）
    :param report_year: 报表年度（可选）
    :param cash_flow_statement_id: 现金流量表ID（可选）
    :param profit_statement_id: 利润表ID（可选）
    :param balance_sheet_id: 资产负债表ID（可选）
    :param report_file_url: 导出报表附件文件（可选）
    :param status: 报表状态（可选）
    :param audit_user_id: 报表审核人ID（可选）
    :param archive_user_id: 报表归档人ID（可选）
    :param remark: 报表编制说明、数据异常备注（可选）
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/financial/{report_id}"
    payload = _compact({
        "report_name": report_name, "report_type": report_type,
        "report_period": report_period, "report_year": report_year,
        "cash_flow_statement_id": cash_flow_statement_id,
        "profit_statement_id": profit_statement_id,
        "balance_sheet_id": balance_sheet_id,
        "report_file_url": report_file_url, "status": status,
        "audit_user_id": audit_user_id, "archive_user_id": archive_user_id,
        "remark": remark,
    })
    return authenticated_request("PUT", url, json=payload)


def finance_report_financial_delete(report_id: int):
    """
    删除财务报表主表（DELETE /api/finance/report/financial/{id}）
    :param report_id: 财务报表主表ID
    """
    url = f"{BASE_URL}{API_FINANCE_REPORT}/financial/{report_id}"
    return authenticated_request("DELETE", url)
