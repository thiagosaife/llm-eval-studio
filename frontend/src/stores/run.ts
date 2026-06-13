import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { GenerateResponse, OperationalSummary, RunResponse, TestCase } from '../api/types'

export type RunStatus = 'idle' | 'running' | 'done' | 'error'

/** Selected metrics, model config, run status, and the latest results (doc §6.3). */
export const useRunStore = defineStore('run', () => {
  const selectedMetrics = ref<string[]>([])
  const status = ref<RunStatus>('idle')
  const error = ref<string | null>(null)
  const currentRun = ref<RunResponse | null>(null)

  // Model config — shared by live generation and the LLM-judge (doc §6.1).
  const model = ref<string>('claude-opus-4-8')
  const systemPrompt = ref<string>('')
  const maxTokens = ref<number>(1024)
  const rubric = ref<string>('')

  // Live-generation state.
  const generating = ref(false)
  const genError = ref<string | null>(null)
  const genSummary = ref<OperationalSummary | null>(null)

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
        judge: { model: model.value, rubric: rubric.value.trim() || null },
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
        model: model.value,
        system: systemPrompt.value.trim() || null,
        max_tokens: maxTokens.value,
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
    model,
    systemPrompt,
    maxTokens,
    rubric,
    generating,
    genError,
    genSummary,
    toggleMetric,
    isSelected,
    deselect,
    run,
    generate,
    loadRun,
  }
})
