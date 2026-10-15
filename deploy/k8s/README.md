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

该集群入口位于内网，现有 GitHub 托管 Runner 无法直接访问。当前是手动发布，不会把集群管理员 kubeconfig 放入 GitHub；后续自动部署需要内网 Runner 或明确配置网络连接和专用命名空间权限。

此配置为单副本测试环境，`local-path` 数据跟随所在节点，不提供数据库高可用。
