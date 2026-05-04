<template>
  <div class="flex gap-2 mt-4">
    <button @click="copyYaml" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">📋 复制</button>
    <button @click="downloadYaml" class="px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">📥 下载 YAML</button>
    <button @click="downloadTemplate" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">📄 下载模板</button>
  </div>
</template>
<script setup lang="ts">
async function copyYaml() {
  const pre = document.querySelector('pre')
  if (pre) {
    await navigator.clipboard.writeText(pre.textContent || '')
    alert('已复制到剪贴板')
  }
}

async function downloadYaml() {
  const pre = document.querySelector('pre')
  if (pre) {
    const blob = new Blob([pre.textContent || ''], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'pipeline.yaml'; a.click()
    URL.revokeObjectURL(url)
  }
}

function downloadTemplate() {
  // placeholder — template download requires backend call
  alert('模板下载功能需要后端支持')
}
</script>
