<template>
  <div class="wizard-progress">
    <template v-for="(step, i) in steps" :key="i">
      <div
        :data-step="i + 1"
        class="wizard-progress__step"
        :class="stepClasses(step.status)"
        :role="step.status !== 'locked' ? 'button' : undefined"
        :tabindex="step.status !== 'locked' ? 0 : -1"
        :aria-current="step.status === 'active' ? 'step' : undefined"
        @click="onStepClick(i + 1, step.status)"
        @keydown.enter.prevent="onStepClick(i + 1, step.status)"
        @keydown.space.prevent="onStepClick(i + 1, step.status)"
      >
        <span class="wizard-progress__number">{{ i + 1 }}</span>
        <span class="wizard-progress__label">{{ step.label }}</span>
        <span v-if="step.badge && step.badge > 0" class="wizard-progress__badge" :title="step.hint || ''">{{ step.badge }}</span>
      </div>
      <div
        v-if="i < steps.length - 1"
        class="wizard-progress__connector"
        :class="{ 'wizard-progress__connector--done': step.status === 'completed' }"
        aria-hidden="true"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
export interface StepState {
  label: string
  status: 'completed' | 'active' | 'locked'
  badge?: number
  hint?: string
}

defineProps<{ steps: StepState[] }>()
const emit = defineEmits<{ stepClick: [step: number] }>()

function stepClasses(status: StepState['status']) {
  return {
    'wizard-progress__step--completed': status === 'completed',
    'wizard-progress__step--active': status === 'active',
    'wizard-progress__step--locked': status === 'locked',
  }
}

function onStepClick(step: number, status: StepState['status']) {
  if (status !== 'locked') emit('stepClick', step)
}
</script>

<style scoped>
.wizard-progress {
  display: flex;
  align-items: center;
  padding: 12px 18px;
  background: var(--color-surface-glass, rgba(255, 255, 255, 0.72));
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
  position: relative;
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
  text-shadow: var(--text-shadow-on-gradient);
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
/* badge styles moved to global style.css */
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

/* Tablet */
@media (max-width: 1023px) {
  .wizard-progress {
    padding: 10px 12px;
    border-radius: var(--radius-md);
  }
  .wizard-progress__step {
    gap: 4px;
  }
  .wizard-progress__number {
    width: 24px;
    height: 24px;
  }
  .wizard-progress__label {
    font-size: 11px;
  }
  .wizard-progress__connector {
    width: 12px;
  }
}

/* Mobile */
@media (max-width: 767px) {
  .wizard-progress {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    gap: 6px;
    scrollbar-width: none;
  }
  .wizard-progress::-webkit-scrollbar {
    display: none;
  }
  .wizard-progress__step {
    flex: 0 0 auto;
    gap: 5px;
  }
  .wizard-progress__number {
    width: 22px;
    height: 22px;
    font-size: 11px;
  }
  .wizard-progress__label {
    font-size: 11px;
  }
  .wizard-progress__connector {
    width: 10px;
    flex-shrink: 0;
  }
}
</style>
