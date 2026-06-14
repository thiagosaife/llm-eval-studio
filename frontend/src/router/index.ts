import { createRouter, createWebHistory } from 'vue-router'

// Height of the sticky chrome an anchor must clear, measured live so it stays
// correct whatever's pinned: always the top bar, plus the guide's sticky
// table-of-contents when present. Without this, a heading lands *behind* that
// chrome and reads as "out of place".
function stickyOffset(): number {
  let offset = 20 // breathing room below the chrome
  for (const sel of ['.topbar', '.toc']) {
    const el = document.querySelector(sel)
    if (el instanceof HTMLElement) offset += el.offsetHeight
  }
  return offset
}

// Wait for the anchor target to exist (the guide is lazy-loaded, so on a fresh
// deep-link the element isn't in the DOM yet), then resolve the scroll target.
function scrollToHash(hash: string, smooth: boolean) {
  return new Promise<{ el: string; top: number; behavior: ScrollBehavior }>((resolve) => {
    const attempt = (n: number) => {
      if (document.querySelector(hash) || n > 20) {
        resolve({ el: hash, top: stickyOffset(), behavior: smooth ? 'smooth' : 'auto' })
      } else {
        requestAnimationFrame(() => attempt(n + 1))
      }
    }
    attempt(0)
  })
}

// The three views from the design doc (§6.1). Lazy-loaded so each route is its
// own chunk.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/datasets' },
    {
      path: '/datasets',
      name: 'datasets',
      component: () => import('../views/DatasetsView.vue'),
      meta: { step: 1, label: 'Dataset' },
    },
    {
      path: '/run',
      name: 'run',
      component: () => import('../views/RunView.vue'),
      meta: { step: 2, label: 'Run' },
    },
    {
      path: '/results/:runId',
      name: 'results',
      component: () => import('../views/ResultsView.vue'),
      props: true,
      meta: { step: 3, label: 'Results' },
    },
    // Reference page: explains every metric + a glossary. Opened in a new tab
    // from the "!" tips in the picker and the dataset editor.
    {
      path: '/guide',
      name: 'guide',
      component: () => import('../views/GuideView.vue'),
      meta: { label: 'Metrics guide' },
    },
    // Side tool: embed + project vectors to 2-D to learn how PCA/t-SNE/UMAP behave.
    {
      path: '/explore',
      name: 'explore',
      component: () => import('../views/ExploreView.vue'),
      meta: { label: 'Explore' },
    },
  ],
  // Jump to #metric-… / #term-… anchors when the guide is opened via a tip;
  // restore the saved position on back/forward, else scroll to top.
  scrollBehavior(to, from, savedPosition) {
    // Smooth for in-page jumps (TOC, chips); instant when arriving via a
    // deep link / new tab, where you expect to land there immediately.
    if (to.hash) return scrollToHash(to.hash, from.name === to.name)
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})
