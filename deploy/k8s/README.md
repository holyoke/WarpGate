# WarpGate Kubernetes 部署

通用安装入口为根目录 `install.ps1 k8s` / `install.sh k8s`。使用 Python 3.9+ 和 kubectl，连接已有集群；不需要 GPU，也不在本机启动 Docker 服务。

```powershell
.\install.ps1 k8s --kubeconfig 'C:\path\kubeconfig.yaml'
```

Linux / macOS 使用 `sh install.sh k8s --kubeconfig ~/.kube/config`。安装器等待 PostgreSQL、Redis、WarpGate 三个 Deployment 就绪后才报告成功。初始化凭据在 `.local/install-warpgate-admin.txt`；已有 Secret 不覆盖，网页修改的密码不重置。

## 存储和访问

默认创建 `warpgate` 命名空间、三个单副本工作负载，以及数据库 5Gi、缓存 1Gi、应用 1Gi 三个 PVC。使用集群默认 StorageClass，可通过 `--storage-class` 指定；不绑定任何测试集群节点。部署前确保存在可用存储类，节点能拉取应用、PostgreSQL 16 和 Redis 7 镜像。

使用 `--namespace` 隔离其他环境，使用 `--node-port` 避免集群端口冲突。已有 PVC 原样保留，指定新存储类不会迁移已有数据。默认 NodePort 为 `30488`，访问 `http://<节点IP>:30488/home`；无法直连时使用相同 kubeconfig/context 转发：

```sh
kubectl --kubeconfig /path/to/config -n warpgate port-forward service/warpgate 18080:8080
```

打开 <http://localhost:18080>。节点端口是否可达由网络和防火墙决定。此方案适合测试和单实例运行，数据库不提供高可用；正式运营需按业务要求另行规划备份、HTTPS 和可用性。

离线预览：

```sh
python3 install/install.py k8s --namespace warpgate-test --dry-run > warpgate-preview.json
```

渲染不生成 Secret，不连接集群。通用模板位于 `install/kubernetes.json`，与现有测试集群的 `deploy/k8s/*.yaml` 运维配置分开。

## 既有测试集群配置

本目录原有 `deploy.ps1` / `kustomization.yaml` 及 YAML 保留给已配置的测试环境，包含专用存储、节点和发布控制器设置，不作为新集群安装入口。不要用它们覆盖通用安装。现有环境继续沿用下列发布链路；新安装不会自动跟随本仓库 master。

## 持续发布

集群运行 `release-agent` 发布控制器，每 120 秒查询成功的 `cluster-release.yml` 工作流。该工作流通过 `workflow_run` 在 **WarpGate CI/CD** 成功结束后触发，只接受本仓库 `master` 分支的 `push` 或手动构建，并验证镜像已存在。控制器额外核对上游 CI 运行的仓库、工作流路径及提交，解析 GHCR 镜像摘要，更新应用并等待健康检查；失败时尝试恢复上一应用镜像，并记录失败运行，避免反复部署。

流程：推送 master → **WarpGate CI/CD** 测试/构建/启动验证/发布镜像 → `workflow_run` 触发 **WarpGate Cluster Release** → 集群主动拉取成功的发布请求 → 更新 WarpGate。构建时间之外，通常最多再等 2 分钟开始更新。Cluster Release 的绿色状态表示发布请求及镜像校验成功，应用实际就绪状态以集群控制器日志和 Deployment 注解为准。

控制器仅通过 HTTPS 向外连接 GitHub 和 GHCR，使用公开仓库的只读接口，不需要 GitHub Token。集群管理员 kubeconfig 留在本机。专用 ServiceAccount 只能读取和修改当前命名空间的 `warpgate` Deployment，不能读取 Secrets、修改数据库或操作其他命名空间。

查看实际运行版本和发布日志：

```powershell
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate logs deployment/release-agent --tail=50
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate get deployment warpgate -o 'jsonpath={.metadata.annotations.warpgate\.io/revision}'
```

暂停/恢复自动更新：

```powershell
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate scale deployment/release-agent --replicas=0
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate scale deployment/release-agent --replicas=1
```

控制器自身代码或 RBAC 配置变更后，需要在有集群权限的本机重新执行部署脚本。应用代码推送后无需手动操作集群。应用镜像回退不回滚数据库迁移。

此配置为单副本测试环境，`local-path` 数据跟随所在节点，不提供数据库高可用。

## 用户注册与密码找回

测试站已开放邮箱和密码注册，首页及登录页提供注册入口。后台可通过“开放注册”开关关闭入口和注册 API；现有数据库设置随应用发布保留，新建环境仍需管理员自行开启注册。

登录页提供“忘记密码”入口。尚未启用邮件找回时，页面提示联系管理员，不提交无效请求。启用步骤：

1. 在管理员设置中开启“邮件验证”，在邮件设置填写 SMTP 主机、端口、账号、授权码、发件地址及加密选项，发送测试邮件并保存。
2. 开启“密码重置”，填写“前端地址”（当前测试站为 `http://172.18.0.36:30488`）并保存。地址不能为空，应使用用户实际可访问的域名或 IP。此功能沿用后端的邮件验证依赖，开启邮件验证后新注册也需验证邮箱。
3. 退出登录，通过“忘记密码”提交账号邮箱，使用收到的链接设置新密码。

SMTP 授权码通过管理员页面保存，不写入仓库。当前未配置邮件服务器，因此尚未验证真实邮件投递。

## 充值与运营设置

测试站已开启支付功能和余额充值，用户侧提供“充值/订阅”“我的订单”、仪表盘余额卡充值按钮。充值页面提供金额选择与充值码入口；未配置可用支付渠道时，在线下单按钮禁用。

管理员在支付配置中设置充值限额、费率、余额兑换比例及支付渠道，在兑换码管理中生成余额充值码。已有支付宝、微信、易支付、Stripe、Airwallex 等渠道实现，真实收款需要填写自己的商户配置，并让支付平台能访问回调地址。当前站点是内网地址，尚未接通真实收款。

管理后台不再要求“部署与运营合规确认”，保留管理员身份验证、操作审计及支付回调验签。源代码许可证与版权说明继续保留。

日常调试仅发布远端集群。本地 WarpGate Compose 服务已停止，需要时才手动启动；不要因发布应用而启动本地数据库或同步本地运行环境。
