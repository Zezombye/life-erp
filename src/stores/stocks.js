import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchStocks } from '../services/api.js'

export const useStockStore = defineStore('stocks', () => {
    const stocks = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function load() {
        loading.value = true
        error.value = null
        try {
            stocks.value = await fetchStocks()
        } catch (e) {
            error.value = e.message
        } finally {
            loading.value = false
        }
    }

    return { stocks, loading, error, load }
})
