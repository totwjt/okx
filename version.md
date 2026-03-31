# 自动交易系统版本说明

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
cp ../AI-OuYi/strategies/auto_multi_ls_v2.py user_data/strategies/

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

## 当前主线策略

### MultiLsV2Strategy

当前仓库已收口到唯一主线策略：

- `MultiLsV2Strategy`

旧的 `VolumeRatio` / `EMARSI` 以及 `MultiLS` / `LongShortSwitch` / `TrendFollowing` 等历史变体，现已不再保留为主线策略。
