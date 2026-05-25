<template>
    <div class="dashboard-panel habit-panel">
        <div class="panel-header">
            <h2 class="panel-title">Habits</h2>
            <div class="panel-header-actions">
                <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="reload" :loading="habitStore.loading" />
                <Button icon="pi pi-ellipsis-v" severity="secondary" text size="small" @click="toggleMenu" aria-haspopup="true" aria-controls="habit-export-menu" />
                <Menu id="habit-export-menu" ref="menuRef" :model="exportMenuItems" :popup="true" />
            </div>
        </div>
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
import {useHabitStore, HABIT_COLUMNS, getCellColor as _getCellColor} from '../stores/habits'

const getCellColor = _getCellColor as (row: any, col: any) => {bg: string; text: string} | null

const habitStore = useHabitStore()
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
})

function onCellUpdate({date, column, value}: {date: string; column: string; value: string | number | null}): void {
    habitStore.setValue(date, column, value as number | null)
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
