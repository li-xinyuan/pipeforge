/**
 * Convert a snake_case key to camelCase.
 * e.g. "connection_id" -> "connectionId", "has_header" -> "hasHeader"
 */
export function snakeToCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}

/**
 * Recursively convert all snake_case keys in an object to camelCase.
 * Preserves non-object values (strings, numbers, arrays, etc.).
 */
export function snakeToCamel<T = Record<string, any>>(obj: T): T {
  if (obj === null || obj === undefined) return obj
  if (Array.isArray(obj)) return obj.map(item => snakeToCamel(item)) as T
  if (typeof obj !== 'object') return obj

  const result: Record<string, any> = {}
  for (const [key, value] of Object.entries(obj as Record<string, any>)) {
    const camelKey = snakeToCamelKey(key)
    result[camelKey] = snakeToCamel(value)
  }
  return result as T
}
