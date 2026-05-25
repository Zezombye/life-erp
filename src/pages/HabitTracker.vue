<template>
    <div class="dashboard-panel habit-panel" :class="{'timer-active-panel': timerStore.hasActive}">
        <div class="panel-header">
            <h2 class="panel-title">Habits</h2>
            <div class="panel-header-actions">
                <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="reload" :loading="habitStore.loading" />
                <Button icon="pi pi-ellipsis-v" severity="secondary" text size="small" @click="toggleMenu" aria-haspopup="true" aria-controls="habit-export-menu" />
                <Menu id="habit-export-menu" ref="menuRef" :model="exportMenuItems" :popup="true" />
            </div>
        </div>
        <TimerBar @quick-add="onQuickAdd" @timer-stopped="onTimerStopped" />
        <Message v-if="habitStore.error" severity="error" :closable="false">
            {{ habitStore.error }}
        </Message>
        <EditableTable :rows="habitStore.rows" :columns="HABIT_COLUMNS" :get-cell-color="getCellColor" :loading="habitStore.loading" @cell-update="onCellUpdate" />
    </div>
</template>

<script setup lang="ts">
import {ref, onMounted} from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
import EditableTable from '../components/EditableTable.vue'
import TimerBar from '../components/TimerBar.vue'
import {useHabitStore, HABIT_COLUMNS, getCellColor as _getCellColor} from '../stores/habits'
import {useTimerStore} from '../stores/timer'

const getCellColor = _getCellColor as (row: any, col: any) => {bg: string; text: string} | null

const habitStore = useHabitStore()
const timerStore = useTimerStore()
const menuRef = ref<InstanceType<typeof Menu>>()

const exportMenuItems = [
    {label: 'Export CSV', icon: 'pi pi-file', command: () => exportData(',', 'csv')},
    {label: 'Export TSV', icon: 'pi pi-file', command: () => exportData('\t', 'tsv')},
]

function toggleMenu(event: Event) {
    menuRef.value!.toggle(event)
}

onMounted(() => {
    habitStore.load()
    timerStore.load()
})

function onCellUpdate({date, column, value}: {date: string; column: string; value: string | number | null}): void {
    habitStore.setValue(date, column, value as number | null)
}

function onQuickAdd({column, delta}: {column: string; delta: number}): void {
    const today = new Date().toISOString().slice(0, 10)
    const row = habitStore.rows.find(r => r.date === today)
    const current = (row && row[column] as number | null) ?? 0
    const newVal = Math.max(0, current + delta)
    habitStore.setValue(today, column, newVal)
}

function onTimerStopped(): void {
    // Reload habits to get updated values from the server
    habitStore.load()
}

function reload(): void {
    habitStore.load()
}

function exportData(separator: string, ext: string): void {
    const headers = HABIT_COLUMNS.map(c => c.label).join(separator)
    const lines = [headers]
    for (const row of habitStore.rows) {
        const values = HABIT_COLUMNS.map(c => {
            const v = row[c.key]
            return v === null || v === undefined ? '' : String(v)
        })
        lines.push(values.join(separator))
    }
    const blob = new Blob([lines.join('\n')], {type: 'text/plain;charset=utf-8'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `habits.${ext}`
    a.click()
    URL.revokeObjectURL(url)
}
</script>

<style lang="scss">
.timer-active-panel {
    border-color: #166534 !important;
    box-shadow: 0 0 8px rgba(22, 101, 52, 0.4), inset 0 0 0 1px rgba(34, 197, 94, 0.15);
}
</style>
