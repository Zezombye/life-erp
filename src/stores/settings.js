import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSettings, setSetting } from '../services/api.js'

const RETRY_INTERVAL = 3000

export const useSettingsStore = defineStore('settings', () => {
    const settings = ref({ work_mn: '300' })
    const loading = ref(false)
    const error = ref(null)
    let retryTimer = null

    function scheduleRetry() {
        if (retryTimer) return
        retryTimer = setInterval(() => {
            load()
        }, RETRY_INTERVAL)
    }

    function clearRetry() {
        if (retryTimer) {
            clearInterval(retryTimer)
            retryTimer = null
        }
    }

    async function load() {
        loading.value = true
        error.value = null
        try {
            settings.value = await fetchSettings()
            clearRetry()
        } catch (e) {
            error.value = e.message
            scheduleRetry()
        } finally {
            loading.value = false
        }
    }

    async function update(key, value) {
        const old = settings.value[key]
        settings.value[key] = value
        try {
            settings.value = await setSetting(key, value)
        } catch (e) {
            error.value = e.message
            settings.value[key] = old
        }
    }

    function get(key, fallback) {
        return settings.value[key] ?? fallback
    }

    function getNumber(key, fallback) {
        const v = settings.value[key]
        if (v === undefined || v === null) return fallback
        const n = Number(v)
        return isNaN(n) ? fallback : n
    }

    return { settings, loading, error, load, update, get, getNumber }
})
