<script setup lang="ts">
import type { MetricInfo, RunResponse } from '../api/types'
import { formatScore, scoreColor } from '../utils/format'

// One card per metric: aggregate score, its 0–1 range, and a one-line "how to
// read this" (doc §6.2).
const props = defineProps<{
  run: RunResponse
  metricsById: Record<string, MetricInfo>
}>()

function info(id: string): MetricInfo | undefined {
  return props.metricsById[id]
}
function barWidth(v: number | null): string {
  if (v === null) return '0%'
  const [min, max] = [0, 1]
  return `${Math.max(0, Math.min(1, (v - min) / (max - min))) * 100}%`
}
</script>

<template>
  <div class="cards">
    <article v-for="id in run.metrics" :key="id" class="card pad scard">
      <div class="row spread center">
        <strong>{{ info(id)?.name ?? id }}</strong>
        <span class="tiny muted">range 0–1</span>
      </div>

      <div
        class="score"
        :style="{ color: scoreColor(run.aggregate[id]) }"
      >
        {{ formatScore(run.aggregate[id]) }}
      </div>

      <div class="track">
        <div
          class="fill"
          :style="{ width: barWidth(run.aggregate[id]), background: scoreColor(run.aggregate[id]) }"
        ></div>
      </div>

      <p class="tiny muted howto">{{ info(id)?.how_to_read }}</p>
    </article>
  </div>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 14px;
}
.scard {
  display: flex;
  flex-direction: column;
}
.score {
  font-size: 2.1rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  margin: 6px 0 8px;
  line-height: 1;
}
.track {
  height: 6px;
  background: var(--c-surface-2);
  border-radius: 999px;
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s ease;
}
.howto {
  margin: 10px 0 0;
}
</style>
