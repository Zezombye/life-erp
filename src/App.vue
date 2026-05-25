<template>
    <div class="app-shell">
        <Menubar :model="navItems" class="app-menubar">
            <template #item="{item, props}">
                <router-link :to="item.route" v-bind="props.action" class="flex items-center gap-2">
                    <span>{{ item.label }}</span>
                </router-link>
            </template>
            <template #end>
                <span class="sync-indicator" :class="connectionState">
                    <span class="sync-dot"></span>
                    {{ connectionState === 'online' ? '' : connectionState }}
                    <span v-if="pendingCount > 0" class="sync-pending">{{ pendingCount }}</span>
                </span>
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
import {onMounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import Menubar from 'primevue/menubar'
import {useSettingsStore} from './stores/settings'
import {init as initSync, getConnectionState, getPendingCount} from './services/sync-engine'
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
const syncReady = ref(false)
const connectionState = getConnectionState()
const pendingCount = getPendingCount()

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

onMounted(async () => {
    await initSync()
    syncReady.value = true
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

.sync-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #a1a1aa;
    padding: 0 12px;
    text-transform: capitalize;
}

.sync-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
}

.sync-indicator.offline .sync-dot {
    background: #ef4444;
}

.sync-indicator.connecting .sync-dot {
    background: #eab308;
}

.sync-indicator.syncing .sync-dot {
    background: #3b82f6;
}

.sync-pending {
    background: #3b82f6;
    color: #fff;
    border-radius: 8px;
    padding: 0 5px;
    font-size: 0.65rem;
    min-width: 16px;
    text-align: center;
}
</style>
