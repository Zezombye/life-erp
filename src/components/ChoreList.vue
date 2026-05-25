<template>
    <div class="dashboard-panel chore-dashboard-panel">
        <div class="panel-header">
            <h2 class="panel-title">Chores</h2>
            <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="choreStore.load()" :loading="choreStore.loading" />
        </div>
        <div v-if="choreStore.loading && choreStore.chores.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            Loading...
        </div>
        <div v-else-if="choreStore.chores.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            No chores configured
        </div>
        <div v-else class="chore-dashboard-list">
            <div v-for="item in sortedChores" :key="item.id" class="chore-dashboard-item" :class="{'chore-dashboard-item--overdue': item.overdue}">
                <div class="chore-dashboard-info">
                    <span class="chore-dashboard-title">{{ item.title }}</span>
                    <span class="chore-dashboard-due">
                        <template v-if="!item.lastDone">Never done</template>
                        <template v-else-if="item.overdue">Overdue — was due {{ item.dueDate }}</template>
                        <template v-else>Due {{ item.dueDate }}</template>
                    </span>
                </div>
                <Button label="Done" severity="success" size="small" @click="markDone(item.id)" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {computed, onMounted} from 'vue'
import Button from 'primevue/button'
import {useChoreStore, getChoreNextDue, isChoreOverdue} from '../stores/chores'

const choreStore = useChoreStore()

onMounted(() => {
    if (choreStore.chores.length === 0) choreStore.load()
})

const sortedChores = computed(() => {
    return choreStore.chores
        .map(c => ({
            id: c.id,
            title: c.title,
            interval: c.interval_days,
            lastDone: c.last_done,
            dueDate: getChoreNextDue(c),
            overdue: isChoreOverdue(c),
        }))
        .sort((a, b) => {
            // Overdue first, then by due date ascending
            if (a.overdue !== b.overdue) return a.overdue ? -1 : 1
            if (!a.dueDate) return -1
            if (!b.dueDate) return 1
            return a.dueDate.localeCompare(b.dueDate)
        })
})

function markDone(id: string): void {
    choreStore.markDone(id)
}
</script>

<style lang="scss">
.chore-dashboard-panel {
    overflow-y: auto;
}

.chore-dashboard-list {
    display: flex;
    flex-direction: column;
    padding: 0.25rem 0;
}

.chore-dashboard-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid #27272a;
}

.chore-dashboard-item--overdue {
    background: rgba(127, 29, 29, 0.3);
}

.chore-dashboard-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.chore-dashboard-title {
    font-size: 0.875rem;
    color: #f4f4f5;
}

.chore-dashboard-due {
    font-size: 0.75rem;
    color: #a1a1aa;
}

.chore-dashboard-item--overdue .chore-dashboard-due {
    color: #fca5a5;
}
</style>
