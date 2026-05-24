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
    <TodoDetail
      v-if="activeTodoId !== null"
      :todo-id="activeTodoId"
      @close="activeTodoId = null"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HabitTracker from './HabitTracker.vue'
import Last30DaysChart from '../components/Last30DaysChart.vue'
import ChoreList from '../components/ChoreList.vue'
import TodoList from '../components/TodoList.vue'
import TodoDetail from '../components/TodoDetail.vue'
import StockWatchlist from '../components/StockWatchlist.vue'
import TaskPanel from '../components/TaskPanel.vue'

const activeTodoId = ref(null)

function openTodoDetail(id) {
  activeTodoId.value = id
}
</script>
