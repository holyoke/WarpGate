export default {
  uiPreview: {
    title: '界面预览', description: '查看有数据时的表格、状态与交互，切换深浅色检查阅读体验。',
    demoOnly: '演示数据 · 仅供界面预览', records: '条样例',
    sections: { users: '用户', channels: '模型渠道', requests: '请求记录', orders: '订单' },
    summaries: { users: '团队与个人账号，多种状态', channels: '四类模型服务，延迟与健康度', requests: '模型、用量与异常请求', orders: '充值、套餐与支付状态' },
    names: { users: '用户 / 邮箱', channels: '渠道 / 线路', requests: '模型 / 用户', orders: '商品 / 用户' },
    metrics: { users: '账户余额 (USD)', channels: '响应延迟', requests: 'Token 数', orders: '订单金额 (CNY)' },
    status: { healthy: '正常 / 已完成', pending: '等待处理', failed: '异常 / 失败', disabled: '已停用 / 已关闭' },
    category: '类型', statusFilter: '状态', allStatuses: '全部状态', updated: '更新时间', action: '操作',
    search: '搜索名称、邮箱、模型或 ID', reset: '重置筛选', details: '查看详情',
    footer: '样例仅在当前页面展示。搜索、排序、筛选、分页与详情均可操作，所有金额均为模拟数值。'
  }
}
