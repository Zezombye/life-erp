<template>
  <div class="todo-page">
    <div class="dashboard-panel todo-page-panel">
      <div class="panel-header">
        <h2 class="panel-title">Todos</h2>
        <div class="panel-header-actions">
          <button class="panel-btn" @click="todoStore.load()" :disabled="todoStore.loading">↻</button>
        </div>
      </div>

      <!-- Quick add -->
      <div class="todo-add-row">
        <input
          v-model="newTitle"
          class="todo-add-input"
          placeholder="New todo..."
          @keydown.enter="addTodo"
        />
        <button class="chore-btn chore-btn--add" @click="addTodo">Add</button>
      </div>

      <!-- Filter tabs -->
      <div class="todo-filter-bar">
        <button
          class="todo-filter-btn"
          :class="{ 'todo-filter-btn--active': filter === 'open' }"
          @click="filter = 'open'"
        >Open ({{ openCount }})</button>
        <button
          class="todo-filter-btn"
          :class="{ 'todo-filter-btn--active': filter === 'closed' }"
          @click="filter = 'closed'"
        >Closed ({{ closedCount }})</button>
      </div>

      <!-- Todo list -->
      <div class="todo-page-list">
        <div
          v-for="todo in filteredTodos"
          :key="todo.id"
          class="todo-page-item"
          @click="activeTodoId = todo.id"
        >
          <div class="todo-page-item-icon" :class="'todo-icon--' + todo.status">
            {{ todo.status === 'open' ? '○' : '●' }}
          </div>
          <div class="todo-page-item-info">
            <span class="todo-page-item-title">{{ todo.title }}</span>
            <span class="todo-page-item-meta">
              Opened {{ todo.created_at }}
              <template v-if="todo.closed_at"> · Closed {{ todo.closed_at }}</template>
            </span>
          </div>
          <button
            v-if="todo.status === 'open'"
            class="chore-btn chore-btn--done"
            @click.stop="todoStore.close(todo.id)"
          >Close</button>
          <button
            v-else
            class="chore-btn"
            @click.stop="todoStore.reopen(todo.id)"
          >Reopen</button>
        </div>
        <div v-if="filteredTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm p-4">
          No {{ filter }} todos
        </div>
      </div>
    </div>

    <!-- Detail overlay -->
    <TodoDetail
      v-if="activeTodoId !== null"
      :todo-id="activeTodoId"
      @close="activeTodoId = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTodoStore } from '../stores/todos.js'
import TodoDetail from '../components/TodoDetail.vue'

const todoStore = useTodoStore()
const newTitle = ref('')
const filter = ref('open')
const activeTodoId = ref(null)

onMounted(() => { todoStore.load() })

const openCount = computed(() => todoStore.todos.filter(t => t.status === 'open').length)
const closedCount = computed(() => todoStore.todos.filter(t => t.status === 'closed').length)

const filteredTodos = computed(() =>
  todoStore.todos.filter(t => t.status === filter.value)
)

async function addTodo() {
  const t = newTitle.value.trim()
  if (!t) return
  await todoStore.add(t)
  newTitle.value = ''
}
</script>
