import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import * as localDb from '../services/local-db'

export interface TimerState {
    id: string
    activity: string
    started_at: string
    paused_at: string | null
    accumulated_ms: number
}

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

    function load(): void {
        try {
            timers.value = localDb.getAll('habit_timer')
            timers.value.sort((a, b) => a.id.localeCompare(b.id))
        } catch {
            // Silently fail
        }
    }

    function start(activity: string): void {
        const timestamp = new Date().toISOString()
        const id = crypto.randomUUID()
        localDb.upsert('habit_timer', {id}, {
            activity, started_at: timestamp, paused_at: null, accumulated_ms: 0,
        })
        timers.value.push({id, activity, started_at: timestamp, paused_at: null, accumulated_ms: 0})
    }

    function pause(timerId: string): void {
        const timestamp = new Date().toISOString()
        localDb.upsert('habit_timer', {id: timerId}, {paused_at: timestamp})
        const idx = timers.value.findIndex(t => t.id === timerId)
        if (idx !== -1) timers.value[idx]!.paused_at = timestamp
    }

    function resume(timerId: string): void {
        const timer = timers.value.find(t => t.id === timerId)
        if (!timer || !timer.paused_at) return
        const now = new Date()
        const pausedAt = new Date(timer.paused_at)
        const pauseDurationMs = now.getTime() - pausedAt.getTime()
        const newAccumulated = (timer.accumulated_ms || 0) + pauseDurationMs
        localDb.upsert('habit_timer', {id: timerId}, {paused_at: null, accumulated_ms: newAccumulated})
        timer.paused_at = null
        timer.accumulated_ms = newAccumulated
    }

    function stop(timerId: string): void {
        const timer = timers.value.find(t => t.id === timerId)
        if (!timer) return

        const stoppedAt = new Date()
        const startedAt = new Date(timer.started_at)
        let accumulatedMs = timer.accumulated_ms || 0

        let effectiveEnd: Date
        if (timer.paused_at) {
            const pausedAt = new Date(timer.paused_at)
            accumulatedMs += stoppedAt.getTime() - pausedAt.getTime()
            effectiveEnd = pausedAt
        } else {
            effectiveEnd = stoppedAt
        }

        const totalActiveMs = Math.max(0, (effectiveEnd.getTime() - startedAt.getTime()) - accumulatedMs)

        // Split across days
        const dayWall: Record<string, number> = {}
        let ct = new Date(startedAt)
        while (ct < effectiveEnd) {
            const dayStr = ct.toISOString().slice(0, 10)
            const nextMidnight = new Date(dayStr + 'T00:00:00')
            nextMidnight.setDate(nextMidnight.getDate() + 1)
            const dayEnd = nextMidnight < effectiveEnd ? nextMidnight : effectiveEnd
            dayWall[dayStr] = (dayWall[dayStr] || 0) + (dayEnd.getTime() - ct.getTime())
            ct = dayEnd
        }

        const totalWallMs = Object.values(dayWall).reduce((s, v) => s + v, 0)
        if (totalWallMs > 0) {
            for (const [dayStr, wallMs] of Object.entries(dayWall)) {
                const ratio = wallMs / totalWallMs
                const activeMn = Math.floor((totalActiveMs * ratio) / 60000)
                if (activeMn <= 0) continue

                // Read current value and add
                const existing = localDb.getByPk('habits', {date: dayStr})
                const currentVal = existing ? (existing[timer.activity] as number || 0) : 0
                localDb.upsert('habits', {date: dayStr}, {[timer.activity]: currentVal + activeMn})
            }
        }

        // Delete the timer
        localDb.remove('habit_timer', {id: timerId})
        timers.value = timers.value.filter(t => t.id !== timerId)
    }

    localDb.onChange((table) => {
        if (table === 'habit_timer') load()
    })

    return {
        timers, hasActive,
        getElapsedMs, formatElapsed, getActivityLabel,
        load, start, pause, resume, stop,
    }
})
