# WarpGate

基于 [Wei-Shaw/Sub2API](https://github.com/Wei-Shaw/sub2api) 开发。上游源码位于 `sub2api/`，保留其 LGPL-3.0 许可证。

## CI/CD 与服务器部署

`.github/workflows/deploy.yml` 在推送到 `master`、提交 Pull Request 或手动触发时，执行相关测试、TypeScript 检查和前端构建。推送和手动运行还会构建完整 Go 应用镜像，启动 PostgreSQL、Redis 和应用，验证健康检查、管理员登录及品牌设置后，发布至 `ghcr.io/holyoke/warpgate`。

镜像同时包含定制前端和后端，支持真实账号、用量计费和网关功能。实际模型调用需要部署后自行配置上游 API 渠道。GitHub Pages 无法承载这一完整平台；当前没有服务器，服务器部署任务保持关闭。

服务器准备好后，按 [部署说明](deploy/README.md) 配置 GitHub Secrets 和 `DEPLOY_ENABLED=true`，即可在推送后自动部署。镜像使用提交 SHA 固定版本，并额外发布 `latest` 标签。

## 本地启动

安装 Node.js、Git 和 Docker Desktop，启动 Docker Desktop 后，在本目录运行：

```powershell
.\start.ps1
```

首次启动会生成 `.env` 和随机管理员密码，并初始化 WarpGate 品牌设置。访问 http://localhost:8080 。登录信息见 `.local/admin-login.txt`，也可查看本机 `.env` 的 `ADMIN_EMAIL`、`ADMIN_PASSWORD`。这些文件已加入 Git 忽略，不会上传。

```powershell
docker compose ps
docker compose logs --tail 100 sub2api
docker compose stop
```

前端使用本项目构建产物，由 Nginx 提供页面并代理 API；后端使用官方 GHCR 镜像 `ghcr.io/wei-shaw/sub2api:0.2.16`，配合 PostgreSQL 16 和 Redis 7。本地入口仅监听 127.0.0.1:8080，后端、数据库及缓存不开放宿主端口。重启保留数据。

## 修改 UI

安装 Node.js 后运行：

```powershell
.\build-ui.ps1
.\start.ps1
```

脚本使用与上游锁文件一致的 pnpm 9，执行国际化检查、TypeScript 检查和生产构建。产物挂载给 Nginx，完成构建后刷新浏览器即可加载新页面。首次启动缺少产物时也会自动构建。

品牌名称为 WarpGate，Logo 是自绘 W 标识，主题为靛蓝色。页面移除上游推广链接、广告与自动更新徽章；许可证、上游版权和合规文档保留，来源说明见 `THIRD_PARTY_NOTICES.md`。站点名称、Logo 路径和副标题同时保存在后台设置中。

后端源码修改仍需另外构建后端镜像。上游源码通过 main 分支压缩包获取，版本文件为 0.2.16；压缩包不包含上游 Git 历史。

启动后可配置自己的上游 API 渠道、模型分组及价格。本次启动不包含任何第三方网站账号或上游 API 密钥，未开通真实支付。
