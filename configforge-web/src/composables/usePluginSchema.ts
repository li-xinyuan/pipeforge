import { ref } from 'vue'
import { useApi, ApiError, handleApiError } from './useApi'

/**
 * usePluginSchema — 插件配置 schema 缓存与查询（限制①动态表单基础设施）。
 *
 * 调用 `GET /api/plugins` 获取所有插件的清单和 config_schema，模块级缓存
 * 供所有组件共享。SchemaForm 通过本 composable 获取 schema 动态渲染表单。
 */

export interface PluginManifestItem {
  name: string
  type: string // 'input' | 'processor' | 'output'
  label: string
  config_schema: Record<string, unknown>
}

// 模块级缓存（所有 composable 实例共享；插件 schema 在运行时不变）
const pluginCache = ref<PluginManifestItem[] | null>(null)
const loading = ref(false)

export function usePluginSchema() {
  const { requestOrThrow } = useApi()

  /** 加载所有插件清单（带缓存，重复调用只请求一次）。 */
  async function load(force = false): Promise<PluginManifestItem[]> {
    if (pluginCache.value && !force) return pluginCache.value
    loading.value = true
    try {
      const result = await requestOrThrow<PluginManifestItem[]>('GET', '/api/plugins')
      pluginCache.value = result || []
      return pluginCache.value
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    } finally {
      loading.value = false
    }
  }

  /** 同步获取 schema（需先 load）；未命中返回 undefined。 */
  function getSchema(plugin: string, type: string): Record<string, unknown> | undefined {
    const item = pluginCache.value?.find((p) => p.name === plugin && p.type === type)
    return item?.config_schema
  }

  /** 异步获取 schema（自动触发 load）。 */
  async function getSchemaAsync(
    plugin: string,
    type: string,
  ): Promise<Record<string, unknown> | undefined> {
    await load()
    return getSchema(plugin, type)
  }

  /** 清空缓存（仅供测试使用）。 */
  function clearCache(): void {
    pluginCache.value = null
  }

  return { loading, load, getSchema, getSchemaAsync, clearCache }
}
