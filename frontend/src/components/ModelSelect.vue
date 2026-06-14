<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useProvidersStore } from '../stores/providers'

// A grouped provider+model picker, reused for both generation and the judge.
// Each provider is an <optgroup>; a model whose provider has no usable key
// (no env key and none entered in Settings) is disabled and flagged "needs key".
defineProps<{ modelValue: string; id?: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const providers = useProvidersStore()

function onChange(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="model-select">
    <select :id="id" class="select" :value="modelValue" @change="onChange">
      <optgroup v-for="p in providers.providers" :key="p.id" :label="p.name">
        <option
          v-for="m in p.models"
          :key="m.id"
          :value="m.id"
          :disabled="!providers.effectiveAvailable(p.id)"
        >
          {{ m.name }}{{ providers.effectiveAvailable(p.id) ? '' : ' — needs key' }}
        </option>
      </optgroup>
    </select>
    <p
      v-if="modelValue && !providers.modelAvailable(modelValue)"
      class="tiny muted needs-key"
    >
      No key for this model's provider.
      <RouterLink to="/settings">Add one in Settings</RouterLink> to run it.
    </p>
  </div>
</template>

<style scoped>
.model-select {
  width: 100%;
}
.select {
  font: inherit;
  width: 100%;
  padding: 8px 32px 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border-strong);
  background-color: var(--c-surface);
}
.needs-key {
  margin: 6px 0 0;
}
</style>
