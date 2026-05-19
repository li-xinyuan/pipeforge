/** 从 SQL 语句推断输出表名 */
export function inferOutputTable(sql: string): string {
  // 1. CREATE TABLE xxx AS SELECT ... / CREATE TEMP TABLE xxx AS SELECT ...
  const createMatch = sql.match(/\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+AS\b/i)
  if (createMatch) return createMatch[1]

  // 2. INSERT INTO xxx SELECT ... (写入已有表)
  const insertMatch = sql.match(/\bINSERT\s+INTO\s+(\w+)\b/i)
  if (insertMatch) return insertMatch[1]

  // 3. CTE: WITH xxx AS ( ... ) SELECT ... — 取最后一个 CTE 名
  const cteMatch = sql.match(/\bWITH\s+(\w+)\s+AS\s*\(/i)
  if (cteMatch) return cteMatch[1]

  // 4. 简单 SELECT — 默认 result
  return 'result'
}

/** 从 SQL SELECT 子句中提取列名/别名 */
export function inferSelectColumns(sql: string): string[] {
  const trimmed = sql.trim()
  if (!trimmed) return []

  // SELECT * / SELECT table.* 无法推断具体列
  if (/\bSELECT\s+(?:\w+\.)?\*/i.test(trimmed)) return []

  // 提取 SELECT ... FROM 之间的内容
  const selectMatch = trimmed.match(/\bSELECT\s+(.+?)\s+FROM\b/is)
  if (!selectMatch) return []

  const columnsClause = selectMatch[1]
  const columns: string[] = []

  // 按逗号分割，但需要正确处理括号嵌套（子查询）
  const parts = splitSelectColumns(columnsClause)
  for (const part of parts) {
    const col = part.trim()
    if (!col) continue

    // 提取 AS 别名（不区分大小写，支持引号包裹，支持中文）
    const asMatch = col.match(/\bAS\s+(?:"([^"]+)"|'([^']+)'|`([^`]+)`|(\S+))\s*$/i)
    if (asMatch) {
      columns.push(asMatch[1] || asMatch[2] || asMatch[3] || asMatch[4])
    } else {
      // 没有 AS：取最后一个非空 token 作为列名
      const nameMatch = col.match(/(\S+)\s*$/)
      if (nameMatch) columns.push(nameMatch[1])
    }
  }

  return columns
}

/** 按逗号分割 SELECT 列，尊重括号嵌套 */
function splitSelectColumns(clause: string): string[] {
  const parts: string[] = []
  let depth = 0
  let start = 0
  for (let i = 0; i < clause.length; i++) {
    const ch = clause[i]
    if (ch === '(') depth++
    else if (ch === ')') depth--
    else if (ch === ',' && depth === 0) {
      parts.push(clause.slice(start, i))
      start = i + 1
    }
  }
  parts.push(clause.slice(start))
  return parts
}
