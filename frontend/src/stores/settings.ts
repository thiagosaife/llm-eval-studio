import { defineStore } from 'pinia'
import { reactive, watch } from 'vue'

/**
 * "Bring your own key" storage. Keys are entered on the Settings page, kept in
 * the browser (localStorage), and sent with each billable request as a
 * provider_id -> key map. The backend uses a request key when present and falls
 * back to its own env; it never persists what the browser sends.
 *
 * This is a local teaching tool — keys live in localStorage, which is fine here
 * but not appropriate for a shared/hosted deployment (the Settings page says so).
 */
const KEYS_STORAGE = 'llm-eval:api-keys'

function loadKeys(): Record<string, string> {
  try {
    const raw = localStorage.getItem(KEYS_STORAGE)
    const parsed = raw ? JSON.parse(raw) : {}
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', () => {
  // provider id -> key (may be empty string while editing).
  const keys = reactive<Record<string, string>>(loadKeys())

  watch(
    keys,
    (v) => localStorage.setItem(KEYS_STORAGE, JSON.stringify(v)),
    { deep: true },
  )

  function setKey(provider: string, value: string) {
    keys[provider] = value
  }
  function clearKey(provider: string) {
    delete keys[provider]
  }
  function hasKey(provider: string): boolean {
    return !!(keys[provider] && keys[provider].trim())
  }

  /** Only the non-empty keys, to send with a request (provider id -> key). */
  function keysPayload(): Record<string, string> {
    const out: Record<string, string> = {}
    for (const [provider, value] of Object.entries(keys)) {
      if (value && value.trim()) out[provider] = value.trim()
    }
    return out
  }

  return { keys, setKey, clearKey, hasKey, keysPayload }
})
