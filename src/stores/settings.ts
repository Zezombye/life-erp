import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchSettings, setSetting} from '../services/api'
import type {Settings} from '../types'

const RETRY_INTERVAL = 3000

export const useSettingsStore = defineStore('settings', () => {
    const settings = ref<Settings>({work_mn: '300'})
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
            settings.value = await fetchSettings()
            clearRetry()
        } catch (e: unknown) {
            error.value = (e as Error).message
            scheduleRetry()
        } finally {
            loading.value = false
        }
    }

    async function update(key: string, value: string): Promise<void> {
        const old = settings.value[key]
        settings.value[key] = value
        try {
            settings.value = await setSetting(key, value)
        } catch (e: unknown) {
            error.value = (e as Error).message
            settings.value[key] = old
        }
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

    return {settings, loading, error, load, update, get, getNumber}
})
