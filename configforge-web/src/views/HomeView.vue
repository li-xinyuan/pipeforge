<template>
  <div class="max-w-3xl mx-auto px-4 py-12">
    <div class="text-center">
      <h1 class="text-xl font-semibold">ConfigForge</h1>
      <p class="text-sm text-slate-500 mt-1">PipeForge 配置创建向导</p>
    </div>
    <div class="mt-8 text-center">
      <router-link
        to="/step/1"
        class="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
      >
        开始创建新配置 &rarr;
      </router-link>
    </div>
  </div>
</template>
