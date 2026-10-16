# WarpGate

**统一模型 API 接入 · 渠道管理 · 用量计费 · 用户运营**

WarpGate 将模型渠道、API 密钥、调用记录与计费管理集中到一个平台。完整镜像包含管理后台、用户中心和网关服务，配套 PostgreSQL 与 Redis，支持本机和 Kubernetes 两种安装方式。

## 平台能力

- **统一接入**：管理上游账号与模型分组，向用户提供统一 API 入口。
- **运营管理**：用户、渠道、定价、调用记录与运行状态集中管理。
- **用户自助**：API 密钥、用量、余额充值、订阅、订单与兑换码。
- **账号体系**：邮箱注册、登录、密码找回，后台配置邮件与支付服务。
- **清晰界面**：管理与用户工作区分离，支持深色和浅色主题。

## 一键安装

下载或克隆仓库后，在仓库根目录执行。需要 Python 3.9+，无需安装 Python 包、Node.js 或 Go。当前预构建应用镜像适用 Linux amd64：本机需运行 Linux 容器，集群需有对应架构节点。

| 安装位置 | 额外准备 | 安装内容 |
| --- | --- | --- |
| 自己的机器 / 单台服务器 | 运行中的 Docker、Compose v2（支持 `--wait`） | WarpGate + PostgreSQL + Redis，Docker 卷持久化 |
| Kubernetes 集群 | kubectl、可用 kubeconfig、动态存储类 | 独立命名空间、三个工作负载、三个 PVC、NodePort |

### 本机

Windows PowerShell：

```powershell
.\install.ps1 local
```

Linux / macOS：

```sh
sh install.sh local
```

访问 <http://localhost:8080>。初始账号和随机密码保存在 `.local/install/local/.env` 的 `ADMIN_EMAIL`、`ADMIN_PASSWORD` 中。安装器显示文件位置，不在终端打印密码。

### 集群

Windows PowerShell：

```powershell
.\install.ps1 k8s --kubeconfig 'C:\path\kubeconfig.yaml'
```

Linux / macOS：

```sh
sh install.sh k8s --kubeconfig ~/.kube/config
```

等待就绪后访问 `http://<可访问的节点IP>:30488`。首次创建账号时，初始登录信息保存到 `.local/install-warpgate-admin.txt`。集群需能拉取应用和基础镜像，并提供默认 StorageClass；也可通过 `--storage-class` 指定。

两种模式都默认安装 `install/release.txt` 固定摘要对应的定稿版本，重复执行保留已有凭据和数据。升级用 `--image` 指定版本；添加 `--dry-run` 可离线检查计划或生成集群清单，不会启动服务或访问集群。

## 首次使用

1. 管理员登录并修改密码。
2. 配置自己的模型渠道、分组及价格，创建测试 API 密钥验证调用。
3. 按业务需要开启注册、充值与订阅；配置 SMTP 后启用密码找回，配置支付商户与可达回调地址后接入真实收款。

安装不自动填入上游密钥、邮件或支付信息；运营开关以后台实际配置为准。

## 文档与开发

- [部署与维护](deploy/README.md)：参数、升级、停止、备份及故障排查。
- [Kubernetes 与持续发布](deploy/k8s/README.md)：存储、访问和现有 GitHub 发布链路。
- [用户使用文档](docs/USER_GUIDE.md)：API 接入与用户中心操作。

源码位于 `sub2api/`，完整镜像通过 `sub2api/Dockerfile` 构建。现有发布链路保持不变：推送 `master` → **WarpGate CI/CD** → **WarpGate Cluster Release** → 已配置的集群发布控制器更新应用。新安装不默认加入持续发布。

根目录 `start.ps1`、`compose.yaml` 属于早期分离式开发环境，新安装统一使用 `install.ps1` / `install.sh`，避免混用数据卷和配置。

## 开源说明

基于 [Wei-Shaw/Sub2API](https://github.com/Wei-Shaw/sub2api) 二次开发，保留上游 LGPL-3.0 许可证及版权声明。参见 [第三方说明](THIRD_PARTY_NOTICES.md) 和 [上游许可证](sub2api/LICENSE)。
