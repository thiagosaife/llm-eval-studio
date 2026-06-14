<script setup lang="ts">
import { useId } from 'vue'

// A small "!" affordance that reveals a brief explanation on hover/focus.
// When `href` is set it becomes a link that opens the full explanation in a new
// tab; otherwise it's an inert button that only shows the bubble. Used in the
// metric picker and the dataset editor to make the app self-teaching.
const props = defineProps<{
  /** The brief explanation shown in the hover/focus bubble. */
  text: string
  /** If set, clicking opens this URL in a new tab (e.g. the metrics guide). */
  href?: string
  /** Accessible label for the trigger. */
  label?: string
}>()

const bubbleId = useId()
</script>

<template>
  <!-- Stop propagation so using the tip never toggles a parent control
       (e.g. the clickable metric card it lives inside). -->
  <span class="info-tip" @click.stop @keydown.enter.stop @keydown.space.stop>
    <a
      v-if="href"
      :href="href"
      target="_blank"
      rel="noopener noreferrer"
      class="info-trigger"
      :aria-label="label ?? 'Open explanation in a new tab'"
      :aria-describedby="bubbleId"
    >!</a>
    <button
      v-else
      type="button"
      class="info-trigger"
      :aria-label="label ?? 'More information'"
      :aria-describedby="bubbleId"
    >!</button>

    <span :id="bubbleId" class="bubble" role="tooltip">
      {{ text }}
      <span v-if="href" class="bubble-more">Click to open the full guide ↗</span>
    </span>
  </span>
</template>

<style scoped>
.info-tip {
  position: relative;
  display: inline-flex;
  align-items: center;
  /* Always sit a touch away from the text it annotates, and ride the text's
     vertical middle so it reads as part of the line. */
  margin-left: 5px;
  vertical-align: middle;
}
.info-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border-radius: 50%;
  border: 1.5px solid var(--c-border-strong);
  background: var(--c-surface);
  color: var(--c-text-soft);
  font-size: 0.7rem;
  font-weight: 800;
  line-height: 1;
  cursor: pointer;
  text-decoration: none;
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.info-trigger:hover,
.info-trigger:focus-visible {
  border-color: var(--c-primary);
  color: var(--c-primary);
  background: var(--c-primary-soft);
}
.bubble {
  position: absolute;
  z-index: 50;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: max-content;
  max-width: 260px;
  padding: 9px 11px;
  border-radius: var(--radius-sm);
  background: var(--c-text);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 400;
  line-height: 1.45;
  text-align: left;
  letter-spacing: normal;
  text-transform: none;
  box-shadow: var(--shadow-md);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.12s, visibility 0.12s;
  pointer-events: none;
}
/* Little arrow pointing up at the trigger. */
.bubble::before {
  content: '';
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-bottom-color: var(--c-text);
}
.info-tip:hover .bubble,
.info-tip:focus-within .bubble {
  opacity: 1;
  visibility: visible;
}
.bubble-more {
  display: block;
  margin-top: 5px;
  color: #c7d2fe;
  font-weight: 600;
}
</style>
