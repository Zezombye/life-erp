import {defineStore} from 'pinia'
import {ref} from 'vue'
import * as localDb from '../services/local-db'
import type {Settings} from '../types'

const DEFAULT_SETTINGS: Settings = {
    work_mn: '300',
    watchlist: 'AAPL,MSFT,GOOGL,AMZN,TSLA',
}

export const useSettingsStore = defineStore('settings', () => {
    const settings = ref<Settings>({work_mn: '300'})
    const loading = ref(false)
    const error = ref<string | null>(null)

    function load(): void {
        loading.value = true
        error.value = null
        try {
            // Ensure defaults exist
            for (const [key, val] of Object.entries(DEFAULT_SETTINGS)) {
                const existing = localDb.getByPk('settings', {key})
                if (!existing) {
                    localDb.runSql("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", [key, val])
                }
            }
            const rows = localDb.getAll('settings')
            const result: Settings = {}
            for (const row of rows) {
                result[row.key as string] = row.value as string
            }
            settings.value = result
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    function update(key: string, value: string): void {
        settings.value[key] = value
        localDb.upsert('settings', {key}, {value})
    }

    function get(key: string, fallback: string): string {
        return settings.value[key] ?? fallback
    }

    function getNumber(key: string, fallback: number): number {
        const v = settings.value[key]
        if (v === undefined || v === null) return fallback
        const n = Number(v)
        return isNaN(n) ? fallback : n
    }

    localDb.onChange((table) => {
        if (table === 'settings') load()
    })

    return {settings, loading, error, load, update, get, getNumber}
})
