# 房产SaaS-销售管理工具（sale 技能）

## 定位

销售端技能，**严格对照后端 `real_estate_agent_saas/sale/router/*` 路由接口实现**，字段对照 `sale/schemas/*` 的 Pydantic 校验模型与 `sale/model/sale_models.py` 的列注释。共 **104 个工具**（5 认证 + 99 业务），覆盖楼盘销控、客户管理、认购签约交易、分销渠道与佣金、销售业绩与考核、数据统计报表六大业务域。

## 与 admin 的关系

- **认证共享**：sale 与 admin 共用同一后端、同一凭证文件 `saas_tenant_auth/cred.json`（由根目录 `auth_core.py` 统一管理）。任一端登录后另一端均可读取使用。
- **登录方式**：调用 `sale_login`（等价于 `tenant_login`）即可，凭证写入共享文件；token 过期由 `auth_core` 基于 `code=5000` 自动刷新。
- **独立清单**：本技能拥有独立的 `skill.json`，注册 `sale_*` 系列工具，可独立加载，不污染 admin 技能。

## 后端对接说明

- **后端路由挂载点**：`main.py` 中 `app.include_router(sale_router, prefix="/api/sale")`，故所有 sale 接口统一以 `/api/sale` 开头。
- **URL 构造规则**：`BASE_URL + /api/sale/<子路由>/<route>`，子路由基址常量见 [`sale/config.py`](file:///d:/saas_tenant_skill-master/sale/config.py)。
- **响应约定**：成功 `code=0`，业务失败 `code=5000`（触发 token 自动刷新重试）。

### 子路由基址

| 常量                   | 路径                    | 业务域         |
| ---------------------- | ----------------------- | -------------- |
| `API_SALE_PROJECT`     | `/api/sale/project`     | 楼盘销控       |
| `API_SALE_CUSTOMER`    | `/api/sale/customer`    | 客户管理       |
| `API_SALE_TRANSACTION` | `/api/sale/transaction` | 认购签约交易   |
| `API_SALE_COMMISSION`  | `/api/sale/commission`  | 分销渠道与佣金 |
| `API_SALE_PERFORMANCE` | `/api/sale/performance` | 销售业绩与考核 |
| `API_SALE_STATISTICS`  | `/api/sale/statistics`  | 数据统计报表   |

## 请求构造规则（遵循 FastAPI）

对照后端 `router` 中各端点的参数声明方式，在 [`sale/main.py`](file:///d:/saas_tenant_skill-master/sale/main.py) 中按下述规则构造请求：

1. **路径参数**（`{xxx_id}`）：直接拼入 URL，如 `/detail/{project_id}` → `/detail/1`。
2. **query 参数**：标量参数（即使 POST）走 `params=`。后端用 `Query(...)` 声明的参数（含部分 POST 端点）均按 query 传递。
3. **body 参数**：后端用 Pydantic schema 声明的请求体走 `json=`，字段平铺为 dict。
4. **多 body 参数**：`customer/create` 为 FastAPI 多 body 参数端点，按规则嵌套为 `{"customer_data": {...}, "tags": [...], "demands": [...]}`。
5. **`_compact`**：剔除值为 `None` 的键（保留 `0`/`False`），让后端按 schema 默认值生效，避免误传 `null`。

## 目录结构

```
saas_tenant_skill-master/
├── auth_core.py            # 共享认证内核（凭证读写 / 认证请求 / token刷新 / 登录登出改密）
├── config.py               # 根配置（BASE_URL / AUTH_FILE / admin 接口路径）
├── main.py                 # admin 技能入口（未改动）
├── skill.json              # admin 技能清单（未改动）
└── sale/
    ├── config.py           # sale API 子路由基址常量（6 个业务域）
    ├── main.py             # sale 技能入口：5 认证 + 99 业务函数
    ├── skill.json          # sale 技能清单（104 工具）
    └── README.md           # 本文件
```

## 已注册工具（104 个）

### 认证（5，复用 `auth_core`）

| 工具                   | 说明                               |
| ---------------------- | ---------------------------------- |
| `sale_login`           | 销售端登录，凭证写入共享 cred.json |
| `sale_logout`          | 登出，销毁本地共享凭证             |
| `sale_refresh_token`   | 主动刷新 access_token              |
| `sale_change_password` | 修改当前账号密码                   |
| `sale_get_login_user`  | 查询当前登录用户信息               |

### 业务（99，按域分组）

| 业务域         | 工具数 | 工具列表                                                                                                                                                                                                                 |
| -------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 楼盘销控       | 25     | project(create/list/detail/update/delete)、building(create/list/update)、unit(create/list/detail/update)、house(create/list/detail/update/lock/unlock/control)、project_rule(create/list/detail/update/delete/get-value) |
| 客户管理       | 15     | customer(create/list/detail/update/delete/transfer)、report(create/list)、visit(confirm/list)、follow(create/list)、sea(add/pick/list)                                                                                   |
| 认购签约交易   | 22     | subscribe(create/list/detail/update/cancel)、contract(create/list/detail/update/record)、payment(create/list/update/confirm)、loan(create/list/update)、receipt(create/list/update/status_update)、transaction(list)     |
| 分销渠道与佣金 | 16     | channel(create/list/detail/update/terminate)、broker(create/list/detail/update)、commission_rule(create/list/update)、bill(generate/list/audit/freeze)                                                                   |
| 销售业绩与考核 | 15     | team(create/list/detail/update/dissolve/member_add)、target(create/list/update)、performance(personal/team)、sales_commission(calculate/list/audit/freeze)                                                               |
| 数据统计报表   | 6      | statistics(overview/project/personal/team/channel/custom)                                                                                                                                                                |

## 字段对照原则

- **schema 为准**：以 `sale/schemas/*` 的 Pydantic 模型为字段契约权威，必填（`Field(...)`）对应函数必填参数，可选（`Field(None)`/默认值）对应可选参数。
- **model 补充语义**：`sale/model/sale_models.py` 的列注释用于补充枚举值说明（如状态码含义），已写入函数 docstring 与 `skill.json` 的 description。
- **枚举说明示例**：
  - `house_status`：1-可售 2-已售 3-锁定 4-预定 5-停售
  - `customer_status`：1-潜客 2-意向 3-认购 4-签约 5-成交 6-无效
  - `loan_status`：1-申请中 2-已批贷 3-已放款 4-已结清
  - `receipt_status`：1-待开票 2-已开票 3-已作废

## 自检与验证

提供两个自检脚本（验证用，非运行时依赖）：

- [`sale/_verify.py`](file:///d:/saas_tenant_skill-master/sale/_verify.py)：导入检查 + 函数/工具名称一致性 + 参数顺序/类型一致性 + admin 回归。
- [`sale/_verify_request.py`](file:///d:/saas_tenant_skill-master/sale/_verify_request.py)：monkeypatch `authenticated_request`，对 99 个业务函数逐个验证 URL 前缀、HTTP 方法、路径参数、query/json 区分。

最近一次自检结果：**104 函数 / 104 工具，名称/参数/类型 0 错误；99 业务请求构造全通过；admin 回归正常**。

运行：

```bash
python sale/_verify.py
python sale/_verify_request.py
```

## 使用示例

```python
# 1. 登录（凭证写入共享 cred.json）
sale_login(account="sale01", password="xxxx")

# 2. 创建楼盘
sale_project_create(
    project_code="P2026001", project_name="翡翠湾", developer="XX地产",
    province="广东省", city="深圳市", district="南山区", address="科技园路1号",
    project_type="住宅", project_status=1,
)

# 3. 创建客户（多 body 参数自动嵌套）
sale_customer_create(
    customer_name="张三", mobile="13800000000", gender=1,
    customer_status=2, belong_user_id=10, tags=["高意向"], demands=[{"room_type":"3室"}],
)

# 4. 查询销控面板
sale_house_control(project_id=1)

# 5. 项目总览统计（首页大屏）
sale_statistics_overview(project_id=1)
```
