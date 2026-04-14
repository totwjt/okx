# execution/ - Docker 执行环境

## 概述

Freqtrade Docker 容器运行环境，包含配置、数据目录和运维脚本。

## 结构
```
execution/
├── configs/         # 样例配置、参数快照
├── freqtrade/       # 主运行目录
│   ├── docker-compose.yml
│   └── user_data/  # 当前运行数据
├── scripts/        # simctl 运维脚本
└── templates/     # 模板（非主目录）
```

## WHERE TO LOOK
| 任务 | 路径 |
|------|------|
| Docker 配置 | `freqtrade/docker-compose.yml` |
| 运行配置 | `freqtrade/user_data/config.json` |
| 运维脚本 | `scripts/simctl` |

## CONVENTIONS
- 主运行目录 = `execution/freqtrade/user_data/`
- 模板目录 = `execution/templates/` 非主目录

## ANTI-PATTERNS
- ❌ 把 templates 当主运行目录
- ❌ 维护 Docker 策略副本（strategies/ 即唯一源码）