<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  FURTHER_READING,
  GLOSSARY,
  METRIC_GROUPS,
  glossaryTerm,
  metricAnchor,
  termAnchor,
} from '../content/metricGuide'
import { useMetricsCatalogStore } from '../stores/metricsCatalog'

// A reference page (doc-style) explaining every metric plus a glossary. The
// static teaching content lives in content/metricGuide.ts; here we merge it
// with the live catalog so availability ("needs install", "needs API key")
// reflects the real backend.
const catalog = useMetricsCatalogStore()

onMounted(() => catalog.load())

function info(id: string) {
  return catalog.byId[id]
}
</script>

<template>
  <div class="guide">
    <header class="page-head">
      <h1>Metrics &amp; concepts guide</h1>
      <p class="muted">
        Every metric in LLM Eval Studio, what it actually measures, how to read it, and where it
        misleads — plus a glossary of the terms behind them. There's no single "best" metric: the
        right one depends on your task, so each entry says when to reach for it.
      </p>
    </header>

    <!-- Table of contents -->
    <nav class="toc card pad" aria-label="On this page">
      <span class="toc-label">Jump to</span>
      <div class="toc-links">
        <RouterLink
          v-for="g in METRIC_GROUPS"
          :key="g.family"
          :to="{ name: 'guide', hash: `#family-${g.family}` }"
          class="toc-link"
        >
          {{ g.label }}
        </RouterLink>
        <RouterLink :to="{ name: 'guide', hash: '#glossary' }" class="toc-link">Glossary</RouterLink>
        <RouterLink :to="{ name: 'guide', hash: '#reading' }" class="toc-link">
          Further reading
        </RouterLink>
      </div>
    </nav>

    <!-- Metric groups -->
    <section v-for="g in METRIC_GROUPS" :key="g.family" :id="`family-${g.family}`" class="family">
      <div class="family-head">
        <h2>{{ g.label }}</h2>
        <p class="muted">{{ g.blurb }}</p>
      </div>

      <article v-for="m in g.metrics" :key="m.id" :id="metricAnchor(m.id)" class="card pad metric">
        <div class="row spread center wrap metric-head">
          <h3>{{ m.name }}</h3>
          <div class="row wrap" style="gap: 5px">
            <span class="badge">Range: {{ m.range }}</span>
            <span v-if="info(m.id)?.requires_reference" class="badge ref">needs reference</span>
            <span v-if="info(m.id)?.requires_context" class="badge ref">needs context</span>
            <span v-if="info(m.id)?.produces_rationale" class="badge primary">writes a rationale</span>
            <span v-if="info(m.id) && !info(m.id)?.available" class="badge ref">unavailable</span>
          </div>
        </div>

        <div
          v-if="info(m.id) && !info(m.id)?.available"
          class="banner info small"
          style="margin-bottom: 12px"
        >
          {{ info(m.id)?.unavailable_reason }}
        </div>

        <p v-for="(para, i) in m.explanation" :key="i" class="para">{{ para }}</p>

        <dl class="facts">
          <template v-if="m.formula">
            <dt>How it's computed</dt>
            <dd>{{ m.formula }}</dd>
          </template>
          <template v-if="m.example">
            <dt>Example</dt>
            <dd>{{ m.example }}</dd>
          </template>
          <template v-if="m.whenToUse">
            <dt>When to use it</dt>
            <dd>{{ m.whenToUse }}</dd>
          </template>
          <template v-if="info(m.id)?.how_to_read">
            <dt>Read it</dt>
            <dd>{{ info(m.id)?.how_to_read }}</dd>
          </template>
          <template v-if="info(m.id)?.caveat">
            <dt class="warn">It lies when</dt>
            <dd>{{ info(m.id)?.caveat }}</dd>
          </template>
        </dl>

        <div v-if="m.related?.length" class="related">
          <span class="related-label">Related terms:</span>
          <template v-for="slug in m.related" :key="slug">
            <RouterLink
              v-if="glossaryTerm(slug)"
              :to="{ name: 'guide', hash: `#${termAnchor(slug)}` }"
              class="chip"
            >
              {{ glossaryTerm(slug)?.term }}
            </RouterLink>
          </template>
        </div>

        <div v-if="m.links?.length" class="links">
          <a v-for="l in m.links" :key="l.url" :href="l.url" target="_blank" rel="noopener noreferrer">
            {{ l.label }} ↗
          </a>
        </div>
      </article>
    </section>

    <!-- Glossary -->
    <section id="glossary" class="family">
      <div class="family-head">
        <h2>Glossary</h2>
        <p class="muted">The recurring concepts the metrics are built on.</p>
      </div>
      <dl class="card pad glossary">
        <div v-for="t in GLOSSARY" :key="t.slug" :id="termAnchor(t.slug)" class="glossary-row">
          <dt>{{ t.term }}</dt>
          <dd>{{ t.definition }}</dd>
        </div>
      </dl>
    </section>

    <!-- Further reading -->
    <section id="reading" class="family">
      <div class="family-head">
        <h2>Further reading</h2>
        <p class="muted">Primary sources and docs if you want to go deeper.</p>
      </div>
      <ul class="card pad reading">
        <li v-for="l in FURTHER_READING" :key="l.url">
          <a :href="l.url" target="_blank" rel="noopener noreferrer">{{ l.label }} ↗</a>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.guide {
  max-width: 820px;
}
.page-head {
  margin-bottom: 20px;
}
.page-head h1 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.page-head p {
  margin: 0;
}

.toc {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 28px;
  position: sticky;
  top: 64px;
  z-index: 5;
}
.toc-label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--c-text-soft);
  white-space: nowrap;
}
.toc-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}
.toc-link {
  font-size: 0.88rem;
  font-weight: 500;
}

.family {
  margin-bottom: 34px;
  scroll-margin-top: 80px;
}
.family-head {
  margin-bottom: 14px;
}
.family-head h2 {
  font-size: 1.18rem;
  margin-bottom: 4px;
}
.family-head p {
  margin: 0;
  max-width: 70ch;
}

.metric {
  margin-bottom: 14px;
  scroll-margin-top: 80px;
}
.metric-head {
  margin-bottom: 12px;
  gap: 10px;
}
.metric-head h3 {
  font-size: 1.04rem;
}
.para {
  margin: 0 0 10px;
  color: var(--c-text);
}

.facts {
  margin: 14px 0 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 6px 16px;
  border-top: 1px solid var(--c-border);
  padding-top: 12px;
}
.facts dt {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--c-text-soft);
  white-space: nowrap;
}
.facts dt.warn {
  color: var(--c-warn);
}
.facts dd {
  margin: 0;
  font-size: 0.9rem;
}

.related {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
}
.related-label {
  font-size: 0.78rem;
  color: var(--c-text-soft);
}
.chip {
  font-size: 0.76rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  color: var(--c-text-soft);
}
.chip:hover {
  border-color: var(--c-primary);
  color: var(--c-primary);
}

.links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
  font-size: 0.85rem;
}

.glossary {
  display: grid;
  gap: 0;
}
.glossary-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--c-border);
  scroll-margin-top: 80px;
}
.glossary-row:first-child {
  padding-top: 0;
}
.glossary-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.glossary dt {
  font-weight: 700;
  margin-bottom: 3px;
}
.glossary dd {
  margin: 0;
  color: var(--c-text-soft);
  font-size: 0.9rem;
}
.glossary-row:target dt {
  color: var(--c-primary);
}

.reading {
  list-style: none;
  margin: 0;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.reading li {
  font-size: 0.9rem;
}
@media (max-width: 640px) {
  .facts {
    grid-template-columns: 1fr;
    gap: 2px 0;
  }
  .facts dt {
    margin-top: 8px;
  }
}
</style>
