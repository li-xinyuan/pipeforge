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
              <span class="mock-yaml__key">processor</span>: python<br>
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
  max-width: 520px;
  margin: 0 auto;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  position: relative;
}

.anim-frame__bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
}

.anim-frame__dots {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

.anim-frame__dots i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
}

.anim-frame__dots i:first-child { background: #f87171; }
.anim-frame__dots i:nth-child(2) { background: #fbbf24; }
.anim-frame__dots i:last-child { background: #34d399; }

.anim-frame__title {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.anim-frame__viewport {
  overflow: hidden;
  height: 260px;
}

.anim-frame__scroll {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px 180px;
}

.anim-frame__hint {
  text-align: center;
  font-size: 10px;
  color: var(--color-text-muted);
  padding: 7px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border-light);
  opacity: 0.7;
}

/* ── Step Card ── */
.anim-step {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 10px 12px;
  flex-shrink: 0;
}

.anim-step__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.anim-step__icon { font-size: 16px; }

.anim-step__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.anim-step__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.anim-step__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

/* ── Mock Form Elements ── */
.mock-input {
  height: 26px;
  padding: 0 8px;
  font-size: 11px;
  color: var(--color-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 5px;
  display: flex;
  align-items: center;
}

.mock-input--sm {
  max-width: 100px;
}

.mock-textarea {
  height: 32px;
  padding: 6px 8px;
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 5px;
  line-height: 1.4;
}

.mock-btn {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #0d9488, #14b8a6);
  border-radius: 6px;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}

.mock-btn--accent {
  background: transparent;
  color: var(--color-primary);
  border: 1.5px solid var(--color-primary);
  text-shadow: none;
}

.mock-cards {
  display: flex;
  gap: 6px;
}

.mock-card {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 5px 10px;
  font-size: 10px;
  font-weight: 500;
  color: var(--color-text-muted);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.mock-card--active {
  color: #166534;
  background: #f0fdf4;
  border-color: #16a34a;
}

.mock-upload {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  font-size: 10px;
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border: 1px dashed var(--color-primary-border);
  border-radius: 6px;
}

.mock-ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 500;
  color: var(--color-primary, #0369a1);
  background: var(--color-primary-bg, #f0f9ff);
  border: 1px solid var(--color-primary-border, #bae6fd);
  border-radius: 5px;
  align-self: flex-start;
}

.mock-code {
  padding: 8px 10px;
  font-size: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--color-code-text, #e2e8f0);
  background: var(--color-code-bg, #1e293b);
  border-radius: 6px;
  line-height: 1.5;
}

.mock-code__kw { color: var(--color-code-keyword, #93c5fd); }
.mock-code__str { color: var(--color-code-string, #fbbf24); }

.mock-mapping {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.mock-mapping__item {
  display: inline-block;
  padding: 2px 6px;
  font-size: 9px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.mock-yaml {
  padding: 8px 10px;
  font-size: 9px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--color-code-text, #cbd5e1);
  background: var(--color-code-bg, #1e293b);
  border-radius: 6px;
  line-height: 1.6;
}

.mock-yaml__key { color: var(--color-code-keyword, #7dd3fc); }

@media (max-width: 480px) {
  .anim-frame { max-width: 100%; }
  .anim-frame__viewport { height: 190px; }
  .anim-step { padding: 8px 10px; }
  .anim-step__title { font-size: 11px; }
  .mock-code { font-size: 9px; }
  .mock-yaml { font-size: 8px; }
}
</style>
