<template>
  <div class="dashboard-panel todo-dashboard-panel">
    <div class="panel-header">
      <h2 class="panel-title">Todo</h2>
      <button class="panel-btn" @click="todoStore.load()" :disabled="todoStore.loading">↻</button>
    </div>

    <!-- Quick add -->
    <div class="todo-add-row">
      <input
        v-model="newTitle"
        class="todo-add-input"
        placeholder="New todo..."
        @keydown.enter="addTodo"
      />
      <button class="chore-btn chore-btn--add" @click="addTodo">+</button>
    </div>

    <div v-if="todoStore.loading && openTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
      Loading...
    </div>
    <div v-else-if="openTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
      No open todos
    </div>
    <div v-else class="todo-dashboard-list">
      <div
        v-for="todo in openTodos"
        :key="todo.id"
        class="todo-dashboard-item"
        @click="$emit('openTodo', todo.id)"
      >
        <div class="todo-dashboard-info">
          <span class="todo-dashboard-title">{{ todo.title }}</span>
          <span class="todo-dashboard-date">Opened {{ todo.created_at }}</span>
        </div>
        <button class="chore-btn chore-btn--done" @click.stop="closeTodo(todo.id)">✓</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTodoStore } from '../stores/todos.js'

const emit = defineEmits(['openTodo'])
const todoStore = useTodoStore()
const newTitle = ref('')

onMounted(() => {
  if (todoStore.todos.length === 0) todoStore.load()
})

const openTodos = computed(() =>
  todoStore.todos.filter(t => t.status === 'open')
)

async function addTodo() {
  const t = newTitle.value.trim()
  if (!t) return
  await todoStore.add(t)
  newTitle.value = ''
}

async function closeTodo(id) {
  await todoStore.close(id)
}
</script>
