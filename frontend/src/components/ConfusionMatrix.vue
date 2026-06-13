<script setup lang="ts">
import { computed } from 'vue'
import type { ConfusionMatrix } from '../api/types'

// The full right/wrong breakdown per class — what you actually look at to debug
// a classification task (doc §3.3). Diagonal = correct (green), off-diagonal =
// confusions (red), shaded by count.
const props = defineProps<{ data: ConfusionMatrix }>()

const max = computed(() => Math.max(1, ...props.data.matrix.flat()))

function cellStyle(i: number, j: number, v: number): Record<string, string> {
  if (v === 0) return {}
  const t = v / max.value
  const alpha = (0.15 + 0.6 * t).toFixed(3)
  const hue = i === j ? 140 : 8 // green for correct, red for confusions
  return { background: `hsla(${hue}, 70%, 45%, ${alpha})` }
}
</script>

<template>
  <div class="card pad cm">
    <div class="row spread center" style="margin-bottom: 4px">
      <h3>Confusion matrix</h3>
      <span class="tiny muted">rows: true label · columns: predicted</span>
    </div>
    <p class="tiny muted" style="margin: 0 0 12px">
      The diagonal is correct; off-diagonal cells are where the model confused one
      label for another.
    </p>
    <div class="cm-scroll">
      <table>
        <thead>
          <tr>
            <th class="corner"></th>
            <th v-for="label in data.labels" :key="'p-' + label" class="pred-head">{{ label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in data.matrix" :key="'r-' + i">
            <th class="true-head">{{ data.labels[i] }}</th>
            <td
              v-for="(v, j) in row"
              :key="'c-' + i + '-' + j"
              :style="cellStyle(i, j, v)"
              :class="{ diag: i === j, zero: v === 0 }"
            >
              {{ v }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.cm h3 {
  margin: 0;
}
.cm-scroll {
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}
th,
td {
  border: 1px solid var(--c-border);
  padding: 8px 12px;
  text-align: center;
  min-width: 46px;
}
.corner {
  border: none;
}
.pred-head,
.true-head {
  font-size: 0.82rem;
  color: var(--c-text-soft);
  background: var(--c-surface-2);
  font-weight: 600;
}
.true-head {
  text-align: right;
}
td {
  font-weight: 650;
}
td.zero {
  color: var(--c-muted);
  font-weight: 400;
}
td.diag {
  font-weight: 750;
}
</style>
