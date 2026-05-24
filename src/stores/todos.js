import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
    fetchTodos, createTodo, updateTodo, setTodoStatus,
    fetchTodoMessages, createTodoMessage, updateTodoMessage, deleteTodoMessage,
} from '../services/api.js'

export const useTodoStore = defineStore('todos', () => {
    const todos = ref([])
    const loading = ref(false)
    const error = ref(null)

    // Messages cache: { [todoId]: Message[] }
    const messages = ref({})

    async function load() {
        loading.value = true
        error.value = null
        try {
            todos.value = await fetchTodos()
        } catch (e) {
            error.value = e.message
        } finally {
            loading.value = false
        }
    }

    async function add(title) {
        const row = await createTodo(title)
        todos.value.unshift(row)
        return row
    }

    async function rename(id, title) {
        const row = await updateTodo(id, title)
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
        return row
    }

    async function close(id) {
        const row = await setTodoStatus(id, 'closed')
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
    }

    async function reopen(id) {
        const row = await setTodoStatus(id, 'open')
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx] = row
    }

    async function loadMessages(todoId) {
        messages.value[todoId] = await fetchTodoMessages(todoId)
    }

    async function addMessage(todoId, content) {
        const msg = await createTodoMessage(todoId, content)
        if (!messages.value[todoId]) messages.value[todoId] = []
        messages.value[todoId].push(msg)
        return msg
    }

    async function editMessage(todoId, messageId, content) {
        const msg = await updateTodoMessage(todoId, messageId, content)
        const arr = messages.value[todoId]
        if (arr) {
            const idx = arr.findIndex(m => m.id === messageId)
            if (idx !== -1) arr[idx] = msg
        }
        return msg
    }

    async function removeMessage(todoId, messageId) {
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
