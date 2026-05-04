<template>
  <div class="flex items-center justify-center gap-0 mb-8">
    <div v-for="i in 4" :key="i" class="flex items-center gap-0">
      <div class="flex items-center gap-2 px-3 py-1 rounded-full text-sm cursor-pointer select-none"
           :class="i < currentStep ? 'text-slate-900 cursor-pointer hover:text-blue-600' : i === currentStep ? 'text-blue-600 font-semibold' : 'text-slate-400 cursor-default'"
           @click="i <= currentStep ? $emit('goto', i) : null">
        <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2"
              :class="i < currentStep ? 'bg-blue-600 border-blue-600 text-white' : i === currentStep ? 'border-blue-600 text-blue-600 shadow-[0_0_0_3px_#EFF6FF]' : 'border-slate-200 text-slate-400 bg-white'">{{ i }}</span>
        {{ labels[i - 1] }}
      </div>
      <div v-if="i < 4" class="w-8 h-0.5 mx-1" :class="i < currentStep ? 'bg-blue-600' : 'bg-slate-200'"></div>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ currentStep: number }>()
defineEmits<{ goto: [step: number] }>()
const labels = ['场景信息', '数据源配置', '输出定义', '预览与导出']
</script>
