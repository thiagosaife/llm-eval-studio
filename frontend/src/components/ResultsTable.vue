<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CaseResult, MetricInfo, RunResponse } from '../api/types'
import { formatScore, scoreColor } from '../utils/format'

// Per-case rows, sortable by any metric so the user can jump straight to the
// worst cases (doc §6.2). We default-sort ascending by the first metric, which
// puts the failures on top — making "read the worst cases" the obvious next
// click (the UX principle in doc §6.4).
const props = defineProps<{
  run: RunResponse
  metricsById: Record<string, MetricInfo>
  selectedId: string | null
}>()

const emit = defineEmits<{ (e: 'select', id: string): void }>()

// Set-level metrics (precision/recall/F1) have no per-case value, so they get
// no column here — they live in the summary cards instead.
const columnMetrics = computed(() =>
  props.run.metrics.filter((id) => !props.metricsById[id]?.aggregate_only),
)

const sortKey = ref<string>(columnMetrics.value[0] ?? props.run.metrics[0] ?? '')
const sortDir = ref<'asc' | 'desc'>('asc')

function setSort(metricId: string) {
  if (sortKey.value === metricId) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = metricId
    sortDir.value = 'asc'
  }
}

const sortedCases = computed<CaseResult[]>(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...props.run.per_case].sort((a, b) => {
    const av = a.scores[key]
    const bv = b.scores[key]
    // null (not applicable) always sinks to the bottom.
    if (av === null || av === undefined) return 1
    if (bv === null || bv === undefined) return -1
    return (av - bv) * dir
  })
})

function preview(c: CaseResult): string {
  return (c.input || c.prediction || '').toString()
}
function name(id: string): string {
  return props.metricsById[id]?.name ?? id
}
</script>

<template>
  <div class="table-wrap card">
    <table>
      <thead>
        <tr>
          <th class="num">#</th>
          <th class="case-col">Case</th>
          <th
            v-for="id in columnMetrics"
            :key="id"
            class="metric-col sortable"
            :class="{ active: sortKey === id }"
            @click="setSort(id)"
            :title="`Sort by ${name(id)}`"
          >
            {{ name(id) }}
            <span class="arrow">{{
              sortKey === id ? (sortDir === 'asc' ? '▲' : '▼') : '↕'
            }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(c, i) in sortedCases"
          :key="c.id"
          :class="{ selected: c.id === selectedId }"
          @click="emit('select', c.id)"
        >
          <td class="num muted">{{ i + 1 }}</td>
          <td class="case-col">
            <span class="preview">{{ preview(c) || '—' }}</span>
          </td>
          <td v-for="id in columnMetrics" :key="id" class="metric-col">
            <span
              class="pill"
              :class="{ na: c.scores[id] === null || c.scores[id] === undefined }"
              :style="
                c.scores[id] === null || c.scores[id] === undefined
                  ? {}
                  : { background: scoreColor(c.scores[id]) }
              "
            >
              {{ formatScore(c.scores[id]) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th,
td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--c-border);
}
thead th {
  background: var(--c-surface-2);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
  position: sticky;
  top: 0;
}
.num {
  width: 38px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.metric-col {
  text-align: center;
  white-space: nowrap;
}
.sortable {
  cursor: pointer;
  user-select: none;
}
.sortable:hover {
  color: var(--c-text);
}
.sortable.active {
  color: var(--c-primary);
}
.arrow {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-left: 2px;
}
.case-col {
  max-width: 460px;
}
.preview {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 460px;
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover {
  background: #fafbff;
}
tbody tr.selected {
  background: var(--c-primary-soft);
}
tbody tr:last-child td {
  border-bottom: none;
}
</style>
