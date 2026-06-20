<template>
  <div class="anim-frame">
    <div class="anim-frame__bar">
      <span class="anim-frame__dots"><i></i><i></i><i></i></span>
      <span class="anim-frame__title">ConfigForge 配置向导</span>
    </div>
    <div class="anim-frame__viewport">
      <div ref="scrollInner" class="anim-frame__scroll">
        <!-- Step 1 -->
        <div class="anim-step">
          <div class="anim-step__head">
            <span class="anim-step__icon">🎨</span>
            <span class="anim-step__title">场景信息</span>
          </div>
          <div class="anim-step__body">
            <div class="mock-input">销售报表生成</div>
            <div class="mock-input mock-input--sm">v1.0</div>
            <div class="mock-textarea">根据每日销售明细生成汇总报表…</div>
          </div>
          <div class="anim-step__foot">
            <span class="mock-btn">下一步 ↓</span>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="anim-step">
          <div class="anim-step__head">
            <span class="anim-step__icon">📂</span>
            <span class="anim-step__title">输入源</span>
          </div>
          <div class="anim-step__body">
            <div class="mock-cards">
              <span class="mock-card mock-card--active">📊 Excel</span>
              <span class="mock-card">🗄 CSV</span>
            </div>
            <div class="mock-upload">📤 上传 Excel 文件</div>
            <div class="mock-input mock-input--sm">sales_data</div>
          </div>
          <div class="anim-step__foot">
            <span class="mock-btn">下一步 ↓</span>
          </div>
        </div>

        <!-- Step 3 -->
        <div class="anim-step">
          <div class="anim-step__head">
            <span class="anim-step__icon">⚡</span>
            <span class="anim-step__title">数据处理</span>
          </div>
          <div class="anim-step__body">
            <div class="mock-ai-btn">🤖 AI 生成代码</div>
            <div class="mock-code">
              <span class="mock-code__kw">SELECT</span> * <span class="mock-code__kw">FROM</span> <span class="mock-code__str">"sales_data"</span>
            </div>
            <div class="mock-input mock-input--sm">result</div>
          </div>
          <div class="anim-step__foot">
            <span class="mock-btn">下一步 ↓</span>
          </div>
        </div>

        <!-- Step 4 -->
        <div class="anim-step">
          <div class="anim-step__head">
            <span class="anim-step__icon">📤</span>
            <span class="anim-step__title">输出配置</span>
          </div>
          <div class="anim-step__body">
            <div class="mock-cards">
              <span class="mock-card mock-card--active">📊 Excel</span>
              <span class="mock-card">🗄 CSV</span>
            </div>
            <div class="mock-mapping">
              <span class="mock-mapping__item">name → 姓名</span>
              <span class="mock-mapping__item">amount → 金额</span>
              <span class="mock-mapping__item">date → 日期</span>
            </div>
          </div>
          <div class="anim-step__foot">
            <span class="mock-btn">下一步 ↓</span>
          </div>
        </div>

        <!-- Step 5 -->
        <div class="anim-step">
          <div class="anim-step__head">
            <span class="anim-step__icon">🚀</span>
            <span class="anim-step__title">预览与导出</span>
          </div>
          <div class="anim-step__body">
            <div class="mock-yaml">
              <span class="mock-yaml__key">pipeline</span>: sales_report<br>
              <span class="mock-yaml__key">inputs</span>:<br>
              &nbsp;&nbsp;- sales_data<br>
              <span class="mock-yaml__key">processors</span>: python<br>
              <span class="mock-yaml__key">output</span>: report.xlsx
            </div>
          </div>
          <div class="anim-step__foot">
            <span class="mock-btn">保存配置</span>
            <span class="mock-btn mock-btn--accent">下载结果文件</span>
          </div>
        </div>
      </div>
    </div>
    <div class="anim-frame__hint">↓ 自动演示流程</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { createTimeline } from 'animejs'

const scrollInner = ref<HTMLElement>()
let anim: ReturnType<typeof createTimeline> | null = null

onMounted(async () => {
  await nextTick()
  const container = scrollInner.value
  if (!container) return

  try {
    const steps = container.querySelectorAll<HTMLElement>('.anim-step')
    if (steps.length === 0) return

    const tl = createTimeline({ loop: true })

    steps.forEach((el) => {
      const y = -(el.offsetTop - 8)
      tl.add(container, {
        translateY: y,
        duration: 600,
        easing: 'easeInOutQuad',
      })
      tl.add({ duration: 2000 })
    })

    tl.add(container, {
      translateY: 0,
      duration: 400,
      easing: 'easeInOutQuad',
    })
    tl.add({ duration: 1000 })

    anim = tl
  } catch { /* silently ignore animation errors */ }
})

onUnmounted(() => {
  anim?.pause()
})
</script>

<style scoped>
.anim-frame {
  max-width: 100%;
  margin: 0 auto;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
  overflow: hidden;
}
.anim-frame__bar {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; background: var(--color-surface-hover);
  border-bottom: 1px solid var(--color-border-light);
}
.anim-frame__dots { display: flex; gap: 4px; }
.anim-frame__dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-border); }
.anim-frame__dots i:first-child { background: #f87171; }
.anim-frame__dots i:nth-child(2) { background: #fbbf24; }
.anim-frame__dots i:last-child { background: #34d399; }
.anim-frame__title { font-size: 10px; color: var(--color-text-muted); }
.anim-frame__viewport { overflow: hidden; height: 130px; }
.anim-frame__scroll { display: flex; gap: 8px; padding: 8px; }
.anim-frame__hint {
  text-align: center; font-size: 10px; color: var(--color-text-muted);
  padding: 6px; background: var(--color-surface-hover);
  border-top: 1px solid var(--color-border-light);
}

.anim-step {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 10px 14px;
  flex-shrink: 0;
  min-width: 380px;
}
.anim-step__head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.anim-step__icon { font-size: 15px; }
.anim-step__title { font-size: 13px; font-weight: 700; color: var(--color-text); }
.anim-step__body { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.anim-step__foot {
  display: flex; align-items: center; justify-content: flex-end; gap: 6px;
  margin-top: 8px; padding-top: 6px; border-top: 1px solid var(--color-border-light);
}

.mock-input {
  height: 24px; padding: 0 8px; font-size: 10px; color: var(--color-text);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 5px; display: flex; align-items: center;
}
.mock-input--sm { max-width: 80px; }
.mock-textarea {
  height: 26px; padding: 4px 8px; font-size: 10px; color: var(--color-text-secondary);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 5px; line-height: 1.3;
}
.mock-btn {
  display: inline-flex; align-items: center;
  padding: 4px 10px; font-size: 10px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #7c3aed, #6366f1);
  border-radius: 6px; white-space: nowrap;
}
.mock-btn--accent {
  background: rgba(255,255,255,0.6); color: #7c3aed;
  border: 1.5px solid rgba(124,58,237,0.3);
  backdrop-filter: blur(4px);
}
.mock-cards { display: flex; gap: 4px; }
.mock-card {
  padding: 4px 8px; font-size: 10px; font-weight: 500;
  color: var(--color-text-muted); background: var(--color-bg);
  border: 1px solid var(--color-border-light); border-radius: 5px;
}
.mock-card--active { color: #166534; background: #f0fdf4; border-color: #16a34a; }
.mock-upload {
  display: flex; align-items: center; gap: 3px;
  padding: 4px 8px; font-size: 10px; color: var(--color-primary);
  background: var(--color-primary-bg); border: 1px dashed var(--color-primary-border);
  border-radius: 5px;
}
.mock-ai-btn {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 4px 8px; font-size: 9px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #7c3aed, #6366f1);
  border-radius: 5px;
}
.mock-code {
  padding: 6px 8px; font-size: 9px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #e2e8f0; background: #1e293b; border-radius: 5px; line-height: 1.4;
  max-width: 220px; overflow: hidden;
}
.mock-code__kw { color: #93c5fd; }
.mock-code__str { color: #fbbf24; }
.mock-mapping { display: flex; gap: 4px; flex-wrap: wrap; }
.mock-mapping__item {
  padding: 2px 6px; font-size: 9px; color: var(--color-text-secondary);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.mock-yaml {
  padding: 6px 8px; font-size: 9px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #cbd5e1; background: #1e293b; border-radius: 5px; line-height: 1.5;
  max-width: 280px; overflow: hidden;
}
.mock-yaml__key { color: #7dd3fc; }

@media (max-width: 600px) {
  .anim-frame__viewport { height: 110px; }
  .anim-step { min-width: 280px; padding: 8px 10px; }
}
</style>
