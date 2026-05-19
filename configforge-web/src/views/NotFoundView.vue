<template>
  <div class="flex items-center justify-center min-h-screen">
    <NResult
      status="404"
      title="404 页面未找到"
      description="您访问的页面不存在，请检查 URL 是否正确。"
    >
      <template #footer>
        <NButton type="primary" @click="router.push('/')">返回首页</NButton>
      </template>
    </NResult>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NResult, NButton } from 'naive-ui'

const router = useRouter()
</script>
