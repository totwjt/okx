# strategies/ - 策略源码管理

## 概述

AI 量化交易策略管理系统，支持 YAML 配置定义策略、自动代码生成、Profile 参数治理。

## 结构
```
strategies/
├── spec/           # 策略 YAML 定义（3 条生成链）
│   ├── grid_ls_v1.yaml
│   ├── multi_ls_v2.yaml
│   └── multi_ls_v3.yaml
├── profiles/       # 参数档案（46 个 profile）
│   ├── grid_ls_v1/
│   ├── multi_ls_v2/
│   └── multi_ls_v3/
├── generated/      # 自动生成代码
├── services/      # CLI 服务层
│   ├── generation_service.py
│   ├── profile_service.py
│   ├── config_service.py
│   └── ...
├── cli.py         # 主 CLI 入口
└── auto_*.py     # Docker 挂载策略
```

## WHERE TO LOOK
| 任务 | 路径 |
|------|------|
| 策略定义修改 | `spec/<strategy>.yaml` |
| 参数调整 | `profiles/<strategy>/` |
| 代码生成逻辑 | `services/generation_service.py` |

## CONVENTIONS
- 唯一策略接入链: `spec -> profile -> generated -> auto_json -> docker运行`
- `generated/`、`auto_*.py` 是生成产物，禁止手工编辑
- 独立实验放 `research/experiments/`

## ANTI-PATTERNS
- ❌ 新建策略文件放 strategies/ 主目录
- ❌ 修改 auto_*.py 手工内容
- ❌ 用测试集调参