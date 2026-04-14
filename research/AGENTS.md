# research/ - 研究实验目录

## 概述

研究脚本、实验报告、线程协调文件。策略代码不放这里。

## 结构
```
research/
├── experiments/   # 实验脚本
├── coordination/ # 线程进度、信号
├── reports/     # 回测报告
├── archive/     # 历史归档
└── README.md
```

## WHERE TO LOOK
| 任务 | 路径 |
|------|------|
| 实验脚本 | `experiments/` |
| 线程进度 | `coordination/progress/` |

## ANTI-PATTERNS
- ❌ 策略放 research/ 主目录（放 strategies/）
- ❌ 独立实验放 strategies/（放 research/experiments/）