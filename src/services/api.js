const API_BASE = 'http://localhost:8000'

export async function fetchHabits() {
    const res = await fetch(`${API_BASE}/api/habits`)
    if (!res.ok) throw new Error(`Failed to fetch habits: ${res.status}`)
    return res.json()
}

export async function setHabitValue(date, column, value) {
    const res = await fetch(`${API_BASE}/api/habits/value`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, column, value }),
    })
    if (!res.ok) throw new Error(`Failed to set value: ${res.status}`)
    return res.json()
}

export async function fetchSettings() {
    const res = await fetch(`${API_BASE}/api/settings`)
    if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`)
    return res.json()
}

export async function setSetting(key, value) {
    const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
    })
    if (!res.ok) throw new Error(`Failed to save setting: ${res.status}`)
    return res.json()
}

export async function fetchWorkouts() {
    const res = await fetch(`${API_BASE}/api/workouts`)
    if (!res.ok) throw new Error(`Failed to fetch workouts: ${res.status}`)
    return res.json()
}

export async function setWorkoutValue(date, column, value) {
    const res = await fetch(`${API_BASE}/api/workouts/value`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, column, value }),
    })
    if (!res.ok) throw new Error(`Failed to set workout value: ${res.status}`)
    return res.json()
}

export async function fetchChores() {
    const res = await fetch(`${API_BASE}/api/chores`)
    if (!res.ok) throw new Error(`Failed to fetch chores: ${res.status}`)
    return res.json()
}

export async function createChore(title, interval_days) {
    const res = await fetch(`${API_BASE}/api/chores`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, interval_days }),
    })
    if (!res.ok) throw new Error(`Failed to create chore: ${res.status}`)
    return res.json()
}

export async function updateChore(id, title, interval_days) {
    const res = await fetch(`${API_BASE}/api/chores/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, interval_days }),
    })
    if (!res.ok) throw new Error(`Failed to update chore: ${res.status}`)
    return res.json()
}

export async function deleteChore(id) {
    const res = await fetch(`${API_BASE}/api/chores/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`Failed to delete chore: ${res.status}`)
    return res.json()
}

export async function markChoreDone(id, date) {
    const res = await fetch(`${API_BASE}/api/chores/${id}/done`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date }),
    })
    if (!res.ok) throw new Error(`Failed to mark chore done: ${res.status}`)
    return res.json()
}

// ── Todos ──

export async function fetchTodos() {
    const res = await fetch(`${API_BASE}/api/todos`)
    if (!res.ok) throw new Error(`Failed to fetch todos: ${res.status}`)
    return res.json()
}

export async function createTodo(title) {
    const res = await fetch(`${API_BASE}/api/todos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    })
    if (!res.ok) throw new Error(`Failed to create todo: ${res.status}`)
    return res.json()
}

export async function updateTodo(id, title) {
    const res = await fetch(`${API_BASE}/api/todos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    })
    if (!res.ok) throw new Error(`Failed to update todo: ${res.status}`)
    return res.json()
}

export async function setTodoStatus(id, status) {
    const res = await fetch(`${API_BASE}/api/todos/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
    })
    if (!res.ok) throw new Error(`Failed to set todo status: ${res.status}`)
    return res.json()
}

export async function fetchTodoMessages(todoId) {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages`)
    if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`)
    return res.json()
}

export async function createTodoMessage(todoId, content) {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error(`Failed to create message: ${res.status}`)
    return res.json()
}

export async function updateTodoMessage(todoId, messageId, content) {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages/${messageId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error(`Failed to update message: ${res.status}`)
    return res.json()
}

export async function deleteTodoMessage(todoId, messageId) {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages/${messageId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`Failed to delete message: ${res.status}`)
    return res.json()
}

// ── Stocks ──

export async function fetchStocks() {
    const res = await fetch(`${API_BASE}/api/stocks`)
    if (!res.ok) throw new Error(`Failed to fetch stocks: ${res.status}`)
    return res.json()
}

// ── Calendar ──

export async function fetchCalendarEvents(start, end) {
    const res = await fetch(`${API_BASE}/api/calendar?start=${start}&end=${end}`)
    if (!res.ok) throw new Error(`Failed to fetch calendar events: ${res.status}`)
    return res.json()
}

export async function createCalendarEvent(data) {
    const res = await fetch(`${API_BASE}/api/calendar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to create event: ${res.status}`)
    return res.json()
}

export async function updateCalendarEvent(id, data) {
    const res = await fetch(`${API_BASE}/api/calendar/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to update event: ${res.status}`)
    return res.json()
}

export async function deleteCalendarEvent(id) {
    const res = await fetch(`${API_BASE}/api/calendar/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`Failed to delete event: ${res.status}`)
    return res.json()
}

// ── Tasks ──

export async function fetchTasks() {
    const res = await fetch(`${API_BASE}/api/tasks`)
    if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`)
    return res.json()
}

export async function startTask(taskName) {
    const res = await fetch(`${API_BASE}/api/tasks/${taskName}/start`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to start task: ${res.status}`)
    return res.json()
}

export async function pauseTask(taskName, paused) {
    const res = await fetch(`${API_BASE}/api/tasks/${taskName}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused }),
    })
    if (!res.ok) throw new Error(`Failed to pause task: ${res.status}`)
    return res.json()
}

export async function fetchTaskLogs(params = {}) {
    const qs = new URLSearchParams()
    if (params.task) qs.set('task', params.task)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.since_id != null) qs.set('since_id', String(params.since_id))
    const res = await fetch(`${API_BASE}/api/task-logs?${qs}`)
    if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`)
    return res.json()
}

export function streamTaskLogs() {
    return new EventSource(`${API_BASE}/api/task-logs/stream`)
}
