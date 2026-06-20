<template>
  <div class="anim-frame">
    <div class="anim-frame__bar">
      <span class="anim-frame__dots"><i></i><i></i><i></i></span>
      <span class="anim-frame__title">ConfigForge 配置向导</span>
    </div>
    <div class="anim-frame__viewport">
      <div ref="scrollInner" class="anim-frame__scroll">
        <!-- Screen 1: Step 1 + Step 2 -->
        <div class="anim-group">
          <div class="anim-step">
            <div class="anim-step__head"><span class="anim-step__icon">🎨</span><span class="anim-step__title">场景信息</span></div>
            <div class="anim-step__body">
              <span class="mock-input">销售报表生成</span>
              <span class="mock-input mock-input--sm">v1.0</span>
            </div>
          </div>
          <div class="anim-step">
            <div class="anim-step__head"><span class="anim-step__icon">📂</span><span class="anim-step__title">输入源</span></div>
            <div class="anim-step__body">
              <span class="mock-card mock-card--active">📊 Excel</span>
              <span class="mock-card">🗄 CSV</span>
              <span class="mock-upload">📤 上传文件</span>
            </div>
          </div>
        </div>

        <!-- Screen 2: Step 3 + Step 4 -->
        <div class="anim-group">
          <div class="anim-step">
            <div class="anim-step__head"><span class="anim-step__icon">⚡</span><span class="anim-step__title">处理步骤</span></div>
            <div class="anim-step__body">
              <span class="mock-ai-btn">✨ AI 生成 SQL</span>
              <span class="mock-code"><span class="mock-code__kw">SELECT</span> * <span class="mock-code__kw">FROM</span> <span class="mock-code__str">"sales_data"</span></span>
              <span class="mock-input mock-input--sm">result</span>
            </div>
          </div>
          <div class="anim-step">
            <div class="anim-step__head"><span class="anim-step__icon">📤</span><span class="anim-step__title">输出配置</span></div>
            <div class="anim-step__body">
              <span class="mock-card mock-card--active">📊 Excel</span>
              <span class="mock-card">🗄 CSV</span>
              <span class="mock-mapping__item">city → 城市</span>
            </div>
          </div>
        </div>

        <!-- Screen 3: Step 5 + Confetti -->
        <div class="anim-group">
          <div class="anim-step">
            <div class="anim-step__head"><span class="anim-step__icon">🚀</span><span class="anim-step__title">预览与导出</span></div>
            <div class="anim-step__body">
              <span class="mock-btn">保存配置</span>
              <span class="mock-btn mock-btn--accent">下载 YAML</span>
            </div>
          </div>
          <div class="anim-confetti">
            <span class="anim-confetti__piece" v-for="i in 12" :key="i" :style="{ '--i': i }">🎉</span>
          </div>
        </div>
      </div>
    </div>
    <div class="anim-frame__hint">↓ 自动演示完整流程</div>
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
    const groups = container.querySelectorAll<HTMLElement>('.anim-group')
    if (groups.length === 0) return

    const tl = createTimeline({ loop: true })

    // Show screen 1
    tl.add({ duration: 3500 })

    // Scroll to screen 2
    tl.add(container, {
      translateY: -(groups[1].offsetTop - 8),
      duration: 700,
      easing: 'easeInOutQuad',
    })
    tl.add({ duration: 3500 })

    // Scroll to screen 3
    tl.add(container, {
      translateY: -(groups[2].offsetTop - 8),
      duration: 700,
      easing: 'easeInOutQuad',
    })
    tl.add({ duration: 4000 })

    // Pause then reset
    tl.add({ duration: 1000 })
    tl.add(container, {
      translateY: 0,
      duration: 500,
      easing: 'easeInOutQuad',
    })
    tl.add({ duration: 2000 })

    anim = tl
  } catch { /* silently ignore */ }
})

onUnmounted(() => { anim?.pause() })
</script>

<style scoped>
.anim-frame {
  max-width: 100%; margin: 0 auto;
  border: 1px solid var(--color-border); border-radius: 12px;
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
.anim-frame__viewport { overflow: hidden; height: 155px; }
.anim-frame__scroll { display: flex; flex-direction: column; gap: 24px; padding: 8px 12px 160px; }
.anim-frame__hint {
  text-align: center; font-size: 10px; color: var(--color-text-muted);
  padding: 6px; background: var(--color-surface-hover);
  border-top: 1px solid var(--color-border-light);
}

/* Group: two steps side by side */
.anim-group {
  display: flex; flex-direction: column; gap: 6px;
  padding: 4px; border: 1px solid var(--color-border-light);
  border-radius: 10px; background: var(--color-bg);
  flex-shrink: 0;
}

/* Step card */
.anim-step {
  background: var(--color-surface); border: 1px solid var(--color-border-light);
  border-radius: 8px; padding: 8px 12px; flex-shrink: 0;
}
.anim-step__head { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.anim-step__icon { font-size: 14px; }
.anim-step__title { font-size: 12px; font-weight: 700; color: var(--color-text); }
.anim-step__body { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }

/* Mock elements */
.mock-input {
  height: 22px; padding: 0 8px; font-size: 10px; color: var(--color-text);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 5px; display: flex; align-items: center;
}
.mock-input--sm { max-width: 70px; }
.mock-btn {
  display: inline-flex; align-items: center;
  padding: 3px 8px; font-size: 9px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #7c3aed, #6366f1);
  border-radius: 5px; white-space: nowrap;
}
.mock-btn--accent {
  background: rgba(255,255,255,0.6); color: #7c3aed;
  border: 1px solid rgba(124,58,237,0.25);
}
.mock-card { padding: 3px 6px; font-size: 9px; font-weight: 500; color: var(--color-text-muted); background: var(--color-bg); border: 1px solid var(--color-border-light); border-radius: 4px; }
.mock-card--active { color: #166534; background: #f0fdf4; border-color: #16a34a; }
.mock-upload { display: flex; align-items: center; gap: 3px; padding: 3px 6px; font-size: 9px; color: var(--color-primary); background: var(--color-primary-bg); border: 1px dashed var(--color-primary-border); border-radius: 4px; }
.mock-ai-btn { display: inline-flex; align-items: center; gap: 3px; padding: 3px 6px; font-size: 9px; font-weight: 600; color: #fff; background: linear-gradient(135deg, #7c3aed, #6366f1); border-radius: 4px; }
.mock-code { padding: 5px 6px; font-size: 8px; font-family: ui-monospace, monospace; color: #e2e8f0; background: #1e293b; border-radius: 4px; line-height: 1.3; max-width: 140px; overflow: hidden; }
.mock-code__kw { color: #93c5fd; }
.mock-code__str { color: #fbbf24; }
.mock-mapping__item { padding: 2px 5px; font-size: 8px; color: var(--color-text-secondary); background: var(--color-bg); border: 1px solid var(--color-border-light); border-radius: 3px; font-family: ui-monospace, monospace; }

/* Confetti */
.anim-confetti {
  display: flex; flex-wrap: wrap; gap: 4px; justify-content: center;
  padding: 12px 8px; opacity: 0.8;
}
.anim-confetti__piece {
  font-size: 18px; animation: confetti-bounce 1.5s ease-in-out infinite;
  animation-delay: calc(var(--i) * 0.12s);
}
@keyframes confetti-bounce {
  0%,100% { transform: translateY(0) scale(1); opacity:1; }
  50% { transform: translateY(-6px) scale(1.2); opacity:0.6; }
}

@media (max-width: 600px) {
  .anim-frame__viewport { height: 180px; }
  .anim-step { padding: 6px 10px; }
}
</style>
