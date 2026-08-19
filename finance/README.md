# 房产SaaS-财务管理工具（finance 技能）

## 定位

财务端技能，**严格对照后端 `real_estate_agent_saas/finance/router/*` 路由接口实现**，字段对照 `finance/schemas/*` 的 Pydantic 校验模型（`Create`/`Update`）。共 **227 个工具**（5 认证 + 222 业务），覆盖财务基础档案、房款收支、票据税务合规、佣金支付、项目成本、应收应付往来台账、资金对账、会计凭证、财务审计追溯、财务统计报表**十大业务域**。

> 独立于 `sale` 技能：本技能所有函数以 `finance_` 前缀命名、单独存放于 `finance/` 目录、拥有独立 `skill.json`，便于大模型精准区分与调用，不与 `sale_*` / admin 工具混淆。

## 与 admin / sale 的关系

- **认证共享**：finance 与 admin、sale 共用同一后端、同一凭证文件 `saas_tenant_auth/cred.json`（由根目录 `auth_core.py` 统一管理）。任一端登录后其它端均可读取使用。
- **登录方式**：调用 `finance_login`（等价于 `tenant_login`）即可，凭证写入共享文件；token 过期由 `auth_core` 基于 `code=5000` 自动刷新。
- **独立清单**：本技能拥有独立的 `skill.json`，注册 `finance_*` 系列工具，可独立加载，不污染 admin / sale 技能。

## 后端对接说明

- **后端路由挂载点**：`main.py` 中 `app.include_router(finance_router, prefix="/api")`，finance 各子路由自身声明 `prefix="/finance/<域>"`，故所有 finance 接口统一以 `/api/finance` 开头。
- **URL 构造规则**：`BASE_URL + /api/finance/<子路由>/<route>`，子路由基址常量见 [`finance/config.py`](file:///d:/test/新建文件夹/saas_tenant_skill-master/finance/config.py)。
- **响应约定**：成功 `code=0`，业务失败 `code=5000`（触发 token 自动刷新重试）。

### 子路由基址

| 常量                          | 路径                          | 业务域             |
| ----------------------------- | ----------------------------- | ------------------ |
| `API_FINANCE_ARCHIVE`         | `/api/finance/archive`        | 财务基础档案       |
| `API_FINANCE_PAYMENT`         | `/api/finance/payment`        | 房款收支           |
| `API_FINANCE_INVOICE`         | `/api/finance/invoice`        | 票据税务合规       |
| `API_FINANCE_COMMISSION`      | `/api/finance/commission`     | 佣金支付           |
| `API_FINANCE_COST`            | `/api/finance/cost`           | 项目成本           |
| `API_FINANCE_AR_AP`           | `/api/finance/ar-ap`          | 应收应付往来台账   |
| `API_FINANCE_RECONCILIATION`  | `/api/finance/reconciliation` | 资金对账           |
| `API_FINANCE_VOUCHER`         | `/api/finance/voucher`        | 会计凭证           |
| `API_FINANCE_AUDIT`           | `/api/finance/audit`          | 财务审计追溯       |
| `API_FINANCE_REPORT`          | `/api/finance/report`         | 财务统计报表       |

## 请求构造规则（遵循 FastAPI）

对照后端 `router` 中各端点的参数声明方式，在 [`finance/main.py`](file:///d:/test/新建文件夹/saas_tenant_skill-master/finance/main.py) 中按下述规则构造请求：

1. **路径参数**（`{id}`）：直接拼入 URL，如 `/archive/config/{config_id}`。函数内以语义化命名（`config_id`/`voucher_id`/`report_id` 等）承接。
2. **query 参数**：`list` 端点的分页与过滤参数（后端以 `Query`/默认值声明）走 `params=`，含 `date` 类型过滤（如 `check_date`/`account_date`/`voucher_date`）以字符串传递。
3. **body 参数**：后端用 Pydantic schema（`XxxCreate`/`XxxUpdate`）声明的请求体走 `json=`，字段平铺为 dict。
4. **特殊 action 端点**（`bank/match`、`bank/finish`、`daily/audit`、`channel/confirm`、`voucher/audit`、`voucher/red-flush`）：请求体主键字段后端名为 `id`，函数参数改用语义化命名（`check_id`/`account_record_id`/`reconcile_id`/`voucher_id`），在 payload 中通过 `"id": <语义化参数>` 映射回后端。
5. **`_compact`**：剔除值为 `None` 的键（保留 `0`/`False`），让后端按 schema 默认值生效（大量 `Decimal` 金额字段默认 `0`、`exchange_rate` 默认 `1.0000` 等），避免误传 `null`。

## 目录结构

```
saas_tenant_skill-master/
├── auth_core.py            # 共享认证内核（凭证读写 / 认证请求 / token刷新 / 登录登出改密）
├── config.py               # 根配置（BASE_URL / AUTH_FILE / admin 接口路径）
├── main.py                 # admin 技能入口（未改动）
├── skill.json              # admin 技能清单（未改动）
├── sale/                   # 销售管理技能（未改动）
└── finance/
    ├── config.py           # finance API 子路由基址常量（10 个业务域）
    ├── main.py             # finance 技能入口：5 认证 + 222 业务函数
    ├── skill.json          # finance 技能清单（227 工具）
    └── README.md           # 本文件
```

## 已注册工具（227 个）

### 认证（5，复用 `auth_core`）

| 工具                      | 说明                               |
| ------------------------- | ---------------------------------- |
| `finance_login`           | 财务端登录，凭证写入共享 cred.json |
| `finance_logout`          | 登出，销毁本地共享凭证             |
| `finance_refresh_token`   | 主动刷新 access_token              |
| `finance_change_password` | 修改当前账号密码                   |
| `finance_get_login_user`  | 查询当前登录用户信息               |

### 业务（222，按域分组）

| 业务域           | 工具数 | 分组（每组含 create/list/get/update/delete，特殊 action 额外标注）                                                                                             |
| ---------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 财务基础档案     | 30     | config、account、subject、tax-rate、bank、preferential-rule（6 组 × 全 CRUD）                                                                                  |
| 房款收支         | 25     | installment、adjustment、receipt、refund、deposit（5 组 × 全 CRUD）                                                                                             |
| 票据税务合规     | 25     | blue、red、receipt、maintenance-fund、tax-declaration（5 组 × 全 CRUD）                                                                                         |
| 佣金支付         | 20     | pay、deduct、sales、bonus（4 组 × 全 CRUD）                                                                                                                     |
| 项目成本         | 25     | expense、reimbursement、payment、advertising、engineering（5 组 × 全 CRUD）                                                                                     |
| 应收应付往来台账 | 20     | receivable、payable、prepayment、other-loan（4 组 × 全 CRUD）                                                                                                   |
| 资金对账         | 19     | bank（CRUD + match/finish）、daily（CRUD + audit）、channel（CRUD + confirm）                                                                                   |
| 会计凭证         | 13     | voucher 主表（create/audit/red-flush/list/get/get-with-items/update/delete，8）+ item 明细（create/list/get/update/delete，5）                                  |
| 财务审计追溯     | 5      | operate-log（create/list/get/update/delete）                                                                                                                   |
| 财务统计报表     | 40     | cash-flow-stat、receivable-stat、tax-stat、commission-stat、cash-flow、profit、balance、financial（8 组 × 全 CRUD）                                             |

## 字段对照原则

- **schema 为准**：以 `finance/schemas/*` 的 Pydantic 模型为字段契约权威。必填（`Field(...)`）对应函数必填参数（排在前、无默认值）；可选（`Field(None)` 或含默认值）对应可选参数（`=None`），由 `_compact` 剔除后按后端默认值生效。
- **Create vs Update 差异**：Create 与 Update 字段集合/必填性不同，已分别对照落地为独立函数。
- **枚举/中文说明**：schema `description` 中的枚举语义已完整写入函数 docstring 与 `skill.json` 的 description，供大模型正确取值。典型枚举示例：
  - 凭证 `voucher_type`：1收款凭证 2付款凭证 3转账凭证；`voucher_status`：1草稿 2已审核 3已结账 4已作废 5已红冲 6反结账
  - 凭证审核 `audit_status`：2已审核 4已作废；红冲需 `red_flush_reason` + `make_user_id`
  - 银行对账 `check_status`：1未匹配 2已匹配一致 3对账差异 4手动调平 5作废
  - 每日轧账审核 `audit_status`：2通过 5驳回；渠道对账确认 `confirm_status`：2无差异 3有差异
  - 报表 `report_status`：1草稿 2已审核 3已归档 4作废；财报主表 `status`：1草稿 2已编制 3已审核 4已归档 5作废
  - 审计 `biz_module`：1收款 2退款 3应付应收 4预付 5其他往来 6资金对账 7会计凭证 8佣金 9费用报销 10财务配置

## 类型约定（skill.json）

- `type` 取值：`string` / `integer` / `number`（金额、税额、汇率、比率等 `Decimal` 字段统一为 `number`）。
- `date` / `datetime` 字段一律以 `string` 传参（如 `YYYY-MM-DD`、`YYYY-MM`）。
- 必填参数描述以「（必填）」标注，可选参数以「（可选）」/「（可选，默认X）」标注，与 `main.py` docstring 完全一致。

## 使用示例

```python
# 1. 登录（凭证写入共享 cred.json，与 admin/sale 通用）
finance_login(account="fin01", password="xxxx")

# 2. 创建项目财务配置
finance_archive_config_create(project_id=1, project_name="翡翠湾", create_user_id=10)

# 3. 创建会计凭证（收款凭证）
finance_voucher_create(
    voucher_type=1, voucher_year=2026, voucher_month="2026-08",
    voucher_date="2026-08-06", source_type=1, source_biz_id=1001,
    source_biz_no="SK202608060001", summary="收取张三首付款",
    make_user_id=10,
)

# 4. 审核凭证（id 通过语义化参数 voucher_id 映射）
finance_voucher_audit(voucher_id=1, audit_user_id=20, audit_status=2)

# 5. 银行对账自动匹配
finance_reconciliation_bank_match(account_id=1, check_date="2026-08-06", amount_tolerance=0.01)

# 6. 生成利润表（正式报表）
finance_report_profit_create(
    report_period="2026-08", report_year=2026, create_user_id=10,
    revenue=1000000, cost=600000, net_profit=300000, report_status=1,
)

# 7. 分页查询会计凭证列表（date 过滤以字符串传递）
finance_voucher_list(page=1, page_size=20, voucher_type=1, voucher_date="2026-08-06")
```
