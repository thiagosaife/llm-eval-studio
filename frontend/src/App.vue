<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useRunStore } from './stores/run'

const route = useRoute()
const router = useRouter()
const runStore = useRunStore()

// The "Metrics guide" button toggles: open the guide, or — when you're already
// on it — return to wherever you were. We remember the last non-guide page so
// the round-trip lands you back where you left off (falling back to /datasets).
const onGuide = computed(() => route.name === 'guide')
const returnTo = ref('/datasets')
watch(
  () => route.fullPath,
  (path) => {
    if (route.name !== 'guide') returnTo.value = path
  },
  { immediate: true },
)
function toggleGuide() {
  router.push(onGuide.value ? returnTo.value : '/guide')
}

// The lifecycle stepper (doc §2.3): Dataset → Run → Results.
const steps = [
  { n: 1, label: 'Dataset', to: '/datasets' },
  { n: 2, label: 'Run', to: '/run' },
  { n: 3, label: 'Results', to: 'results' },
]
const currentStep = computed(() => (route.meta.step as number) ?? 1)
const resultsTo = computed(() =>
  runStore.currentRun ? `/results/${runStore.currentRun.run_id}` : null,
)
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <RouterLink to="/datasets" class="brand">
        <span class="brand-mark">⬡</span>
        <span>LLM Eval Studio</span>
      </RouterLink>

      <nav class="stepper" aria-label="Evaluation lifecycle">
        <template v-for="(s, i) in steps" :key="s.n">
          <span v-if="i > 0" class="stepper-arrow" aria-hidden="true">→</span>
          <RouterLink
            v-if="s.to !== 'results'"
            :to="s.to"
            class="step"
            :class="{ active: currentStep === s.n, done: currentStep > s.n }"
          >
            <span class="step-num">{{ s.n }}</span>
            <span>{{ s.label }}</span>
          </RouterLink>
          <RouterLink
            v-else-if="resultsTo"
            :to="resultsTo"
            class="step"
            :class="{ active: currentStep === s.n, done: currentStep > s.n }"
          >
            <span class="step-num">{{ s.n }}</span>
            <span>{{ s.label }}</span>
          </RouterLink>
          <span v-else class="step disabled">
            <span class="step-num">{{ s.n }}</span>
            <span>{{ s.label }}</span>
          </span>
        </template>
      </nav>

      <div class="top-tools">
        <RouterLink
          to="/explore"
          class="guide-link"
          :class="{ active: route.name === 'explore' }"
          title="Embedding & dimensionality-reduction explorer"
        >
          <span aria-hidden="true">🔭</span>
          <span>Explore</span>
        </RouterLink>
        <button
          type="button"
          class="guide-link"
          :class="{ active: onGuide }"
          :aria-pressed="onGuide"
          :title="onGuide ? 'Close the guide and go back' : 'Open the metrics guide'"
          @click="toggleGuide"
        >
          <span aria-hidden="true">📖</span>
          <span>Metrics guide</span>
        </button>
      </div>
    </div>
  </header>

  <main class="container">
    <RouterView />
  </main>
</template>

<style scoped>
.topbar {
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  position: sticky;
  top: 0;
  z-index: 10;
}
.topbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--c-text);
}
.brand-mark {
  color: var(--c-primary);
  font-size: 1.25rem;
}
.stepper {
  display: flex;
  align-items: center;
  gap: 6px;
}
.top-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}
.guide-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 550;
  color: var(--c-text-soft);
  border: 1px solid var(--c-border);
}
.guide-link:hover {
  background: var(--c-surface-2);
  color: var(--c-text);
}
.guide-link.active {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-color: #dcdcfb;
}
.stepper-arrow {
  color: var(--c-muted);
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 11px;
  border-radius: 999px;
  color: var(--c-text-soft);
  font-size: 0.9rem;
  font-weight: 500;
}
.step:hover:not(.disabled) {
  background: var(--c-surface-2);
}
.step.active {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  font-weight: 650;
}
.step.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--c-surface-2);
  color: var(--c-text-soft);
  font-size: 0.78rem;
  font-weight: 700;
}
.step.active .step-num {
  background: var(--c-primary);
  color: #fff;
}
.step.done .step-num {
  background: #d7f5e0;
  color: #1c8a4b;
}
@media (max-width: 720px) {
  .step span:not(.step-num) {
    display: none;
  }
  .guide-link span:last-child {
    display: none;
  }
}
</style>
