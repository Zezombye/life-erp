<template>
  <div class="dashboard-panel stats-chart-panel">
    <div class="panel-header">
      <h2 class="panel-title">{{ title }}</h2>
    </div>
    <div class="chart-body">
      <div class="chart-plot">
        <div
          v-for="line in gridLines"
          :key="line.pct"
          class="chart-gridline"
          :style="{ bottom: line.pct + '%', backgroundColor: line.color }"
        >
          <span class="chart-gridline-label" :style="{ color: line.color }">{{ line.pct }}%</span>
        </div>

        <div class="chart-bars stats-chart-bars">
          <div v-for="day in chartData" :key="day.date" class="chart-col">
            <div
              class="chart-bar stats-chart-bar"
              :style="{ height: clamp(day.pct) + '%', backgroundColor: day.bg }"
            ></div>
          </div>
        </div>

        <svg
          v-if="chartData.length > 0"
          class="chart-ma-overlay"
          preserveAspectRatio="none"
          :viewBox="'0 0 ' + chartData.length + ' 100'"
        >
          <polyline :points="ma30Points" class="chart-ma-line chart-ma-30" />
          <polyline :points="ma7Points" class="chart-ma-line chart-ma-7" />
        </svg>
      </div>

      <div class="chart-x-axis stats-x-axis">
        <div v-for="(day, idx) in chartData" :key="'x' + day.date" class="chart-date-col">
          <span v-if="shouldShowLabel(idx)" class="chart-date-label chart-date-diagonal">
            {{ day.dateLabel }}
          </span>
        </div>
      </div>

      <div class="chart-legend">
        <span class="chart-legend-item">
          <span class="chart-legend-swatch" style="background: white"></span>7-day avg
        </span>
        <span class="chart-legend-item">
          <span class="chart-legend-swatch" style="background: #f97316"></span>30-day avg
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useHabitStore, getColorForPercent } from '../stores/habits.js'

const props = defineProps({
  title: { type: String, required: true },
  mode: { type: String, required: true },
})

const habitStore = useHabitStore()

const gridLines = (() => {
  const lines = []
  for (let p = 0; p <= 100; p += 10) {
    let color = '#3f3f46'
    if (p === 50) color = '#ef4444'
    else if (p > 50) color = '#3b82f6'
    lines.push({ pct: p, color })
  }
  return lines
})()

function clamp(v) {
  return Math.max(0, Math.min(v, 100))
}

const chartData = computed(() => {
  const rows = habitStore.rows
  if (rows.length === 0) return []

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayStr = today.toISOString().slice(0, 10)

  const map = new Map()
  for (const r of rows) map.set(r.date, r.total ?? 0)

  let dates
  if (props.mode === '365') {
    dates = []
    for (let i = 364; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      dates.push(d.toISOString().slice(0, 10))
    }
  } else {
    dates = rows.map(r => r.date).filter(d => d <= todayStr)
  }

  const data = dates.map(dateStr => {
    const pct = Math.round(map.get(dateStr) ?? 0)
    const c = getColorForPercent(pct)
    const d = new Date(dateStr + 'T00:00:00')
    return {
      date: dateStr,
      pct,
      bg: c?.bg ?? '#3b82f6',
      dateLabel: `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getFullYear()).slice(2)}`,
    }
  })

  for (let i = 0; i < data.length; i++) {
    let s7 = 0, c7 = 0
    for (let j = Math.max(0, i - 6); j <= i; j++) { s7 += data[j].pct; c7++ }
    data[i].ma7 = s7 / c7

    let s30 = 0, c30 = 0
    for (let j = Math.max(0, i - 29); j <= i; j++) { s30 += data[j].pct; c30++ }
    data[i].ma30 = s30 / c30
  }

  return data
})

const ma7Points = computed(() =>
  chartData.value.map((d, i) => `${i + 0.5},${100 - clamp(d.ma7)}`).join(' ')
)

const ma30Points = computed(() =>
  chartData.value.map((d, i) => `${i + 0.5},${100 - clamp(d.ma30)}`).join(' ')
)

function shouldShowLabel(idx) {
  const total = chartData.value.length
  if (total <= 30) return true
  const interval = Math.max(1, Math.ceil(total / 15))
  return idx % interval === 0
}
</script>
