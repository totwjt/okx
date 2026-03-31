# AI-OuYi

## 项目定位

这是一个以 `Freqtrade + OKX` 为核心的研究型量化仓库，当前更接近“策略实验平台”，而不是可直接实盘托管的成熟交易系统。

## 当前事实来源

- 运行中的 Docker 数据目录: `ft_userdata/user_data/`
- 本地策略研发目录: `strategies/`
- 本地实验脚本目录: `backtest/`
- 自定义实时机器人原型: `freqtrade_bot/realtime_bot.py`
- OpenCode 知识库: `.opencode/knowledge-base/`

优先相信以下路径中的内容是否与彼此一致，而不是只相信单个说明文件：

- `ft_userdata/user_data/config.json`
- `ft_userdata/user_data/strategies/`
- `strategies/`
- `AI_CONTEXT.md`

## 运行环境

### Docker（主环境）

`freqtrade` 容器是当前主要运行入口。默认挂载关系见：

- `ft_userdata/docker-compose.yml`

当前唯一主线策略：

- `MultiLsV2Strategy`

常用命令：

```bash
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker logs -f freqtrade
```

### 本地 Python（辅助环境）

仅适合阅读脚本、做研究型回测或生成策略，不应默认假设本地环境和 Docker 环境完全一致。

## 目录说明

```text
AI-OuYi/
├── .opencode/                  # OpenCode 项目配置与知识库
├── backtest/                   # 自定义回测脚本（OKX API / vectorbt）
├── config/                     # 本地配置样例
├── freqtrade_bot/              # 自定义实时机器人原型
├── ft_userdata/                # Docker 实际使用的数据与配置
├── strategies/                 # 本地策略源码、生成器、规范
├── user_data/                  # Freqtrade 模板目录，非当前主运行目录
├── AI_CONTEXT.md               # AI 快速接手上下文
└── requirements.txt            # Python 依赖
```

## AI 协作规则

- 不要默认 `user_data/` 是当前真实运行目录，当前主目录是 `ft_userdata/user_data/`。
- 不要默认 `strategies/` 与 `ft_userdata/user_data/strategies/` 已自动同步。
- 不要仅凭文档断言策略有效，优先核对最近的回测产物与配置。
- 如果要修改策略逻辑，先说明会影响 `Freqtrade`、自定义回测脚本、Docker 副本中的哪一层。
- 如果只做文档或 AI 说明优化，不要顺手改交易逻辑。

## 当前状态

- 仓库当前只保留一个多空主线策略: `MultiLsV2Strategy`。
- `MultiLS`、`LongShortSwitch`、`TrendFollowing` 等历史变体已退出主线，不再继续演进。
- `freqtrade_bot/realtime_bot.py` 目前更像信号演示原型，不应视作生产交易执行引擎。

## 建议的阅读顺序

1. `AI_CONTEXT.md`
2. `.opencode/knowledge-base/project.md`
3. `.opencode/knowledge-base/ai-collaboration.md`
4. `ft_userdata/docker-compose.yml`
5. `ft_userdata/user_data/config.json`
6. `strategies/README.md`
