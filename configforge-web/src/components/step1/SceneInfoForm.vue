<template>
  <div class="space-y-4">
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">场景名称</label>
      <input
        v-model="store.scene.name"
        type="text"
        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="例如：订单数据管道"
      />
    </div>
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">描述</label>
      <textarea
        v-model="store.scene.description"
        rows="3"
        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="描述这个管道的用途..."
      ></textarea>
    </div>
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">版本</label>
      <input
        v-model="store.scene.version"
        type="text"
        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="1.0"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { useWizardStore } from '../../stores/wizard'
const store = useWizardStore()
</script>
