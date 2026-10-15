import { describe, expect, it } from 'vitest'
import { createPreviewRows, filterPreviewRows, sections } from './fixtures'

describe('UI preview fixtures', () => {
  it.each(sections)('provides stable unique rows and all four states for %s', section => {
    const rows = createPreviewRows(section)
    expect(rows).toHaveLength(24)
    expect(new Set(rows.map(row => row.id)).size).toBe(24)
    expect(new Set(rows.map(row => row.status)).size).toBe(4)
    expect(rows.every(row => Number.isFinite(row.metric))).toBe(true)
    expect(createPreviewRows(section)).toEqual(rows)
  })
  it('combines case-insensitive search and status filters without changing original rows', () => {
    const rows = createPreviewRows('users')
    expect(filterPreviewRows(rows, 'MEMBER-001', 'healthy')).toHaveLength(1)
    expect(filterPreviewRows(rows, 'member-001', 'failed')).toHaveLength(0)
    expect(filterPreviewRows(rows, 'does-not-exist', 'all')).toHaveLength(0)
    expect(filterPreviewRows(rows, '  ', 'all')).toHaveLength(24)
    expect(rows).toHaveLength(24)
  })
})
