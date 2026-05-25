<template>
    <div class="app-shell">
        <Menubar :model="navItems" class="app-menubar">
            <template #item="{item, props}">
                <router-link :to="item.route" v-bind="props.action" class="flex items-center gap-2">
                    <span>{{ item.label }}</span>
                </router-link>
            </template>
        </Menubar>
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

<script setup lang="ts">
import {onMounted} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import Menubar from 'primevue/menubar'
import {useSettingsStore} from './stores/settings'
import DashboardPage from './pages/DashboardPage.vue'
import WorkoutPage from './pages/WorkoutPage.vue'
import TodoPage from './pages/TodoPage.vue'
import WorkoutTimerPage from './pages/WorkoutTimerPage.vue'
import ChoresPage from './pages/ChoresPage.vue'
import CalendarPage from './pages/CalendarPage.vue'
import StatsPage from './pages/StatsPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()

const navItems = [
    {label: 'Dashboard', route: '/'},
    {label: 'Workout', route: '/workout'},
    {label: 'Timer', route: '/timer'},
    {label: 'Todo', route: '/todo'},
    {label: 'Chores', route: '/chores'},
    {label: 'Calendar', route: '/calendar'},
    {label: 'Stats', route: '/stats'},
    {label: 'Settings', route: '/settings'},
]

onMounted(() => {
    settingsStore.load()
})
</script>

<style lang="scss">
.app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: #18181b;
    color: #f4f4f5;
}

.app-menubar {
    flex-shrink: 0;
    border-radius: 0 !important;
    border-left: none !important;
    border-right: none !important;
    border-top: none !important;
}

.app-content {
    flex: 1;
    min-height: 0;
}
</style>
