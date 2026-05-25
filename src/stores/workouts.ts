import {defineStore} from 'pinia'
import {ref} from 'vue'
import * as localDb from '../services/local-db'
import type {WorkoutRow, WorkoutColumn, CellColor} from '../types'

// Generate columns for exercises 1-4, sets 1-5
function buildColumns(): WorkoutColumn[] {
    const cols: WorkoutColumn[] = [
        {key: 'date', label: 'Date', editable: false, width: 190, colType: 'date'},
        {key: 'type', label: 'Type', editable: true, width: 55, colType: 'text'},
    ]

    for (let ex = 1; ex <= 4; ex++) {
        cols.push({
            key: `e${ex}_name`,
            label: `E${ex}`,
            editable: true,
            width: 72,
            colType: 'text',
        })
        for (let set = 1; set <= 5; set++) {
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

    function load(): void {
        loading.value = true
        error.value = null
        try {
            localDb.ensureWorkoutRows()
            rows.value = localDb.getAll('workouts') as WorkoutRow[]
            rows.value.sort((a, b) => a.date.localeCompare(b.date))
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    function setValue(date: string, column: string, value: string | number | null): void {
        const row = rows.value.find(r => r.date === date)
        if (row) row[column] = value
        localDb.upsert('workouts', {date}, {[column]: value})
    }

    localDb.onChange((table) => {
        if (table === 'workouts') load()
    })

    return {rows, loading, error, load, setValue}
})
