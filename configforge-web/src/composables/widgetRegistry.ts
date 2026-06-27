import type { Component } from 'vue'

/**
 * widgetRegistry — 命名 widget 注册中心（限制①动态表单基础设施）。
 *
 * SchemaForm 通过 schema 中的 `x-ui-widget` 扩展字段引用命名 widget，
 * 避免在 SchemaForm 内部硬编码插件专属组件（如 CodeEditor、ConnectionManager）。
 *
 * 异步选项（`x-ui-options-from`）：用于 excel sheet 字段（选项来自 fetchPreview）、
 * database tables 字段（选项来自 fetchTables(connectionId)）等需要异步加载选项的场景。
 */

export interface SelectOption {
  label: string
  value: string | number
}

export type AsyncOptionsLoader = () => Promise<SelectOption[]>

const widgetMap = new Map<string, Component>()
const asyncLoaderMap = new Map<string, AsyncOptionsLoader>()

/** 注册命名 widget（如 'code-editor'、'connection-manager'）。 */
export function registerWidget(name: string, component: Component): void {
  widgetMap.set(name, component)
}

/** 获取命名 widget；未注册返回 undefined（SchemaForm 回退到通用 widget）。 */
export function getWidget(name: string): Component | undefined {
  return widgetMap.get(name)
}

/** 注册异步选项加载器（如 'preview-sheets'、'db-tables'）。 */
export function registerAsyncOptionsLoader(name: string, loader: AsyncOptionsLoader): void {
  asyncLoaderMap.set(name, loader)
}

/** 获取异步选项加载器；未注册返回 undefined。 */
export function getAsyncOptionsLoader(name: string): AsyncOptionsLoader | undefined {
  return asyncLoaderMap.get(name)
}

/** 清空注册中心（仅供测试使用）。 */
export function clearWidgetRegistry(): void {
  widgetMap.clear()
  asyncLoaderMap.clear()
}
