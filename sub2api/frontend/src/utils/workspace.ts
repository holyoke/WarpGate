const personalPaths = ['/dashboard', '/keys', '/usage', '/monitor', '/subscriptions', '/purchase', '/orders', '/redeem', '/affiliate', '/batch-image', '/available-channels', '/payment']

export function isUserWorkspace(isAdmin: boolean, path: string): boolean {
  return !isAdmin || personalPaths.some(base => path === base || path.startsWith(base + '/'))
}

export function defaultDashboard(isAdmin: boolean): string {
  return isAdmin ? '/admin/dashboard' : '/dashboard'
}
