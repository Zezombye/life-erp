<template>
  <div class="stats-page">
    <StatsChart title="Last 365 days" mode="365" />
    <StatsChart title="All time" mode="all" />
  </div>
</template>

<script setup>
import StatsChart from '../components/StatsChart.vue'
</script>
