# WarpGate 安装与维护

统一入口为根目录的 `install.ps1`（Windows）和 `install.sh`（Linux / macOS），逻辑位于 `install/install.py`。也可直接执行 `python install/install.py local` 或 `python3 install/install.py k8s`。

需要 Python 3.9+；安装器不编译源码，不安装 Docker / kubectl，也不更改 GitHub 工作流。执行前确认当前 Docker context 或 Kubernetes context 是目标环境。

## 本机 / 单台服务器

准备运行中的 Docker 和支持 `up --wait` 的 Compose v2：

```powershell
.\install.ps1 local
```

Linux / macOS 使用 `sh install.sh local`。默认仅监听 `127.0.0.1:8080`，Compose 项目名为 `warpgate`。配置目录 `.local/install/local` 保存 `.env` 和 `compose.yaml`，业务数据保存在 Docker 命名卷。

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `--port` | `8080` | 首次安装访问端口 |
| `--bind` | `127.0.0.1` | 首次安装监听地址；经反向代理开放时可保持默认值 |
| `--data-dir` | `.local/install/local` | 配置目录，升级须保持相同路径 |
| `--admin-email` | `admin@warpgate.local` | 首次管理员邮箱 |
| `--image` | `install/release.txt` | 安装或升级目标镜像，推荐固定摘要 |
| `--timeout` | `600` | 就绪等待秒数 |
| `--dry-run` | 关闭 | 仅输出计划，不写文件、不启动服务 |

已有 `.env` 时保留凭据、监听地址和端口；修改监听配置请编辑该文件后重跑。网页改密后，初始密码文件不会同步或重置实际密码。本入口只管理一个本机 `warpgate` Compose 实例，`--data-dir` 不是多实例开关。

### 日常操作

默认目录下执行：

```sh
docker compose -p warpgate --env-file .local/install/local/.env -f .local/install/local/compose.yaml ps
docker compose -p warpgate --env-file .local/install/local/.env -f .local/install/local/compose.yaml logs --tail 100 app
docker compose -p warpgate --env-file .local/install/local/.env -f .local/install/local/compose.yaml stop
```

再次执行安装命令可启动服务。`stop` / `down` 不删除数据卷；保留数据时不要运行 `down -v`。旧根目录 `.env` 与 `warp-sub2api` 环境不会自动迁移，切换安装方式前另行备份和迁移。

## Kubernetes

```powershell
.\install.ps1 k8s --kubeconfig 'C:\path\kubeconfig.yaml'
```

默认命名空间 `warpgate`、NodePort `30488`。额外参数为 `--context`、`--namespace`、`--storage-class`、`--node-port`，共有参数为 `--image`、`--admin-email`、`--timeout`、`--dry-run`。未指定 kubeconfig/context 时使用 kubectl 当前配置。

```sh
sh install.sh k8s --kubeconfig ~/.kube/config --namespace warpgate-test --node-port 30489 --storage-class local-path
sh install.sh k8s --namespace warpgate-test --dry-run > warpgate-preview.json
```

离线渲染不包含 Secret，首次安装时自动生成。已有 Secret 必须包含完整凭据，否则停止；鉴权或网络错误也会停止，不当作“Secret 不存在”。已有 PVC 不修改存储类或容量。详见 [集群说明](k8s/README.md)。

## 升级与恢复

两种模式都用 `--image` 指定已验证镜像：

```powershell
.\install.ps1 local --image ghcr.io/holyoke/warpgate:<提交SHA>
.\install.ps1 k8s --kubeconfig 'C:\path\kubeconfig.yaml' --image ghcr.io/holyoke/warpgate:<提交SHA>
```

替换占位值，也可使用 `ghcr.io/holyoke/warpgate@sha256:...`。省略 `--image` 会安装本仓库 `install/release.txt` 指定版本，并非自动选最新版本；已升级环境重跑时应继续传入目标镜像。

升级前备份 PostgreSQL、应用数据卷及私密配置。数据库导出可使用 `docker compose ... exec -T postgres pg_dump -U warpgate -d warpgate -Fc`；集群使用 `kubectl ... exec deployment/postgres -- pg_dump -U warpgate -d warpgate -Fc`。二进制输出须使用支持二进制重定向的终端，或先在容器内导出文件后复制。

失败会返回非零退出码并保留数据，不自动回滚应用或数据库。回退应用可指定上一镜像重跑，数据库迁移是否可回退需单独评估。已有发布控制器的环境继续使用其发布链路，避免与手动安装同时更新镜像。

## 故障定位

- **镜像拉取失败**：检查到 GHCR 和基础镜像仓库的网络，用 Compose 日志或 `kubectl describe pod` 定位。
- **PVC Pending**：检查默认 StorageClass，或首次安装指定 `--storage-class`；该参数不能迁移已有卷。
- **端口冲突**：首次本机安装用 `--port`，集群用 `--node-port`；检查防火墙及节点可达性。
- **等待超时**：查看数据库、Redis 和应用日志，修复后可重跑，必要时增加 `--timeout`。
- **账号文件存在但 Secret 未创建**：可能在上次创建时中断。核对集群后将提示的本机初始账号文件移走再重试，不要删除仍在使用的 Secret。

私密配置已被 Git 忽略；Linux / macOS 新建凭据文件权限为 `0600`，Windows 请通过 ACL 限制读取。自定义配置目录位于仓库其他路径时，须自行避免提交凭据。

安装模块的离线检查可运行 `python -m unittest discover -s install -p 'test_*.py'`，覆盖首次安装、重复安装、凭据保留和错误中止，不会启动服务或连接集群。

## 现有发布入口

现有 **WarpGate CI/CD → WarpGate Cluster Release → 集群发布控制器** 保持不变，见 [持续发布](k8s/README.md#持续发布)。新安装不默认加入持续发布。

`deploy/deploy-server.sh` 保留为原有可选 SSH 发布入口，由 `DEPLOY_ENABLED=true` 启用，使用独立服务器配置。`sub2api/deploy/install.sh` 为保留的上游二进制安装脚本，不作为 WarpGate 安装入口。
