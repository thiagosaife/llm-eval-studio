<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import InfoTip from './InfoTip.vue'
import { metricAnchor, metricTooltip } from '../content/metricGuide'
import { useDatasetStore } from '../stores/dataset'
import { useRunStore } from '../stores/run'

const router = useRouter()
// "!" tip → the full "What costs money" explanation in the guide (new tab).
const costTip = metricTooltip('cost-estimate')
const costGuideHref = router.resolve({
  name: 'guide',
  hash: `#${metricAnchor('cost-estimate')}`,
}).href

// Pre-run cost projection (doc §3.6). Token counting via Anthropic's count_tokens
// endpoint is free (it doesn't run the model), and the offline heuristic needs no
// key at all — so a cost estimate is available *before* spending a cent on a run.
const dataset = useDatasetStore()
const run = useRunStore()

const est = computed(() => run.estimateResult)
const hasLlmCalls = computed(() => (est.value?.llm_calls ?? 0) > 0)

// A run is only billable if an LLM-judge metric is selected; local metrics are free.
function money(n: number): string {
  if (n <= 0) return '$0'
  if (n < 0.0001) return '<$0.0001'
  return `$${n.toFixed(4)}`
}
function tokens(n: number): string {
  return n.toLocaleString()
}

// Live heuristic estimate: re-run (debounced) whenever the inputs that change the
// projection change. Heuristic only — exact counts are an explicit click.
let timer: ReturnType<typeof setTimeout> | undefined
const signature = computed(() =>
  JSON.stringify({
    m: run.selectedMetrics,
    model: run.judgeModel,
    rubric: run.rubric,
    cases: dataset.readyCases,
  }),
)
watch(
  signature,
  () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      run.estimate(dataset.readyCases, false).catch(() => {
        /* surfaced via run.estimateError */
      })
    }, 300)
  },
  { immediate: true },
)
onBeforeUnmount(() => timer && clearTimeout(timer))

async function refine() {
  try {
    await run.estimate(dataset.readyCases, true)
  } catch {
    /* surfaced via run.estimateError */
  }
}
</script>

<template>
  <div class="card pad estimate">
    <div class="row spread center" style="margin-bottom: 10px">
      <h3>
        Cost estimate
        <InfoTip
          :text="costTip"
          :href="costGuideHref"
          label="Why does a run cost money? Open the guide"
        />
      </h3>
      <span
        v-if="hasLlmCalls"
        class="badge"
        :class="est?.exact ? 'exact' : 'approx'"
        :title="
          est?.exact
            ? 'Exact input tokens via the free count_tokens endpoint'
            : 'Offline heuristic (~±20%). Refine for exact input tokens.'
        "
        >{{ est?.exact ? 'exact' : 'approx' }}</span
      >
    </div>

    <p v-if="!est" class="tiny muted no-est">
      Pick a metric and add predictions to project a run's cost.
    </p>

    <p v-else-if="!hasLlmCalls" class="tiny muted no-est">
      No LLM-judge metric selected — this run is free (local metrics only).
    </p>

    <template v-else>
      <div class="headline">
        <div class="primary">
          <span class="figure">{{ money(est!.expected_cost) }}</span>
          <span class="tiny muted">expected</span>
        </div>
        <div class="ceiling">
          up to <strong>{{ money(est!.max_cost) }}</strong>
          <span class="tiny muted">worst case</span>
        </div>
      </div>

      <dl class="rows">
        <div>
          <dt>LLM calls</dt>
          <dd>{{ est!.llm_calls }}</dd>
        </div>
        <div>
          <dt>Input tokens</dt>
          <dd>{{ tokens(est!.tokens_in) }}</dd>
        </div>
        <div>
          <dt>Output (est. / max)</dt>
          <dd>{{ tokens(est!.expected_tokens_out) }} / {{ tokens(est!.max_tokens_out) }}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd class="model">{{ est!.model }}</dd>
        </div>
      </dl>

      <div class="row spread center refine-row">
        <button
          class="btn-sm refine-btn"
          :disabled="run.estimating"
          title="Replace the heuristic with exact input tokens via Anthropic's count_tokens endpoint — free, and it doesn't run the model"
          @click="refine"
        >
          <span class="refine-icon" aria-hidden="true">🎯</span>
          <span>{{ run.estimating ? 'Counting…' : 'Get exact count' }}</span>
        </button>
        <span v-if="!est!.exact" class="tiny muted">free · no model run</span>
      </div>

      <label class="cap">
        <span class="tiny muted">Warn me if a run could exceed</span>
        <span class="cap-input">
          $<input
            v-model.number="run.spendCap"
            type="number"
            min="0"
            step="0.5"
            aria-label="Spend cap in USD"
          />
        </span>
      </label>

      <p class="tiny muted note">
        Output size can't be known in advance — judge replies are tiny, so the real
        cost lands near “expected”; “worst case” assumes every reply hits the token cap.
      </p>
    </template>

    <div v-if="run.estimateError" class="banner error tiny" style="margin-top: 10px">
      {{ run.estimateError }}
    </div>
  </div>
</template>

<style scoped>
h3 {
  margin: 0;
}
.no-est {
  margin: 0;
}
.badge.approx {
  background: var(--c-surface-2);
  color: var(--c-text-soft);
}
.badge.exact {
  background: var(--c-primary);
  color: #fff;
}
.headline {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.primary {
  display: flex;
  flex-direction: column;
}
.figure {
  font-size: 1.6rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.ceiling {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.ceiling strong {
  font-size: 1.05rem;
}
.ceiling .tiny {
  display: block;
}
.rows {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 16px;
  margin: 0 0 12px;
}
.rows dt {
  color: var(--c-text-soft);
  font-size: 0.8rem;
}
.rows dd {
  margin: 1px 0 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.rows dd.model {
  font-weight: 600;
  font-size: 0.85rem;
}
.refine-row {
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
  gap: 8px;
}
/* A bordered, accent-colored button (not a ghost link) so the action reads
   clearly; the 🎯 icon signals "exact / precise". */
.refine-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--c-primary);
  font-weight: 600;
  white-space: nowrap;
}
.refine-btn:hover:not(:disabled) {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
}
.refine-icon {
  font-size: 0.9em;
  line-height: 1;
}
.cap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
}
.cap-input {
  font-weight: 700;
}
.cap-input input {
  width: 72px;
  padding: 4px 6px;
  margin-left: 2px;
  border: 1px solid var(--c-border);
  border-radius: 6px;
  font: inherit;
  text-align: right;
}
.note {
  margin: 12px 0 0;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}
</style>
