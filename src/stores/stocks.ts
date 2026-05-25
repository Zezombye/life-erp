import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchStocks} from '../services/api'
import type {Stock} from '../types'

export const useStockStore = defineStore('stocks', () => {
    const stocks = ref<Stock[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)

    async function load(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            stocks.value = await fetchStocks()
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    return {stocks, loading, error, load}
})
