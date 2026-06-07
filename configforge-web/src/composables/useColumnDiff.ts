export function useColumnDiff() {
  function extractSelectColumns(sql: string): string[] {
    try {
      const upper = sql.toUpperCase().trim()
      const selectIdx = upper.indexOf('SELECT')
      const fromIdx = upper.indexOf('FROM', selectIdx + 6)
      if (selectIdx === -1 || fromIdx === -1) return []

      const columnsStr = sql.slice(selectIdx + 6, fromIdx).trim()
      if (columnsStr === '*') return ['*']

      const columns: string[] = []
      let depth = 0, current = ''
      for (const ch of columnsStr) {
        if (ch === '(') depth++
        else if (ch === ')') depth--
        if (ch === ',' && depth === 0) {
          columns.push(current.trim())
          current = ''
        } else {
          current += ch
        }
      }
      if (current.trim()) columns.push(current.trim())

      return columns.map(col => {
        const parts = col.trim().split(/\s+AS\s+/i)
        const lastPart = parts[parts.length - 1].trim()
        const dotIdx = lastPart.lastIndexOf('.')
        return dotIdx > -1 ? lastPart.slice(dotIdx + 1) : lastPart
      })
    } catch {
      return []
    }
  }

  function diffColumns(oldCols: string[], newCols: string[]) {
    const oldSet = new Set(oldCols)
    const newSet = new Set(newCols)
    return {
      added: newCols.filter(c => !oldSet.has(c)),
      removed: oldCols.filter(c => !newSet.has(c)),
      hasChanges: oldCols.length !== newCols.length || newCols.some(c => !oldSet.has(c)),
    }
  }

  return { extractSelectColumns, diffColumns }
}
