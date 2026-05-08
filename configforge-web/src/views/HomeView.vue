<template>
  <div class="max-w-3xl mx-auto px-4 py-12">
    <div class="text-center">
      <h1 class="text-xl font-semibold">ConfigForge</h1>
      <p class="text-sm text-slate-500 mt-1">PipeForge 配置创建向导</p>
    </div>

    <div class="mt-8 bg-white border border-slate-200 rounded-lg p-6 text-sm text-slate-600 leading-relaxed space-y-3 max-w-xl mx-auto">
      <p>ConfigForge 是一个<strong class="text-slate-800">引导式、可视化的配置创建工具</strong>，帮助你将数据处理需求转化为 PipeForge 可执行的流水线配置，无需手写 YAML。</p>
      <p>通过 <strong class="text-slate-800">4 步向导</strong>完成配置：描述场景 → 上传数据源 → 配置处理逻辑与输出格式 → 一键导出 YAML 和模板文件。</p>
      <p>支持 <strong class="text-slate-800">AI 辅助</strong>生成 SQL、列映射建议和场景推断，所有数据<strong class="text-slate-800">本地处理</strong>，不上传至外部服务。</p>
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
