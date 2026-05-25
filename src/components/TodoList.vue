<template>
    <div class="dashboard-panel todo-dashboard-panel">
        <div class="panel-header">
            <h2 class="panel-title">Todo</h2>
            <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="todoStore.load()" :loading="todoStore.loading" />
        </div>

        <!-- Quick add -->
        <div class="todo-add-row">
            <InputText v-model="newTitle" placeholder="New todo..." class="flex-1" size="small" @keydown.enter="addTodo" />
            <Button icon="pi pi-plus" severity="success" size="small" @click="addTodo" />
        </div>

        <div v-if="todoStore.loading && openTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            Loading...
        </div>
        <div v-else-if="openTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
            No open todos
        </div>
        <div v-else class="todo-dashboard-list">
            <div v-for="todo in openTodos" :key="todo.id" class="todo-dashboard-item" @click="$emit('openTodo', todo.id)">
                <div class="todo-dashboard-info">
                    <span class="todo-dashboard-title">{{ todo.title }}</span>
                    <span class="todo-dashboard-date">Opened {{ todo.created_at }}</span>
                </div>
                <Button icon="pi pi-check" severity="success" text size="small" @click.stop="closeTodo(todo.id)" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted} from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import {useTodoStore} from '../stores/todos'

const emit = defineEmits<{
    openTodo: [id: string]
}>()
const todoStore = useTodoStore()
const newTitle = ref('')

onMounted(() => {
    if (todoStore.todos.length === 0) todoStore.load()
})

const openTodos = computed(() =>
    todoStore.todos.filter((t: {status: string}) => t.status === 'open')
)

function addTodo(): void {
    const t = newTitle.value.trim()
    if (!t) return
    todoStore.add(t)
    newTitle.value = ''
}

function closeTodo(id: string): void {
    todoStore.close(id)
}
</script>

<style lang="scss">
.todo-dashboard-panel {
    overflow-y: auto;
}

.todo-add-row {
    display: flex;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid #3f3f46;
}

.todo-dashboard-list {
    display: flex;
    flex-direction: column;
    padding: 0.25rem 0;
}

.todo-dashboard-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid #27272a;
    cursor: pointer;

    &:hover {
        background: #27272a;
    }
}

.todo-dashboard-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.todo-dashboard-title {
    font-size: 0.875rem;
    color: #f4f4f5;
}

.todo-dashboard-date {
    font-size: 0.75rem;
    color: #71717a;
}
</style>
