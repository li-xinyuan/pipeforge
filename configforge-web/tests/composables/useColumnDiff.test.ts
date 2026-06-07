import { describe, it, expect } from 'vitest'
import { useColumnDiff } from '../../src/composables/useColumnDiff'

describe('useColumnDiff', () => {
  const { extractSelectColumns, diffColumns } = useColumnDiff()

  it('extracts columns from simple SELECT', () => {
    expect(extractSelectColumns('SELECT city, COUNT(id) AS cnt FROM t')).toEqual(['city', 'cnt'])
  })

  it('extracts columns from SELECT with JOIN', () => {
    const cols = extractSelectColumns('SELECT u.city, COUNT(o.id) AS order_count, SUM(o.amount) AS total FROM users u JOIN orders o')
    expect(cols).toEqual(['city', 'order_count', 'total'])
  })

  it('handles SELECT *', () => {
    expect(extractSelectColumns('SELECT * FROM t')).toEqual(['*'])
  })

  it('diffs columns: added', () => {
    const diff = diffColumns(['city'], ['city', 'order_count'])
    expect(diff.added).toEqual(['order_count'])
    expect(diff.removed).toEqual([])
    expect(diff.hasChanges).toBe(true)
  })

  it('diffs columns: removed', () => {
    const diff = diffColumns(['city', 'order_count', 'total'], ['city', 'order_count'])
    expect(diff.removed).toEqual(['total'])
  })

  it('no changes', () => {
    const diff = diffColumns(['city', 'cnt'], ['city', 'cnt'])
    expect(diff.hasChanges).toBe(false)
  })
})
