# 自动交易系统版本说明

## 当前版本口径

当前仓库的主环境以 Docker 为准。

- 当前确认的 Docker 运行版本: `freqtrade 2026.2`
- 当前判断兼容性时，优先以 Docker 环境结论为准
- 历史上通过本地 package 安装方式出现过兼容性问题，但这不是当前主环境，不再作为版本判断依据

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

本地 package 安装仅作为辅助研究环境，不作为当前主执行环境。
如果本地安装与 Docker 版本存在差异，以 Docker 为准。

### 1. Python 环境
| 组件 | 推荐版本 | 说明 |
|------|---------|------|
| Python | 3.11.8 | 适合本地研究脚本和辅助工具，不作为 Docker 主环境版本依据 |

### 2. Freqtrade 及核心依赖
| 组件 | 推荐版本 | 说明 |
|------|---------|------|
| Freqtrade | 2026.2 (Docker 当前主环境) | 当前仓库实际运行口径，以 Docker 容器内版本为准 |
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
