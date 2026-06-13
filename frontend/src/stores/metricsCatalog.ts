import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { MetricInfo, ModelInfo } from '../api/types'

/**
 * The metric + model catalog, fetched once from the backend so the picker, the
 * summary cards, the inspector, and the model config all stay consistent with
 * the engine (doc §6.3).
 */
export const useMetricsCatalogStore = defineStore('metricsCatalog', () => {
  const metrics = ref<MetricInfo[]>([])
  const models = ref<ModelInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  const byId = computed<Record<string, MetricInfo>>(() =>
    Object.fromEntries(metrics.value.map((m) => [m.id, m])),
  )

  // LLM features (judge / RAG / live generation) are on iff the backend has a key.
  const llmAvailable = computed(() =>
    metrics.value.some((m) => (m.family === 'model_judge' || m.family === 'rag') && m.available),
  )
  const llmReason = computed(
    () =>
      metrics.value.find((m) => m.family === 'model_judge')?.unavailable_reason ??
      'Set ANTHROPIC_API_KEY in the backend to enable live generation and LLM-judge metrics.',
  )

  async function load(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      const [m, md] = await Promise.all([api.listMetrics(), api.listModels()])
      metrics.value = m
      models.value = md
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { metrics, models, loading, error, loaded, byId, llmAvailable, llmReason, load }
})
