<template>
  <div class="anim-frame">
    <div class="anim-frame__bar">
      <span class="anim-frame__dots"><i /><i /><i /></span>
      <span class="anim-frame__title">ConfigForge 配置向导</span>
    </div>
    <div class="anim-frame__viewport">
      <div ref="scrollInner" class="anim-frame__scroll">
        <!-- Screen 1: Scene Info -->
        <div class="anim-group">
          <div class="anim-group__left">
            <div class="anim-step">
              <div class="anim-step__head">🎨 步骤 1 · 场景信息</div>
              <div class="anim-step__body">
                <div class="a-input a-input--lg">销售数据月度汇总</div>
                <div class="a-input a-input--sm">v1.0</div>
              </div>
            </div>
          </div>
          <div class="anim-group__right">
            <div class="a-panel">
              <div class="a-panel__title">🤖 AI 助手</div>
              <div class="a-panel__text">请填写场景名称，描述你的数据处理目标</div>
              <div class="a-panel__dots"><i /><i /><i /><i /><i /></div>
            </div>
          </div>
        </div>

        <!-- Screen 2: Input Sources -->
        <div class="anim-group">
          <div class="anim-group__left">
            <div class="anim-step">
              <div class="anim-step__head">📂 步骤 2 · 输入源</div>
              <div class="anim-step__body">
                <div class="a-types">
                  <span class="a-type a-type--active">📊 Excel</span>
                  <span class="a-type">🗄 CSV</span>
                  <span class="a-type">🔌 数据库</span>
                  <span class="a-type">📋 JSON</span>
                  <span class="a-type">📄 XML</span>
                  <span class="a-type">📦 Parquet</span>
                  <span class="a-type">🌐 REST API</span>
                </div>
              </div>
            </div>
          </div>
          <div class="anim-group__right">
            <div class="a-panel">
              <div class="a-panel__title">🤖 AI 助手</div>
              <div class="a-panel__text">请选择数据来源类型。支持 7 种格式，上传后可 AI 分析列结构</div>
              <div class="a-panel__dots"><i class="on" /><i class="on" /><i /><i /><i /></div>
            </div>
          </div>
        </div>

        <!-- Screen 3: Processing -->
        <div class="anim-group">
          <div class="anim-group__left">
            <div class="anim-step">
              <div class="anim-step__head">⚡ 步骤 3 · 处理步骤</div>
              <div class="anim-step__body">
                <div class="a-code">
                  <span class="a-code__kw">SELECT</span> city,
                  <span class="a-code__kw">COUNT</span>(*) <span class="a-code__kw">AS</span> cnt,
                  <span class="a-code__kw">SUM</span>(amount) <span class="a-code__kw">AS</span> total
                  <span class="a-code__kw">FROM</span> <span class="a-code__str">"sales"</span>
                  <span class="a-code__kw">GROUP BY</span> city
                </div>
                <div class="a-types" style="margin-top:2px">
                  <span class="a-type a-type--active">🧪 SQL</span>
                  <span class="a-type">🐍 Python</span>
                </div>
                <span class="a-btn a-btn--ai">✨ AI 生成代码</span>
              </div>
            </div>
          </div>
          <div class="anim-group__right">
            <div class="a-panel">
              <div class="a-panel__title">🤖 AI 助手</div>
              <div class="a-panel__text">已根据场景自动生成 SQL 代码。支持自然语言描述需求，AI 生成查询</div>
              <div class="a-panel__dots"><i class="on" /><i class="on" /><i class="on" /><i /><i /></div>
            </div>
          </div>
        </div>

        <!-- Screen 4: Output -->
        <div class="anim-group">
          <div class="anim-group__left">
            <div class="anim-step">
              <div class="anim-step__head">📤 步骤 4 · 输出配置</div>
              <div class="anim-step__body">
                <div class="a-types">
                  <span class="a-type a-type--active">📊 Excel</span>
                  <span class="a-type">🗄 CSV</span>
                  <span class="a-type">🔌 数据库</span>
                </div>
                <div class="a-mapping">
                  <span>city → 城市</span>
                  <span>cnt → 订单数</span>
                  <span>total → 总金额</span>
                </div>
              </div>
            </div>
          </div>
          <div class="anim-group__right">
            <div class="a-panel">
              <div class="a-panel__title">🤖 AI 助手</div>
              <div class="a-panel__text">列映射已自动完成。输出格式为 Excel，文件名自动生成</div>
              <div class="a-panel__dots"><i class="on" /><i class="on" /><i class="on" /><i class="on" /><i /></div>
            </div>
          </div>
        </div>

        <!-- Screen 5: Export -->
        <div class="anim-group">
          <div class="anim-group__left">
            <div class="anim-step">
              <div class="anim-step__head">🚀 步骤 5 · 预览与导出</div>
              <div class="anim-step__body">
                <div class="a-actions">
                  <span class="a-btn">📥 下载 YAML</span>
                  <span class="a-btn a-btn--accent">▶ 执行流水线</span>
                </div>
              </div>
            </div>
          </div>
          <div class="anim-group__right">
            <div class="a-panel a-panel--done">
              <div class="a-panel__title">🤖 AI 助手</div>
              <div class="a-panel__text">🎉 配置完成！5 个步骤全部就绪，可下载 YAML 或直接执行</div>
              <div class="a-panel__dots"><i class="on" /><i class="on" /><i class="on" /><i class="on" /><i class="on" /></div>
            </div>
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
    const stepH = 170 // matches viewport + group height
    const tl = createTimeline({ loop: true })
    tl.add({ duration: 4000 })
    for (let i = 1; i < 5; i++) {
      tl.add(container, { translateY: -(stepH * i), duration: 800, easing: 'easeInOutQuad' })
      tl.add({ duration: 4000 })
    }
    tl.add({ duration: 1500 })
    tl.add(container, { translateY: 0, duration: 500, easing: 'easeInOutQuad' })
    tl.add({ duration: 2000 })
    anim = tl
  } catch { /* ignore */ }
})

onUnmounted(() => { anim?.pause() })
</script>

<style scoped>
.anim-frame {
  max-width: 560px; margin: 0 auto;
  border: 1px solid var(--color-border); border-radius: 12px;
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
  overflow: hidden;
}
.anim-frame__bar {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  background: var(--color-surface-hover); border-bottom: 1px solid var(--color-border-light);
}
.anim-frame__dots { display: flex; gap: 4px; }
.anim-frame__dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-border); }
.anim-frame__dots i:first-child { background: #f87171; }
.anim-frame__dots i:nth-child(2) { background: #fbbf24; }
.anim-frame__dots i:last-child { background: #34d399; }
.anim-frame__title { font-size: 10px; color: var(--color-text-muted); }
.anim-frame__viewport { overflow: hidden; height: 170px; }
.anim-frame__scroll { display: flex; flex-direction: column; gap: 0; padding: 0; }
.anim-frame__hint {
  text-align: center; font-size: 10px; color: var(--color-text-muted);
  padding: 5px; background: var(--color-surface-hover); border-top: 1px solid var(--color-border-light);
}

/* Group: left content + right AI panel */
.anim-group {
  display: flex; gap: 8px; padding: 8px;
  background: linear-gradient(180deg, var(--color-bg), var(--color-surface));
  flex-shrink: 0; height: 170px; overflow: hidden;
}
.anim-group__left { flex: 1; min-width: 0; }
.anim-group__right { width: 140px; flex-shrink: 0; }

/* Step card */
.anim-step {
  background: var(--color-surface); border: 1px solid var(--color-border-light);
  border-radius: 8px; padding: 10px 12px;
}
.anim-step__head { font-size: 12px; font-weight: 700; color: var(--color-text); margin-bottom: 8px; }
.anim-step__body { display: flex; flex-direction: column; gap: 6px; }

/* Mock form */
.a-input {
  height: 24px; padding: 0 8px; font-size: 10px; color: var(--color-text);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 5px; display: flex; align-items: center;
}
.a-input--lg { width: 100%; }
.a-input--sm { max-width: 80px; }

.a-types { display: flex; gap: 3px; flex-wrap: wrap; }
.a-type {
  padding: 3px 5px; font-size: 8px; font-weight: 500;
  color: var(--color-text-muted); background: var(--color-bg);
  border: 1px solid var(--color-border-light); border-radius: 4px;
}
.a-type--active { color: var(--color-success); background: var(--color-success-bg); border-color: var(--color-success); }

.a-code {
  padding: 6px 8px; font-size: 9px; font-family: ui-monospace, monospace;
  color: var(--color-code-text); background: var(--color-code-bg); border-radius: 5px; line-height: 1.5;
}
.a-code__kw { color: #93c5fd; }
.a-code__str { color: #fbbf24; }

.a-btn {
  display: inline-flex; align-items: center; gap: 3px; padding: 4px 8px;
  font-size: 9px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border-radius: 4px; align-self: flex-start;
}
.a-btn--ai {
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(124,58,237,.3)} 50%{box-shadow:0 0 0 4px rgba(124,58,237,0)} }
.a-btn--accent {
  background: var(--color-surface-input); color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
}

.a-mapping { display: flex; gap: 3px; flex-wrap: wrap; }
.a-mapping span {
  padding: 2px 5px; font-size: 8px; color: var(--color-text-secondary);
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 3px; font-family: ui-monospace, monospace;
}

.a-actions { display: flex; gap: 6px; }

/* AI panel */
.a-panel {
  background: linear-gradient(180deg, rgba(124,58,237,0.04), rgba(99,102,241,0.02));
  border: 1px solid rgba(124,58,237,0.1); border-radius: 8px;
  padding: 10px; height: 100%; display: flex; flex-direction: column;
}
.a-panel--done { border-color: rgba(16,185,129,0.2); background: linear-gradient(180deg, rgba(16,185,129,0.04), rgba(5,150,105,0.02)); }
.a-panel__title { font-size: 10px; font-weight: 600; color: var(--color-ai); margin-bottom: 6px; }
.a-panel--done .a-panel__title { color: var(--color-success); }
.a-panel__text { font-size: 9px; color: var(--color-text-muted); line-height: 1.5; flex: 1; }
.a-panel__dots { display: flex; gap: 4px; margin-top: 8px; }
.a-panel__dots i { width: 5px; height: 5px; border-radius: 50%; background: var(--color-border); }
.a-panel__dots i.on { background: #7c3aed; }

@media (max-width: 480px) {
  .anim-group__right { width: 100px; }
  .anim-frame__viewport { height: 150px; }
}
</style>
