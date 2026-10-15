export default {
  uiPreview: {
    title: 'Interface preview', description: 'Explore populated tables, statuses and interactions in light and dark themes.',
    demoOnly: 'Demo data · Interface preview only', records: 'examples',
    sections: { users: 'Users', channels: 'Model channels', requests: 'Requests', orders: 'Orders' },
    summaries: { users: 'Teams, individuals and account states', channels: 'Four providers, latency and health', requests: 'Models, usage and failed requests', orders: 'Top-ups, plans and payment states' },
    names: { users: 'User / email', channels: 'Channel / route', requests: 'Model / user', orders: 'Product / user' },
    metrics: { users: 'Balance (USD)', channels: 'Latency', requests: 'Tokens', orders: 'Amount (CNY)' },
    status: { healthy: 'Healthy / completed', pending: 'Pending', failed: 'Error / failed', disabled: 'Disabled / closed' },
    category: 'Type', statusFilter: 'Status', allStatuses: 'All statuses', updated: 'Updated', action: 'Actions',
    search: 'Search name, email, model or ID', reset: 'Reset filters', details: 'View details',
    footer: 'Fixtures appear only on this page. Search, sort, filter, pagination and details work; all amounts are simulated.'
  }
}
