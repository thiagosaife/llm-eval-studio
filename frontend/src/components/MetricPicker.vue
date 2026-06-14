<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { MetricInfo } from '../api/types'
import InfoTip from './InfoTip.vue'
import { metricAnchor, metricTooltip } from '../content/metricGuide'
import { familyLabel } from '../utils/format'

// Lists metrics from GET /api/metrics. Each shows its description and a
// "requires reference" badge, and reference-based metrics are disabled when no
// reference exists. This is where most of the teaching happens (doc §6.2).
const props = defineProps<{
  metrics: MetricInfo[]
  selected: string[]
  hasReference: boolean
}>()

const emit = defineEmits<{ (e: 'toggle', id: string): void }>()

const router = useRouter()

// Each metric's "!" tip links to its entry on the metrics guide (new tab).
function guideHref(id: string): string {
  return router.resolve({ name: 'guide', hash: `#${metricAnchor(id)}` }).href
}
function tooltip(m: MetricInfo): string {
  return metricTooltip(m.id, m.description)
}

function isSelected(id: string) {
  return props.selected.includes(id)
}
// Returns why a metric can't be picked, or null if it can. Key-gated LLM metrics
// (estimable but not yet runnable) stay *selectable* so they can be estimated —
// only a missing library (`!estimable`) or a missing reference blocks selection.
function disabledReason(m: MetricInfo): string | null {
  if (!m.estimable) return m.unavailable_reason ?? 'Not installed.'
  if (m.requires_reference && !props.hasReference)
    return 'Add a reference to at least one case to enable this metric.'
  return null
}
function isDisabled(m: MetricInfo) {
  return disabledReason(m) !== null
}
function onToggle(m: MetricInfo) {
  if (isDisabled(m)) return
  emit('toggle', m.id)
}
</script>

<template>
  <div class="picker">
    <article
      v-for="m in metrics"
      :key="m.id"
      class="metric card"
      :class="{ selected: isSelected(m.id), disabled: isDisabled(m) }"
      role="checkbox"
      :aria-checked="isSelected(m.id)"
      :aria-disabled="isDisabled(m)"
      tabindex="0"
      @click="onToggle(m)"
      @keydown.enter.prevent="onToggle(m)"
      @keydown.space.prevent="onToggle(m)"
    >
      <div class="row spread center">
        <div class="row center title" style="gap: 9px">
          <span class="check" :class="{ on: isSelected(m.id) }" aria-hidden="true">✓</span>
          <strong>
            {{ m.name }}
            <InfoTip
              :text="tooltip(m)"
              :href="guideHref(m.id)"
              :label="`What is ${m.name}? Open the guide`"
            />
          </strong>
        </div>
        <div class="row" style="gap: 5px">
          <span class="badge">{{ familyLabel(m.family) }}</span>
          <span v-if="m.requires_reference" class="badge ref">needs reference</span>
          <span v-if="!m.estimable" class="badge ref">needs install</span>
          <span v-else-if="!m.available" class="badge ref">needs key to run</span>
        </div>
      </div>

      <p class="desc small muted">{{ m.description }}</p>

      <div class="notes tiny">
        <p><span class="note-key">Read it:</span> {{ m.how_to_read }}</p>
        <p class="lies"><span class="note-key">It lies when:</span> {{ m.caveat }}</p>
      </div>

      <p v-if="disabledReason(m)" class="tiny disabled-hint">{{ disabledReason(m) }}</p>
    </article>
  </div>
</template>

<style scoped>
.picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.metric {
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color 0.12s, box-shadow 0.12s, background 0.12s;
}
.metric:hover:not(.disabled) {
  border-color: var(--c-border-strong);
}
.metric.selected {
  border-color: var(--c-primary);
  box-shadow: 0 0 0 1px var(--c-primary);
  background: #fcfcff;
}
.metric.disabled {
  cursor: not-allowed;
  opacity: 0.6;
  background: var(--c-surface-2);
}
/* Keep the title group from forcing the checkbox to deform: the checkbox never
   shrinks, and the title shrinks/wraps instead (it stays aligned to the first
   line). */
.title {
  align-items: flex-start;
}
.check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 19px;
  height: 19px;
  margin-top: 1px;
  border-radius: 5px;
  border: 1.5px solid var(--c-border-strong);
  color: transparent;
  font-size: 0.72rem;
  font-weight: 800;
}
.title strong {
  min-width: 0;
}
.check.on {
  background: var(--c-primary);
  border-color: var(--c-primary);
  color: #fff;
}
.desc {
  margin: 9px 0 8px;
}
.notes {
  border-top: 1px solid var(--c-border);
  padding-top: 8px;
  color: var(--c-text-soft);
}
.notes p {
  margin: 2px 0;
}
.note-key {
  font-weight: 700;
  color: var(--c-text);
}
.lies .note-key {
  color: var(--c-warn);
}
.disabled-hint {
  margin: 8px 0 0;
  color: var(--c-warn);
}
@media (max-width: 720px) {
  .picker {
    grid-template-columns: 1fr;
  }
}
</style>
