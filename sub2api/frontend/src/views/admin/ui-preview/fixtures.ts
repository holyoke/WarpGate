export type PreviewSection = 'users' | 'channels' | 'requests' | 'orders'
export interface PreviewRow {
  id: string
  name: string
  description: string
  category: string
  status: 'healthy' | 'pending' | 'failed' | 'disabled'
  metric: number
  updated: string
}

const users = ['林屿 · 产品团队', 'Aurora Labs', '陈澄 · 独立开发者', '北辰工作室', 'Mira Research', '星野数据']
const statuses: PreviewRow['status'][] = ['healthy', 'healthy', 'pending', 'healthy', 'disabled', 'failed']
export const sections: PreviewSection[] = ['users', 'channels', 'requests', 'orders']

// UI-only fixtures. No accounts, payments, credentials or gateway requests are created.
export function createPreviewRows(section: PreviewSection): PreviewRow[] {
  return Array.from({ length: 24 }, (_, index) => {
    const n = index + 1
    const common = { id: `DEMO-${section.toUpperCase()}-${String(n).padStart(3, '0')}`,
      status: statuses[index % statuses.length], updated: `2026-10-15 ${String(14 - Math.floor(index / 6)).padStart(2, '0')}:${String(56 - index).padStart(2, '0')}` }
    switch (section) {
      case 'users': return { ...common, name: users[index % users.length] + (index >= 6 ? ` ${Math.floor(index / 6) + 1}` : ''), description: `member-${String(n).padStart(3, '0')}@example.com`, category: ['团队版', '开发者', '企业版'][index % 3], metric: Number((1250 / n + index * 8.2).toFixed(2)) }
      case 'channels': return { ...common, name: ['OpenAI · 主线路', 'Claude · 团队专线', 'Gemini · 长上下文', 'DeepSeek · 推理池'][index % 4] + ` ${Math.floor(index / 4) + 1}`, description: `demo-region-${index % 3 + 1} / API Key`, category: ['OpenAI', 'Anthropic', 'Google', 'DeepSeek'][index % 4], metric: 120 + index * 37 }
      case 'requests': return { ...common, name: ['gpt-4.1', 'claude-sonnet-4', 'gemini-2.5-pro', 'deepseek-chat'][index % 4], description: users[index % users.length], category: ['Chat', 'Messages', 'Responses'][index % 3], metric: 425 + index * 213 }
      case 'orders': return { ...common, name: ['余额充值', '开发者月包', '团队月包'][index % 3], description: users[index % users.length], category: ['支付宝', '微信支付', '充值码'][index % 3], metric: [100, 299, 999, 50, 200, 500][index % 6] }
    }
  })
}

export function filterPreviewRows(rows: PreviewRow[], search: string, status: string): PreviewRow[] {
  const query = search.trim().toLocaleLowerCase()
  return rows.filter(row => (status === 'all' || row.status === status) &&
    (!query || `${row.id} ${row.name} ${row.description} ${row.category}`.toLocaleLowerCase().includes(query)))
}
