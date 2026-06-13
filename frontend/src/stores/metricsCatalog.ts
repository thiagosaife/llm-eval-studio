import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { MetricInfo } from '../api/types'

/**
 * The metric definitions, fetched once from the backend so the picker, the
 * summary cards, and the inspector all describe metrics identically (doc §6.3).
 */
export const useMetricsCatalogStore = defineStore('metricsCatalog', () => {
  const metrics = ref<MetricInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  const byId = computed<Record<string, MetricInfo>>(() =>
    Object.fromEntries(metrics.value.map((m) => [m.id, m])),
  )

  async function load(force = false) {
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

  return { metrics, loading, error, loaded, byId, load }
})
