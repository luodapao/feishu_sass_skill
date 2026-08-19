"""
main.py —— 房产SaaS 租户技能统一主入口（薄聚合层）

聚合 admin / sale / finance 三个模块的全部工具函数，作为项目统一入口，
本身不含任何业务逻辑，仅做 re-export：
- admin.main  —— 租户用户管理 / 角色管理（tenant_* 系列）
- sale.main   —— 销售管理（sale_* 系列）
- finance.main —— 财务管理（finance_* 系列）

三端复用同一认证内核 auth_core，共享同一 cred.json。
各模块仍保留独立 skill.json（admin/skill.json、sale/skill.json、finance/skill.json），
可单独加载；本文件仅便于在需要时一次性导入全部工具。
"""
import os
import sys

# 将项目根加入搜索路径，确保 admin / sale / finance 包均可导入
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 透传三端全部工具函数（保持原有函数名与签名不变）
from admin.main import *      # noqa: F401,F403  tenant_* 系列
from sale.main import *       # noqa: F401,F403  sale_* 系列
from finance.main import *    # noqa: F401,F403  finance_* 系列
