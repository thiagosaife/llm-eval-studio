<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import SummaryCards from '../components/SummaryCards.vue'
import ResultsTable from '../components/ResultsTable.vue'
import CaseInspector from '../components/CaseInspector.vue'
import ConfusionMatrix from '../components/ConfusionMatrix.vue'
import type { CaseResult, RunResponse } from '../api/types'
import { ApiError } from '../api/client'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'
import { useRunStore } from '../stores/run'

const props = defineProps<{ runId: string }>()

const catalog = useMetricsCatalogStore()
const runStore = useRunStore()

const run = ref<RunResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const selectedId = ref<string | null>(null)

async function load(runId: string) {
  loading.value = true
  error.value = null
  try {
    await catalog.load()
    const result = await runStore.loadRun(runId)
    run.value = result
    selectedId.value = worstCaseId(result)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 404
        ? 'This run is no longer in memory (the backend may have restarted). Re-run to see results.'
        : e instanceof Error
          ? e.message
          : String(e)
  } finally {
    loading.value = false
  }
}

/** The UX principle (doc §6.4): open the worst case first, by the primary metric. */
function worstCaseId(r: RunResponse): string | null {
  const key = r.metrics[0]
  if (!key) return r.per_case[0]?.id ?? null
  let worst: CaseResult | null = null
  for (const c of r.per_case) {
    const v = c.scores[key]
    if (v === null || v === undefined) continue
    if (worst === null || (v as number) < (worst.scores[key] as number)) worst = c
  }
  return (worst ?? r.per_case[0])?.id ?? null
}

const selectedCase = computed<CaseResult | null>(
  () => run.value?.per_case.find((c) => c.id === selectedId.value) ?? null,
)
const confusion = computed(() => run.value?.confusion_matrix ?? null)
const createdLabel = computed(() => {
  if (!run.value) return ''
  const d = new Date(run.value.created_at)
  return isNaN(d.getTime()) ? run.value.created_at : d.toLocaleString()
})

watch(() => props.runId, load, { immediate: true })
</script>

<template>
  <div>
    <p v-if="loading" class="muted">Loading results…</p>

    <div v-else-if="error" class="banner error">
      {{ error }} <RouterLink to="/run">Back to run</RouterLink>
    </div>

    <template v-else-if="run">
      <header class="page-head">
        <div class="row spread center wrap" style="gap: 12px">
          <div>
            <h1>Results</h1>
            <p class="muted small">
              <strong>{{ run.dataset_name || 'dataset' }}</strong>
              · {{ run.per_case.length }} cases ·
              <span class="mono">{{ run.run_id }}</span>
              · {{ createdLabel }}
            </p>
          </div>
          <RouterLink to="/run" class="btn btn-sm">Tweak &amp; re-run</RouterLink>
        </div>
      </header>

      <section style="margin-bottom: 24px">
        <SummaryCards :run="run" :metrics-by-id="catalog.byId" />
      </section>

      <section v-if="confusion" style="margin-bottom: 24px">
        <ConfusionMatrix :data="confusion" />
      </section>

      <p class="muted small tip">
        💡 The average hides the failures. Sort by a metric column to surface the worst cases, then
        open one to see why.
      </p>

      <div class="layout">
        <ResultsTable
          :run="run"
          :metrics-by-id="catalog.byId"
          :selected-id="selectedId"
          @select="selectedId = $event"
        />
        <CaseInspector
          :case-result="selectedCase"
          :metric-ids="run.metrics"
          :metrics-by-id="catalog.byId"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 20px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 4px;
}
.tip {
  margin: 0 0 14px;
}
.layout {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 18px;
  align-items: start;
}
@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
