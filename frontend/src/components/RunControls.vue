<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '../stores/dataset'
import { useRunStore } from '../stores/run'

// Trigger POST /api/evaluate and show progress (doc §6.2). Phase 1 scores
// pasted/imported outputs; live generation arrives in Phase 3.
const dataset = useDatasetStore()
const run = useRunStore()
const router = useRouter()

// `readyCases` is a store getter, already unwrapped to a plain array here.
const ready = computed(() => dataset.readyCases.length)
const skipped = computed(() => dataset.cases.length - dataset.readyCases.length)

const canRun = computed(
  () => run.selectedMetrics.length > 0 && dataset.readyCases.length > 0 && run.status !== 'running',
)

const blockReason = computed(() => {
  if (dataset.readyCases.length === 0) return 'Add a prediction to at least one case.'
  if (run.selectedMetrics.length === 0) return 'Select at least one metric.'
  return null
})

async function launch() {
  try {
    const result = await run.run(dataset.readyCases, dataset.name)
    router.push(`/results/${result.run_id}`)
  } catch {
    /* error surfaced via run.error */
  }
}
</script>

<template>
  <div class="card pad run-controls">
    <h3>Run</h3>

    <dl class="stats">
      <div>
        <dt>Cases to score</dt>
        <dd>{{ ready }}</dd>
      </div>
      <div>
        <dt>Metrics selected</dt>
        <dd>{{ run.selectedMetrics.length }}</dd>
      </div>
      <div v-if="skipped > 0">
        <dt>Skipped (no prediction)</dt>
        <dd class="muted">{{ skipped }}</dd>
      </div>
    </dl>

    <button class="btn-primary launch" :disabled="!canRun" @click="launch">
      <span v-if="run.status === 'running'">Scoring…</span>
      <span v-else>Run evaluation</span>
    </button>

    <p v-if="blockReason" class="tiny muted blocked">{{ blockReason }}</p>

    <div v-if="run.error" class="banner error tiny" style="margin-top: 10px">
      {{ run.error }}
    </div>

    <p class="tiny muted gen-note">
      Outputs are scored as pasted/imported. Live model generation is a Phase 3 feature.
    </p>
  </div>
</template>

<style scoped>
.run-controls h3 {
  margin-bottom: 12px;
}
.stats {
  margin: 0 0 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stats > div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px dashed var(--c-border);
  padding-bottom: 6px;
}
.stats dt {
  color: var(--c-text-soft);
  font-size: 0.88rem;
}
.stats dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.launch {
  width: 100%;
  padding: 11px;
  font-size: 1rem;
}
.blocked {
  margin: 8px 0 0;
  text-align: center;
}
.gen-note {
  margin: 14px 0 0;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}
</style>
