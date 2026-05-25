<template>
    <div class="stats-page">
        <StatsChart title="Last 365 days" mode="365" />
        <StatsChart title="All time" mode="all" />
    </div>
</template>

<script setup lang="ts">
import StatsChart from '../components/StatsChart.vue'
</script>

<style lang="scss">
.stats-page {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.75rem;
    height: calc(100vh - 2.75rem);
}
</style>
