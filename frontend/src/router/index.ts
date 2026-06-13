import { createRouter, createWebHistory } from 'vue-router'

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
  ],
})
