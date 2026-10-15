# WarpGate 自动部署

工作流：`.github/workflows/deploy.yml`。源码仓库为 https://github.com/holyoke/WarpGate 。

## 当前行为

- PR：测试、类型检查、构建前端，并上传构建产物。
- 推送 master 或手动运行：上述检查 → 构建包含定制 UI 的完整镜像 → 启动数据库/缓存/应用进行真实登录验证 → 推送提交 SHA 镜像和 latest 标签。
- 只有仓库变量 `DEPLOY_ENABLED` 为 `true` 才会连接服务器。当前尚未配置服务器。

## 准备服务器

需要 Linux amd64、Docker Engine、Docker Compose v2、Python 3、OpenSSL。SSH 用户需能执行 Docker，并可写入部署目录（默认 `/opt/warpgate`）。现有部署的数据库、缓存和配置保存在独立卷及服务器 `.env` 中，不随代码推送覆盖。

在 GitHub 仓库 Settings → Secrets and variables → Actions 配置：

| 类型 | 名称 | 内容 |
| --- | --- | --- |
| Secret | `DEPLOY_HOST` | 服务器 IP 或主机名 |
| Secret | `DEPLOY_USER` | SSH 用户 |
| Secret | `DEPLOY_SSH_KEY` | 专用部署 SSH 私钥，在服务器 authorized_keys 安装对应公钥 |
| Secret | `DEPLOY_KNOWN_HOSTS` | 经核验的服务器 SSH 公钥记录；非 22 端口使用 `[host]:port` 格式 |
| Variable | `DEPLOY_PORT` | 默认 `22` |
| Variable | `DEPLOY_PATH` | 默认 `/opt/warpgate`；绝对路径，仅支持字母、数字、斜杠、下划线和短横线 |
| Variable | `DEPLOY_ENABLED` | 服务器准备完毕后设为 `true` |

无需另配 GHCR 长期访问令牌：工作流使用短期 `GITHUB_TOKEN` 拉取镜像，服务器上的临时登录配置在拉取结束后删除。

## 首次部署和访问

服务器首次运行会生成随机数据库/缓存密码、JWT/TOTP 密钥和管理员账号，并存入部署目录 `.env`，权限由 `umask 077` 限制。管理员邮箱默认为 `admin@warp.local`，密码在该文件的 `ADMIN_PASSWORD` 中。

应用默认只监听服务器 `127.0.0.1:8080`。可在域名的 HTTPS 反向代理中转发至此地址；暂时没有域名时，也可使用 SSH 端口转发测试：

```sh
ssh -L 8080:127.0.0.1:8080 user@server
```

本地打开 http://localhost:8080 。配置上游模型渠道后即可真实调用，支付需要另行配置商户信息。

## 运行维护

在服务器部署目录：

```sh
export APP_IMAGE="$(cat deployed-image.txt)"
docker compose -p warpgate --env-file .env -f compose.server.yaml ps
docker compose -p warpgate --env-file .env -f compose.server.yaml logs --tail 100 app
```

脚本验证新版本启动和登录后才记录镜像版本。启动失败时会尝试恢复上一应用镜像；这不回滚数据库迁移。升级前应按实际数据重要性备份数据库。
