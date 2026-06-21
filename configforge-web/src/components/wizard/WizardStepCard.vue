<template>
  <section
    class="wizard-step-card"
    :class="{
      'wizard-step-card--active': status === 'active',
      'wizard-step-card--completed': status === 'completed',
      'wizard-step-card--locked': status === 'locked',
      'wizard-step-card--collapsed': collapsed,
    }"
    tabindex="-1"
    :data-step="step"
  >
    <div
      class="wizard-step-card__header"
      :class="{ 'wizard-step-card__header--clickable': status === 'completed' }"
      @click="onHeaderClick"
    >
      <div
        class="wizard-step-card__icon"
        :style="iconBg ? { background: iconBg } : {}"
        aria-hidden="true"
      >{{ icon }}</div>
      <div class="wizard-step-card__titles">
        <h3 class="wizard-step-card__title">{{ title }}</h3>
        <p v-if="!collapsed" class="wizard-step-card__desc">{{ description }}</p>
        <p v-else-if="summary" class="wizard-step-card__summary">{{ summary }}</p>
      </div>
      <span v-if="badge" class="wizard-step-card__badge" :class="`wizard-step-card__badge--${status}`">{{ badge }}</span>
      <span v-if="status === 'completed'" class="wizard-step-card__chevron" :class="{ 'wizard-step-card__chevron--up': !collapsed }">▼</span>
    </div>

    <Transition name="wizard-step-card-collapse">
      <div v-if="!collapsed" class="wizard-step-card__body">
        <slot />
      </div>
    </Transition>

    <Transition name="wizard-step-card-collapse">
      <div v-if="!collapsed && $slots.footer" class="wizard-step-card__footer">
        <slot name="footer" />
      </div>
    </Transition>

    <!-- Locked overlay -->
    <div v-if="status === 'locked'" class="wizard-step-card__lock-overlay" aria-hidden="true">
      <span class="wizard-step-card__lock-icon">🔒</span>
      <span class="wizard-step-card__lock-text">请先完成上一步</span>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  title: string
  description: string
  icon: string
  status: 'completed' | 'active' | 'locked'
  badge?: string
  iconBg?: string
  step?: number
  collapsed?: boolean
  summary?: string
}>()

const emit = defineEmits<{
  (e: 'header-click'): void
}>()

function onHeaderClick() {
  if (props.status === 'completed') {
    emit('header-click')
  }
}
</script>

<style scoped>
.wizard-step-card {
  position: relative;
  z-index: 0;
  background: var(--color-surface-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  padding: var(--space-card-padding);
  margin-bottom: var(--space-section-gap);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  scroll-margin-top: 72px;
  transition: all var(--transition-normal);
}
.wizard-step-card:hover { box-shadow: var(--shadow-md); border-color: var(--color-border); }
.wizard-step-card--active {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-active);
}
.wizard-step-card--completed {
  opacity: 0.85;
}
.wizard-step-card--collapsed {
  padding-bottom: calc(var(--space-card-padding) * 0.6);
}
.wizard-step-card--collapsed .wizard-step-card__header {
  margin-bottom: 0;
}
.wizard-step-card--locked {
  opacity: 0.4;
  filter: grayscale(0.3);
}

.wizard-step-card--locked .wizard-step-card__body,
.wizard-step-card--locked .wizard-step-card__footer {
  pointer-events: none;
}
.wizard-step-card__lock-overlay {
  position: absolute;
  z-index: 1;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--color-surface);
  opacity: 0.6;
  border-radius: inherit;
  pointer-events: none;
}
.wizard-step-card__lock-icon {
  font-size: 28px;
  opacity: 0.6;
}
.wizard-step-card__lock-text {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 500;
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
.wizard-step-card__summary {
  margin: 1px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-style: italic;
}
.wizard-step-card__chevron {
  font-size: 10px;
  color: var(--color-text-muted);
  transition: transform 0.25s ease;
  flex-shrink: 0;
  align-self: center;
}
.wizard-step-card__chevron--up {
  transform: rotate(180deg);
}
.wizard-step-card__header--clickable {
  cursor: pointer;
  border-radius: var(--radius-md);
  margin: calc(var(--space-card-padding) * -1);
  margin-bottom: 0;
  padding: var(--space-card-padding);
  transition: background 0.15s ease;
}
.wizard-step-card__header--clickable:hover {
  background: var(--color-surface-hover);
}

/* Collapse transition */
.wizard-step-card-collapse-enter-active,
.wizard-step-card-collapse-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.wizard-step-card-collapse-enter-from,
.wizard-step-card-collapse-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}
.wizard-step-card-collapse-enter-to,
.wizard-step-card-collapse-leave-from {
  opacity: 1;
  max-height: 2000px;
  margin-top: 0;
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
.wizard-step-card__badge--locked {
  color: var(--color-text-muted);
  background: var(--color-border-light);
  border: 1px solid var(--color-border);
}
.wizard-step-card__footer {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* Tablet */
@media (max-width: 1023px) {
  .wizard-step-card {
    padding: 16px;
    border-radius: var(--radius-lg);
    margin-bottom: 14px;
    scroll-margin-top: 60px;
  }
  .wizard-step-card__icon {
    width: 30px;
    height: 30px;
    font-size: 15px;
  }
  .wizard-step-card__title {
    font-size: var(--font-size-base);
  }
}

/* Mobile */
@media (max-width: 767px) {
  .wizard-step-card {
    padding: 14px;
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    scroll-margin-top: 52px;
  }
  .wizard-step-card__header {
    gap: 8px;
    margin-bottom: 12px;
  }
  .wizard-step-card__icon {
    width: 28px;
    height: 28px;
    font-size: 14px;
    border-radius: var(--radius-sm);
  }
  .wizard-step-card__title {
    font-size: var(--font-size-sm);
  }
  .wizard-step-card__desc {
    font-size: 11px;
  }
  .wizard-step-card__badge {
    font-size: 11px;
    padding: 2px 6px;
  }
  .wizard-step-card__footer {
    margin-top: 10px;
  }
}
</style>
