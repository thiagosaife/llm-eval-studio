<script setup lang="ts">
import { computed, ref } from 'vue'
import Papa from 'papaparse'
import type { TestCase } from '../api/types'
import { useDatasetStore } from '../stores/dataset'

// Add/edit cases; import CSV or JSON and mark which column is input / reference
// / context (doc §6.2).
const store = useDatasetStore()

// --- JSON import -----------------------------------------------------------
const showImport = ref(false)
const importText = ref('')
const importError = ref<string | null>(null)

function runImport() {
  importError.value = null
  try {
    const parsed = JSON.parse(importText.value)
    if (!Array.isArray(parsed)) throw new Error('Expected a JSON array of cases.')
    store.setCases(parsed)
    showImport.value = false
    importText.value = ''
  } catch (e) {
    importError.value = e instanceof Error ? e.message : String(e)
  }
}

// --- CSV import with column mapping ----------------------------------------
type FieldKey = 'input' | 'prediction' | 'reference' | 'context' | 'ignore'
const FIELD_OPTIONS: { value: FieldKey; label: string }[] = [
  { value: 'input', label: 'Input' },
  { value: 'prediction', label: 'Prediction' },
  { value: 'reference', label: 'Reference' },
  { value: 'context', label: 'Context' },
  { value: 'ignore', label: 'Ignore' },
]

const showCsv = ref(false)
const csvError = ref<string | null>(null)
const csvHeaders = ref<string[]>([])
const csvRows = ref<Record<string, string>[]>([])
const mapping = ref<Record<string, FieldKey>>({})

function guessField(header: string): FieldKey {
  const h = header.toLowerCase()
  if (/(input|prompt|question|query)/.test(h)) return 'input'
  if (/(prediction|output|answer|response|generated|completion|hypothesis)/.test(h))
    return 'prediction'
  if (/(reference|expected|gold|target|truth|ground)/.test(h)) return 'reference'
  if (/(context|document|passage|retrieved|source)/.test(h)) return 'context'
  return 'ignore'
}

function parseCsv(text: string) {
  csvError.value = null
  const result = Papa.parse<Record<string, string>>(text.trim(), {
    header: true,
    skipEmptyLines: true,
  })
  if (result.errors.length) {
    csvError.value = result.errors[0].message
    return
  }
  const headers = result.meta.fields ?? []
  if (headers.length === 0) {
    csvError.value = 'No columns found in the CSV.'
    return
  }
  csvHeaders.value = headers
  csvRows.value = result.data
  const m: Record<string, FieldKey> = {}
  for (const h of headers) m[h] = guessField(h)
  mapping.value = m
}

async function onCsvFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    parseCsv(await file.text())
  } catch (err) {
    csvError.value = err instanceof Error ? err.message : String(err)
  }
  input.value = '' // allow re-selecting the same file
}

const mappedToPrediction = computed(() =>
  Object.values(mapping.value).includes('prediction'),
)

function applyCsv() {
  const rows: Partial<TestCase>[] = csvRows.value.map((row) => {
    const c: Partial<TestCase> = {}
    for (const h of csvHeaders.value) {
      const field = mapping.value[h]
      const value = row[h] ?? ''
      if (field === 'input') c.input = value
      else if (field === 'prediction') c.prediction = value
      else if (field === 'reference') c.reference = value
      else if (field === 'context') c.context = value
    }
    return c
  })
  store.setCases(rows)
  resetCsv()
}

function resetCsv() {
  showCsv.value = false
  csvHeaders.value = []
  csvRows.value = []
  mapping.value = {}
  csvError.value = null
}
</script>

<template>
  <section>
    <div class="row spread wrap" style="margin-bottom: 16px; gap: 10px">
      <label class="field grow" style="max-width: 360px">
        <span class="label">Dataset name</span>
        <input v-model="store.name" type="text" placeholder="Untitled dataset" />
      </label>
      <div class="row center wrap" style="gap: 8px">
        <button class="btn-sm" @click="store.loadExample()">Example: QA</button>
        <button class="btn-sm" @click="store.loadClassificationExample()">Example: labels</button>
        <button class="btn-sm" @click="(showCsv = !showCsv), (showImport = false)">
          Import CSV
        </button>
        <button class="btn-sm" @click="(showImport = !showImport), (showCsv = false)">
          Import JSON
        </button>
        <button class="btn-sm btn-danger" @click="store.clear()">Clear</button>
      </div>
    </div>

    <!-- CSV import + column mapping -->
    <div v-if="showCsv" class="card pad importer">
      <div class="row spread center wrap" style="gap: 10px">
        <div class="label" style="margin: 0">Import CSV</div>
        <label class="btn btn-sm file-btn">
          Choose file…
          <input type="file" accept=".csv,text/csv" @change="onCsvFile" hidden />
        </label>
      </div>

      <div v-if="csvError" class="banner error tiny" style="margin-top: 10px">{{ csvError }}</div>

      <div v-if="csvHeaders.length" style="margin-top: 14px">
        <p class="tiny muted" style="margin: 0 0 8px">
          {{ csvRows.length }} rows found — map each column to a field:
        </p>
        <div class="mapping">
          <div v-for="h in csvHeaders" :key="h" class="map-row">
            <span class="col-name mono">{{ h }}</span>
            <span class="arrow">→</span>
            <select v-model="mapping[h]">
              <option v-for="opt in FIELD_OPTIONS" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>
        <p v-if="!mappedToPrediction" class="tiny disabled-hint" style="margin: 10px 0 0">
          Tip: map a column to <strong>Prediction</strong> — only cases with a prediction can be
          scored.
        </p>
        <div class="row" style="margin-top: 12px">
          <button class="btn-primary btn-sm" @click="applyCsv">
            Import {{ csvRows.length }} cases
          </button>
          <button class="btn-sm btn-ghost" @click="resetCsv">Cancel</button>
        </div>
      </div>
    </div>

    <!-- JSON import -->
    <div v-if="showImport" class="card pad importer">
      <div class="label" style="margin-bottom: 6px">
        Paste an array of cases — keys: input, prediction, reference, context
      </div>
      <textarea
        v-model="importText"
        rows="6"
        class="mono"
        placeholder='[{"input": "...", "prediction": "...", "reference": "..."}]'
      ></textarea>
      <div v-if="importError" class="banner error tiny" style="margin-top: 8px">
        {{ importError }}
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="btn-primary btn-sm" @click="runImport">Import</button>
        <button class="btn-sm btn-ghost" @click="showImport = false">Cancel</button>
      </div>
    </div>

    <div class="cases">
      <article v-for="(c, i) in store.cases" :key="c.id" class="card pad case">
        <div class="row spread center" style="margin-bottom: 10px">
          <span class="badge primary">Case {{ i + 1 }}</span>
          <button class="btn-danger btn-sm" title="Remove case" @click="store.removeCase(c.id)">
            Remove
          </button>
        </div>

        <label class="field" style="margin-bottom: 10px">
          <span class="label">Input <span class="muted tiny">· the prompt / question</span></span>
          <textarea v-model="c.input" rows="2" placeholder="What is the capital of France?"></textarea>
        </label>

        <div class="grid-2">
          <label class="field">
            <span class="label">
              Prediction <span class="muted tiny">· the LLM output (required to score)</span>
            </span>
            <textarea v-model="c.prediction" rows="3" placeholder="Paris"></textarea>
          </label>
          <label class="field">
            <span class="label">
              Reference
              <span class="badge ref" style="margin-left: 4px">optional · gold answer</span>
            </span>
            <textarea v-model="c.reference" rows="3" placeholder="Paris"></textarea>
          </label>
        </div>

        <label class="field" style="margin-top: 10px">
          <span class="label">
            Context
            <span class="muted tiny">· retrieved docs, for RAG metrics (optional)</span>
          </span>
          <textarea v-model="c.context" rows="2" placeholder=""></textarea>
        </label>
      </article>
    </div>

    <button class="btn add-btn" @click="store.addCase()">+ Add case</button>
  </section>
</template>

<style scoped>
.importer {
  margin-bottom: 16px;
}
.cases {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.add-btn {
  margin-top: 14px;
  width: 100%;
  border-style: dashed;
  color: var(--c-text-soft);
}
.file-btn {
  display: inline-flex;
  align-items: center;
}
.mapping {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.map-row {
  display: grid;
  grid-template-columns: 1fr auto 150px;
  align-items: center;
  gap: 10px;
}
.col-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arrow {
  color: var(--c-muted);
}
.map-row select {
  font: inherit;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
}
.disabled-hint {
  color: var(--c-warn);
}
@media (max-width: 640px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
