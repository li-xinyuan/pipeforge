<template>
  <div class="cf-form-grid">
    <!-- URL -->
    <div class="col-span-2">
      <label class="cf-label"><span class="cf-required">*</span> URL</label>
      <NInput
        :value="config.url"
        placeholder="https://api.example.com/data"
        size="small"
        @update:value="updateConfig('url', $event)"
      />
    </div>

    <!-- Method -->
    <div>
      <label class="cf-label">请求方法</label>
      <NSelect
        :value="config.method"
        :options="methodOptions"
        size="small"
        @update:value="updateConfig('method', $event)"
      />
    </div>

    <!-- Data Path -->
    <div>
      <label class="cf-label">数据路径</label>
      <NInput
        :value="config.dataPath"
        placeholder="data.items"
        size="small"
        @update:value="updateConfig('dataPath', $event)"
      />
      <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">JSON 响应中数据列表的路径，如 data.items</p>
    </div>

    <!-- Headers -->
    <div class="col-span-2">
      <label class="cf-label">请求头</label>
      <div class="space-y-1.5">
        <div v-for="(value, key, idx) in config.headers" :key="idx" class="flex items-center gap-2">
          <NInput
            :value="String(key)"
            placeholder="Header 名称"
            size="small"
            class="flex-1"
            @update:value="updateKeyValue('headers', String(key), $event, 'key')"
          />
          <NInput
            :value="String(value)"
            placeholder="Header 值"
            size="small"
            class="flex-1"
            @update:value="updateKeyValue('headers', String(key), $event, 'value')"
          />
          <NButton text size="tiny" type="error" aria-label="删除请求头" @click="removeKeyValue('headers', String(key))">✕</NButton>
        </div>
        <NButton text size="tiny" type="primary" @click="addKeyValue('headers')">+ 添加请求头</NButton>
      </div>
    </div>

    <!-- Params -->
    <div class="col-span-2">
      <label class="cf-label">查询参数</label>
      <div class="space-y-1.5">
        <div v-for="(value, key, idx) in config.params" :key="idx" class="flex items-center gap-2">
          <NInput
            :value="String(key)"
            placeholder="参数名"
            size="small"
            class="flex-1"
            @update:value="updateKeyValue('params', String(key), $event, 'key')"
          />
          <NInput
            :value="String(value)"
            placeholder="参数值"
            size="small"
            class="flex-1"
            @update:value="updateKeyValue('params', String(key), $event, 'value')"
          />
          <NButton text size="tiny" type="error" aria-label="删除查询参数" @click="removeKeyValue('params', String(key))">✕</NButton>
        </div>
        <NButton text size="tiny" type="primary" @click="addKeyValue('params')">+ 添加参数</NButton>
      </div>
    </div>

    <!-- Pagination -->
    <div>
      <label class="cf-label">分页方式</label>
      <NSelect
        :value="config.pagination"
        :options="paginationOptions"
        size="small"
        @update:value="updateConfig('pagination', $event)"
      />
    </div>

    <!-- Page Size -->
    <div>
      <label class="cf-label">每页条数</label>
      <NInputNumber
        :value="config.pageSize"
        :min="1"
        :max="10000"
        size="small"
        class="w-full"
        @update:value="updateConfig('pageSize', $event ?? 20)"
      />
    </div>

    <!-- Max Pages -->
    <div>
      <label class="cf-label">最大页数</label>
      <NInputNumber
        :value="config.maxPages"
        :min="1"
        :max="1000"
        size="small"
        class="w-full"
        @update:value="updateConfig('maxPages', $event ?? 1)"
      />
    </div>

    <!-- Test connection button -->
    <div class="flex items-end gap-2">
      <NButton size="small" type="primary" :loading="testing" @click="testApi">测试连接</NButton>
      <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500 dark:text-red-400'" class="text-xs">
        {{ testResult.ok ? '连接成功' : testResult.error }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NInput, NSelect, NButton, NInputNumber } from 'naive-ui'
import type { InputSource, ApiInputConfig } from '../../types/wizard'
import { useApi } from '../../composables/useApi'

const props = defineProps<{ input: InputSource; index: number }>()
const emit = defineEmits<{ update: [input: InputSource] }>()

const config = computed(() => props.input.config as ApiInputConfig)

const { apiTest } = useApi()

const testing = ref(false)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)

const methodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
]

const paginationOptions = [
  { label: '无分页', value: 'none' },
  { label: '偏移量分页 (offset)', value: 'offset' },
  { label: '游标分页 (cursor)', value: 'cursor' },
]

function emitUpdate(newConfig: Partial<ApiInputConfig>) {
  emit('update', {
    ...props.input,
    config: { ...config.value, ...newConfig } as ApiInputConfig,
  })
}

function updateConfig<K extends keyof ApiInputConfig>(key: K, value: ApiInputConfig[K]) {
  emitUpdate({ [key]: value } as Partial<ApiInputConfig>)
}

function updateKeyValue(
  field: 'headers' | 'params',
  oldKey: string,
  newValue: string,
  type: 'key' | 'value',
) {
  const current = { ...config.value[field] }
  if (type === 'key') {
    const val = current[oldKey]
    delete current[oldKey]
    current[newValue] = val ?? ''
  } else {
    current[oldKey] = newValue
  }
  emitUpdate({ [field]: current } as Partial<ApiInputConfig>)
}

function addKeyValue(field: 'headers' | 'params') {
  const current = { ...config.value[field] }
  // Generate a unique placeholder key
  let idx = Object.keys(current).length + 1
  let key = `key_${idx}`
  while (current[key] !== undefined) {
    idx++
    key = `key_${idx}`
  }
  current[key] = ''
  emitUpdate({ [field]: current } as Partial<ApiInputConfig>)
}

function removeKeyValue(field: 'headers' | 'params', key: string) {
  const current = { ...config.value[field] }
  delete current[key]
  emitUpdate({ [field]: current } as Partial<ApiInputConfig>)
}

async function testApi() {
  testing.value = true
  testResult.value = null
  try {
    const cfg = config.value
    const result = await apiTest({
      url: cfg.url,
      method: cfg.method,
      headers: cfg.headers,
      params: cfg.params,
      data_path: cfg.dataPath,
      pagination: cfg.pagination,
      page_size: cfg.pageSize,
      max_pages: cfg.maxPages,
    })
    if (result) {
      testResult.value = { ok: true }
    } else {
      testResult.value = { ok: false, error: '请求失败' }
    }
  } catch (e) {
    testResult.value = { ok: false, error: e instanceof Error ? e.message : '网络错误' }
  } finally {
    testing.value = false
  }
}
</script>
