import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import type { TestCase } from '../api/types'

const STORAGE_KEY = 'llm-eval:dataset'

let seq = 0
function newId(): string {
  return `case-${Date.now().toString(36)}-${(seq++).toString(36)}`
}

function emptyCase(): TestCase {
  return { id: newId(), input: '', prediction: '', reference: '', context: '' }
}

// A small, well-chosen example set that makes the metrics' behaviour obvious —
// especially the lesson that lexical metrics punish correct paraphrases (doc §3.1).
function exampleCases(): TestCase[] {
  return [
    {
      id: newId(),
      input: 'What is the capital of France?',
      prediction: 'Paris',
      reference: 'paris',
      context: '',
    },
    {
      id: newId(),
      input: 'What is the capital of Australia?',
      prediction: 'Canberra is the capital city.',
      reference: 'Canberra',
      context: '',
    },
    {
      id: newId(),
      input: 'Summarize: the firm’s revenue increased 12% versus the prior quarter.',
      prediction: 'The company grew revenue 12% last quarter.',
      reference: 'Revenue rose 12% quarter over quarter.',
      context: '',
    },
    {
      id: newId(),
      input: 'Repeat the sentence exactly.',
      prediction: 'The cat sat on the mat.',
      reference: 'The cat sat on the mat.',
      context: '',
    },
    {
      id: newId(),
      input: 'Summarize the weather report.',
      prediction: 'It will be sunny tomorrow.',
      reference: 'Heavy rain is expected overnight.',
      context: '',
    },
  ]
}

// A sentiment-classification set: the prediction/reference are labels, and a
// couple are wrong on purpose so accuracy/precision/recall/F1 and the confusion
// matrix have something to show (doc §3.3).
function classificationCases(): TestCase[] {
  const rows: [string, string, string][] = [
    ['Loved every minute — fantastic!', 'positive', 'positive'],
    ['Terrible service, never again.', 'negative', 'negative'],
    ['It was okay, nothing special.', 'negative', 'neutral'],
    ['Absolutely wonderful experience.', 'positive', 'positive'],
    ['Worst purchase I have made.', 'negative', 'negative'],
    ['Pretty average, met expectations.', 'neutral', 'neutral'],
    ['Not bad, could be better.', 'positive', 'neutral'],
    ['Disappointing and slow.', 'negative', 'negative'],
  ]
  return rows.map(([input, prediction, reference]) => ({
    id: newId(),
    input,
    prediction,
    reference,
    context: '',
  }))
}

/** The current dataset being edited (doc §6.3). Persisted to localStorage so a
 *  refresh doesn't lose the user's cases. */
export const useDatasetStore = defineStore('dataset', () => {
  const name = ref('Untitled dataset')
  const cases = ref<TestCase[]>([])

  // Hydrate from localStorage, falling back to a single blank case.
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved) as { name?: string; cases?: TestCase[] }
      if (parsed.name) name.value = parsed.name
      if (Array.isArray(parsed.cases)) cases.value = parsed.cases
    } catch {
      /* ignore corrupt storage */
    }
  }
  if (cases.value.length === 0) cases.value = [emptyCase()]

  watch(
    [name, cases],
    () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ name: name.value, cases: cases.value }))
    },
    { deep: true },
  )

  // Which metric families are even valid is driven by the data present.
  const hasAnyReference = computed(() =>
    cases.value.some((c) => (c.reference ?? '').trim() !== ''),
  )
  const hasAnyContext = computed(() => cases.value.some((c) => (c.context ?? '').trim() !== ''))
  // Only cases with a prediction can be scored at all.
  const readyCases = computed(() => cases.value.filter((c) => (c.prediction ?? '').trim() !== ''))

  function addCase() {
    cases.value.push(emptyCase())
  }
  function removeCase(id: string) {
    cases.value = cases.value.filter((c) => c.id !== id)
    if (cases.value.length === 0) cases.value = [emptyCase()]
  }
  function clear() {
    name.value = 'Untitled dataset'
    cases.value = [emptyCase()]
  }
  function loadExample() {
    name.value = 'Example: QA + summarization'
    cases.value = exampleCases()
  }
  function loadClassificationExample() {
    name.value = 'Example: sentiment classification'
    cases.value = classificationCases()
  }
  /** Replace cases from imported rows (used by the JSON import). */
  function setCases(rows: Partial<TestCase>[]) {
    cases.value = rows.map((r) => ({
      id: newId(),
      input: r.input ?? '',
      prediction: r.prediction ?? '',
      reference: r.reference ?? '',
      context: r.context ?? '',
    }))
    if (cases.value.length === 0) cases.value = [emptyCase()]
  }

  return {
    name,
    cases,
    hasAnyReference,
    hasAnyContext,
    readyCases,
    addCase,
    removeCase,
    clear,
    loadExample,
    loadClassificationExample,
    setCases,
  }
})
