import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { RunResponse, TestCase } from '../api/types'

export type RunStatus = 'idle' | 'running' | 'done' | 'error'

/** Selected metrics, run status, and the latest results (doc §6.3). */
export const useRunStore = defineStore('run', () => {
  const selectedMetrics = ref<string[]>([])
  const status = ref<RunStatus>('idle')
  const error = ref<string | null>(null)
  const currentRun = ref<RunResponse | null>(null)

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

  /** Load a run by id — from memory if it's the current one, else fetch it
   *  (so a page refresh on /results/:id still works). */
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
    toggleMetric,
    isSelected,
    deselect,
    run,
    loadRun,
  }
})
