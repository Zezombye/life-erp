import {defineStore} from 'pinia'
import {ref} from 'vue'
import * as localDb from '../services/local-db'
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

    function load(): void {
        loading.value = true
        error.value = null
        try {
            chores.value = localDb.getAll('chores')
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    function add(title: string, interval_days: number): Chore {
        const id = crypto.randomUUID()
        const row: Chore = {id, title, interval_days, last_done: null}
        localDb.upsert('chores', {id}, {title, interval_days, last_done: null})
        return row
    }

    function update(id: string, title: string, interval_days: number): void {
        localDb.upsert('chores', {id}, {title, interval_days})
        const idx = chores.value.findIndex(c => c.id === id)
        if (idx !== -1) {
            chores.value[idx]!.title = title
            chores.value[idx]!.interval_days = interval_days
        }
    }

    function remove(id: string): void {
        localDb.remove('chores', {id})
        chores.value = chores.value.filter(c => c.id !== id)
    }

    function markDone(id: string): void {
        const today = new Date().toISOString().slice(0, 10)
        localDb.upsert('chores', {id}, {last_done: today})
        const idx = chores.value.findIndex(c => c.id === id)
        if (idx !== -1) chores.value[idx]!.last_done = today
    }

    localDb.onChange((table) => {
        if (table === 'chores') load()
    })

    return {chores, loading, error, load, add, update, remove, markDone}
})
