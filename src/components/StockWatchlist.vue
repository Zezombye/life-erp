<template>
    <div class="dashboard-panel stock-panel">
        <div class="panel-header">
            <h2 class="panel-title">Watchlist</h2>
            <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="stockStore.load()" :loading="stockStore.loading" />
        </div>
        <div v-if="stockStore.loading && stockStore.stocks.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            Loading...
        </div>
        <div v-else-if="stockStore.stocks.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            No stocks in watchlist
        </div>
        <div v-else class="stock-list">
            <div v-for="stock in stockStore.stocks" :key="stock.ticker" class="stock-item">
                <div class="stock-info">
                    <span class="stock-ticker">{{ stock.ticker }}</span>
                    <span class="stock-price">${{ stock.price.toFixed(2) }}</span>
                    <span class="stock-change" :class="stock.change >= 0 ? 'stock-change--up' : 'stock-change--down'">
                        {{ stock.change >= 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}
                        ({{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%)
                    </span>
                </div>
                <div class="stock-chart">
                    <CandleChart :candles="stock.candles" :bullish="stock.change >= 0" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {onMounted} from 'vue'
import Button from 'primevue/button'
import {useStockStore} from '../stores/stocks'
import CandleChart from './CandleChart.vue'

const stockStore = useStockStore()

onMounted(() => {
    stockStore.load()
})
</script>

<style lang="scss">
.stock-panel {
    overflow-y: auto;
    max-height: 280px;
}

.stock-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0;
}

.stock-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid #27272a;
    min-width: 280px;
    flex: 1;
}

.stock-info {
    display: flex;
    flex-direction: column;
    gap: 0.0625rem;
    min-width: 90px;
}

.stock-ticker {
    font-size: 0.8125rem;
    font-weight: 600;
    color: #f4f4f5;
}

.stock-price {
    font-size: 0.875rem;
    font-variant-numeric: tabular-nums;
    color: #d4d4d8;
}

.stock-change {
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
}

.stock-change--up {
    color: #4ade80;
}

.stock-change--down {
    color: #f87171;
}

.stock-chart {
    flex: 1;
    min-width: 120px;
    max-width: 200px;
    height: 48px;
}
</style>
