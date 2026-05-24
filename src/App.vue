<template>
  <div class="app-shell">
    <nav class="app-tabs">
      <router-link to="/" class="app-tab" active-class="app-tab--active" exact>Dashboard</router-link>
      <router-link to="/workout" class="app-tab" active-class="app-tab--active">Workout</router-link>
      <router-link to="/timer" class="app-tab" active-class="app-tab--active">Timer</router-link>
      <router-link to="/todo" class="app-tab" active-class="app-tab--active">Todo</router-link>
      <router-link to="/chores" class="app-tab" active-class="app-tab--active">Chores</router-link>
      <router-link to="/calendar" class="app-tab" active-class="app-tab--active">Calendar</router-link>
      <router-link to="/stats" class="app-tab" active-class="app-tab--active">Stats</router-link>
      <router-link to="/settings" class="app-tab" active-class="app-tab--active">Settings</router-link>
    </nav>
    <div class="app-content">
      <DashboardPage :style="route.path !== '/' ? 'visibility: hidden; z-index: -999999; position: fixed;' : ''" />
      <WorkoutPage :style="route.path !== '/workout' ? 'visibility: hidden; z-index: -999999; position: fixed;' : ''" />
      <TodoPage v-show="route.path === '/todo'" />
      <WorkoutTimerPage v-show="route.path === '/timer'" />
      <ChoresPage v-show="route.path === '/chores'" />
      <CalendarPage v-show="route.path === '/calendar'" />
      <StatsPage v-show="route.path === '/stats'" />
      <SettingsPage v-show="route.path === '/settings'" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from './stores/settings.js'
import DashboardPage from './pages/DashboardPage.vue'
import WorkoutPage from './pages/WorkoutPage.vue'
import TodoPage from './pages/TodoPage.vue'
import WorkoutTimerPage from './pages/WorkoutTimerPage.vue'
import ChoresPage from './pages/ChoresPage.vue'
import CalendarPage from './pages/CalendarPage.vue'
import StatsPage from './pages/StatsPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
onMounted(() => {
  settingsStore.load()
})
</script>
