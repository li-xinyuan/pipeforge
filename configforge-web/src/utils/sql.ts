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
