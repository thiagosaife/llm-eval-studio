<script setup lang="ts">
import { RouterLink } from 'vue-router'
import DatasetEditor from '../components/DatasetEditor.vue'
import { useDatasetStore } from '../stores/dataset'

const dataset = useDatasetStore()
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Build a dataset</h1>
        <p class="muted">
          Each case is one test: a prompt, the model's output, and optionally a gold reference.
          A tiny, well-chosen set beats a huge noisy one when you're learning.
        </p>
      </div>
    </header>

    <DatasetEditor />

    <div class="row spread center next-bar card pad">
      <span class="muted small">
        {{ dataset.cases.length }} case{{ dataset.cases.length === 1 ? '' : 's' }} ·
        {{ dataset.readyCases.length }} with a prediction ·
        {{ dataset.hasAnyReference ? 'references present' : 'no references yet' }}
      </span>
      <RouterLink to="/run" class="btn btn-primary">Next: pick metrics →</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 22px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.page-head p {
  max-width: 70ch;
  margin: 0;
}
.next-bar {
  margin-top: 20px;
  position: sticky;
  bottom: 16px;
}
</style>
