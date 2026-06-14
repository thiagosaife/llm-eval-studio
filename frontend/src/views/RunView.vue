<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import MetricPicker from '../components/MetricPicker.vue'
import RunControls from '../components/RunControls.vue'
import EstimateCard from '../components/EstimateCard.vue'
import ModelConfig from '../components/ModelConfig.vue'
import { useDatasetStore } from '../stores/dataset'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'
import { useRunStore } from '../stores/run'

const dataset = useDatasetStore()
const catalog = useMetricsCatalogStore()
const run = useRunStore()

onMounted(() => catalog.load())

// If references disappear (e.g. the user cleared them), drop any selected
// reference-based metrics so we never launch a run that can't compute them.
watch(
  () => dataset.hasAnyReference,
  (hasRef) => {
    if (hasRef) return
    for (const m of catalog.metrics) {
      if (m.requires_reference && run.isSelected(m.id)) run.deselect(m.id)
    }
  },
)
</script>

<template>
  <div>
    <header class="page-head">
      <h1>Pick metrics &amp; run</h1>
      <p class="muted">
        The picker only enables metrics your data supports. Reference-based metrics need a gold
        answer — they're greyed out until at least one case has one.
      </p>
    </header>

    <div v-if="!dataset.hasAnyReference" class="banner info" style="margin-bottom: 18px">
      No references in this dataset, so only reference-free metrics are available.
      <RouterLink to="/datasets">Add references</RouterLink> to unlock Exact Match and ROUGE.
    </div>

    <section style="margin-bottom: 18px">
      <ModelConfig />
    </section>

    <div class="layout">
      <section class="picker-col">
        <p v-if="catalog.loading" class="muted">Loading metrics…</p>
        <div v-else-if="catalog.error" class="banner error">{{ catalog.error }}</div>
        <template v-else>
          <MetricPicker
            :metrics="catalog.metrics"
            :selected="run.selectedMetrics"
            :has-reference="dataset.hasAnyReference"
            @toggle="run.toggleMetric"
          />

          <div v-if="run.isSelected('llm_judge')" class="card pad rubric">
            <div class="label">LLM-judge rubric</div>
            <textarea
              v-model="run.rubric"
              rows="3"
              placeholder="Rate the overall correctness, relevance, and quality of the answer."
            ></textarea>
            <p class="tiny muted" style="margin: 8px 0 0">
              The judge grades each answer 1–5 against this rubric and explains why. Leave blank for
              a sensible default.
            </p>
          </div>
        </template>
      </section>

      <aside class="controls-col">
        <RunControls />
        <EstimateCard />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 20px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.page-head p {
  max-width: 70ch;
  margin: 0;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}
.controls-col {
  position: sticky;
  top: 84px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.rubric {
  margin-top: 14px;
}
.rubric .label {
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
  margin-bottom: 6px;
}
@media (max-width: 880px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .controls-col {
    position: static;
  }
}
</style>
