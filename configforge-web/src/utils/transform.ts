/**
 * Convert a snake_case key to camelCase.
 * e.g. "connection_id" -> "connectionId", "has_header" -> "hasHeader"
 */
export function snakeToCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}

/**
 * Convert a camelCase key to snake_case.
 * e.g. "onFailure" -> "on_failure", "maxNullRate" -> "max_null_rate"
 */
export function camelToSnakeKey(key: string): string {
  return key.replace(/[A-Z]/g, (c) => '_' + c.toLowerCase())
}

/**
 * Recursively convert all snake_case keys in an object to camelCase.
 * Preserves non-object values (strings, numbers, arrays, etc.).
 */
export function snakeToCamel<T = Record<string, unknown>>(obj: T): T {
  if (obj === null || obj === undefined) return obj
  if (Array.isArray(obj)) return obj.map(item => snakeToCamel(item)) as T
  if (typeof obj !== 'object') return obj

  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    const camelKey = snakeToCamelKey(key)
    result[camelKey] = snakeToCamel(value)
  }
  return result as T
}
