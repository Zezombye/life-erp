import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchHabits, setHabitValue} from '../services/api'
import {useSettingsStore} from './settings'
import type {HabitRow, HabitColumn, CellColor} from '../types'

const RETRY_INTERVAL = 3000

const HABIT_KEYS = ['business', 'reading_watching', 'misc', 'girls_family', 'mma']

export const HABIT_COLUMNS: HabitColumn[] = [
    {key: 'date', label: 'Date', editable: false, width: 190},
    {key: 'weight', label: 'Weight', editable: true, width: 51},
    {key: 'job', label: 'Job', editable: true, width: 51, displayFormat: 'minutes'},
    {key: 'workout', label: 'Workout', editable: true, width: 64, displayFormat: 'percentage', colorGroup: 'percentage'},
    {key: 'business', label: 'Business', editable: true, width: 69, displayFormat: 'minutes', colorGroup: 'habit'},
    {key: 'reading_watching', label: 'Reading', editable: true, width: 69, displayFormat: 'minutes', colorGroup: 'habit'},
    {key: 'misc', label: 'Misc', editable: true, width: 69, displayFormat: 'minutes', colorGroup: 'habit'},
    {key: 'girls_family', label: 'Girls', editable: true, width: 69, displayFormat: 'minutes', colorGroup: 'habit'},
    {key: 'mma', label: 'MMA', editable: true, width: 69, displayFormat: 'minutes', colorGroup: 'habit'},
    {key: 'total', label: 'Total', editable: false, width: 72, displayFormat: 'percentage', colorGroup: 'percentage'},
    {key: 'total_hours', label: 'Hours', editable: false, width: 77, displayFormat: 'hours'},
]

// 0=red, <25=orange, <50=yellow, <75=green, <100=blue, >=100=purple
const COLOR_SCALE: CellColor[] = [
    {max: 0, bg: '#991b1b', text: '#fca5a5'},     // red
    {max: 25, bg: '#92400e', text: '#fcd34d'},     // orange
    {max: 50, bg: '#854d0e', text: '#fef08a'},     // yellow
    {max: 75, bg: '#166534', text: '#86efac'},     // green
    {max: 100, bg: '#1e3a5f', text: '#93c5fd'},    // blue
    {max: Infinity, bg: '#581c87', text: '#d8b4fe'}, // purple
]

export function getColorForPercent(pct: number | null | undefined): CellColor | null {
    if (pct === null || pct === undefined) return null
    for (const level of COLOR_SCALE) {
        if (pct <= level.max!) return level
    }
    return COLOR_SCALE[COLOR_SCALE.length - 1]!
}

export function getCellColor(row: HabitRow, col: HabitColumn): CellColor | null {
    if (!col.colorGroup) return null

    if (col.colorGroup === 'percentage') {
        return getColorForPercent(row[col.key] as number | null)
    }

    if (col.colorGroup === 'habit') {
        const settingsStore = useSettingsStore()
        const workMn = settingsStore.getNumber('work_mn', 300)
        const sum = HABIT_KEYS.reduce((s, k) => s + ((row[k] as number) || 0), 0)
        const pct = (sum / workMn) * 100
        return getColorForPercent(pct)
    }

    return null
}

export function getDateColor(dateStr: string): CellColor | null {
    if (!dateStr) return null
    const d = new Date(dateStr + 'T00:00:00')
    const day = d.getDay()
    const isWeekend = day === 0 || day === 6
    const isHoliday = isFrenchHoliday(d)
    if (isWeekend || isHoliday) return {bg: '#1c1c1e', text: '#71717a'}
    return {bg: '#27272a', text: '#a1a1aa'}
}

function isFrenchHoliday(d: Date): boolean {
    const m = d.getMonth() + 1
    const day = d.getDate()
    const y = d.getFullYear()
    // Fixed holidays
    if (m === 1 && day === 1) return true   // Jour de l'An
    if (m === 5 && day === 1) return true   // Fête du Travail
    if (m === 5 && day === 8) return true   // Victoire 1945
    if (m === 7 && day === 14) return true  // Fête nationale
    if (m === 8 && day === 15) return true  // Assomption
    if (m === 11 && day === 1) return true  // Toussaint
    if (m === 11 && day === 11) return true // Armistice
    if (m === 12 && day === 25) return true // Noël
    // Easter-based holidays (Lundi de Pâques, Ascension, Lundi de Pentecôte)
    const easter = computeEaster(y)
    const easterMs = easter.getTime()
    const dMs = new Date(y, m - 1, day).getTime()
    const dayMs = 86400000
    if (dMs === easterMs + 1 * dayMs) return true   // Lundi de Pâques
    if (dMs === easterMs + 39 * dayMs) return true  // Ascension
    if (dMs === easterMs + 50 * dayMs) return true  // Lundi de Pentecôte
    return false
}

function computeEaster(year: number): Date {
    // Anonymous Gregorian algorithm
    const a = year % 19
    const b = Math.floor(year / 100)
    const c = year % 100
    const d = Math.floor(b / 4)
    const e = b % 4
    const f = Math.floor((b + 8) / 25)
    const g = Math.floor((b - f + 1) / 3)
    const h = (19 * a + b - d - g + 15) % 30
    const i = Math.floor(c / 4)
    const k = c % 4
    const l = (32 + 2 * e + 2 * i - h - k) % 7
    const m = Math.floor((a + 11 * h + 22 * l) / 451)
    const month = Math.floor((h + l - 7 * m + 114) / 31)
    const day = ((h + l - 7 * m + 114) % 31) + 1
    return new Date(year, month - 1, day)
}

export const useHabitStore = defineStore('habits', () => {
    const rows = ref<HabitRow[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    let retryTimer: ReturnType<typeof setInterval> | null = null

    function scheduleRetry(): void {
        if (retryTimer) return
        retryTimer = setInterval(() => {
            load()
        }, RETRY_INTERVAL)
    }

    function clearRetry(): void {
        if (retryTimer) {
            clearInterval(retryTimer)
            retryTimer = null
        }
    }

    async function load(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            rows.value = await fetchHabits()
            clearRetry()
        } catch (e: unknown) {
            error.value = (e as Error).message
            scheduleRetry()
        } finally {
            loading.value = false
        }
    }

    async function setValue(date: string, column: string, value: number | null): Promise<void> {
        // Optimistic update
        const row = rows.value.find(r => r.date === date)
        if (row) {
            row[column] = value
        }

        try {
            const updatedRow = await setHabitValue(date, column, value)
            // Replace with server response
            const idx = rows.value.findIndex(r => r.date === updatedRow.date)
            if (idx !== -1) {
                rows.value[idx] = updatedRow
            } else {
                // New row (date didn't exist before)
                rows.value.unshift(updatedRow)
            }
        } catch (e: unknown) {
            error.value = (e as Error).message
            // Reload to get consistent state
            await load()
        }
    }

    return {rows, loading, error, load, setValue}
})
