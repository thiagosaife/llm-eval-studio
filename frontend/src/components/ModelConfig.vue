<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDatasetStore } from '../stores/dataset'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'
import { useRunStore } from '../stores/run'

// Optionally configure a model and generate outputs live (doc §6.1, §8.3).
const dataset = useDatasetStore()
const catalog = useMetricsCatalogStore()
const run = useRunStore()

const promptCases = computed(() => dataset.cases.filter((c) => (c.input ?? '').trim() !== ''))
const canGenerate = computed(
  () => catalog.llmAvailable && promptCases.value.length > 0 && !run.generating,
)

async function generate() {
  try {
    const resp = await run.generate(promptCases.value)
    const predictions = new Map(resp.cases.map((c) => [c.id, c.prediction]))
    for (const c of dataset.cases) {
      const p = predictions.get(c.id)
      if (p !== undefined) c.prediction = p
    }
  } catch {
    /* surfaced via run.genError */
  }
}
</script>

<template>
  <div class="card pad">
    <div class="row spread center" style="margin-bottom: 12px">
      <h3>Model</h3>
      <span class="badge" :class="catalog.llmAvailable ? 'primary' : ''">
        {{ catalog.llmAvailable ? 'live generation ready' : 'no API key' }}
      </span>
    </div>

    <div v-if="!catalog.llmAvailable" class="banner info small" style="margin-bottom: 12px">
      {{ catalog.llmReason }} You can still paste outputs and use lexical, classification, and
      embedding metrics.
    </div>

    <div class="grid">
      <label class="field">
        <span class="label">Model</span>
        <select v-model="run.model" class="select">
          <option v-for="m in catalog.models" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
      </label>
      <label class="field">
        <span class="label">Max tokens</span>
        <input v-model.number="run.maxTokens" type="text" inputmode="numeric" />
      </label>
    </div>

    <label class="field" style="margin-top: 10px">
      <span class="label">System prompt <span class="muted tiny">· optional</span></span>
      <textarea v-model="run.systemPrompt" rows="2" placeholder="You are a concise assistant."></textarea>
    </label>

    <div class="row center" style="gap: 10px; margin-top: 12px">
      <button class="btn" :disabled="!canGenerate" @click="generate">
        <span v-if="run.generating">Generating…</span>
        <span v-else>Generate predictions for {{ promptCases.length }} case(s)</span>
      </button>
      <RouterLink to="/datasets" class="tiny muted">edit dataset</RouterLink>
    </div>

    <div v-if="run.genError" class="banner error tiny" style="margin-top: 10px">
      {{ run.genError }}
    </div>

    <div v-if="run.genSummary" class="gen-summary tiny" style="margin-top: 12px">
      Generated · {{ run.genSummary.calls }} calls · p50
      {{ Math.round(run.genSummary.latency_p50_ms) }}ms / p95
      {{ Math.round(run.genSummary.latency_p95_ms) }}ms ·
      {{ run.genSummary.tokens_in + run.genSummary.tokens_out }} tokens · ${{
        run.genSummary.cost.toFixed(4)
      }}
    </div>
  </div>
</template>

<style scoped>
h3 {
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
}
.select {
  font: inherit;
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
}
.gen-summary {
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
  color: var(--c-text-soft);
  font-variant-numeric: tabular-nums;
}
</style>
