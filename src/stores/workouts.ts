import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchWorkouts, setWorkoutValue} from '../services/api'
import type {WorkoutRow, WorkoutColumn, CellColor} from '../types'

const RETRY_INTERVAL = 3000

// Generate columns for exercises 1-4, sets 1-3
function buildColumns(): WorkoutColumn[] {
    const cols: WorkoutColumn[] = [
        {key: 'date', label: 'Date', editable: false, width: 190, colType: 'date'},
        {key: 'type', label: 'Type', editable: true, width: 55, colType: 'text'},
    ]

    for (let ex = 1; ex <= 4; ex++) {
        for (let set = 1; set <= 3; set++) {
            cols.push({
                key: `e${ex}s${set}_wt`,
                label: `${ex}-${set} wt`,
                editable: true,
                width: 56,
                displayFormat: 'kg',
                colType: 'number',
            })
            cols.push({
                key: `e${ex}s${set}_reps`,
                label: `${ex}-${set} rp`,
                editable: true,
                width: 48,
                colType: 'number',
            })
        }
    }

    cols.push({key: 'notes', label: 'Notes', editable: true, width: 160, colType: 'text'})
    return cols
}

export const WORKOUT_COLUMNS: WorkoutColumn[] = buildColumns()

const TYPE_COLORS: Record<string, CellColor> = {
    push: {bg: '#166534', text: '#86efac'},
    pull: {bg: '#1e3a5f', text: '#93c5fd'},
    legs: {bg: '#581c87', text: '#d8b4fe'},
    rest: {bg: '#27272a', text: '#a1a1aa'},
}

export function getWorkoutRowColor(row: WorkoutRow): CellColor | null {
    const t = (row.type || '').toLowerCase().trim()
    return TYPE_COLORS[t] || null
}

export const useWorkoutStore = defineStore('workouts', () => {
    const rows = ref<WorkoutRow[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    let retryTimer: ReturnType<typeof setInterval> | null = null

    function scheduleRetry(): void {
        if (retryTimer) return
        retryTimer = setInterval(() => {load()}, RETRY_INTERVAL)
    }

    function clearRetry(): void {
        if (retryTimer) {clearInterval(retryTimer); retryTimer = null}
    }

    async function load(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            rows.value = await fetchWorkouts()
            clearRetry()
        } catch (e: unknown) {
            error.value = (e as Error).message
            scheduleRetry()
        } finally {
            loading.value = false
        }
    }

    async function setValue(date: string, column: string, value: string | number | null): Promise<void> {
        const row = rows.value.find(r => r.date === date)
        if (row) row[column] = value

        try {
            const updatedRow = await setWorkoutValue(date, column, value)
            const idx = rows.value.findIndex(r => r.date === updatedRow.date)
            if (idx !== -1) rows.value[idx] = updatedRow
            else rows.value.unshift(updatedRow)
        } catch (e: unknown) {
            error.value = (e as Error).message
            await load()
        }
    }

    return {rows, loading, error, load, setValue}
})
