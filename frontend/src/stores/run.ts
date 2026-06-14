import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { api } from '../api/client'
import type {
  EstimateResponse,
  GenerateResponse,
  OperationalSummary,
  RunResponse,
  TestCase,
} from '../api/types'
import { useSettingsStore } from './settings'

export type RunStatus = 'idle' | 'running' | 'done' | 'error'

const SPEND_CAP_KEY = 'llm-eval:spend-cap'

function loadSpendCap(): number {
  const raw = localStorage.getItem(SPEND_CAP_KEY)
  const n = raw === null ? NaN : Number(raw)
  return Number.isFinite(n) && n >= 0 ? n : 1
}

/** Selected metrics, model config, run status, and the latest results (doc §6.3). */
export const useRunStore = defineStore('run', () => {
  const settings = useSettingsStore()

  const selectedMetrics = ref<string[]>([])
  const status = ref<RunStatus>('idle')
  const error = ref<string | null>(null)
  const currentRun = ref<RunResponse | null>(null)

  // Model config — generation and the LLM-judge each pick their own provider+model
  // (doc §6.1). Both default to Claude Opus; either can be any provider.
  const genModel = ref<string>('claude-opus-4-8')
  const judgeModel = ref<string>('claude-opus-4-8')
  const systemPrompt = ref<string>('')
  const maxTokens = ref<number>(1024)
  const rubric = ref<string>('')

  // Live-generation state.
  const generating = ref(false)
  const genError = ref<string | null>(null)
  const genSummary = ref<OperationalSummary | null>(null)

  // Pre-run cost estimate (doc §3.6). The heuristic estimate runs live without a
  // key; `spendCap` (USD) drives a confirmation gate before an expensive run.
  const estimateResult = ref<EstimateResponse | null>(null)
  const estimating = ref(false)
  const estimateError = ref<string | null>(null)
  const spendCap = ref<number>(loadSpendCap())
  watch(spendCap, (v) => localStorage.setItem(SPEND_CAP_KEY, String(v)))

  function toggleMetric(id: string) {
    const i = selectedMetrics.value.indexOf(id)
    if (i === -1) selectedMetrics.value.push(id)
    else selectedMetrics.value.splice(i, 1)
  }
  function isSelected(id: string) {
    return selectedMetrics.value.includes(id)
  }
  function deselect(id: string) {
    selectedMetrics.value = selectedMetrics.value.filter((m) => m !== id)
  }

  async function run(cases: TestCase[], datasetName: string): Promise<RunResponse> {
    status.value = 'running'
    error.value = null
    try {
      const result = await api.evaluate({
        metrics: selectedMetrics.value,
        cases,
        dataset_name: datasetName,
        judge: {
          model: judgeModel.value,
          rubric: rubric.value.trim() || null,
          keys: settings.keysPayload(),
        },
      })
      currentRun.value = result
      status.value = 'done'
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      status.value = 'error'
      throw e
    }
  }

  /** Produce predictions live from the configured model (doc §8.3). */
  async function generate(cases: TestCase[]): Promise<GenerateResponse> {
    generating.value = true
    genError.value = null
    try {
      const resp = await api.generate({
        cases,
        model: genModel.value,
        system: systemPrompt.value.trim() || null,
        max_tokens: maxTokens.value,
        keys: settings.keysPayload(),
      })
      genSummary.value = resp.summary
      return resp
    } catch (e) {
      genError.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      generating.value = false
    }
  }

  /** Project tokens + cost before running. Heuristic by default (no key needed);
   *  pass exact=true to use the free count_tokens endpoint when a key is set. */
  async function estimate(cases: TestCase[], exact = false): Promise<EstimateResponse | null> {
    if (selectedMetrics.value.length === 0 || cases.length === 0) {
      estimateResult.value = null
      return null
    }
    estimating.value = true
    estimateError.value = null
    try {
      const result = await api.estimate({
        metrics: selectedMetrics.value,
        cases,
        judge: {
          model: judgeModel.value,
          rubric: rubric.value.trim() || null,
          keys: settings.keysPayload(),
        },
        exact,
      })
      estimateResult.value = result
      return result
    } catch (e) {
      estimateError.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      estimating.value = false
    }
  }

  /** Load a run by id — from memory if it's the current one, else fetch it. */
  async function loadRun(runId: string): Promise<RunResponse> {
    if (currentRun.value?.run_id === runId) return currentRun.value
    const result = await api.getRun(runId)
    currentRun.value = result
    return result
  }

  return {
    selectedMetrics,
    status,
    error,
    currentRun,
    genModel,
    judgeModel,
    systemPrompt,
    maxTokens,
    rubric,
    generating,
    genError,
    genSummary,
    estimateResult,
    estimating,
    estimateError,
    spendCap,
    toggleMetric,
    isSelected,
    deselect,
    run,
    generate,
    estimate,
    loadRun,
  }
})
