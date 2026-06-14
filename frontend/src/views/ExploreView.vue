<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import ScatterPlot from '../components/ScatterPlot.vue'
import InfoTip from '../components/InfoTip.vue'
import type { ProjectionResult, ProjectResponse } from '../api/types'
import { metricAnchor, metricTooltip, termAnchor } from '../content/metricGuide'
import { useDatasetStore } from '../stores/dataset'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'
import { useProjectionStore } from '../stores/projection'

// The Embedding & Dimensionality-Reduction Explorer: turn high-dimensional
// vectors (your dataset's embeddings, or a built-in demo) into a 2-D scatter,
// and swap PCA / t-SNE / UMAP to *see* how each algorithm lays the same data out.
const router = useRouter()
const store = useProjectionStore()
const dataset = useDatasetStore()
const catalog = useMetricsCatalogStore() // reused only to know if embeddings are installed

type Source = 'sample' | 'dataset'
type Field = 'input' | 'prediction' | 'reference' | 'context'

const source = ref<Source>('sample')
const sampleId = ref<string>('')
const field = ref<Field>('prediction')
const activeAlgos = ref<string[]>([])
const compare = ref(true)
const focus = ref<string>('')
const params = reactive<Record<string, Record<string, number>>>({})
const result = ref<ProjectResponse | null>(null)

const FIELDS: Field[] = ['input', 'prediction', 'reference', 'context']

onMounted(async () => {
  catalog.load()
  await store.loadCatalog()
  sampleId.value = store.samples[0]?.id ?? ''
  activeAlgos.value = store.algorithms.filter((a) => a.available).map((a) => a.id)
  focus.value = activeAlgos.value[0] ?? ''
  for (const a of store.algorithms) {
    if (!a.params.length) continue
    params[a.id] = params[a.id] ?? {}
    for (const p of a.params) if (params[a.id][p.key] === undefined) params[a.id][p.key] = p.default
  }
})

// Embeddings (sentence-transformers) power the "your dataset" source. The cosine
// metric needs the exact same library, so its availability is our signal.
const embeddingsAvailable = computed(() => catalog.byId['cosine']?.available ?? true)
const embeddingsReason = computed(
  () => catalog.byId['cosine']?.unavailable_reason ?? 'Embeddings need sentence-transformers.',
)

const usableCount = computed(
  () => dataset.cases.filter((c) => ((c[field.value] as string) ?? '').trim() !== '').length,
)
const activeWithParams = computed(() =>
  store.algorithms.filter((a) => activeAlgos.value.includes(a.id) && a.params.length),
)

const canProject = computed(() => {
  if (activeAlgos.value.length === 0) return false
  if (source.value === 'sample') return !!sampleId.value
  return embeddingsAvailable.value && usableCount.value >= 3
})

const displayed = computed<ProjectionResult[]>(() => {
  if (!result.value) return []
  const order = activeAlgos.value
  const all = [...result.value.results]
    .filter((r) => order.includes(r.algorithm))
    .sort((a, b) => order.indexOf(a.algorithm) - order.indexOf(b.algorithm))
  return compare.value ? all : all.filter((r) => r.algorithm === focus.value)
})

function algoName(id: string): string {
  return store.algorithms.find((a) => a.id === id)?.name ?? id
}
function toggleAlgo(id: string) {
  const a = store.algorithms.find((x) => x.id === id)
  if (!a?.available) return
  const i = activeAlgos.value.indexOf(id)
  if (i === -1) activeAlgos.value.push(id)
  else activeAlgos.value.splice(i, 1)
  if (!activeAlgos.value.includes(focus.value)) focus.value = activeAlgos.value[0] ?? ''
}
function guideHref(id: string): string {
  return router.resolve({ name: 'guide', hash: `#${metricAnchor(id)}` }).href
}
function termHref(slug: string): string {
  return router.resolve({ name: 'guide', hash: `#${termAnchor(slug)}` }).href
}
const PARAM_SLUG: Record<string, string> = {
  perplexity: 'perplexity',
  n_neighbors: 'n-neighbors',
  min_dist: 'min-dist',
}

function metaLine(r: ProjectionResult): string {
  const m = r.meta
  if (r.algorithm === 'pca' && m.variance_explained) {
    const [a, b] = m.variance_explained
    return `PC1 ${(a * 100).toFixed(1)}% · PC2 ${(b * 100).toFixed(1)}% of variance (${(
      (a + b) * 100
    ).toFixed(1)}% total)`
  }
  const parts: string[] = []
  if (m.perplexity != null) parts.push(`perplexity ${m.perplexity}`)
  if (m.n_neighbors != null) parts.push(`n_neighbors ${m.n_neighbors}`)
  if (m.min_dist != null) parts.push(`min_dist ${m.min_dist}`)
  if (m.preprocessed_dims != null) parts.push(`PCA-reduced to ${m.preprocessed_dims}-D first`)
  return parts.join(' · ')
}
const TEACHING: Record<string, string> = {
  pca: 'Linear & global — distances between points are meaningful, but curved/nonlinear structure can stay hidden.',
  tsne: 'Local & nonlinear — similar points form tight clusters, but cluster sizes and the gaps between clusters are NOT meaningful.',
  umap: 'Balances local and global structure, usually faster than t-SNE and keeps more of the big picture.',
}

async function runProjection() {
  if (!canProject.value) return
  try {
    result.value = await store.project({
      source: source.value,
      algorithms: activeAlgos.value,
      ...(source.value === 'sample'
        ? { sample_id: sampleId.value }
        : { field: field.value, cases: dataset.cases }),
      params,
    })
  } catch {
    /* surfaced via store.projectError */
  }
}

// A changed data source invalidates the plotted result (different points).
watch([source, sampleId, field], () => {
  result.value = null
})
</script>

<template>
  <div>
    <header class="page-head">
      <h1>Dimensionality-reduction explorer</h1>
      <p class="muted">
        High-dimensional data — like the 384-dimension embeddings behind Cosine/BERTScore —
        can't be plotted directly. Dimensionality reduction squashes it to 2-D so you can see
        structure. Each algorithm makes different trade-offs; project the same data with several and
        compare.
        <RouterLink :to="{ name: 'guide', hash: '#family-dimred' }" target="_blank">
          Read the full guide ↗
        </RouterLink>
      </p>
    </header>

    <p v-if="store.loading" class="muted">Loading explorer…</p>
    <div v-else-if="store.error" class="banner error">{{ store.error }}</div>

    <template v-else>
      <!-- 1 · Data source -->
      <section class="card pad block">
        <div class="label">1 · Data to project</div>
        <div class="seg">
          <button :class="{ on: source === 'sample' }" @click="source = 'sample'">
            Sample datasets
          </button>
          <button :class="{ on: source === 'dataset' }" @click="source = 'dataset'">
            Your dataset
          </button>
        </div>

        <div v-if="source === 'sample'" class="src-body">
          <label class="field" style="max-width: 280px">
            <span class="sublabel">Dataset</span>
            <select v-model="sampleId" class="select">
              <option v-for="s in store.samples" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <p v-if="store.samples.find((s) => s.id === sampleId)" class="tiny muted hint">
            {{ store.samples.find((s) => s.id === sampleId)?.description }}
            ({{ store.samples.find((s) => s.id === sampleId)?.n_samples }} points ·
            {{ store.samples.find((s) => s.id === sampleId)?.n_features }}-D)
          </p>
        </div>

        <div v-else class="src-body">
          <div v-if="!embeddingsAvailable" class="banner info small">{{ embeddingsReason }}</div>
          <template v-else>
            <label class="field" style="max-width: 280px">
              <span class="sublabel">Embed which field?</span>
              <select v-model="field" class="select">
                <option v-for="f in FIELDS" :key="f" :value="f">{{ f }}</option>
              </select>
            </label>
            <p class="tiny muted hint">
              Embeds each case's <strong>{{ field }}</strong> and maps it to 2-D — a semantic map of
              your dataset. {{ usableCount }} of {{ dataset.cases.length }} cases have a non-empty
              {{ field }}.
              <span v-if="usableCount < 3" class="warn">
                Need at least 3 — <RouterLink to="/datasets">add cases</RouterLink>.
              </span>
            </p>
          </template>
        </div>
      </section>

      <!-- 2 · Algorithms & params -->
      <section class="card pad block">
        <div class="label">2 · Algorithms</div>
        <div class="chips">
          <button
            v-for="a in store.algorithms"
            :key="a.id"
            class="chip"
            :class="{ on: activeAlgos.includes(a.id), disabled: !a.available }"
            :title="a.available ? '' : a.unavailable_reason || 'Unavailable'"
            @click="toggleAlgo(a.id)"
          >
            <span class="tick" aria-hidden="true">✓</span>
            {{ a.name }}
            <InfoTip
              :text="metricTooltip(a.id, a.description)"
              :href="guideHref(a.id)"
              :label="`What is ${a.name}?`"
            />
          </button>
        </div>

        <div v-if="activeWithParams.length" class="params">
          <div v-for="a in activeWithParams" :key="a.id" class="param-group">
            <span class="param-algo tiny">{{ a.name }}</span>
            <div v-for="p in a.params" :key="p.key" class="param-row">
              <span class="param-label tiny">
                {{ p.label }}
                <InfoTip
                  :text="p.help"
                  :href="PARAM_SLUG[p.key] ? termHref(PARAM_SLUG[p.key]) : undefined"
                  :label="`What is ${p.label}?`"
                />
              </span>
              <input
                type="range"
                :min="p.min"
                :max="p.max"
                :step="p.step"
                v-model.number="params[a.id][p.key]"
              />
              <span class="param-val mono tiny">{{ params[a.id][p.key] }}</span>
            </div>
          </div>
        </div>

        <div class="row spread center wrap actions">
          <label class="compare">
            <input type="checkbox" v-model="compare" />
            Compare side-by-side
          </label>
          <div v-if="!compare && activeAlgos.length > 1" class="seg small">
            <button
              v-for="id in activeAlgos"
              :key="id"
              :class="{ on: focus === id }"
              @click="focus = id"
            >
              {{ algoName(id) }}
            </button>
          </div>
          <button class="btn btn-primary" :disabled="!canProject || store.projecting" @click="runProjection">
            <span v-if="store.projecting">Projecting…</span>
            <span v-else>Project →</span>
          </button>
        </div>

        <div v-if="store.projectError" class="banner error tiny" style="margin-top: 10px">
          {{ store.projectError }}
        </div>
      </section>

      <!-- 3 · Results -->
      <section v-if="displayed.length" class="block">
        <p class="tiny muted" style="margin: 0 0 10px">
          {{ result?.n_points }} points · {{ result?.dims_in }}-D input →
          {{ compare ? 'compared across' : 'showing' }}
          {{ compare ? displayed.length + ' algorithms' : algoName(focus) }}.
        </p>
        <div class="plots" :class="{ single: !compare || displayed.length === 1 }">
          <article v-for="r in displayed" :key="r.algorithm" class="card pad plot-card">
            <div class="row spread center" style="margin-bottom: 2px">
              <h3>
                {{ algoName(r.algorithm) }}
                <InfoTip
                  :text="metricTooltip(r.algorithm, '')"
                  :href="guideHref(r.algorithm)"
                  :label="`What is ${algoName(r.algorithm)}?`"
                />
              </h3>
            </div>
            <p class="meta tiny mono">{{ metaLine(r) }}</p>
            <ScatterPlot :points="r.points" :label-kind="result?.label_kind ?? 'none'" />
            <p class="teach tiny">{{ TEACHING[r.algorithm] }}</p>
          </article>
        </div>
      </section>

      <div v-else class="card pad empty">
        <p class="muted">
          Pick your data and algorithms above, then <strong>Project →</strong> to see the 2-D map.
        </p>
      </div>

      <!-- reading guide -->
      <div class="callout small">
        <strong>Reading these plots.</strong> Color groups points by label (digit, species, or a
        class label from your references). Look for whether like-colored points cluster — that means
        the high-dimensional structure survived the squash. Remember t-SNE/UMAP distort global
        distances, so don't read meaning into how far apart two clusters sit; PCA preserves global
        distances but can blur subtle nonlinear groups.
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 18px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.page-head p {
  max-width: 78ch;
  margin: 0;
}
.block {
  margin-bottom: 18px;
}
.label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
  margin-bottom: 12px;
}
.sublabel {
  display: block;
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--c-text-soft);
  margin-bottom: 4px;
}
.seg {
  display: inline-flex;
  border: 1px solid var(--c-border-strong);
  border-radius: 999px;
  overflow: hidden;
}
.seg button {
  border: none;
  border-radius: 0;
  background: var(--c-surface);
  padding: 6px 14px;
  font-size: 0.88rem;
}
.seg button.on {
  background: var(--c-primary);
  color: #fff;
}
.seg.small button {
  padding: 4px 10px;
  font-size: 0.82rem;
}
.src-body {
  margin-top: 14px;
}
.hint {
  margin: 8px 0 0;
  max-width: 72ch;
}
.warn {
  color: var(--c-warn);
}
.select {
  font: inherit;
  width: 100%;
  padding: 8px 32px 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background-color: var(--c-surface);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
  font-weight: 550;
}
.chip .tick {
  color: transparent;
  font-weight: 800;
  font-size: 0.78rem;
}
.chip.on {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  color: var(--c-primary);
}
.chip.on .tick {
  color: var(--c-primary);
}
.chip.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.params {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--c-border);
}
.param-group {
  min-width: 220px;
}
.param-algo {
  display: block;
  font-weight: 700;
  color: var(--c-text-soft);
  margin-bottom: 6px;
}
.param-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 4px 8px;
  margin-bottom: 6px;
}
.param-label {
  grid-column: 1 / -1;
  color: var(--c-text);
}
.param-row input[type='range'] {
  width: 100%;
  accent-color: var(--c-primary);
}
.param-val {
  color: var(--c-text-soft);
  min-width: 30px;
  text-align: right;
}
.actions {
  margin-top: 18px;
  gap: 12px;
}
.compare {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.9rem;
  cursor: pointer;
}
.plots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}
.plots.single {
  grid-template-columns: minmax(0, 540px);
}
.plot-card h3 {
  font-size: 1rem;
  margin: 0;
}
.meta {
  color: var(--c-text-soft);
  margin: 0 0 8px;
}
.teach {
  margin: 8px 0 0;
  color: var(--c-text-soft);
  border-top: 1px solid var(--c-border);
  padding-top: 8px;
}
.empty {
  text-align: center;
}
.empty p {
  margin: 0;
}
.callout {
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  background: var(--c-primary-soft);
  color: var(--c-text);
  border: 1px solid #dcdcfb;
}
</style>
