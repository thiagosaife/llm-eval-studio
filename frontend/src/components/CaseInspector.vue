<script setup lang="ts">
import { computed } from 'vue'
import type { CaseResult, MetricInfo } from '../api/types'
import { formatScore, scoreColor, wordDiff } from '../utils/format'

// Side-by-side prediction vs reference with a word-level diff, plus the per-case
// metric scores (doc §6.2). The diff makes tangible *what a lexical metric
// pays for*: the highlighted (unaligned) words are exactly what costs it.
const props = defineProps<{
  caseResult: CaseResult | null
  metricIds: string[]
  metricsById: Record<string, MetricInfo>
}>()

const diff = computed(() => wordDiff(props.caseResult?.prediction, props.caseResult?.reference))
const hasReference = computed(() => !!(props.caseResult?.reference ?? '').trim())

// Set-level metrics (precision/recall/F1) have no per-case value — skip them here.
const caseMetricIds = computed(() =>
  props.metricIds.filter((id) => !props.metricsById[id]?.aggregate_only),
)

function info(id: string): MetricInfo | undefined {
  return props.metricsById[id]
}
</script>

<template>
  <div v-if="caseResult" class="card pad inspector">
    <div class="row spread center" style="margin-bottom: 4px">
      <h3>Case inspector</h3>
      <span class="tiny muted">differences are highlighted</span>
    </div>

    <div v-if="caseResult.input" class="field-block">
      <div class="label">Input</div>
      <p class="text">{{ caseResult.input }}</p>
    </div>

    <div class="compare">
      <div class="pane">
        <div class="label">Prediction</div>
        <p class="text">
          <template v-for="(seg, i) in diff.left" :key="i"
            ><span :class="{ added: seg.status === 'changed' }">{{ seg.text }}</span></template
          >
        </p>
      </div>
      <div class="pane">
        <div class="label">Reference</div>
        <p v-if="hasReference" class="text">
          <template v-for="(seg, i) in diff.right" :key="i"
            ><span :class="{ missing: seg.status === 'changed' }">{{ seg.text }}</span></template
          >
        </p>
        <p v-else class="text muted">No reference — reference-based metrics were skipped.</p>
      </div>
    </div>

    <p v-if="hasReference" class="tiny legend">
      <span class="swatch added">in prediction only</span>
      <span class="swatch missing">in reference only</span>
    </p>

    <div v-if="caseResult.context" class="field-block">
      <div class="label">Context</div>
      <p class="text muted">{{ caseResult.context }}</p>
    </div>

    <hr class="sep" />

    <div class="label" style="margin-bottom: 10px">Scores</div>
    <div class="scores">
      <div v-for="id in caseMetricIds" :key="id" class="score-row">
        <span
          class="pill"
          :class="{ na: caseResult.scores[id] === null || caseResult.scores[id] === undefined }"
          :style="
            caseResult.scores[id] === null || caseResult.scores[id] === undefined
              ? {}
              : { background: scoreColor(caseResult.scores[id]) }
          "
          >{{ formatScore(caseResult.scores[id]) }}</span
        >
        <div class="score-meta">
          <strong>{{ info(id)?.name ?? id }}</strong>
          <span class="tiny muted">{{ info(id)?.how_to_read }}</span>
          <p v-if="caseResult.rationales[id]" class="rationale tiny">
            <span class="judge-tag">judge</span> {{ caseResult.rationales[id] }}
          </p>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="card pad muted empty">Select a row to inspect a case.</div>
</template>

<style scoped>
.inspector h3 {
  margin-bottom: 0;
}
.field-block {
  margin-top: 14px;
}
.label {
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
  margin-bottom: 4px;
}
.text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}
.pane {
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}
.added {
  background: #ffe3d6;
  box-shadow: 0 0 0 1px #f5c4ad;
  border-radius: 3px;
}
.missing {
  background: #d8ecff;
  box-shadow: 0 0 0 1px #aed3f5;
  border-radius: 3px;
}
.legend {
  display: flex;
  gap: 14px;
  margin: 10px 0 0;
  color: var(--c-text-soft);
}
.swatch {
  padding: 1px 6px;
  border-radius: 3px;
}
.swatch.added {
  background: #ffe3d6;
}
.swatch.missing {
  background: #d8ecff;
}
.scores {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.score-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.score-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.rationale {
  margin: 5px 0 0;
  color: var(--c-text);
  background: var(--c-surface-2);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
}
.judge-tag {
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.66rem;
  letter-spacing: 0.04em;
  color: var(--c-primary);
  margin-right: 4px;
}
.empty {
  text-align: center;
}
@media (max-width: 640px) {
  .compare {
    grid-template-columns: 1fr;
  }
}
</style>
