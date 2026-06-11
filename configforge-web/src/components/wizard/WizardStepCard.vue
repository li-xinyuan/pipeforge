<template>
  <section
    class="wizard-step-card"
    :class="{
      'wizard-step-card--active': status === 'active',
      'wizard-step-card--completed': status === 'completed',
      'wizard-step-card--locked': status === 'locked',
    }"
  >
    <div class="wizard-step-card__header">
      <div
        class="wizard-step-card__icon"
        :style="iconBg ? { background: iconBg } : {}"
        aria-hidden="true"
      >{{ icon }}</div>
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

    <!-- Locked overlay -->
    <div v-if="status === 'locked'" class="wizard-step-card__lock-overlay">
      <span class="wizard-step-card__lock-text">请先完成上一步</span>
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
  iconBg?: string
}>()
</script>

<style scoped>
.wizard-step-card {
  position: relative;
  z-index: 0;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: var(--space-card-padding);
  margin-bottom: var(--space-section-gap);
  border: 2px solid transparent;
  box-shadow: var(--shadow-md);
  scroll-margin-top: 72px;
  transition: opacity var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal);
}
.wizard-step-card--active {
  border: 2px solid var(--color-primary-lighter);
  box-shadow: var(--shadow-active);
}
.wizard-step-card--completed {
  border: 1px solid var(--color-primary-border);
  opacity: 0.85;
}
.wizard-step-card--locked {
  opacity: 0.35;
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
  border-radius: inherit;
  pointer-events: none;
}
.wizard-step-card__lock-overlay::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--color-surface);
  opacity: 0.6;
  border-radius: inherit;
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
