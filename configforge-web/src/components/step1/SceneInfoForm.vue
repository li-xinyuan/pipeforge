<template>
  <div class="bg-white border border-slate-200 rounded-lg p-6">
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label for="scene-name" class="block text-sm font-medium text-slate-900 mb-1">场景名称</label>
        <input id="scene-name" v-model="store.scene.name" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
      </div>
      <div>
        <label for="scene-version" class="block text-sm font-medium text-slate-900 mb-1">版本</label>
        <input id="scene-version" v-model="store.scene.version" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
      </div>
    </div>
    <div class="mb-4">
      <label for="scene-description" class="block text-sm font-medium text-slate-900 mb-1">场景描述</label>
      <input id="scene-description" v-model="store.scene.description" class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none transition-colors h-9" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { useWizardStore } from '../../stores/wizard'

const store = useWizardStore()
</script>
