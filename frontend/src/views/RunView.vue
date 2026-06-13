<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import MetricPicker from '../components/MetricPicker.vue'
import RunControls from '../components/RunControls.vue'
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

    <div class="layout">
      <section class="picker-col">
        <p v-if="catalog.loading" class="muted">Loading metrics…</p>
        <div v-else-if="catalog.error" class="banner error">{{ catalog.error }}</div>
        <MetricPicker
          v-else
          :metrics="catalog.metrics"
          :selected="run.selectedMetrics"
          :has-reference="dataset.hasAnyReference"
          @toggle="run.toggleMetric"
        />
      </section>

      <aside class="controls-col">
        <RunControls />
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
