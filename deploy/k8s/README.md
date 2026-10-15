# Kubernetes 测试部署

部署独立命名空间 `warpgate`，不使用 GPU。包括 WarpGate、PostgreSQL 16、Redis 7 和三个 `local-path` 持久化卷。应用使用已通过 CI 完整验证的镜像摘要；NodePort 为 `30488`。

当前测试集群中，PostgreSQL 固定在 `l20c-07-wanghuaizhen`，利用该节点已有的 PostgreSQL 镜像缓存。迁移至其他集群前，需要调整 `database.yaml` 的 `nodeSelector`。

本机 PowerShell 7：

```powershell
.\deploy\k8s\deploy.ps1 -Kubeconfig 'C:\path\kubeconfig.yaml'
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate get pods,pvc,svc
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate rollout status deployment/warpgate
```

首次部署会创建随机 Secret，登录信息只保存在本机 `.local/cluster-admin.txt`。重复执行保留已有 Secret 和数据，不覆盖密码。kubeconfig 不复制到项目或仓库。

浏览器打开 `http://<可访问的节点IP>:30488/home`。若无法访问节点端口，可临时转发：

```powershell
kubectl --kubeconfig 'C:\path\kubeconfig.yaml' -n warpgate port-forward service/warpgate 18080:8080
```

再打开 http://localhost:18080/home 。首次登录后的管理员确认需由运营者本人完成。模型请求需要在后台配置自己的上游渠道。

## 持续发布

集群运行 `release-agent` 发布控制器，每 120 秒查询 GitHub `master` 分支成功的 `deploy.yml` 工作流。只有本仓库 `push` 或手动触发的成功运行才会发布。控制器解析对应提交的 GHCR 镜像摘要，更新应用并等待健康检查；失败时尝试恢复上一应用镜像，并记录失败运行，避免反复部署。

流程：推送 master → GitHub Actions 测试/构建/启动验证/发布镜像 → 集群主动拉取成功运行 → 更新 WarpGate。构建时间之外，通常最多再等 2 分钟开始更新。

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
