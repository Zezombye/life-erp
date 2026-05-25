<template>
    <div class="min-h-screen bg-zinc-900 text-zinc-100">
        <!-- Dashboard grid -->
        <div class="dashboard-grid">
            <!-- Top-left: Todos -->
            <TodoList @open-todo="openTodoDetail" />

            <!-- Top-right: Chores -->
            <ChoreList />

            <!-- Middle: Stocks -->
            <div class="stock-area">
                <StockWatchlist />
            </div>

            <!-- Tasks + Logs -->
            <div class="task-area">
                <TaskPanel />
            </div>

            <!-- Bottom: Chart + Habit tracker -->
            <div class="habit-area">
                <Last30DaysChart />
                <HabitTracker />
            </div>
        </div>

        <!-- Todo detail overlay -->
        <TodoDetail v-if="activeTodoId !== null" :todo-id="activeTodoId" @close="activeTodoId = null" />
    </div>
</template>

<script setup lang="ts">
import {ref} from 'vue'
import HabitTracker from './HabitTracker.vue'
import Last30DaysChart from '../components/Last30DaysChart.vue'
import ChoreList from '../components/ChoreList.vue'
import TodoList from '../components/TodoList.vue'
import TodoDetail from '../components/TodoDetail.vue'
import StockWatchlist from '../components/StockWatchlist.vue'
import TaskPanel from '../components/TaskPanel.vue'

const activeTodoId = ref<string | null>(null)

function openTodoDetail(id: string): void {
    activeTodoId.value = id
}
</script>

<style lang="scss">
.dashboard-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.75rem;
    padding: 0.75rem;
    height: calc(100vh - 2.75rem);
    grid-template-rows: auto auto auto auto 1fr;

    @media (min-width: 768px) {
        grid-template-columns: 1fr 1fr;
        grid-template-rows: 1fr auto auto 1fr;
    }
}

.stock-area {
    grid-column: 1 / -1;
    min-height: 0;
}

.task-area {
    grid-column: 1 / -1;
    min-height: 0;
}

.habit-area {
    grid-column: 1 / -1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;

    @media (min-width: 768px) {
        flex-direction: row;
    }
}
</style>
