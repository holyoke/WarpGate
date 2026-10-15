import { describe, expect, it } from 'vitest'
import { defaultDashboard, isUserWorkspace } from '../workspace'

describe('administrator and consumer workspaces', () => {
  it.each(['/admin/dashboard', '/admin/orders', '/admin/testing/keys', '/profile', '/custom/1'])('keeps %s in the administrator workspace', path => {
    expect(isUserWorkspace(true, path)).toBe(false)
  })
  it.each(['/dashboard', '/keys', '/usage', '/purchase', '/orders', '/redeem', '/payment/stripe'])('uses the personal workspace for %s', path => {
    expect(isUserWorkspace(true, path)).toBe(true)
  })
  it('matches route boundaries and preserves the ordinary user experience', () => {
    expect(isUserWorkspace(true, '/orders-management')).toBe(false)
    expect(isUserWorkspace(false, '/profile')).toBe(true)
    expect(defaultDashboard(true)).toBe('/admin/dashboard')
    expect(defaultDashboard(false)).toBe('/dashboard')
  })
})
