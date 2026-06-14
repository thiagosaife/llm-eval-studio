import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  ProjectionAlgorithmInfo,
  ProjectRequest,
  ProjectResponse,
  SampleDatasetInfo,
} from '../api/types'

/**
 * The Explorer's catalog (DR algorithms + built-in sample datasets), fetched
 * once, plus the `project()` action. Mirrors the metricsCatalog store: the
 * catalog drives the picker and its availability flags, so a missing backend
 * library (e.g. umap-learn) greys the option out instead of erroring.
 */
export const useProjectionStore = defineStore('projection', () => {
  const algorithms = ref<ProjectionAlgorithmInfo[]>([])
  const samples = ref<SampleDatasetInfo[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const projecting = ref(false)
  const projectError = ref<string | null>(null)

  async function loadCatalog(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      const [a, s] = await Promise.all([
        api.listProjectionAlgorithms(),
        api.listProjectionSamples(),
      ])
      algorithms.value = a
      samples.value = s
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function project(req: ProjectRequest): Promise<ProjectResponse> {
    projecting.value = true
    projectError.value = null
    try {
      return await api.project(req)
    } catch (e) {
      projectError.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      projecting.value = false
    }
  }

  return {
    algorithms,
    samples,
    loaded,
    loading,
    error,
    projecting,
    projectError,
    loadCatalog,
    project,
  }
})
