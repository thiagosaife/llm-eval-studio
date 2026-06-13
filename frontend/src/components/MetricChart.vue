<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MetricInfo, RunResponse } from '../api/types'
import { scoreColor } from '../utils/format'

// Distribution of per-case scores for one metric — a histogram makes clusters
// of failures visible that the average hides (doc §6.2, §6.4).
const props = defineProps<{ run: RunResponse; metricsById: Record<string, MetricInfo> }>()

const chartable = computed(() =>
  props.run.metrics.filter((id) => !props.metricsById[id]?.aggregate_only),
)
const selected = ref(chartable.value[0] ?? '')

const bins = computed<number[]>(() => {
  const counts = new Array(10).fill(0)
  for (const c of props.run.per_case) {
    const v = c.scores[selected.value]
    if (v === null || v === undefined) continue
    const idx = Math.max(0, Math.min(9, Math.floor(v * 10)))
    counts[idx]++
  }
  return counts
})
const maxCount = computed(() => Math.max(1, ...bins.value))

function name(id: string): string {
  return props.metricsById[id]?.name ?? id
}
</script>

<template>
  <div class="card pad">
    <div class="row spread center wrap" style="gap: 10px; margin-bottom: 14px">
      <h3>Score distribution</h3>
      <select v-model="selected" class="select">
        <option v-for="id in chartable" :key="id" :value="id">{{ name(id) }}</option>
      </select>
    </div>

    <div class="chart">
      <div v-for="(count, i) in bins" :key="i" class="bar-col">
        <span class="count tiny">{{ count || '' }}</span>
        <div
          class="bar"
          :style="{
            height: `${(count / maxCount) * 100}%`,
            background: scoreColor((i + 0.5) / 10),
          }"
        ></div>
        <span class="xlabel tiny">{{ (i / 10).toFixed(1) }}</span>
      </div>
    </div>
    <p class="tiny muted axis">bins by score · count of cases per bin</p>
  </div>
</template>

<style scoped>
h3 {
  margin: 0;
}
.select {
  font: inherit;
  padding: 5px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
}
.chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 150px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  gap: 3px;
}
.bar {
  width: 100%;
  min-height: 2px;
  border-radius: 3px 3px 0 0;
  transition: height 0.3s ease;
}
.count {
  font-variant-numeric: tabular-nums;
  color: var(--c-text-soft);
  height: 14px;
}
.xlabel {
  color: var(--c-muted);
}
.axis {
  margin: 8px 0 0;
}
</style>
