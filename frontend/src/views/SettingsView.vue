<script setup lang="ts">
import { onMounted } from 'vue'
import type { ProviderInfo } from '../api/types'
import { useProvidersStore } from '../stores/providers'
import { useSettingsStore } from '../stores/settings'

// Bring-your-own-key settings. Keys are saved in this browser (localStorage) and
// sent with each billable request; the backend uses them over its own env and
// never persists what the browser sends.
const providers = useProvidersStore()
const settings = useSettingsStore()

onMounted(() => providers.load())

// Where a provider's credential comes from, for the status badge.
function status(p: ProviderInfo): { label: string; kind: string } {
  if (!p.sdk_installed) return { label: 'SDK not installed', kind: 'off' }
  if (settings.hasKey(p.id)) return { label: 'Using your key', kind: 'mine' }
  if (p.env_available) return { label: 'Backend env key', kind: 'env' }
  return { label: 'No key', kind: 'none' }
}
</script>

<template>
  <div class="settings">
    <header class="page-head">
      <h1>API keys</h1>
      <p class="muted">
        Add a key to enable a provider's models for live generation and the LLM-judge. Keys are
        stored <strong>in this browser only</strong> and sent with each run — fine for local use,
        not for a shared machine. The backend's own <code>.env</code> keys are used when a field is
        left blank.
      </p>
    </header>

    <p v-if="providers.loading" class="muted">Loading providers…</p>
    <div v-else-if="providers.error" class="banner error">{{ providers.error }}</div>

    <div v-else class="provider-list">
      <div v-for="p in providers.providers" :key="p.id" class="card pad provider">
        <div class="row spread center">
          <div>
            <h3>{{ p.name }}</h3>
            <p class="tiny muted">
              {{ p.models.length }} model{{ p.models.length === 1 ? '' : 's' }} · env var
              <code>{{ p.env_var }}</code>
            </p>
          </div>
          <span class="badge" :class="status(p).kind">{{ status(p).label }}</span>
        </div>

        <label class="field key-field">
          <span class="label">API key</span>
          <div class="key-row">
            <input
              v-model="settings.keys[p.id]"
              type="password"
              autocomplete="off"
              spellcheck="false"
              :placeholder="p.env_available ? 'Using backend env key — paste to override' : `Paste your ${p.name} key`"
              :disabled="!p.sdk_installed"
            />
            <button
              v-if="settings.hasKey(p.id)"
              class="btn-ghost btn-sm"
              type="button"
              @click="settings.clearKey(p.id)"
            >
              Clear
            </button>
          </div>
        </label>

        <p v-if="!p.sdk_installed" class="tiny muted">
          The {{ p.name }} SDK isn't installed on the backend — a key won't help until it is.
        </p>
        <p v-else-if="settings.hasKey(p.id)" class="tiny ok">
          ✓ Saved in this browser. Its models are now selectable on the Run page.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 20px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.page-head p {
  max-width: 72ch;
  margin: 0;
}
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.provider h3 {
  margin: 0;
}
.provider .tiny code,
.page-head code {
  background: var(--c-surface-2);
  padding: 1px 5px;
  border-radius: 5px;
}
.key-field {
  margin-top: 12px;
}
.key-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.key-row input {
  flex: 1;
  font: inherit;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background: var(--c-surface);
}
.badge.mine {
  background: var(--c-primary);
  color: #fff;
}
.badge.env {
  background: #d7f5e0;
  color: #1c8a4b;
}
.badge.none,
.badge.off {
  background: var(--c-surface-2);
  color: var(--c-text-soft);
}
.ok {
  color: #1c8a4b;
  margin: 8px 0 0;
}
</style>
