<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '../stores/dataset'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'
import { useRunStore } from '../stores/run'

// Trigger POST /api/evaluate and show progress (doc §6.2). Scores
// pasted/imported/generated outputs; gated by a spend confirmation when the
// estimated worst-case cost exceeds the user's cap.
const dataset = useDatasetStore()
const catalog = useMetricsCatalogStore()
const run = useRunStore()
const router = useRouter()

// `readyCases` is a store getter, already unwrapped to a plain array here.
const ready = computed(() => dataset.readyCases.length)
const skipped = computed(() => dataset.cases.length - dataset.readyCases.length)

// Selected metrics that can be estimated but not run yet (no API key). The run
// is blocked on these (the server enforces it too), but the estimate still works.
const keyBlocked = computed(() =>
  run.selectedMetrics.filter((id) => {
    const m = catalog.metrics.find((x) => x.id === id)
    return m !== undefined && !m.available
  }),
)

const canRun = computed(
  () =>
    run.selectedMetrics.length > 0 &&
    dataset.readyCases.length > 0 &&
    keyBlocked.value.length === 0 &&
    run.status !== 'running',
)

const blockReason = computed(() => {
  if (dataset.readyCases.length === 0) return 'Add a prediction to at least one case.'
  if (run.selectedMetrics.length === 0) return 'Select at least one metric.'
  if (keyBlocked.value.length > 0)
    return 'Set ANTHROPIC_API_KEY to run the selected judge metric(s) — the estimate works without it.'
  return null
})

const pendingConfirm = ref(false)

function money(n: number): string {
  if (n <= 0) return '$0'
  if (n < 0.0001) return '<$0.0001'
  return `$${n.toFixed(4)}`
}

async function launch() {
  const est = run.estimateResult
  // Gate on the worst-case ceiling so the user is never surprised.
  if (est && est.llm_calls > 0 && est.max_cost > run.spendCap) {
    pendingConfirm.value = true
    return
  }
  await doLaunch()
}

async function doLaunch() {
  pendingConfirm.value = false
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

    <button v-if="!pendingConfirm" class="btn-primary launch" :disabled="!canRun" @click="launch">
      <span v-if="run.status === 'running'">Scoring…</span>
      <span v-else>Run evaluation</span>
    </button>

    <div v-else class="confirm">
      <p class="tiny">
        This run could cost up to
        <strong>{{ money(run.estimateResult!.max_cost) }}</strong>
        (expected ~{{ money(run.estimateResult!.expected_cost) }}), above your
        {{ money(run.spendCap) }} cap. Proceed?
      </p>
      <div class="confirm-actions">
        <button class="btn-primary btn-sm" @click="doLaunch">Run anyway</button>
        <button class="btn-ghost btn-sm" @click="pendingConfirm = false">Cancel</button>
      </div>
    </div>

    <p v-if="blockReason && !pendingConfirm" class="tiny muted blocked">{{ blockReason }}</p>

    <div v-if="run.error" class="banner error tiny" style="margin-top: 10px">
      {{ run.error }}
    </div>

    <p class="tiny muted gen-note">
      Score pasted/imported outputs, or generate them live from the Model panel above.
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
.confirm {
  border: 1px solid var(--c-warn, #d9a400);
  background: var(--c-warn-soft, #fdf6e3);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.confirm p {
  margin: 0 0 10px;
}
.confirm-actions {
  display: flex;
  gap: 8px;
}
.confirm-actions .btn-primary {
  flex: 1;
}
.gen-note {
  margin: 14px 0 0;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}
</style>
