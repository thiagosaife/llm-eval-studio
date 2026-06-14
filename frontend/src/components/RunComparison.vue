<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { MetricInfo, RunResponse, RunSummary } from '../api/types'
import { formatScore, scoreColor } from '../utils/format'

// Compare this run's aggregates against an earlier run, to confirm a prompt/model
// tweak actually improved things (doc §8.6). The whole point of iterating.
const props = defineProps<{ current: RunResponse; metricsById: Record<string, MetricInfo> }>()

const others = ref<RunSummary[]>([])
const baselineId = ref<string>('')

onMounted(async () => {
  try {
    const all = await api.listRuns()
    others.value = all.filter((r) => r.run_id !== props.current.run_id)
  } catch {
    /* comparison is optional */
  }
})

const baseline = computed<RunSummary | null>(
  () => others.value.find((r) => r.run_id === baselineId.value) ?? null,
)

interface Row {
  id: string
  name: string
  current: number | null
  base: number | null
  delta: number | null
}

const rows = computed<Row[]>(() => {
  if (!baseline.value) return []
  return props.current.metrics
    .filter((id) => id in baseline.value!.aggregate)
    .map((id) => {
      const cur = props.current.aggregate[id] ?? null
      const base = baseline.value!.aggregate[id] ?? null
      const delta = cur !== null && base !== null ? Math.round((cur - base) * 10000) / 10000 : null
      return { id, name: props.metricsById[id]?.name ?? id, current: cur, base, delta }
    })
})

function label(r: RunSummary): string {
  const when = new Date(r.created_at)
  const t = isNaN(when.getTime()) ? r.created_at : when.toLocaleString()
  return `${r.dataset_name || 'run'} · ${t}`
}
</script>

<template>
  <div class="card pad">
    <div class="row spread center wrap" style="gap: 10px; margin-bottom: 4px">
      <h3>Compare runs</h3>
      <select v-model="baselineId" class="select" :disabled="others.length === 0">
        <option value="">{{ others.length ? 'Pick a baseline run…' : 'No earlier runs yet' }}</option>
        <option v-for="r in others" :key="r.run_id" :value="r.run_id">{{ label(r) }}</option>
      </select>
    </div>

    <p v-if="!baseline" class="tiny muted" style="margin: 6px 0 0">
      Run again after tweaking the prompt or model, then compare the two here.
    </p>

    <table v-else class="cmp">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Baseline</th>
          <th>This run</th>
          <th>Δ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.name }}</td>
          <td>
            <span class="pill" :style="{ background: scoreColor(r.base) }">{{
              formatScore(r.base)
            }}</span>
          </td>
          <td>
            <span class="pill" :style="{ background: scoreColor(r.current) }">{{
              formatScore(r.current)
            }}</span>
          </td>
          <td
            class="delta"
            :class="{ up: (r.delta ?? 0) > 0, down: (r.delta ?? 0) < 0 }"
          >
            <template v-if="r.delta === null">—</template>
            <template v-else
              >{{ (r.delta ?? 0) > 0 ? '▲' : (r.delta ?? 0) < 0 ? '▼' : '·' }}
              {{ Math.abs(r.delta ?? 0).toFixed(2) }}</template
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
h3 {
  margin: 0;
}
.select {
  font: inherit;
  padding: 5px 30px 5px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background-color: var(--c-surface);
  max-width: 260px;
}
.cmp {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
  font-size: 0.9rem;
}
.cmp th,
.cmp td {
  text-align: left;
  padding: 7px 10px;
  border-bottom: 1px solid var(--c-border);
}
.cmp th {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
}
.delta {
  font-variant-numeric: tabular-nums;
  font-weight: 650;
  color: var(--c-muted);
}
.delta.up {
  color: #1c8a4b;
}
.delta.down {
  color: var(--c-danger);
}
</style>
