import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchWorkouts, setWorkoutValue } from '../services/api.js'

const RETRY_INTERVAL = 3000

// Generate columns for exercises 1-4, sets 1-3
function buildColumns() {
    const cols = [
        { key: 'date', label: 'Date', editable: false, width: 190, colType: 'date' },
        { key: 'type', label: 'Type', editable: true, width: 55, colType: 'text' },
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

    cols.push({ key: 'notes', label: 'Notes', editable: true, width: 160, colType: 'text' })
    return cols
}

export const WORKOUT_COLUMNS = buildColumns()

const TYPE_COLORS = {
    push: { bg: '#166534', text: '#86efac' },
    pull: { bg: '#1e3a5f', text: '#93c5fd' },
    legs: { bg: '#581c87', text: '#d8b4fe' },
    rest: { bg: '#27272a', text: '#a1a1aa' },
}

export function getWorkoutRowColor(row) {
    const t = (row.type || '').toLowerCase().trim()
    return TYPE_COLORS[t] || null
}

export const useWorkoutStore = defineStore('workouts', () => {
    const rows = ref([])
    const loading = ref(false)
    const error = ref(null)
    let retryTimer = null

    function scheduleRetry() {
        if (retryTimer) return
        retryTimer = setInterval(() => { load() }, RETRY_INTERVAL)
    }

    function clearRetry() {
        if (retryTimer) { clearInterval(retryTimer); retryTimer = null }
    }

    async function load() {
        loading.value = true
        error.value = null
        try {
            rows.value = await fetchWorkouts()
            clearRetry()
        } catch (e) {
            error.value = e.message
            scheduleRetry()
        } finally {
            loading.value = false
        }
    }

    async function setValue(date, column, value) {
        const row = rows.value.find(r => r.date === date)
        if (row) row[column] = value

        try {
            const updatedRow = await setWorkoutValue(date, column, value)
            const idx = rows.value.findIndex(r => r.date === updatedRow.date)
            if (idx !== -1) rows.value[idx] = updatedRow
            else rows.value.unshift(updatedRow)
        } catch (e) {
            error.value = e.message
            await load()
        }
    }

    return { rows, loading, error, load, setValue }
})
