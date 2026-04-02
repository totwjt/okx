# Docker 环境说明

## 重要提示

**Freqtrade 通过 Docker 安装，运行目录: `/freqtrade/`**

## 容器信息

| 项目 | 值 |
|------|-----|
| 容器名称 | `freqtrade` |
| 运行目录 | `/freqtrade/` |
| 挂载源 | `execution/freqtrade/user_data` -> `/freqtrade/user_data` |
| 策略源码挂载 | `strategies` -> `/freqtrade/user_data/strategies` |
| 用户数据目录 | `/freqtrade/user_data/` |
| 策略目录 | `/freqtrade/user_data/strategies/` |
| 配置文件 | `/freqtrade/user_data/config.json` |

## 常用命令

### 进入容器

```bash
docker exec -it freqtrade /bin/bash
```

### 执行 freqtrade 命令

```bash
# 回测
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s MultiLsV2Strategy

# 模拟盘
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s MultiLsV2Strategy --dry-run

# 实盘（谨慎！）
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
```

### 查看日志

```bash
# 实时日志
docker logs -f freqtrade

# 最近 100 行
docker logs --tail 100 freqtrade
```

### 策略开发

```bash
# 直接在仓库根目录修改 strategies/
# 容器会通过 bind mount 直接读取这些文件
```

### 数据下载

```bash
# 下载 K线数据（1m）
docker exec freqtrade freqtrade download-data -c /freqtrade/user_data/config.json --pairs BTC/USDT --timeframes 1m 5m 15m
```

## Docker Compose

项目包含 `docker-compose.yml`，可通过以下命令管理：

```bash
# 启动
docker compose -f execution/freqtrade/docker-compose.yml up -d

# 停止
docker compose -f execution/freqtrade/docker-compose.yml down

# 重启
docker compose -f execution/freqtrade/docker-compose.yml restart
```

## 注意事项

1. **首次启动**需要初始化配置和数据
2. **API 密钥**在 `.env` 文件中，Docker 启动时自动加载
3. **数据持久化** - `execution/freqtrade/user_data/` 目录挂载到容器，容器删除后数据保留
4. **日志大小** - 定期清理: `docker system prune`
5. **策略单一事实来源** - 只维护仓库根目录 `strategies/`

---
*最后更新: 2026-04-02*
