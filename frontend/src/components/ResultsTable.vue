<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

// Vertical-scroll affordance: the table is capped in height and scrolls, with
// up/down arrows that appear only when there are more rows in that direction —
// so it's obvious there are more cases to inspect below the fold.
const scroller = ref<HTMLElement | null>(null)
const canUp = ref(false)
const canDown = ref(false)
const canLeft = ref(false)
const canRight = ref(false)

function updateArrows() {
  const el = scroller.value
  if (!el) return
  canUp.value = el.scrollTop > 2
  canDown.value = el.scrollTop + el.clientHeight < el.scrollHeight - 2
  canLeft.value = el.scrollLeft > 2
  canRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 2
}

function scrollByPageY(dir: number) {
  const el = scroller.value
  if (!el) return
  el.scrollBy({ top: dir * el.clientHeight * 0.85, behavior: 'smooth' })
}

function scrollByPageX(dir: number) {
  const el = scroller.value
  if (!el) return
  el.scrollBy({ left: dir * el.clientWidth * 0.85, behavior: 'smooth' })
}

let ro: ResizeObserver | undefined
onMounted(() => {
  updateArrows()
  if (typeof ResizeObserver !== 'undefined' && scroller.value) {
    ro = new ResizeObserver(updateArrows)
    ro.observe(scroller.value)
  }
  window.addEventListener('resize', updateArrows)
})
onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', updateArrows)
})
// Row count changes alter scrollHeight without resizing the (height-capped)
// container, so ResizeObserver won't fire — recompute explicitly.
watch(
  () => props.run.per_case.length,
  () => nextTick(updateArrows),
)
</script>

<template>
  <div class="table-scroll">
    <div ref="scroller" class="table-wrap card" @scroll="updateArrows">
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

    <!-- Scroll affordances (edge fades + arrows): each shows only when there's
         more content in that direction, so the table never looks like a dead end. -->
    <div v-show="canDown" class="fade fade-bottom" aria-hidden="true"></div>
    <div v-show="canRight" class="fade fade-right" aria-hidden="true"></div>
    <div v-show="canLeft" class="fade fade-left" aria-hidden="true"></div>

    <button
      v-show="canUp"
      type="button"
      class="scroll-arrow up"
      aria-label="Scroll results up"
      title="Scroll up"
      @click="scrollByPageY(-1)"
    >
      ▲
    </button>
    <button
      v-show="canDown"
      type="button"
      class="scroll-arrow down"
      aria-label="More results — scroll down"
      title="More results — scroll down"
      @click="scrollByPageY(1)"
    >
      ▼
    </button>
    <button
      v-show="canLeft"
      type="button"
      class="scroll-arrow left"
      aria-label="Scroll results left"
      title="Scroll left"
      @click="scrollByPageX(-1)"
    >
      ◀
    </button>
    <button
      v-show="canRight"
      type="button"
      class="scroll-arrow right"
      aria-label="More columns — scroll right"
      title="More columns — scroll right"
      @click="scrollByPageX(1)"
    >
      ▶
    </button>
  </div>
</template>

<style scoped>
.table-scroll {
  position: relative;
  /* As a grid item this wrapper must be allowed to shrink below the table's
     intrinsic width, or it blows out the column (pushing the inspector off to
     the right). The inner .table-wrap then scrolls horizontally instead. */
  min-width: 0;
}
.table-wrap {
  /* Cap the height so long result sets scroll inside the card instead of
     running off the page; the scrollbar + fade + arrows signal there's more. */
  max-height: 360px;
  overflow: auto;
  /* Keep the scrollbar visible — macOS hides overlay scrollbars until you
     actively scroll, which made the table look like it didn't scroll at all. */
  scrollbar-width: thin;
  scrollbar-color: var(--c-border-strong) transparent;
}
.table-wrap::-webkit-scrollbar {
  width: 11px;
  height: 11px;
}
.table-wrap::-webkit-scrollbar-track {
  background: transparent;
}
.table-wrap::-webkit-scrollbar-thumb {
  background: var(--c-border-strong);
  border-radius: 6px;
  border: 2px solid var(--c-surface);
}
.table-wrap::-webkit-scrollbar-thumb:hover {
  background: var(--c-text-soft);
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
  z-index: 1;
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

/* Floating scroll arrows — sit over the card, above the sticky header. */
.scroll-arrow {
  position: absolute;
  right: 16px;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
  box-shadow: var(--shadow-md);
  color: var(--c-text-soft);
  font-size: 0.72rem;
  line-height: 1;
}
.scroll-arrow:hover {
  color: var(--c-primary);
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
}
.scroll-arrow.up {
  top: 10px;
}
/* The "there's more" arrows (down/right) get the accent color to draw the eye;
   the back-arrows (up/left) stay neutral. */
.scroll-arrow.down {
  bottom: 16px;
  color: var(--c-primary);
  border-color: var(--c-primary);
}
.scroll-arrow.left {
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
}
.scroll-arrow.right {
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--c-primary);
  border-color: var(--c-primary);
}

/* Soft edge fades so cut-off rows/columns read as "more this way". */
.fade {
  position: absolute;
  z-index: 2;
  pointer-events: none;
}
.fade-bottom {
  left: 1px;
  right: 1px;
  bottom: 1px;
  height: 44px;
  border-radius: 0 0 var(--radius) var(--radius);
  background: linear-gradient(to top, var(--c-surface), transparent);
}
.fade-right {
  top: 1px;
  bottom: 1px;
  right: 1px;
  width: 48px;
  border-radius: 0 var(--radius) var(--radius) 0;
  background: linear-gradient(to left, var(--c-surface), transparent);
}
.fade-left {
  top: 1px;
  bottom: 1px;
  left: 1px;
  width: 48px;
  border-radius: var(--radius) 0 0 var(--radius);
  background: linear-gradient(to right, var(--c-surface), transparent);
}
</style>
