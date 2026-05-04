import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/step/1', name: 'step1', component: () => import('../views/Step1SceneView.vue') },
    { path: '/step/2', name: 'step2', component: () => import('../views/Step2InputView.vue') },
    { path: '/step/3', name: 'step3', component: () => import('../views/Step3OutputView.vue') },
    { path: '/step/4', name: 'step4', component: () => import('../views/Step4ExportView.vue') },
  ],
})

export default router
