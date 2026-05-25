import {defineStore} from 'pinia'
import {ref} from 'vue'
import {
    fetchChores, createChore, updateChore, deleteChore, markChoreDone,
} from '../services/api'
import type {Chore} from '../types'

/**
 * Compute the next due date for a chore.
 * due = next Sunday >= (last_done + interval_days)
 * If last_done is null, chore has never been done → always overdue.
 */
export function getChoreNextDue(chore: Chore): string | null {
    if (!chore.last_done) return null
    const base = new Date(chore.last_done + 'T00:00:00')
    base.setDate(base.getDate() + chore.interval_days)
    // Advance to next Sunday (0 = Sunday)
    const day = base.getDay()
    if (day !== 0) base.setDate(base.getDate() + (7 - day))
    return base.toISOString().slice(0, 10)
}

export function isChoreOverdue(chore: Chore): boolean {
    if (!chore.last_done) return true
    const due = getChoreNextDue(chore)
    if (!due) return true
    const today = new Date().toISOString().slice(0, 10)
    return today >= due
}

export const useChoreStore = defineStore('chores', () => {
    const chores = ref<Chore[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)

    async function load(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            chores.value = await fetchChores()
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    async function add(title: string, interval_days: number): Promise<Chore> {
        const row = await createChore(title, interval_days)
        chores.value.push(row)
        return row
    }

    async function update(id: number, title: string, interval_days: number): Promise<Chore> {
        const row = await updateChore(id, title, interval_days)
        const idx = chores.value.findIndex(c => c.id === id)
        if (idx !== -1) chores.value[idx] = row
        return row
    }

    async function remove(id: number): Promise<void> {
        await deleteChore(id)
        chores.value = chores.value.filter(c => c.id !== id)
    }

    async function markDone(id: number): Promise<Chore> {
        const today = new Date().toISOString().slice(0, 10)
        const row = await markChoreDone(id, today)
        const idx = chores.value.findIndex(c => c.id === id)
        if (idx !== -1) chores.value[idx] = row
        return row
    }

    return {chores, loading, error, load, add, update, remove, markDone}
})
