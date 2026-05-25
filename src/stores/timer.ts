import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import {fetchHabitTimers, postHabitTimer} from '../services/api'
import type {TimerState} from '../services/api'

export const TIMER_ACTIVITIES = [
    {key: 'job', label: 'Job'},
    {key: 'business', label: 'Business'},
    {key: 'reading_watching', label: 'Reading'},
    {key: 'misc', label: 'Misc'},
    {key: 'girls_family', label: 'Girls'},
    {key: 'mma', label: 'MMA'},
] as const

export const useTimerStore = defineStore('timer', () => {
    const timers = ref<TimerState[]>([])

    const hasActive = computed(() => timers.value.length > 0)

    function getElapsedMs(t: TimerState): number {
        const startedAt = new Date(t.started_at).getTime()
        const accumulated = t.accumulated_ms || 0
        if (t.paused_at) {
            const pausedAt = new Date(t.paused_at).getTime()
            return (pausedAt - startedAt) - accumulated
        }
        return (Date.now() - startedAt) - accumulated
    }

    function formatElapsed(ms: number): string {
        const totalSec = Math.floor(Math.max(0, ms) / 1000)
        const h = Math.floor(totalSec / 3600)
        const m = Math.floor((totalSec % 3600) / 60)
        const s = totalSec % 60
        if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
        return `${m}:${String(s).padStart(2, '0')}`
    }

    function getActivityLabel(key: string): string {
        return TIMER_ACTIVITIES.find(a => a.key === key)?.label ?? key
    }

    async function load() {
        try {
            timers.value = await fetchHabitTimers()
        } catch {
            // Silently fail
        }
    }

    async function start(activity: string) {
        const timestamp = new Date().toISOString()
        const result = await postHabitTimer('start', timestamp, {activity})
        timers.value.push(result)
    }

    async function pause(timerId: number) {
        const timestamp = new Date().toISOString()
        const result = await postHabitTimer('pause', timestamp, {timer_id: timerId})
        const idx = timers.value.findIndex(t => t.id === timerId)
        if (idx !== -1) timers.value[idx] = result
    }

    async function resume(timerId: number) {
        const timestamp = new Date().toISOString()
        const result = await postHabitTimer('resume', timestamp, {timer_id: timerId})
        const idx = timers.value.findIndex(t => t.id === timerId)
        if (idx !== -1) timers.value[idx] = result
    }

    async function stop(timerId: number) {
        const timestamp = new Date().toISOString()
        await postHabitTimer('stop', timestamp, {timer_id: timerId})
        timers.value = timers.value.filter(t => t.id !== timerId)
    }

    return {
        timers, hasActive,
        getElapsedMs, formatElapsed, getActivityLabel,
        load, start, pause, resume, stop,
    }
})
