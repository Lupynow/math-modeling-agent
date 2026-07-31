# 部署指南

## 本地与演示环境

第一版推荐使用 `docker compose up --build`。默认 `APP_MODE=fake`，不需要密钥。确认接口、数据库和向量库均能启动后，再切换到 production。

## Production 配置

生产环境至少需要：

- 注入 Chat 与 Embedding API 的地址、密钥和模型名。
- 为 MySQL 使用独立强密码，不暴露 3306 公网端口。
- 不暴露 Qdrant 6333 公网端口。
- 为 FastAPI 增加 HTTPS、认证、速率限制和请求体限制。
- 将 MySQL、Qdrant 数据目录挂载到持久化磁盘。
- 把 `.env` 替换为部署平台的 Secrets。

## 部署步骤

1. 在云主机安装 Docker 与 Compose。
2. 克隆仓库并建立仅服务器可读的环境变量。
3. 把 `APP_MODE` 设为 `production`。
4. 执行 `docker compose up -d --build`。
5. 检查 `/health` 和 `/ready`。
6. 首次启动后运行 `python -m modeling_agent.cli reindex` 完成知识索引。
7. 通过反向代理只公开 8000 对应的 HTTPS 域名。

## 上线前检查

- `/ready` 中三个依赖均为 true。
- 上传无效文件得到 422，未知运行 ID 得到 404。
- 日志不包含 API Key、完整赛题或数据库密码。
- 已设置备份、磁盘告警和容器重启策略。
- 已根据使用规模评估模型费用和最大并发。

本仓库不绑定具体云厂商；第一版交付目标是本地可复现和容器可迁移，而不是提供长期公开服务。
