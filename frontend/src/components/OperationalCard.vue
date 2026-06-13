<script setup lang="ts">
import type { OperationalSummary } from '../api/types'

// Operational metrics — not about quality, but about whether it's shippable
// (doc §3.6). Shown next to the quality cards so the trade-off stays honest.
defineProps<{ summary: OperationalSummary }>()
</script>

<template>
  <div class="card pad">
    <div class="row spread center" style="margin-bottom: 10px">
      <h3>Operational</h3>
      <span class="tiny muted">across {{ summary.calls }} model call(s)</span>
    </div>
    <dl class="ops">
      <div>
        <dt>Latency p50</dt>
        <dd>{{ Math.round(summary.latency_p50_ms) }} ms</dd>
      </div>
      <div>
        <dt>Latency p95</dt>
        <dd>{{ Math.round(summary.latency_p95_ms) }} ms</dd>
      </div>
      <div>
        <dt>Tokens in / out</dt>
        <dd>{{ summary.tokens_in }} / {{ summary.tokens_out }}</dd>
      </div>
      <div>
        <dt>Cost</dt>
        <dd>${{ summary.cost.toFixed(4) }}</dd>
      </div>
    </dl>
    <p class="tiny muted note">
      A model that's 2% better but 5× slower and 10× more expensive is often the wrong choice.
    </p>
  </div>
</template>

<style scoped>
h3 {
  margin: 0;
}
.ops {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin: 0;
}
.ops dt {
  color: var(--c-text-soft);
  font-size: 0.8rem;
}
.ops dd {
  margin: 2px 0 0;
  font-size: 1.2rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.note {
  margin: 12px 0 0;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}
</style>
