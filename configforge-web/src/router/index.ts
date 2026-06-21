import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/change-password', name: 'change-password', component: () => import('../views/ChangePasswordView.vue') },
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    {
      path: '/config/new',
      name: 'config-new',
      component: () => import('../views/ConfigWizardView.vue'),
    },
    {
      path: '/guide',
      name: 'guide',
      component: () => import('../views/GuideView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsPage.vue'),
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('../views/TemplateMarketView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/ExecutionHistoryView.vue'),
    },
    {
      path: '/schedules',
      name: 'schedules',
      component: () => import('../views/SchedulesPage.vue'),
    },
    {
      path: '/step/:step(\\d)',
      redirect: () => '/config/new',
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ],
})

// Auth guard: redirect to /login when JWT is enabled and user is not authenticated
router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Check JWT status on first navigation (if unknown)
  if (auth.jwtEnabled === null) {
    await auth.checkJwtStatus()
  }

  // If JWT is not enabled, allow all routes
  if (!auth.jwtEnabled) {
    if (to.path === '/login') {
      next('/')
      return
    }
    next()
    return
  }

  // JWT is enabled — validate cached token on first load
  if (auth.token) {
    const valid = await auth.fetchUser()
    if (!valid) {
      auth.clearAuth()
    }
  }

  // JWT is enabled — check authentication
  if (to.path === '/login') {
    if (auth.isAuthenticated) {
      next('/')
      return
    }
    next()
    return
  }

  // Protected route — must be authenticated
  if (!auth.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 强制修改密码
  if (auth.needChangePassword && to.path !== '/change-password') {
    next('/change-password')
    return
  }

  next()
})

export default router
