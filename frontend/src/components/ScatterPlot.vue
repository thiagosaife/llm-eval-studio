<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProjectedPoint } from '../api/types'

// A hand-rolled SVG scatter of 2-D projected points — same no-charting-library
// approach as MetricChart / ConfusionMatrix. Points are colored by category when
// the data carries labels (digits, species, a class label); otherwise a single
// hue. The axes are intentionally unlabeled: after a nonlinear projection the
// coordinates aren't directly interpretable, only the *relative* layout is.
const props = defineProps<{
  points: ProjectedPoint[]
  labelKind: 'category' | 'none'
}>()

const W = 420
const H = 320
const PAD = 18

// A categorical palette (distinct, reasonably colorblind-aware).
const PALETTE = [
  '#4338ca', '#0891b2', '#16a34a', '#ca8a04', '#dc2626', '#9333ea',
  '#db2777', '#2563eb', '#65a30d', '#ea580c', '#0d9488', '#7c3aed',
]

const labels = computed(() => {
  if (props.labelKind !== 'category') return []
  const seen: string[] = []
  for (const p of props.points) {
    const l = p.label ?? ''
    if (l && !seen.includes(l)) seen.push(l)
  }
  return seen
})
const colorByLabel = computed<Record<string, string>>(() =>
  Object.fromEntries(labels.value.map((l, i) => [l, PALETTE[i % PALETTE.length]])),
)
function colorFor(p: ProjectedPoint): string {
  if (props.labelKind === 'category' && p.label) return colorByLabel.value[p.label] ?? '#4338ca'
  return '#4338ca'
}

const bounds = computed(() => {
  const xs = props.points.map((p) => p.x)
  const ys = props.points.map((p) => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  // Guard against a zero-width range (e.g. all points identical on an axis).
  return {
    minX,
    maxX: maxX === minX ? minX + 1 : maxX,
    minY,
    maxY: maxY === minY ? minY + 1 : maxY,
  }
})

interface Placed {
  p: ProjectedPoint
  cx: number
  cy: number
  color: string
}
const placed = computed<Placed[]>(() => {
  const b = bounds.value
  return props.points.map((p) => ({
    p,
    cx: PAD + ((p.x - b.minX) / (b.maxX - b.minX)) * (W - 2 * PAD),
    // invert y so "up" is the larger value, as in a normal plot
    cy: H - PAD - ((p.y - b.minY) / (b.maxY - b.minY)) * (H - 2 * PAD),
    color: colorFor(p),
  }))
})

const hovered = ref<ProjectedPoint | null>(null)
const radius = computed(() => (props.points.length > 250 ? 3 : 4.5))
</script>

<template>
  <div class="scatter">
    <svg :viewBox="`0 0 ${W} ${H}`" class="plot" role="img" aria-label="2-D projection scatter plot">
      <rect :x="1" :y="1" :width="W - 2" :height="H - 2" class="frame" />
      <circle
        v-for="(d, i) in placed"
        :key="d.p.id + '-' + i"
        :cx="d.cx"
        :cy="d.cy"
        :r="radius"
        :fill="d.color"
        :class="{ faded: hovered && hovered.id !== d.p.id }"
        @mouseenter="hovered = d.p"
        @mouseleave="hovered = null"
      >
        <title>{{ d.p.label ? d.p.label + ' · ' : '' }}{{ d.p.text ?? d.p.id }}</title>
      </circle>
    </svg>

    <div class="readout tiny">
      <template v-if="hovered">
        <span v-if="hovered.label" class="dot" :style="{ background: colorFor(hovered) }"></span>
        <strong v-if="hovered.label">{{ hovered.label }}</strong>
        <span class="muted">{{ hovered.text ?? `#${hovered.id}` }}</span>
      </template>
      <span v-else class="muted">Hover a point to inspect it.</span>
    </div>

    <div v-if="labels.length" class="legend">
      <span v-for="l in labels" :key="l" class="legend-item tiny">
        <span class="dot" :style="{ background: colorByLabel[l] }"></span>{{ l }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.scatter {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.plot {
  width: 100%;
  height: auto;
  display: block;
}
.frame {
  fill: var(--c-surface-2);
  stroke: var(--c-border);
  rx: 8;
}
circle {
  stroke: #fff;
  stroke-width: 0.6;
  cursor: pointer;
  transition: opacity 0.1s;
}
circle.faded {
  opacity: 0.22;
}
.readout {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 18px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--c-text-soft);
}
.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
}
</style>
