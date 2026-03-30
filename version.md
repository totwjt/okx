# 自动交易系统稳定版本组合（生产可用）

## 推荐安装方式：Docker

推荐使用 Docker 运行 Freqtrade，避免依赖冲突。

### Docker 安装步骤
```bash
# 1. 创建目录
mkdir -p ft_userdata && cd ft_userdata

# 2. 下载 docker-compose.yml
curl https://raw.githubusercontent.com/freqtrade/freqtrade/stable/docker-compose.yml -o docker-compose.yml

# 3. 拉取镜像
docker compose pull

# 4. 创建配置目录
docker compose run --rm freqtrade create-userdir --userdir user_data

# 5. 创建配置文件（交互式）
docker compose run --rm freqtrade new-config --config user_data/config.json

# 6. 复制策略文件
mkdir -p user_data/strategies
cp ../AI-OuYi/strategies/volume_ratio_strategy.py user_data/strategies/

# 7. 启动 Bot
docker compose up -d

# 8. 查看日志
docker compose logs -f
```

### Webserver 访问
- 地址: http://localhost:8080
- 用户名: freqtrader
- 密码: 1234

---

## 备用：Python 本地安装（不推荐）

以下版本组合存在依赖兼容性问题，Webserver 可能无法正常运行。

### 1. Python 环境
| 组件 | 推荐版本 | 说明 |
|------|---------|------|
| Python | 3.11.8 | 官方 LTS 支持，兼容 Freqtrade 2025.x 和 FastAPI |

### 2. Freqtrade 及核心依赖
| 组件 | 推荐版本 | 说明 |
|------|---------|------|
| Freqtrade | 2025.10 (Docker stable) | 稳定 LTS，支持 Webserver、CLI、回测 |
| ccxt | >=4.5.4 | 交易所接口库 |
| pandas | >=2.2.0 | 数据处理 |
| numpy | >=2.0 | numpy 需支持 Python 3.11 |

### 3. FastAPI Web 层（仅本地安装需要）
| 组件 | 推荐版本 | 说明 |
|------|---------|------|
| FastAPI | >=0.135.0 | Docker 镜像自带版本 |
| Uvicorn | >=0.42.0 | Docker 镜像自带版本 |

---

## 策略参数

### VolumeRatioStrategy（已优化）
| 参数 | 值 | 单位 | 说明 |
|------|-----|------|------|
| buy_volume_ratio_threshold | 0.33 | 倍数 | 买入：量能 < 均量的 33% |
| sell_volume_ratio_threshold | 2.37 | 倍数 | 卖出：量能 > 均量的 237% |
| volume_ma_window | 5 | 根K线 | 均量窗口 = 5 × 5m = 25分钟 |
| timeframe | 5m | 分钟 | K线周期 |
| stoploss | -0.03 | 比例 | 止损 -3% |

### 回测结果（394天）
| 指标 | 值 |
|------|-----|
| 总交易数 | 1801 |
| 胜率 | 28.7% |
| 总收益 | -84.11% |

> 注：该策略在当前市场环境下表现为负收益，建议更换策略或调整思路。
