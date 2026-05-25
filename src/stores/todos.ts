import {defineStore} from 'pinia'
import {ref} from 'vue'
import * as localDb from '../services/local-db'
import type {Todo, TodoMessage} from '../types'

export const useTodoStore = defineStore('todos', () => {
    const todos = ref<Todo[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)

    const messages = ref<Record<string, TodoMessage[]>>({})

    function load(): void {
        loading.value = true
        error.value = null
        try {
            todos.value = localDb.getAll('todos')
            todos.value.sort((a, b) => b.created_at.localeCompare(a.created_at))
        } catch (e: unknown) {
            error.value = (e as Error).message
        } finally {
            loading.value = false
        }
    }

    function add(title: string): Todo {
        const now = new Date().toISOString().slice(0, 10)
        const id = crypto.randomUUID()
        const row: Todo = {id, title, status: 'open', created_at: now, closed_at: null}
        localDb.upsert('todos', {id}, {title, status: 'open', created_at: now, closed_at: null})
        return row
    }

    function rename(id: string, title: string): void {
        localDb.upsert('todos', {id}, {title})
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) todos.value[idx]!.title = title
    }

    function close(id: string): void {
        const now = new Date().toISOString().slice(0, 10)
        localDb.upsert('todos', {id}, {status: 'closed', closed_at: now})
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) {
            todos.value[idx]!.status = 'closed'
            todos.value[idx]!.closed_at = now
        }
    }

    function reopen(id: string): void {
        localDb.upsert('todos', {id}, {status: 'open', closed_at: null})
        const idx = todos.value.findIndex(t => t.id === id)
        if (idx !== -1) {
            todos.value[idx]!.status = 'open'
            todos.value[idx]!.closed_at = null
        }
    }

    function loadMessages(todoId: string): void {
        const rows = localDb.query(
            "SELECT * FROM todo_messages WHERE todo_id = ? ORDER BY id ASC",
            [todoId]
        )
        messages.value[todoId] = rows
    }

    function addMessage(todoId: string, content: string): TodoMessage {
        const now = new Date().toISOString().slice(0, 10)
        const id = crypto.randomUUID()
        const msg: TodoMessage = {id, content, created_at: now, updated_at: now}
        localDb.upsert('todo_messages', {id}, {todo_id: todoId, content, created_at: now, updated_at: now})
        if (!messages.value[todoId]) messages.value[todoId] = []
        messages.value[todoId].push(msg)
        return msg
    }

    function editMessage(todoId: string, messageId: string, content: string): void {
        const now = new Date().toISOString().slice(0, 10)
        localDb.upsert('todo_messages', {id: messageId}, {content, updated_at: now})
        const arr = messages.value[todoId]
        if (arr) {
            const idx = arr.findIndex(m => m.id === messageId)
            if (idx !== -1) {
                arr[idx]!.content = content
                arr[idx]!.updated_at = now
            }
        }
    }

    function removeMessage(todoId: string, messageId: string): void {
        localDb.remove('todo_messages', {id: messageId})
        const arr = messages.value[todoId]
        if (arr) {
            messages.value[todoId] = arr.filter(m => m.id !== messageId)
        }
    }

    localDb.onChange((table) => {
        if (table === 'todos') load()
        if (table === 'todo_messages') {
            // Reload messages for all loaded todos
            for (const todoId of Object.keys(messages.value)) {
                loadMessages(todoId)
            }
        }
    })

    return {
        todos, loading, error, messages,
        load, add, rename, close, reopen,
        loadMessages, addMessage, editMessage, removeMessage,
    }
})
