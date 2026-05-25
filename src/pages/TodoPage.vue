<template>
    <div class="todo-page">
        <div class="dashboard-panel todo-page-panel">
            <div class="panel-header">
                <h2 class="panel-title">Todos</h2>
                <div class="panel-header-actions">
                    <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="todoStore.load()" :loading="todoStore.loading" />
                </div>
            </div>

            <!-- Quick add -->
            <div class="todo-add-row">
                <InputText v-model="newTitle" placeholder="New todo..." class="flex-1" size="small" @keydown.enter="addTodo" />
                <Button label="Add" icon="pi pi-plus" severity="success" size="small" @click="addTodo" />
            </div>

            <!-- Filter tabs -->
            <div class="todo-filter-bar">
                <SelectButton v-model="filter" :options="filterOptions" optionLabel="label" optionValue="value" size="small" />
            </div>

            <!-- Todo list -->
            <div class="todo-page-list">
                <div v-for="todo in filteredTodos" :key="todo.id" class="todo-page-item" @click="activeTodoId = todo.id">
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
                    <Button v-if="todo.status === 'open'" label="Close" severity="success" size="small" @click.stop="todoStore.close(todo.id)" />
                    <Button v-else label="Reopen" severity="secondary" size="small" @click.stop="todoStore.reopen(todo.id)" />
                </div>
                <div v-if="filteredTodos.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm p-4">
                    No {{ filter }} todos
                </div>
            </div>
        </div>

        <!-- Detail overlay -->
        <TodoDetail v-if="activeTodoId !== null" :todo-id="activeTodoId" @close="activeTodoId = null" />
    </div>
</template>

<script setup lang="ts">
import {ref, computed, onMounted} from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import {useTodoStore} from '../stores/todos'
import TodoDetail from '../components/TodoDetail.vue'

const todoStore = useTodoStore()
const newTitle = ref('')
const filter = ref('open')
const activeTodoId = ref<number | null>(null)

const filterOptions = computed(() => [
    {label: `Open (${openCount.value})`, value: 'open'},
    {label: `Closed (${closedCount.value})`, value: 'closed'},
])

onMounted(() => {todoStore.load()})

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

<style lang="scss">
.todo-page {
    padding: 0.75rem;
    height: calc(100vh - 2.75rem);
    display: flex;
    flex-direction: column;
}

.todo-page-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.todo-filter-bar {
    display: flex;
    gap: 0;
    border-bottom: 1px solid #3f3f46;
    flex-shrink: 0;
}

.todo-page-list {
    flex: 1;
    overflow-y: auto;
}

.todo-page-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #27272a;
    cursor: pointer;

    &:hover {
        background: #27272a;
    }
}

.todo-page-item-icon {
    font-size: 1rem;
    width: 1.25rem;
    text-align: center;
    flex-shrink: 0;
}

.todo-icon--open {
    color: #22c55e;
}

.todo-icon--closed {
    color: #a855f7;
}

.todo-page-item-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.todo-page-item-title {
    font-size: 0.875rem;
    color: #f4f4f5;
}

.todo-page-item-meta {
    font-size: 0.75rem;
    color: #71717a;
}
</style>
