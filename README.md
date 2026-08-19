# 房产SaaS 技能集（saas_tenant_skill-master）

> 测试开发专家 · 技能工作区总览入口
> 维护时间：2026-08-14

## 项目结构

```
saas_tenant_skill-master/
├── README.md            # 本文件（总览入口）
├── auth_core.py         # 共享认证内核（凭证读写 / 认证请求 / token刷新 / 登录登出改密）
├── config.py            # 根配置（BASE_URL / AUTH_FILE / 认证接口路径）
├── main.py              # admin 技能入口
├── skill.json           # admin 技能清单
├── docs/
│   └── 07_确认交互卡片化.md   # 确认交互规范（feishu_ask_user_question 选项卡片）
├── admin/
│   ├── config.py        # admin 业务 API 路径
│   ├── main.py          # admin 技能实现（tenant_* 系列）
│   ├── skill.json       # admin 工具清单
│   └── ...
├── sale/
│   ├── config.py        # sale 业务 API 路径（6 个业务域）
│   ├── main.py          # sale 技能实现（sale_* 系列，104 工具）
│   ├── skill.json       # sale 工具清单
│   ├── README.md        # sale 使用说明
│   └── ...
├── finance/
│   ├── main.py          # finance 技能实现（finance_* 系列）
│   ├── skill.json       # finance 工具清单
│   └── ...
├── saas_tenant_auth/    # 本地凭证存储（cred.json，三端共享）
├── test_results/        # 测试报告 / 缺陷清单
└── test_framework.py    # 测试框架
```

## 文档索引

| 文档 | 说明 |
|:-----|:-----|
| [docs/07_确认交互卡片化.md](docs/07_确认交互卡片化.md) | **确认交互规范**：所有 `need_confirm` 二次确认一律用 `feishu_ask_user_question` 发选项卡片（7.1-7.4 完整规范） |
| [sale/README.md](sale/README.md) | sale 技能定位、后端对接、请求构造规则、104 工具清单、自检脚本 |
| [finance/README.md](finance/README.md) | finance 技能说明 |
| [test_results/11_后端缺陷与优化清单.md](test_results/11_后端缺陷与优化清单.md) | 后端缺陷与优化清单 |

## 本次变更（2026-08-14）

### 新增
- **`docs/07_确认交互卡片化.md`** — 确认交互卡片化规范（核心交付）：
  - **7.1** `feishu_ask_user_question` 完整 JSON 参数模板（question / header≤12字 / options[{label,description}] / multiSelect）+ 关键参数约定（选项顺序：第一项=确认执行，第二项=取消）
  - **7.2** Agent 处理逻辑：收到答案→解析确认/取消→confirmed=True/False 调技能；含 `tenant_logout`、`sale_project_create` 两段示例代码
  - **7.3** 标准流程完整闭环：发起操作→技能返回 need_confirm→发选项卡片→用户点选→答案回传→执行/取消
  - **7.4** 使用要点 5 条：必须用官方工具 / 两个选项足够 / 敏感字段脱敏 / 保持技能 confirmed 机制不变 / 适用技能清单

### 修改
- **`admin/skill.json`** — 顶层 `description` 追加「确认交互规范：need_confirm 一律用 feishu_ask_user_question 发选项卡片，详见 docs/07_确认交互卡片化.md」
- **`sale/skill.json`** — 顶层 `description` 追加同款确认交互规范引用

### 未改动
- `finance/skill.json` — 无 `need_confirm` 机制（不含写确认），不涉及
- 所有技能 `main.py` 业务逻辑 — 三段式 confirmed 机制保持不变
- `auth_core.py` / `config.py` — 未改动

### 验证
- 三个 skill.json（admin / sale / finance）均通过 JSON 合法性校验 ✅

---

## 当前约束备忘

- 确认卡片依赖 `feishu_ask_user_question`（需飞书渠道 + 飞书后台开通 `card.action.trigger` 卡片回调事件）。
- 若目标渠道非飞书或回调未开通，Agent 降级为**文字二次确认**（沿用原 need_confirm 交互），不影响技能可用性。
