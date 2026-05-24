const routes = [
  {
    path: '/',
    component: () => import('pages/DashboardPage.vue'),
  },
  {
    path: '/workout',
    component: () => import('pages/WorkoutPage.vue'),
  },
  {
    path: '/todo',
    component: () => import('pages/TodoPage.vue'),
  },
  {
    path: '/timer',
    component: () => import('pages/WorkoutTimerPage.vue'),
  },
  {
    path: '/chores',
    component: () => import('pages/ChoresPage.vue'),
  },
  {
    path: '/calendar',
    component: () => import('pages/CalendarPage.vue'),
  },
  {
    path: '/stats',
    component: () => import('pages/StatsPage.vue'),
  },
  {
    path: '/settings',
    component: () => import('pages/SettingsPage.vue'),
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes
