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
  gap: 4px;
  padding: 12px 16px;
  margin-bottom: 10px;
  background: var(--color-surface-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 10;
}
.wizard-progress__step {
  flex: 1;
  text-align: center;
  padding: 6px 4px;
  border-radius: 6px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: all 0.25s;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.wizard-progress__step--completed { color: var(--color-success); cursor: pointer; }
.wizard-progress__step--active { background: var(--color-primary-bg); color: var(--color-primary); cursor: pointer; }
.wizard-progress__step--locked { cursor: default; }
.wizard-progress__number { display: none; }
.wizard-progress__label { font-size: 12px; white-space: nowrap; }
.wizard-progress__step--locked .wizard-progress__label { color: var(--color-text-muted); }
.wizard-progress__badge {
  position: absolute; top: -6px; right: -6px;
  min-width: 18px; height: 18px; padding: 0 4px; border-radius: 9px;
  background: var(--color-error); color: #fff; font-size: 10px; font-weight: 700;
  line-height: 18px; text-align: center;
}
.wizard-progress__connector {
  width: 16px; height: 2px; background: var(--color-border-light); align-self: center; flex-shrink: 0;
}
.wizard-progress__connector--done { background: var(--color-primary-light); }

@media (max-width: 767px) {
  .wizard-progress { padding: 8px; gap: 2px; }
  .wizard-progress__label { font-size: 10px; }
  .wizard-progress__badge { display: none; }
  .wizard-progress__connector { width: 8px; }
}
</style>
