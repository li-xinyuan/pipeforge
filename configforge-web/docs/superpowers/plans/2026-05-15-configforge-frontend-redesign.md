# ConfigForge Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign ConfigForge frontend from a 5-page wizard to a single-page scroll layout with Teal design system, embedded AI, dark mode, and responsive design.

**Architecture:** Single `ConfigWizardView.vue` replaces 5 step route pages. Sticky `WizardProgress` bar tracks scroll position via Intersection Observer. Right-side `AiChatPanel` (340px, collapsible) provides conversational AI interaction. `AiInlineTip` component embeds AI suggestions within step cards. CSS custom properties drive the Teal design system with light/dark theme switching via `data-theme` attribute.

**Tech Stack:** Vue 3 + Naive UI + Tailwind CSS + Pinia + Vue Router + Vitest + happy-dom

---

### Task 1: CSS Design System & Theme Variables

**Files:**
- Modify: `src/style.css`

Replace the single-line Tailwind import with a complete design system of CSS custom properties, including light and dark theme, typography, and component tokens.

- [ ] **Step 1: Write the CSS design system**

Replace `src/style.css`:

```css
@import "tailwindcss";

:root {
  /* === Teal Primary Palette === */
  --color-primary: #0d9488;
  --color-primary-light: #14b8a6;
  --color-primary-lighter: #5eead4;
  --color-primary-bg: #f0fdfa;
  --color-primary-border: #99f6e4;

  /* === Surfaces === */
  --color-bg: #fafdfb;
  --color-bg-secondary: #f0fdfa;
  --color-surface: #ffffff;
  --color-surface-hover: #f8fafc;

  /* === Text === */
  --color-text: #134e4a;
  --color-text-secondary: #64748b;
  --color-text-muted: #94a3b8;

  /* === Borders === */
  --color-border: #d1d5db;
  --color-border-light: #e2e8f0;

  /* === Semantic === */
  --color-success: #166534;
  --color-success-bg: #f0fdf4;
  --color-success-border: #bbf7d0;
  --color-warning: #d97706;
  --color-warning-bg: #fffbeb;
  --color-warning-border: #fde68a;
  --color-error: #dc2626;
  --color-error-bg: #fef2f2;
  --color-error-border: #fecaca;
  --color-info: #0284c7;
  --color-info-bg: #eff6ff;
  --color-info-border: #bfdbfe;

  /* === Radius === */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;

  /* === Shadows === */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.03);
  --shadow-md: 0 2px 12px rgba(0, 0, 0, 0.04);
  --shadow-active: 0 3px 16px rgba(13, 148, 136, 0.06);
  --shadow-button: 0 2px 8px rgba(13, 148, 136, 0.25);

  /* === Typography === */
  --font-family: "Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-size-xs: 0.625rem;
  --font-size-sm: 0.75rem;
  --font-size-base: 0.8125rem;
  --font-size-lg: 0.9375rem;
  --font-size-xl: 1.0625rem;
  --font-size-2xl: 2.125rem;

  /* === Spacing === */
  --space-card-padding: 1.5rem;
  --space-section-gap: 1.125rem;

  /* === Transitions === */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.4s ease;

  /* === AI Panel === */
  --ai-panel-width: 340px;
}

/* === Dark Theme === */
[data-theme="dark"] {
  --color-primary: #14b8a6;
  --color-primary-light: #34d399;
  --color-primary-lighter: #6ee7b7;
  --color-primary-bg: rgba(13, 148, 136, 0.08);
  --color-primary-border: rgba(13, 148, 136, 0.2);

  --color-bg: #0a1c14;
  --color-bg-secondary: #0d241a;
  --color-surface: rgba(255, 255, 255, 0.04);
  --color-surface-hover: rgba(255, 255, 255, 0.06);

  --color-text: #d1fae5;
  --color-text-secondary: #999999;
  --color-text-muted: #64748b;

  --color-border: #1a3d2c;
  --color-border-light: #164e35;

  --color-success-bg: rgba(5, 150, 105, 0.1);
  --color-success-border: rgba(5, 150, 105, 0.2);
  --color-warning-bg: rgba(180, 83, 9, 0.1);
  --color-warning-border: rgba(180, 83, 9, 0.2);
  --color-error-bg: rgba(220, 38, 38, 0.1);
  --color-error-border: rgba(220, 38, 38, 0.2);

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 2px 12px rgba(0, 0, 0, 0.3);
  --shadow-active: 0 3px 16px rgba(13, 148, 136, 0.1);
}

/* === Base Styles === */
body {
  font-family: var(--font-family);
  background: var(--color-bg);
  color: var(--color-text);
  transition: background var(--transition-normal), color var(--transition-normal);
}

/* === Scrollbar === */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}

/* === Focus === */
*:focus-visible {
  outline: 2px solid var(--color-primary-lighter);
  outline-offset: 2px;
}
```

- [ ] **Step 2: Verify build succeeds**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite build 2>&1 | tail -5`
Expected: Build completes without CSS errors.

- [ ] **Step 3: Commit**

```bash
git add src/style.css
git commit -m "feat: add Teal CSS design system with light/dark theme tokens"
```

---

### Task 2: Theme Composable

**Files:**
- Create: `src/composables/useTheme.ts`

A simple composable to manage theme state (light/dark) with localStorage persistence and a `data-theme` attribute on `<html>`.

- [ ] **Step 1: Write the composable**

Create `src/composables/useTheme.ts`:

```typescript
import { ref, watchEffect } from 'vue'

const THEME_KEY = 'configforge-theme'

const isDark = ref(false)

function initTheme() {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'dark') {
    isDark.value = true
  } else if (stored === 'light') {
    isDark.value = false
  } else {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyTheme()
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
}

function toggleTheme() {
  isDark.value = !isDark.value
}

watchEffect(() => { applyTheme() })

export function useTheme() {
  return { isDark, initTheme, toggleTheme }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit src/composables/useTheme.ts 2>&1 | head -5`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/composables/useTheme.ts
git commit -m "feat: add useTheme composable with light/dark toggle and localStorage"
```

---

### Task 3: AiInlineTip Component

**Files:**
- Create: `src/components/wizard/AiInlineTip.vue`
- Create: `tests/components/AiInlineTip.test.ts`

An inline AI suggestion bar displayed inside step cards. Shows an icon, message, and optional action button.

- [ ] **Step 1: Write the test**

Create `tests/components/AiInlineTip.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiInlineTip from '../../src/components/wizard/AiInlineTip.vue'

describe('AiInlineTip', () => {
  it('renders the message text', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'AI has analyzed your data' },
    })
    expect(wrapper.text()).toContain('AI has analyzed your data')
  })

  it('shows the lightning emoji by default', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test' },
    })
    expect(wrapper.text()).toContain('⚡')
  })

  it('renders action button when actionLabel and showAction are provided', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: true, actionLabel: 'Apply' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.find('button').text()).toBe('Apply →')
  })

  it('does not render action button when showAction is false', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: false },
    })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('emits action event when button is clicked', async () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: true, actionLabel: 'Apply' },
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/AiInlineTip.test.ts 2>&1 | tail -5`
Expected: FAIL (file not found).

- [ ] **Step 3: Write the component**

Create `src/components/wizard/AiInlineTip.vue`:

```vue
<template>
  <div class="ai-inline-tip">
    <span class="ai-inline-tip__icon">⚡</span>
    <span class="ai-inline-tip__message">{{ message }}</span>
    <button
      v-if="showAction && actionLabel"
      class="ai-inline-tip__action"
      @click="$emit('action')"
    >{{ actionLabel }} →</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
  showAction?: boolean
  actionLabel?: string
}>()

defineEmits<{ action: [] }>()
</script>

<style scoped>
.ai-inline-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, var(--color-primary-bg), #ccfbf1);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  margin-top: 12px;
}
.ai-inline-tip__icon {
  font-size: 16px;
  flex-shrink: 0;
}
.ai-inline-tip__message {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  flex: 1;
  line-height: 1.5;
}
.ai-inline-tip__action {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.ai-inline-tip__action:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/AiInlineTip.test.ts 2>&1 | tail -5`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/wizard/AiInlineTip.vue tests/components/AiInlineTip.test.ts
git commit -m "feat: add AiInlineTip component for embedded AI suggestions"
```

---

### Task 4: WizardProgress Component

**Files:**
- Create: `src/components/wizard/WizardProgress.vue`
- Create: `tests/components/WizardProgress.test.ts`

Sticky horizontal progress bar showing 5 steps with status (completed/active/locked). Click completed/active steps to navigate.

- [ ] **Step 1: Write the test**

Create `tests/components/WizardProgress.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WizardProgress from '../../src/components/wizard/WizardProgress.vue'

const steps = [
  { label: '场景', status: 'completed' as const },
  { label: '数据源', status: 'active' as const },
  { label: '处理', status: 'locked' as const },
  { label: '输出', status: 'locked' as const },
  { label: '导出', status: 'locked' as const },
]

describe('WizardProgress', () => {
  it('renders all 5 steps', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const items = wrapper.findAll('[data-step]')
    expect(items).toHaveLength(5)
  })

  it('shows step numbers', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('2')
  })

  it('renders connector lines between steps', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const connectors = wrapper.findAll('.wizard-progress__connector')
    expect(connectors).toHaveLength(4)
  })

  it('emits stepClick with correct index when a completed step is clicked', async () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    await wrapper.find('[data-step="1"]').trigger('click')
    expect(wrapper.emitted('stepClick')).toBeTruthy()
    expect(wrapper.emitted('stepClick')![0]).toEqual([1])
  })

  it('does not emit stepClick when a locked step is clicked', async () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    await wrapper.find('[data-step="3"]').trigger('click')
    expect(wrapper.emitted('stepClick')).toBeFalsy()
  })

  it('applies active class to the active step', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const active = wrapper.find('[data-step="2"]')
    expect(active.classes()).toContain('wizard-progress__step--active')
  })

  it('applies completed class to the completed step', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const completed = wrapper.find('[data-step="1"]')
    expect(completed.classes()).toContain('wizard-progress__step--completed')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/WizardProgress.test.ts 2>&1 | tail -5`
Expected: FAIL.

- [ ] **Step 3: Write the component**

Create `src/components/wizard/WizardProgress.vue`:

```vue
<template>
  <div class="wizard-progress">
    <template v-for="(step, i) in steps" :key="i">
      <div
        :data-step="i + 1"
        class="wizard-progress__step"
        :class="stepClasses(step.status)"
        :role="step.status !== 'locked' ? 'button' : undefined"
        :tabindex="step.status !== 'locked' ? 0 : -1"
        @click="onStepClick(i + 1, step.status)"
      >
        <span class="wizard-progress__number">{{ i + 1 }}</span>
        <span class="wizard-progress__label">{{ step.label }}</span>
      </div>
      <div
        v-if="i < steps.length - 1"
        class="wizard-progress__connector"
        :class="{ 'wizard-progress__connector--done': step.status === 'completed' }"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
export interface StepState {
  label: string
  status: 'completed' | 'active' | 'locked'
}

defineProps<{ steps: StepState[] }>()
const emit = defineEmits<{ stepClick: [step: number] }>()

function stepClasses(status: string) {
  return {
    'wizard-progress__step--completed': status === 'completed',
    'wizard-progress__step--active': status === 'active',
    'wizard-progress__step--locked': status === 'locked',
  }
}

function onStepClick(step: number, status: string) {
  if (status !== 'locked') emit('stepClick', step)
}
</script>

<style scoped>
.wizard-progress {
  display: flex;
  align-items: center;
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-primary-border);
  box-shadow: 0 1px 6px rgba(13, 148, 136, 0.05);
  position: sticky;
  top: 0;
  z-index: 10;
}
.wizard-progress__step {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}
.wizard-progress__step--completed,
.wizard-progress__step--active {
  cursor: pointer;
}
.wizard-progress__step--locked {
  cursor: default;
}
.wizard-progress__number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: 700;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}
.wizard-progress__step--completed .wizard-progress__number {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  box-shadow: 0 2px 6px rgba(13, 148, 136, 0.25);
}
.wizard-progress__step--active .wizard-progress__number {
  background: var(--color-primary-bg);
  border: 2px solid var(--color-primary-lighter);
  color: var(--color-primary);
}
.wizard-progress__step--locked .wizard-progress__number {
  background: var(--color-surface-hover);
  border: 2px solid var(--color-border-light);
  color: var(--color-text-muted);
}
.wizard-progress__label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  white-space: nowrap;
}
.wizard-progress__step--locked .wizard-progress__label {
  color: var(--color-text-muted);
}
.wizard-progress__connector {
  width: 18px;
  height: 2px;
  background: var(--color-border-light);
  border-radius: 1px;
  flex-shrink: 0;
  transition: background var(--transition-slow);
}
.wizard-progress__connector--done {
  background: var(--color-primary-lighter);
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/WizardProgress.test.ts 2>&1 | tail -10`
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/wizard/WizardProgress.vue tests/components/WizardProgress.test.ts
git commit -m "feat: add WizardProgress component with step states and click navigation"
```

---

### Task 5: WizardStepCard Component

**Files:**
- Create: `src/components/wizard/WizardStepCard.vue`
- Create: `tests/components/WizardStepCard.test.ts`

Reusable wrapper for each step section. Handles the three visual states (completed/active/locked) with icon, title, description, status badge, and content slot.

- [ ] **Step 1: Write the test**

Create `tests/components/WizardStepCard.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WizardStepCard from '../../src/components/wizard/WizardStepCard.vue'

describe('WizardStepCard', () => {
  it('renders title and description', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: '场景信息', description: '填写基本信息', icon: '🎨', status: 'active' },
    })
    expect(wrapper.text()).toContain('场景信息')
    expect(wrapper.text()).toContain('填写基本信息')
    expect(wrapper.text()).toContain('🎨')
  })

  it('renders slot content', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
      slots: { default: '<p class="slot-content">Hello world</p>' },
    })
    expect(wrapper.find('.slot-content').exists()).toBe(true)
  })

  it('applies active border class when status is active', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
    })
    expect(wrapper.find('.wizard-step-card').classes()).toContain('wizard-step-card--active')
  })

  it('applies locked opacity when status is locked', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'locked' },
    })
    expect(wrapper.find('.wizard-step-card').classes()).toContain('wizard-step-card--locked')
  })

  it('shows status badge text', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'completed', badge: '✓ 已完成' },
    })
    expect(wrapper.text()).toContain('✓ 已完成')
  })

  it('renders footer slot', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
      slots: { footer: '<button class="footer-btn">下一步</button>' },
    })
    expect(wrapper.find('.footer-btn').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/WizardStepCard.test.ts 2>&1 | tail -5`
Expected: FAIL.

- [ ] **Step 3: Write the component**

Create `src/components/wizard/WizardStepCard.vue`:

```vue
<template>
  <section
    class="wizard-step-card"
    :class="{
      'wizard-step-card--active': status === 'active',
      'wizard-step-card--locked': status === 'locked',
    }"
  >
    <div class="wizard-step-card__header">
      <div class="wizard-step-card__icon">{{ icon }}</div>
      <div class="wizard-step-card__titles">
        <h3 class="wizard-step-card__title">{{ title }}</h3>
        <p class="wizard-step-card__desc">{{ description }}</p>
      </div>
      <span v-if="badge" class="wizard-step-card__badge" :class="`wizard-step-card__badge--${status}`">{{ badge }}</span>
    </div>

    <div class="wizard-step-card__body">
      <slot />
    </div>

    <div v-if="$slots.footer" class="wizard-step-card__footer">
      <slot name="footer" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
  icon: string
  status: 'completed' | 'active' | 'locked'
  badge?: string
}>()
</script>

<style scoped>
.wizard-step-card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: var(--space-card-padding);
  margin-bottom: var(--space-section-gap);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-md);
  transition: opacity var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal);
}
.wizard-step-card--active {
  border: 2px solid var(--color-primary-lighter);
  box-shadow: var(--shadow-active);
}
.wizard-step-card--locked {
  opacity: 0.55;
  pointer-events: none;
}
.wizard-step-card__header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 16px;
}
.wizard-step-card__icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.wizard-step-card__titles {
  flex: 1;
}
.wizard-step-card__title {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--color-text);
}
.wizard-step-card__desc {
  margin: 1px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.wizard-step-card__badge {
  font-size: var(--font-size-xs);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  flex-shrink: 0;
}
.wizard-step-card__badge--completed {
  color: var(--color-success);
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
}
.wizard-step-card__badge--active {
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-border);
}
.wizard-step-card__footer {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/WizardStepCard.test.ts 2>&1 | tail -10`
Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/wizard/WizardStepCard.vue tests/components/WizardStepCard.test.ts
git commit -m "feat: add WizardStepCard component with three visual states"
```

---

### Task 6: AiChatPanel Component

**Files:**
- Create: `src/components/wizard/AiChatPanel.vue`
- Create: `tests/components/AiChatPanel.test.ts`

Right-side collapsible AI assistant panel with message list, quick actions, and a chat input.

- [ ] **Step 1: Write the test**

Create `tests/components/AiChatPanel.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiChatPanel from '../../src/components/wizard/AiChatPanel.vue'

describe('AiChatPanel', () => {
  it('renders the AI panel title', () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    expect(wrapper.text()).toContain('AI 助手')
  })

  it('renders messages correctly', () => {
    const messages = [
      { role: 'ai' as const, content: 'Hello, I am AI' },
      { role: 'user' as const, content: 'Help me' },
    ]
    const wrapper = mount(AiChatPanel, {
      props: { messages, quickActions: [], visible: true },
    })
    expect(wrapper.text()).toContain('Hello, I am AI')
    expect(wrapper.text()).toContain('Help me')
  })

  it('renders quick action buttons', () => {
    const actions = ['AI 生成 SQL', '自动添加列映射']
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: actions, visible: true },
    })
    expect(wrapper.text()).toContain('AI 生成 SQL')
    expect(wrapper.text()).toContain('自动添加列映射')
  })

  it('emits send when typing and clicking send', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    const input = wrapper.find('input')
    await input.setValue('Generate SQL')
    await wrapper.find('.ai-panel__send-btn').trigger('click')
    expect(wrapper.emitted('send')).toBeTruthy()
    expect(wrapper.emitted('send')![0]).toEqual(['Generate SQL'])
  })

  it('emits quickAction when a quick action is clicked', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: ['AI 生成 SQL'], visible: true },
    })
    await wrapper.find('.ai-panel__quick-action').trigger('click')
    expect(wrapper.emitted('quickAction')).toBeTruthy()
    expect(wrapper.emitted('quickAction')![0]).toEqual(['AI 生成 SQL'])
  })

  it('hides when visible is false', () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: false },
    })
    expect(wrapper.find('.ai-panel').exists()).toBe(false)
  })

  it('emits toggle when collapse button is clicked', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    await wrapper.find('.ai-panel__collapse').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/AiChatPanel.test.ts 2>&1 | tail -5`
Expected: FAIL.

- [ ] **Step 3: Write the component**

Create `src/components/wizard/AiChatPanel.vue`:

```vue
<template>
  <aside v-if="visible" class="ai-panel">
    <div class="ai-panel__header">
      <div class="ai-panel__title">
        <span class="ai-panel__title-icon">⚡</span>
        <span>AI 助手</span>
      </div>
      <button class="ai-panel__collapse" @click="$emit('toggle')">−</button>
    </div>

    <div class="ai-panel__messages" ref="messagesEl">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="ai-panel__bubble"
        :class="msg.role === 'ai' ? 'ai-panel__bubble--ai' : 'ai-panel__bubble--user'"
      >
        <div class="ai-panel__bubble-content" v-html="sanitize(msg.content)" />
        <div v-if="msg.code" class="ai-panel__code-block">
          <pre>{{ msg.code }}</pre>
        </div>
      </div>

      <div v-if="quickActions.length" class="ai-panel__actions">
        <p class="ai-panel__actions-label">快捷操作</p>
        <button
          v-for="action in quickActions"
          :key="action"
          class="ai-panel__quick-action"
          @click="$emit('quickAction', action)"
        >› {{ action }}</button>
      </div>
    </div>

    <div class="ai-panel__input">
      <span>💬</span>
      <input
        v-model="inputText"
        placeholder="向 AI 提问..."
        @keyup.enter="sendMessage"
      />
      <button class="ai-panel__send-btn" @click="sendMessage">发送</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import DOMPurify from 'dompurify'

export interface ChatMessage {
  role: 'ai' | 'user'
  content: string
  code?: string
}

defineProps<{
  visible: boolean
  messages: ChatMessage[]
  quickActions: string[]
}>()

const emit = defineEmits<{
  send: [text: string]
  quickAction: [action: string]
  toggle: []
}>()

const inputText = ref('')
const messagesEl = ref<HTMLElement>()

function sanitize(html: string): string {
  return DOMPurify.sanitize(html)
}

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}

watch(() => ({}), () => {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
})
</script>

<style scoped>
.ai-panel {
  width: var(--ai-panel-width);
  background: var(--color-surface);
  border-left: 1px solid var(--color-primary-border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal);
}
.ai-panel__header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-primary-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-panel__title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text);
}
.ai-panel__title-icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.ai-panel__collapse {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--color-text-muted);
  cursor: pointer;
}
.ai-panel__messages {
  flex: 1;
  padding: 12px 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-panel__bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: var(--font-size-xs);
  line-height: 1.5;
}
.ai-panel__bubble--ai {
  align-self: flex-start;
  background: linear-gradient(135deg, var(--color-primary-bg), #ccfbf1);
  color: var(--color-primary);
  border-radius: 12px 12px 12px 3px;
}
.ai-panel__bubble--user {
  align-self: flex-end;
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  border-radius: 12px 12px 3px 12px;
}
.ai-panel__code-block {
  margin-top: 6px;
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-family: monospace;
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  overflow-x: auto;
}
.ai-panel__actions {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.ai-panel__actions-label {
  margin: 0 0 6px;
  font-size: 9px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.ai-panel__quick-action {
  display: block;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  cursor: pointer;
  padding: 2px 0;
  width: 100%;
  text-align: left;
}
.ai-panel__quick-action:hover {
  text-decoration: underline;
}
.ai-panel__input {
  padding: 10px 14px;
  border-top: 1px solid var(--color-primary-border);
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin: 8px 12px 12px;
  border: 1px solid var(--color-border-light);
}
.ai-panel__input input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: var(--font-size-xs);
  color: var(--color-text);
}
.ai-panel__input input::placeholder {
  color: var(--color-text-muted);
}
.ai-panel__send-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: var(--font-size-xs);
  font-weight: 500;
  cursor: pointer;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/AiChatPanel.test.ts 2>&1 | tail -10`
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/wizard/AiChatPanel.vue tests/components/AiChatPanel.test.ts
git commit -m "feat: add AiChatPanel component for conversational AI interaction"
```

---

### Task 7: Redesign HomeView

**Files:**
- Modify: `src/views/HomeView.vue`

Redesign the homepage with a hero section (badge, title, CTA, prompt chips) and redesigned config list cards. The existing logic (load, delete, execute, menu) stays, only template and styles change.

- [ ] **Step 1: Verify existing tests pass before changes**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run 2>&1 | tail -5`
Expected: All existing tests pass.

- [ ] **Step 2: Rewrite the template and styles**

Replace `src/views/HomeView.vue`:

```vue
<template>
  <div class="home">
    <!-- Nav -->
    <nav class="home__nav">
      <div class="home__nav-brand">
        <span class="home__logo">⚡</span>
        <span class="home__brand">ConfigForge</span>
      </div>
      <div class="home__nav-links">
        <span class="home__nav-link home__nav-link--active">首页</span>
        <router-link to="/settings" class="home__nav-link">设置</router-link>
        <button class="home__theme-toggle" @click="toggleTheme" :title="isDark ? '切换到浅色模式' : '切换到暗色模式'">
          {{ isDark ? '☀' : '☾' }}
        </button>
      </div>
    </nav>

    <!-- Hero -->
    <section class="home__hero">
      <span class="home__hero-badge">⚡ AI 驱动的数据流水线配置工具</span>
      <h1 class="home__hero-title">
        用自然语言描述需求<br>
        <span class="home__hero-gradient">AI 自动生成配置</span>
      </h1>
      <p class="home__hero-subtitle">
        不需要懂 SQL 或 YAML。上传文件，描述你想做什么，AI 完成剩下的工作。
      </p>
      <div class="home__hero-cta">
        <NButton type="primary" size="large" class="btn-primary" @click="startNewConfig">
          ✏ 开始新配置
        </NButton>
        <NButton size="large" class="btn-secondary" @click="router.push('/settings')">
          📖 使用指南
        </NButton>
      </div>
      <div class="home__prompts">
        <p class="home__prompts-label">试试这样说</p>
        <div class="home__prompts-chips">
          <span class="home__prompt-chip" @click="startNewConfig">合并两个 Excel 表</span>
          <span class="home__prompt-chip" @click="startNewConfig">CSV 数据过滤导出</span>
          <span class="home__prompt-chip" @click="startNewConfig">多表关联汇总统计</span>
        </div>
      </div>
    </section>

    <!-- Config List -->
    <section class="home__configs">
      <div class="home__configs-header">
        <h2 class="home__configs-title">最近配置</h2>
        <NTag v-if="configs.length" size="small" :bordered="false" class="home__config-count">{{ configs.length }} 个配置</NTag>
      </div>

      <NSkeleton v-if="loading" text :repeat="3" />

      <NAlert v-else-if="error" type="error" :title="error" />

      <!-- Empty state -->
      <div v-else-if="configs.length === 0" class="home__empty">
        <span class="home__empty-icon">🚀</span>
        <p class="home__empty-title">开始你的第一个配置</p>
        <p class="home__empty-desc">点击上方按钮，用自然语言描述你的数据需求</p>
      </div>

      <!-- Config cards -->
      <div v-else class="home__config-list">
        <div
          v-for="cfg in configs"
          :key="cfg.id"
          class="home__config-card"
        >
          <div class="home__config-card-left" @click="onLoadConfig(cfg.id)">
            <span class="home__config-card-icon">📋</span>
            <div class="home__config-card-info">
              <span class="home__config-card-name">{{ cfg.sceneName }}</span>
              <span class="home__config-card-meta">
                <span>{{ cfg.version }}</span>
                <span>{{ cfg.inputCount }} 个数据源</span>
                <span>{{ cfg.outputType }}</span>
                <span>{{ formatTime(cfg.updatedAt) }}</span>
              </span>
            </div>
          </div>
          <div class="home__config-card-right">
            <span class="home__executable-badge" v-if="cfg.inputCount > 0">✓ 可执行</span>
            <NDropdown trigger="click" :options="getMenuOptions(cfg)" @select="(key: string) => onMenuSelect(key, cfg)">
              <NButton text size="tiny" class="home__menu-btn">···</NButton>
            </NDropdown>
          </div>
        </div>
      </div>
    </section>

    <!-- Delete Modal -->
    <NModal v-model:show="deleteModalVisible" preset="card" title="确认删除" style="max-width: 400px">
      <p class="text-sm" style="color:var(--color-text-secondary)">
        确定要删除配置 "<strong>{{ deletingConfig?.sceneName }}</strong>" 吗？此操作不可撤销。
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <NButton @click="deleteModalVisible = false">取消</NButton>
          <NButton type="error" :loading="deleting" @click="onConfirmDelete">删除</NButton>
        </div>
      </template>
    </NModal>

    <!-- Execute Modal -->
    <ExecuteConfigModal
      :visible="executeModalVisible"
      :config="executingConfig"
      @close="executeModalVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigApi } from '../composables/useConfigApi'
import { useWizardStore } from '../stores/wizard'
import { useTheme } from '../composables/useTheme'
import type { SavedConfig } from '../types/wizard'
import { NButton, NSkeleton, NAlert, NModal, NTag, NDropdown, useMessage } from 'naive-ui'
import ExecuteConfigModal from '../components/ExecuteConfigModal.vue'

const router = useRouter()
const store = useWizardStore()
const message = useMessage()
const { listConfigs, loadConfigState, deleteConfig, downloadConfigYaml } = useConfigApi()
const { isDark, toggleTheme } = useTheme()

const loading = ref(true)
const error = ref('')
const configs = ref<SavedConfig[]>([])
const deleteModalVisible = ref(false)
const deletingConfig = ref<SavedConfig | null>(null)
const deleting = ref(false)
const executeModalVisible = ref(false)
const executingConfig = ref<SavedConfig | null>(null)

onMounted(async () => {
  configs.value = await listConfigs()
  loading.value = false
})

function startNewConfig() {
  store.resetAll()
  router.push('/config/new')
}

async function onLoadConfig(id: string) {
  const state = await loadConfigState(id)
  if (state) {
    store.loadFromConfigState(state)
    router.push('/step/5')
  }
}

async function onDownloadYaml(id: string) {
  await downloadConfigYaml(id)
}

function promptDelete(cfg: SavedConfig) {
  deletingConfig.value = cfg
  deleteModalVisible.value = true
}

async function onConfirmDelete() {
  if (!deletingConfig.value) return
  deleting.value = true
  const ok = await deleteConfig(deletingConfig.value.id)
  if (ok) {
    message.success('已删除')
    configs.value = configs.value.filter(c => c.id !== deletingConfig.value!.id)
    deleteModalVisible.value = false
    deletingConfig.value = null
  } else {
    message.error('删除失败')
  }
  deleting.value = false
}

function getMenuOptions(cfg: SavedConfig) {
  return [
    { label: '下载 YAML', key: 'download' },
    { label: '执行', key: 'execute' },
    { label: '删除', key: 'delete' },
  ]
}

function onMenuSelect(key: string, cfg: SavedConfig) {
  if (key === 'download') onDownloadYaml(cfg.id)
  else if (key === 'execute') openExecuteModal(cfg)
  else if (key === 'delete') promptDelete(cfg)
}

function openExecuteModal(cfg: SavedConfig) {
  executingConfig.value = cfg
  executeModalVisible.value = true
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return iso.slice(0, 10)
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: var(--color-bg);
}
.home__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 54px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-primary-border);
}
.home__nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.home__logo {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}
.home__brand {
  font-weight: 800;
  font-size: 16px;
  color: var(--color-text);
}
.home__nav-links {
  display: flex;
  align-items: center;
  gap: 18px;
}
.home__nav-link {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  text-decoration: none;
}
.home__nav-link--active,
.home__nav-link:hover {
  color: var(--color-primary);
  font-weight: 600;
}
.home__theme-toggle {
  background: none;
  border: none;
  font-size: 17px;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 0;
}

/* Hero */
.home__hero {
  text-align: center;
  padding: 56px 24px 44px;
  background: linear-gradient(180deg, var(--color-primary-bg) 0%, var(--color-bg) 100%);
}
.home__hero-badge {
  display: inline-block;
  background: #ccfbf1;
  padding: 5px 14px;
  border-radius: 16px;
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  font-weight: 500;
  margin-bottom: 16px;
}
.home__hero-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--color-text);
  line-height: 1.25;
}
.home__hero-gradient {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.home__hero-subtitle {
  margin: 14px auto 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  max-width: 460px;
  line-height: 1.6;
}
.home__hero-cta {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 10px;
}
.home__prompts {
  margin-top: 26px;
}
.home__prompts-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  font-weight: 600;
}
.home__prompts-chips {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
.home__prompt-chip {
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  padding: 7px 14px;
  border-radius: 16px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}
.home__prompt-chip:hover {
  border-color: var(--color-primary-lighter);
  color: var(--color-primary);
}

/* Configs */
.home__configs {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 24px 40px;
}
.home__configs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.home__configs-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}
.home__config-count {
  font-size: var(--font-size-xs);
}

/* Empty */
.home__empty {
  border: 2px dashed var(--color-primary-border);
  border-radius: var(--radius-lg);
  padding: 36px;
  text-align: center;
  background: var(--color-primary-bg);
}
.home__empty-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 10px;
}
.home__empty-title {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-primary);
  font-weight: 600;
}
.home__empty-desc {
  margin: 4px 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-primary-lighter);
}

/* Config Cards */
.home__config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.home__config-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast);
}
.home__config-card:hover {
  border-color: var(--color-primary-border);
}
.home__config-card-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.home__config-card-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}
.home__config-card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.home__config-card-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}
.home__config-card-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 1px;
  display: flex;
  gap: 10px;
}
.home__config-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.home__executable-badge {
  font-size: var(--font-size-xs);
  background: var(--color-success-bg);
  color: var(--color-success);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.home__menu-btn {
  font-size: 16px;
  color: var(--color-text-muted);
}

/* Override Naive UI button styles for the hero */
:deep(.btn-primary) {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)) !important;
  border: none !important;
  box-shadow: var(--shadow-button) !important;
  border-radius: var(--radius-md) !important;
  font-weight: 600 !important;
}
:deep(.btn-secondary) {
  border: 1px solid var(--color-primary-border) !important;
  color: var(--color-primary) !important;
  border-radius: var(--radius-md) !important;
  font-weight: 500 !important;
}
</style>
```

- [ ] **Step 3: Run tests to verify**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run 2>&1 | tail -5`
Expected: All existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/views/HomeView.vue
git commit -m "feat: redesign HomeView with hero section, prompt chips, and styled config cards"
```

---

### Task 8: Create ConfigWizardView (Single Page Wizard)

**Files:**
- Create: `src/views/ConfigWizardView.vue`

The core of the redesign — a single-page scrollable wizard replacing the 5 separate step routes. Uses WizardProgress, WizardStepCard, AiChatPanel, and AiInlineTip.

- [ ] **Step 1: Write the view**

Create `src/views/ConfigWizardView.vue`:

```vue
<template>
  <div class="wizard">
    <!-- Top Nav -->
    <nav class="wizard__nav">
      <div class="wizard__nav-brand">
        <span class="wizard__logo">⚡</span>
        <span class="wizard__brand">ConfigForge</span>
        <span class="wizard__new-badge">新配置</span>
      </div>
      <div class="wizard__nav-right">
        <router-link to="/" class="wizard__nav-link">我的配置</router-link>
        <router-link to="/settings" class="wizard__nav-link">设置</router-link>
        <label class="wizard__panel-toggle">
          <span class="wizard__panel-toggle-label">AI 面板</span>
          <button
            class="wizard__toggle-switch"
            :class="{ 'wizard__toggle-switch--on': aiPanelVisible }"
            @click="aiPanelVisible = !aiPanelVisible"
          />
        </label>
        <button class="wizard__theme-btn" @click="toggleTheme">
          {{ isDark ? '☀' : '☾' }}
        </button>
      </div>
    </nav>

    <!-- Main Content Area -->
    <div class="wizard__main">
      <!-- Scrollable Step Area -->
      <div class="wizard__steps" ref="scrollEl" @scroll="onScroll">
        <WizardProgress :steps="progressSteps" @step-click="scrollToStep" />

        <!-- Step 1: Scene Info -->
        <WizardStepCard
          ref="step1El"
          title="场景信息"
          description="告诉 ConfigForge 你想做什么"
          icon="🎨"
          :status="stepStatus(1)"
          :badge="stepBadge(1)"
        >
          <div class="wizard__form-grid">
            <div>
              <label class="wizard__label">场景名称 <span class="wizard__required">*</span></label>
              <input
                v-model="store.scene.name"
                class="wizard__input"
                :class="{ 'wizard__input--focus': currentStep === 1 }"
                placeholder="如：客户订单汇总"
              />
            </div>
            <div>
              <label class="wizard__label">版本</label>
              <input v-model="store.scene.version" class="wizard__input" placeholder="1.0" />
            </div>
          </div>
          <div style="margin-top:10px">
            <label class="wizard__label">描述</label>
            <textarea
              v-model="store.scene.description"
              class="wizard__textarea"
              placeholder="描述这个流水线的用途..."
              rows="2"
            />
          </div>
          <AiInlineTip
            v-if="store.scene.name"
            message="AI 已识别场景信息。继续添加数据源，AI 将帮你完成后续配置。"
          />

          <template #footer>
            <NButton class="btn-primary" @click="completeStep(1)">保存并继续 ↓</NButton>
          </template>
        </WizardStepCard>

        <!-- Step 2: Data Sources -->
        <WizardStepCard
          ref="step2El"
          title="数据源"
          description="上传文件，AI 自动解析列结构"
          icon="📂"
          :status="stepStatus(2)"
          :badge="stepBadge(2)"
        >
          <InputSourceList @file-ready="onFileReady" />

          <AiInlineTip
            v-if="currentStep === 2 && store.inputs.length > 0"
            message="文件上传成功！AI 将自动分析列类型。点击右侧面板查看分析结果。"
            show-action
            action-label="查看分析"
            @action="aiPanelVisible = true"
          />

          <template #footer>
            <div class="wizard__footer-row">
              <NButton text @click="completeStep(2)">跳过</NButton>
              <NButton class="btn-primary" @click="completeStep(2)">保存并继续 ↓</NButton>
            </div>
          </template>
        </WizardStepCard>

        <!-- Step 3: SQL Processing -->
        <WizardStepCard
          ref="step3El"
          title="数据转换"
          description="AI 根据数据源自动生成 SQL"
          icon="🧪"
          :status="stepStatus(3)"
          :badge="stepBadge(3)"
        >
          <SqlEditorTab />

          <template #footer>
            <div class="wizard__footer-row">
              <NButton text @click="completeStep(3)">跳过</NButton>
              <NButton class="btn-primary" @click="completeStep(3)">保存并继续 ↓</NButton>
            </div>
          </template>
        </WizardStepCard>

        <!-- Step 4: Output Config -->
        <WizardStepCard
          ref="step4El"
          title="输出定义"
          description="列映射与格式设置"
          icon="📋"
          :status="stepStatus(4)"
          :badge="stepBadge(4)"
        >
          <OutputConfigTab />

          <template #footer>
            <div class="wizard__footer-row">
              <NButton text @click="completeStep(4)">跳过</NButton>
              <NButton class="btn-primary" @click="completeStep(4)">保存并继续 ↓</NButton>
            </div>
          </template>
        </WizardStepCard>

        <!-- Step 5: Export -->
        <WizardStepCard
          ref="step5El"
          title="导出 YAML"
          description="预览与下载配置"
          icon="💾"
          :status="stepStatus(5)"
          :badge="stepBadge(5)"
        >
          <YamlPreview ref="yamlRef" />
          <ExportActions />

          <template #footer>
            <div class="wizard__footer-row">
              <NButton class="btn-primary" @click="router.push('/')">完成 ✓</NButton>
            </div>
          </template>
        </WizardStepCard>

        <div class="wizard__bottom-spacer" />
      </div>

      <!-- AI Panel -->
      <AiChatPanel
        :visible="aiPanelVisible"
        :messages="aiMessages"
        :quick-actions="aiQuickActions"
        @send="onAiSend"
        @quick-action="onAiQuickAction"
        @toggle="aiPanelVisible = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { useTheme } from '../composables/useTheme'
import { NButton } from 'naive-ui'
import WizardProgress from '../components/wizard/WizardProgress.vue'
import WizardStepCard from '../components/wizard/WizardStepCard.vue'
import AiChatPanel from '../components/wizard/AiChatPanel.vue'
import type { ChatMessage } from '../components/wizard/AiChatPanel.vue'
import AiInlineTip from '../components/wizard/AiInlineTip.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'

const router = useRouter()
const store = useWizardStore()
const { isDark, toggleTheme } = useTheme()

const currentStep = ref(1)
const aiPanelVisible = ref(false)
const scrollEl = ref<HTMLElement>()
const step1El = ref<InstanceType<typeof WizardStepCard>>()
const step2El = ref<InstanceType<typeof WizardStepCard>>()
const step3El = ref<InstanceType<typeof WizardStepCard>>()
const step4El = ref<InstanceType<typeof WizardStepCard>>()
const step5El = ref<InstanceType<typeof WizardStepCard>>()
const yamlRef = ref<InstanceType<typeof YamlPreview>>()

const aiMessages = ref<ChatMessage[]>([
  { role: 'ai', content: '你好！我是 AI 助手。上传数据文件后，我会帮你分析列结构、生成 SQL 和列映射。随时向我提问！' },
])

const aiQuickActions = [
  'AI 分析列',
  'AI 生成 SQL',
  'AI 自动映射',
  '生成场景描述',
]

function stepStatus(step: number): 'completed' | 'active' | 'locked' {
  if (step < currentStep.value) return 'completed'
  if (step === currentStep.value) return 'active'
  return 'locked'
}

function stepBadge(step: number): string {
  if (step < currentStep.value) return '✓ 已完成'
  if (step === currentStep.value) return '⟳ 当前步骤'
  return '🔒 待解锁'
}

const progressSteps = computed(() => [
  { label: '场景', status: stepStatus(1) },
  { label: '数据源', status: stepStatus(2) },
  { label: '处理', status: stepStatus(3) },
  { label: '输出', status: stepStatus(4) },
  { label: '导出', status: stepStatus(5) },
])

const stepRefs: Record<number, any> = {
  1: step1El,
  2: step2El,
  3: step3El,
  4: step4El,
  5: step5El,
}

function completeStep(step: number) {
  currentStep.value = Math.min(step + 1, 5)
  scrollToStep(currentStep.value)
}

function scrollToStep(step: number) {
  const el = stepRefs[step] as any
  if (el?.$el) {
    el.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  currentStep.value = step
}

function onScroll() {
  // Simplified: Intersection Observer would be more robust in production
  // For now, steps advance via the "保存并继续" button
}

function onFileReady(_fileId: string) {
  aiMessages.value.push({
    role: 'ai',
    content: '文件上传成功！我正在分析列结构...',
  })
}

function onAiSend(text: string) {
  aiMessages.value.push({ role: 'user', content: text })
  aiMessages.value.push({
    role: 'ai',
    content: '收到！我正在进行 AI 分析，请稍候...',
  })
}

function onAiQuickAction(action: string) {
  aiMessages.value.push({ role: 'user', content: action })
  aiMessages.value.push({
    role: 'ai',
    content: `正在执行"${action}"...结果将显示在主面板中。`,
  })
}

onMounted(() => {
  store.currentStep = 1
})
</script>

<style scoped>
.wizard {
  min-height: 100vh;
  background: var(--color-bg);
}
.wizard__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 50px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-primary-border);
}
.wizard__nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.wizard__logo {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.wizard__brand {
  font-weight: 800;
  font-size: 15px;
  color: var(--color-text);
}
.wizard__new-badge {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  background: var(--color-primary-bg);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.wizard__nav-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.wizard__nav-link {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  text-decoration: none;
}
.wizard__nav-link:hover {
  color: var(--color-primary);
}
.wizard__panel-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}
.wizard__panel-toggle-label {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  font-weight: 500;
}
.wizard__toggle-switch {
  width: 32px;
  height: 18px;
  background: var(--color-primary-border);
  border: none;
  border-radius: 9px;
  position: relative;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.wizard__toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: var(--color-primary);
  border-radius: 50%;
  transition: transform var(--transition-fast);
}
.wizard__toggle-switch--on {
  background: var(--color-primary-lighter);
}
.wizard__toggle-switch--on::after {
  transform: translateX(14px);
}
.wizard__theme-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 0;
}
.wizard__main {
  display: flex;
  flex: 1;
}
.wizard__steps {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  background: linear-gradient(180deg, var(--color-primary-bg) 0%, var(--color-bg) 100%);
}
.wizard__form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.wizard__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  display: block;
  margin-bottom: 4px;
}
.wizard__required {
  color: var(--color-error);
}
.wizard__input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 9px 12px;
  font-size: var(--font-size-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.wizard__input--focus {
  border: 2px solid var(--color-primary-lighter);
  background: var(--color-primary-bg);
}
.wizard__input:focus {
  border-color: var(--color-primary-lighter);
}
.wizard__textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 9px 12px;
  font-size: var(--font-size-sm);
  outline: none;
  resize: vertical;
  background: var(--color-surface);
  color: var(--color-text);
  font-family: var(--font-family);
}
.wizard__textarea:focus {
  border-color: var(--color-primary-lighter);
}
.wizard__footer-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}
.wizard__bottom-spacer {
  height: 64px;
}

:deep(.btn-primary) {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  font-weight: 600 !important;
  box-shadow: var(--shadow-button) !important;
}
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: No new errors introduced.

- [ ] **Step 3: Verify build succeeds**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite build 2>&1 | tail -5`
Expected: Build completes.

- [ ] **Step 4: Commit**

```bash
git add src/views/ConfigWizardView.vue
git commit -m "feat: add ConfigWizardView with single-page scroll layout and embedded AI"
```

---

### Task 9: Update Router

**Files:**
- Modify: `src/router/index.ts`

Add `/config/new` route for the new wizard. Add redirects from old `/step/:n` routes to maintain backward compatibility.

- [ ] **Step 1: Update the router**

Replace `src/router/index.ts`:

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    {
      path: '/config/new',
      name: 'config-new',
      component: () => import('../views/ConfigWizardView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsPage.vue'),
    },
    // Backward compatibility: redirect old step routes
    {
      path: '/step/:step(\\d)',
      redirect: () => '/config/new',
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ],
})

export default router
```

- [ ] **Step 2: Verify build succeeds**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite build 2>&1 | tail -5`
Expected: Build completes.

- [ ] **Step 3: Commit**

```bash
git add src/router/index.ts
git commit -m "feat: add /config/new route, redirect /step/:n for backward compatibility"
```

---

### Task 10: Update App.vue Theme Overrides

**Files:**
- Modify: `src/App.vue`

Update Naive UI theme overrides to match the Teal design system. Initialize the theme composable. Add a dark theme config provider.

- [ ] **Step 1: Update App.vue**

Replace `src/App.vue`:

```vue
<template>
  <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NModalProvider>
        <NDialogProvider>
          <div class="app-shell">
            <router-view />
          </div>
        </NDialogProvider>
      </NModalProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  NConfigProvider,
  NMessageProvider,
  NModalProvider,
  NDialogProvider,
  darkTheme,
} from 'naive-ui'
import { useTheme } from './composables/useTheme'
import 'highlight.js/lib/languages/yaml'

const { isDark, initTheme } = useTheme()
initTheme()

const naiveTheme = computed(() => isDark.value ? darkTheme : undefined)

const themeOverrides = {
  common: {
    primaryColor: '#0d9488',
    primaryColorHover: '#14b8a6',
    primaryColorPressed: '#0f766e',
    primaryColorSuppl: '#14b8a6',
    borderRadius: '8px',
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  Button: {
    borderRadiusMedium: '8px',
    colorPrimary: '#0d9488',
    colorPrimaryHover: '#14b8a6',
    colorPrimaryPressed: '#0f766e',
  },
  Card: {
    borderRadius: '14px',
    color: '#ffffff',
  },
  Steps: {
    stepHeaderFontSize: '13px',
    headerTextColorProcess: '#0d9488',
    headerTextColorWait: '#94a3b8',
    headerTextColorFinish: '#64748b',
    indicatorColorProcess: '#0d9488',
    indicatorBorderColorProcess: '#0f766e',
  },
  Tag: {
    borderRadius: '6px',
  },
}
</script>

<style>
.app-shell {
  min-height: 100vh;
}
</style>
```

- [ ] **Step 2: Verify build succeeds**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite build 2>&1 | tail -5`
Expected: Build completes.

- [ ] **Step 3: Commit**

```bash
git add src/App.vue
git commit -m "feat: update Naive UI theme overrides to Teal, add dark theme support"
```

---

### Task 11: Final Integration & Cleanup

**Files:**
- Modify: `src/views/SettingsPage.vue` (minor style touch-up)
- No deletions needed (old step views kept for reference)

Final verification pass: run full test suite, type-check, and build.

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run 2>&1`
Expected: All tests pass (existing + new).

- [ ] **Step 2: Run TypeScript check**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1`
Expected: No type errors.

- [ ] **Step 3: Run production build**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite build 2>&1`
Expected: Build succeeds without warnings.

- [ ] **Step 4: Check the dev server**

Run: `cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vite --host 2>&1 &`
Start dev server and verify pages load correctly at `/`, `/config/new`, `/settings`.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete ConfigForge frontend redesign with Teal theme and single-page wizard"
```
