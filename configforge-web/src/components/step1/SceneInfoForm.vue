<template>
  <NCard>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label class="block text-sm font-medium mb-1" for="scene-name"><span class="text-red-500">*</span> 场景名称</label>
        <NInput id="scene-name" v-model:value="store.scene.name" placeholder="输入场景名称" />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1" for="scene-version">版本</label>
        <NInput id="scene-version" v-model:value="store.scene.version" placeholder="1.0" />
      </div>
    </div>
    <div>
      <label class="block text-sm font-medium mb-1" for="scene-description">场景描述</label>
      <NInput id="scene-description" v-model:value="store.scene.description" placeholder="可选，描述此流水线的用途" />
    </div>
  </NCard>
</template>
<script setup lang="ts">
import { NCard, NInput } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'

const store = useWizardStore()
</script>
