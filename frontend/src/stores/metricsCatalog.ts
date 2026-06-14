import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { MetricInfo } from '../api/types'
import { useProvidersStore } from './providers'

/**
 * The metric catalog, fetched once from the backend so the picker, the summary
 * cards, and the inspector stay consistent with the engine (doc §6.3). Model /
 * provider availability lives in the providers store; `llmAvailable` here just
 * re-exposes it so existing call sites keep working.
 */
export const useMetricsCatalogStore = defineStore('metricsCatalog', () => {
  const metrics = ref<MetricInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  const providers = useProvidersStore()

  const byId = computed<Record<string, MetricInfo>>(() =>
    Object.fromEntries(metrics.value.map((m) => [m.id, m])),
  )

  // LLM features (judge / RAG / live generation) are on iff at least one provider
  // is effectively available (a backend env key, or a key entered in Settings).
  const llmAvailable = computed(() => providers.anyAvailable)
  const llmReason = computed(() =>
    providers.loaded
      ? 'Add an API key for Anthropic, OpenAI, or Gemini on the Settings page to enable live generation and LLM-judge metrics.'
      : 'Set an API key to enable live generation and LLM-judge metrics.',
  )

  async function load(force = false) {
    // Metrics + the provider catalog load together; the providers store dedupes.
    await providers.load(force)
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      metrics.value = await api.listMetrics()
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { metrics, loading, error, loaded, byId, llmAvailable, llmReason, load }
})
