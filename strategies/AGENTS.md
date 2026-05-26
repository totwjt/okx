# strategies/ - 策略工厂与策略资产管理

## 概述

AI 量化交易策略管理系统。当前目录正在从“文件型策略仓库”迁移为“PostgreSQL 驱动的策略注册表 + 临时运行产物生成器”。

先读：

- `STRATEGY_LIFECYCLE.md`：策略生命周期、生成物隔离、数据库化方案。
- `../docs/operations/ai-strategy-generation-sop.md`：AI 生成策略必须遵循的 step 操作 SOP。

## 结构
```
strategies/
├── spec/           # 旧策略 YAML 定义（待迁移到 PostgreSQL）
│   ├── grid_ls_v1.yaml
│   ├── multi_ls_v2.yaml
│   └── multi_ls_v3.yaml
├── profiles/       # 旧参数档案（待迁移到 PostgreSQL）
│   ├── grid_ls_v1/
│   ├── multi_ls_v2/
│   └── multi_ls_v3/
├── generated/      # 旧自动生成代码（生成物，待隔离）
├── services/      # CLI 服务层
│   ├── generation_service.py
│   ├── profile_service.py
│   ├── config_service.py
│   └── ...
├── cli.py         # 主 CLI 入口
└── auto_*.py     # 旧 Docker 挂载策略（生成物，待隔离）
```

## WHERE TO LOOK
| 任务 | 路径 |
|------|------|
| 策略定义修改 | `spec/<strategy>.yaml` |
| 参数调整 | `profiles/<strategy>/` |
| 代码生成逻辑 | `services/generation_service.py` |

## CONVENTIONS
- 目标策略接入链: `PostgreSQL strategy registry -> materialize runtime artifact -> docker运行`
- 过渡期旧链路: `spec -> profile -> generated -> auto_json -> docker运行`
- `generated/`、`auto_*.py`、`auto_*.json` 是生成产物，禁止手工编辑
- `DATABASE_URL` 是策略注册表连接配置的唯一来源
- 独立实验放 `research/experiments/`
- AI 生成策略前必须声明使用 `docs/operations/ai-strategy-generation-sop.md`，并逐步推进 Step。
- Web scaffold 只是流程模板；最终 spec 必须体现 AI 的专业策略判断。

## ANTI-PATTERNS
- ❌ 新建策略文件放 strategies/ 主目录
- ❌ 修改 auto_*.py 手工内容
- ❌ 把 generated/runtime 产物作为源码长期维护
- ❌ 用测试集调参
- ❌ 跳过 hypothesis/spec/profile/registry/materialize/static-check 的最小闭环
