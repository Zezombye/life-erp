<template>
    <div class="workout-page">
        <div class="dashboard-panel habit-panel">
            <div class="panel-header">
                <h2 class="panel-title">Workouts</h2>
                <div class="panel-header-actions">
                    <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="reload" :loading="workoutStore.loading" />
                    <Button icon="pi pi-ellipsis-v" severity="secondary" text size="small" @click="toggleMenu" aria-haspopup="true" aria-controls="workout-export-menu" />
                    <Menu id="workout-export-menu" ref="menuRef" :model="exportMenuItems" :popup="true" />
                </div>
            </div>
            <Message v-if="workoutStore.error" severity="error" :closable="false">
                {{ workoutStore.error }}
            </Message>
            <EditableTable :rows="workoutStore.rows" :columns="WORKOUT_COLUMNS" :get-cell-color="workoutCellColor" :loading="workoutStore.loading" @cell-update="onCellUpdate" />
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, onMounted} from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
import EditableTable from '../components/EditableTable.vue'
import {useWorkoutStore, WORKOUT_COLUMNS, getWorkoutRowColor} from '../stores/workouts'

const workoutCellColor = (row: any) => getWorkoutRowColor(row)

const workoutStore = useWorkoutStore()
const menuRef = ref<InstanceType<typeof Menu>>()

const exportMenuItems = [
    {label: 'Export CSV', icon: 'pi pi-file', command: () => exportData(',', 'csv')},
    {label: 'Export TSV', icon: 'pi pi-file', command: () => exportData('\t', 'tsv')},
]

function toggleMenu(event: Event) {
    menuRef.value!.toggle(event)
}

onMounted(() => {
    workoutStore.load()
})

function onCellUpdate({date, column, value}: {date: string; column: string; value: string | number | null}): void {
    workoutStore.setValue(date, column, value)
}

function reload(): void {
    workoutStore.load()
}

function exportData(separator: string, ext: string): void {
    const headers = WORKOUT_COLUMNS.map(c => c.label).join(separator)
    const lines = [headers]
    for (const row of workoutStore.rows) {
        const values = WORKOUT_COLUMNS.map(c => {
            const v = row[c.key]
            return v === null || v === undefined ? '' : String(v)
        })
        lines.push(values.join(separator))
    }
    const blob = new Blob([lines.join('\n')], {type: 'text/plain;charset=utf-8'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `workouts.${ext}`
    a.click()
    URL.revokeObjectURL(url)
}
</script>

<style lang="scss">
.workout-page {
    display: flex;
    flex-direction: column;
    padding: 0.75rem;
    height: calc(100vh - 2.75rem);
}

.workout-page .habit-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}
</style>
