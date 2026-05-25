<template>
    <div class="dashboard-panel chart-panel">
        <div class="panel-header">
            <h2 class="panel-title">Last 30 days</h2>
        </div>
        <div class="chart-body">
            <div class="chart-plot">
                <div v-for="line in gridLines" :key="line.pct" class="chart-gridline" :style="{bottom: line.pct + '%', backgroundColor: line.color}">
                    <span class="chart-gridline-label" :style="{color: line.color}">{{ line.pct }}%</span>
                </div>

                <div class="chart-bars">
                    <div v-for="day in chartData" :key="day.date" class="chart-col">
                        <span class="chart-bar-value" :style="{bottom: 'calc(' + clamp(day.pct) + '% + 2px)'}">{{ day.pct }}%</span>
                        <div class="chart-bar" :style="{height: clamp(day.pct) + '%', backgroundColor: day.bg}"></div>
                    </div>
                </div>
            </div>

            <div class="chart-x-axis">
                <div v-for="day in chartData" :key="'x' + day.date" class="chart-date-col">
                    <span class="chart-date-label">{{ day.dateLabel }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import {useHabitStore, getColorForPercent} from '../stores/habits'

const habitStore = useHabitStore()

const gridLines = (() => {
    const lines = []
    for (let p = 0; p <= 100; p += 10) {
        let color = '#3f3f46'
        if (p === 50) color = '#ef4444'
        else if (p > 50) color = '#3b82f6'
        lines.push({pct: p, color})
    }
    return lines
})()

function clamp(v: number): number {
    return Math.max(0, Math.min(v, 100))
}

const chartData = computed(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const rows = habitStore.rows
    const data: {date: string; pct: number; bg: string; dateLabel: string}[] = []

    for (let i = 29; i >= 0; i--) {
        const d = new Date(today)
        d.setDate(d.getDate() - i)
        const dateStr = d.toISOString().slice(0, 10)
        const row = rows.find(r => r.date === dateStr)
        const pct = row?.total !== null && row?.total !== undefined ? Math.round(row.total) : 0
        const c = getColorForPercent(pct)

        data.push({
            date: dateStr,
            pct,
            bg: c?.bg ?? '#3b82f6',
            dateLabel: `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`,
        })
    }

    return data
})
</script>

<style lang="scss">
.chart-panel {
    flex-shrink: 0;

    @media (min-width: 768px) {
        width: 540px;
    }
}

.chart-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 0.5rem 0.5rem 0 2rem;
}

.chart-plot {
    flex: 1;
    position: relative;
    min-height: 120px;
}

.chart-gridline {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
}

.chart-gridline-label {
    position: absolute;
    right: calc(100% + 4px);
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.5625rem;
    white-space: nowrap;
    line-height: 1;
}

.chart-bars {
    position: absolute;
    inset: 0;
    display: flex;
    gap: 2px;
}

.chart-col {
    flex: 1;
    position: relative;
    min-width: 0;
}

.chart-bar {
    position: absolute;
    bottom: 0;
    left: 15%;
    right: 15%;
    border-radius: 2px 2px 0 0;
    min-height: 1px;
}

.chart-bar-value {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.5rem;
    white-space: nowrap;
    color: #a1a1aa;
    pointer-events: none;
}

.chart-x-axis {
    flex-shrink: 0;
    display: flex;
    gap: 2px;
    height: 68px;
    border-top: 1px solid #3f3f46;
}

.chart-date-col {
    flex: 1;
    min-width: 0;
    display: flex;
    justify-content: center;
    padding-top: 4px;
}

.chart-date-label {
    writing-mode: vertical-rl;
    font-size: 0.5625rem;
    color: #71717a;
    white-space: nowrap;
}
</style>
