<template>
  <div class="dashboard-panel stock-panel">
    <div class="panel-header">
      <h2 class="panel-title">Watchlist</h2>
      <button class="panel-btn" @click="stockStore.load()" :disabled="stockStore.loading">↻</button>
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

<script setup>
import { onMounted } from 'vue'
import { useStockStore } from '../stores/stocks.js'
import CandleChart from './CandleChart.vue'

const stockStore = useStockStore()

onMounted(() => {
  stockStore.load()
})
</script>
