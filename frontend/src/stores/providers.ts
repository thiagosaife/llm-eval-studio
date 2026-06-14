import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { ModelInfo, ProviderInfo } from '../api/types'
import { useSettingsStore } from './settings'

/**
 * The provider catalog (Anthropic / OpenAI / Gemini): models + availability.
 * Fetched once from `GET /api/providers`. A provider is *effectively available*
 * when the backend env has a key OR the user pasted one in Settings — so a
 * browser-only key unlocks a provider without a backend restart.
 */
export const useProvidersStore = defineStore('providers', () => {
  const providers = ref<ProviderInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  const settings = useSettingsStore()

  const byId = computed<Record<string, ProviderInfo>>(() =>
    Object.fromEntries(providers.value.map((p) => [p.id, p])),
  )

  /** Every model across providers, in display order. */
  const allModels = computed<ModelInfo[]>(() => providers.value.flatMap((p) => p.models))

  function providerForModel(modelId: string): ProviderInfo | undefined {
    return providers.value.find((p) => p.models.some((m) => m.id === modelId))
  }

  /** Runnable now: backend env key, or a key the user entered in Settings. */
  function effectiveAvailable(providerId: string): boolean {
    const p = byId.value[providerId]
    if (!p) return false
    return p.env_available || settings.hasKey(providerId)
  }

  /** Is this specific model runnable (its provider effectively available)? */
  function modelAvailable(modelId: string): boolean {
    const p = providerForModel(modelId)
    return p ? effectiveAvailable(p.id) : false
  }

  /** True if at least one provider is effectively available. */
  const anyAvailable = computed(() => providers.value.some((p) => effectiveAvailable(p.id)))

  function label(modelId: string): string {
    for (const p of providers.value) {
      const m = p.models.find((x) => x.id === modelId)
      if (m) return m.name
    }
    return modelId
  }

  async function load(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      providers.value = await api.listProviders()
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return {
    providers,
    loading,
    error,
    loaded,
    byId,
    allModels,
    anyAvailable,
    providerForModel,
    effectiveAvailable,
    modelAvailable,
    label,
    load,
  }
})
