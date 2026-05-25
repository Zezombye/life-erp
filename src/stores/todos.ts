import {defineStore} from 'pinia'
import {ref} from 'vue'
import {
    fetchTodos, createTodo, updateTodo, setTodoStatus,
    fetchTodoMessages, createTodoMessage, updateTodoMessage, deleteTodoMessage,
} from '../services/api'
import type {Todo, TodoMessage} from '../types'

export const useTodoStore = defineStore('todos', () => {
    const todos = ref<Todo[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)

    const messages = ref<Record<number, TodoMessage[]>>({})

    async function load(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            todos.value = await fetchTodos()
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    async function add(title: string): Promise<Todo> {
        const row = await createTodo(title)
        todos.value.unshift(row)
        return row
    }

    async function rename(id: number, title: string): Promise<Todo> {
        const row = await updateTodo(id, title)
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
        return row
    }

    async function close(id: number): Promise<void> {
        const row = await setTodoStatus(id, 'closed')
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
    }

    async function reopen(id: number): Promise<void> {
        const row = await setTodoStatus(id, 'open')
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
    }

    async function loadMessages(todoId: number): Promise<void> {
        messages.value[todoId] = await fetchTodoMessages(todoId)
    }

    async function addMessage(todoId: number, content: string): Promise<TodoMessage> {
        const msg = await createTodoMessage(todoId, content)
        if (!messages.value[todoId]) messages.value[todoId] = []
        messages.value[todoId].push(msg)
        return msg
    }

    async function editMessage(todoId: number, messageId: number, content: string): Promise<TodoMessage> {
        const msg = await updateTodoMessage(todoId, messageId, content)
        const arr = messages.value[todoId]
        if (arr) {
            const idx = arr.findIndex(m => m.id === messageId)
            if (idx !== -1) arr[idx] = msg
        }
        return msg
    }

    async function removeMessage(todoId: number, messageId: number): Promise<void> {
        await deleteTodoMessage(todoId, messageId)
        const arr = messages.value[todoId]
        if (arr) {
            messages.value[todoId] = arr.filter(m => m.id !== messageId)
        }
    }

    return {
        todos, loading, error, messages,
        load, add, rename, close, reopen,
        loadMessages, addMessage, editMessage, removeMessage,
    }
})
