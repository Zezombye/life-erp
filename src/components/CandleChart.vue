<template>
  <svg class="candle-svg" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none">
    <line
      v-for="(c, i) in candles"
      :key="'w' + i"
      :x1="cx(i)" :x2="cx(i)"
      :y1="sy(c.high)" :y2="sy(c.low)"
      class="candle-wick"
    />
    <rect
      v-for="(c, i) in candles"
      :key="'b' + i"
      :x="cx(i) - bodyW / 2"
      :y="sy(Math.max(c.open, c.close))"
      :width="bodyW"
      :height="Math.max(sy(Math.min(c.open, c.close)) - sy(Math.max(c.open, c.close)), 0.5)"
      :class="c.close >= c.open ? 'candle-bull' : 'candle-bear'"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  candles: { type: Array, required: true },
  bullish: { type: Boolean, default: true },
})

const width = 200
const height = 48
const padY = 2

const bodyW = computed(() => {
  const n = props.candles.length
  return Math.max((width / n) * 0.5, 1)
})

const priceRange = computed(() => {
  if (!props.candles.length) return { min: 0, max: 1 }
  let min = Infinity, max = -Infinity
  for (const c of props.candles) {
    if (c.low < min) min = c.low
    if (c.high > max) max = c.high
  }
  if (min === max) { min -= 1; max += 1 }
  return { min, max }
})

function cx(i) {
  const n = props.candles.length
  const step = width / n
  return step * i + step / 2
}

function sy(price) {
  const { min, max } = priceRange.value
  const ratio = (price - min) / (max - min)
  return padY + (1 - ratio) * (height - padY * 2)
}
</script>
