import type {
    HabitRow, Stock, WorkoutRow, Chore, CalendarEvent,
    CalendarEventInput, Todo, TodoMessage, Task, TaskLog,
    TaskLogParams, Settings,
} from '../types'

const API_BASE = 'http://localhost:8000'

export async function fetchHabits(): Promise<HabitRow[]> {
    const res = await fetch(`${API_BASE}/api/habits`)
    if (!res.ok) throw new Error(`Failed to fetch habits: ${res.status}`)
    return res.json()
}

export async function setHabitValue(date: string, column: string, value: number | null): Promise<HabitRow> {
    const res = await fetch(`${API_BASE}/api/habits/value`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({date, column, value}),
    })
    if (!res.ok) throw new Error(`Failed to set value: ${res.status}`)
    return res.json()
}

export async function fetchSettings(): Promise<Settings> {
    const res = await fetch(`${API_BASE}/api/settings`)
    if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`)
    return res.json()
}

export async function setSetting(key: string, value: string): Promise<Settings> {
    const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key, value}),
    })
    if (!res.ok) throw new Error(`Failed to save setting: ${res.status}`)
    return res.json()
}

export async function fetchWorkouts(): Promise<WorkoutRow[]> {
    const res = await fetch(`${API_BASE}/api/workouts`)
    if (!res.ok) throw new Error(`Failed to fetch workouts: ${res.status}`)
    return res.json()
}

export async function setWorkoutValue(date: string, column: string, value: string | number | null): Promise<WorkoutRow> {
    const res = await fetch(`${API_BASE}/api/workouts/value`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({date, column, value}),
    })
    if (!res.ok) throw new Error(`Failed to set workout value: ${res.status}`)
    return res.json()
}

export async function fetchChores(): Promise<Chore[]> {
    const res = await fetch(`${API_BASE}/api/chores`)
    if (!res.ok) throw new Error(`Failed to fetch chores: ${res.status}`)
    return res.json()
}

export async function createChore(title: string, interval_days: number): Promise<Chore> {
    const res = await fetch(`${API_BASE}/api/chores`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, interval_days}),
    })
    if (!res.ok) throw new Error(`Failed to create chore: ${res.status}`)
    return res.json()
}

export async function updateChore(id: number, title: string, interval_days: number): Promise<Chore> {
    const res = await fetch(`${API_BASE}/api/chores/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, interval_days}),
    })
    if (!res.ok) throw new Error(`Failed to update chore: ${res.status}`)
    return res.json()
}

export async function deleteChore(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/chores/${id}`, {method: 'DELETE'})
    if (!res.ok) throw new Error(`Failed to delete chore: ${res.status}`)
}

export async function markChoreDone(id: number, date: string): Promise<Chore> {
    const res = await fetch(`${API_BASE}/api/chores/${id}/done`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({date}),
    })
    if (!res.ok) throw new Error(`Failed to mark chore done: ${res.status}`)
    return res.json()
}

// ── Todos ──

export async function fetchTodos(): Promise<Todo[]> {
    const res = await fetch(`${API_BASE}/api/todos`)
    if (!res.ok) throw new Error(`Failed to fetch todos: ${res.status}`)
    return res.json()
}

export async function createTodo(title: string): Promise<Todo> {
    const res = await fetch(`${API_BASE}/api/todos`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title}),
    })
    if (!res.ok) throw new Error(`Failed to create todo: ${res.status}`)
    return res.json()
}

export async function updateTodo(id: number, title: string): Promise<Todo> {
    const res = await fetch(`${API_BASE}/api/todos/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title}),
    })
    if (!res.ok) throw new Error(`Failed to update todo: ${res.status}`)
    return res.json()
}

export async function setTodoStatus(id: number, status: string): Promise<Todo> {
    const res = await fetch(`${API_BASE}/api/todos/${id}/status`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status}),
    })
    if (!res.ok) throw new Error(`Failed to set todo status: ${res.status}`)
    return res.json()
}

export async function fetchTodoMessages(todoId: number): Promise<TodoMessage[]> {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages`)
    if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`)
    return res.json()
}

export async function createTodoMessage(todoId: number, content: string): Promise<TodoMessage> {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content}),
    })
    if (!res.ok) throw new Error(`Failed to create message: ${res.status}`)
    return res.json()
}

export async function updateTodoMessage(todoId: number, messageId: number, content: string): Promise<TodoMessage> {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages/${messageId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content}),
    })
    if (!res.ok) throw new Error(`Failed to update message: ${res.status}`)
    return res.json()
}

export async function deleteTodoMessage(todoId: number, messageId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/todos/${todoId}/messages/${messageId}`, {method: 'DELETE'})
    if (!res.ok) throw new Error(`Failed to delete message: ${res.status}`)
}

// ── Stocks ──

export async function fetchStocks(): Promise<Stock[]> {
    const res = await fetch(`${API_BASE}/api/stocks`)
    if (!res.ok) throw new Error(`Failed to fetch stocks: ${res.status}`)
    return res.json()
}

// ── Calendar ──

export async function fetchCalendarEvents(start: string, end: string): Promise<CalendarEvent[]> {
    const res = await fetch(`${API_BASE}/api/calendar?start=${start}&end=${end}`)
    if (!res.ok) throw new Error(`Failed to fetch calendar events: ${res.status}`)
    return res.json()
}

export async function createCalendarEvent(data: CalendarEventInput): Promise<CalendarEvent> {
    const res = await fetch(`${API_BASE}/api/calendar`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to create event: ${res.status}`)
    return res.json()
}

export async function updateCalendarEvent(id: number, data: Partial<CalendarEventInput>): Promise<CalendarEvent> {
    const res = await fetch(`${API_BASE}/api/calendar/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to update event: ${res.status}`)
    return res.json()
}

export async function deleteCalendarEvent(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/calendar/${id}`, {method: 'DELETE'})
    if (!res.ok) throw new Error(`Failed to delete event: ${res.status}`)
}

// ── Tasks ──

export async function fetchTasks(): Promise<Task[]> {
    const res = await fetch(`${API_BASE}/api/tasks`)
    if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`)
    return res.json()
}

export async function startTask(taskName: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/tasks/${taskName}/start`, {method: 'POST'})
    if (!res.ok) throw new Error(`Failed to start task: ${res.status}`)
}

export async function pauseTask(taskName: string, paused: boolean): Promise<void> {
    const res = await fetch(`${API_BASE}/api/tasks/${taskName}/pause`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({paused}),
    })
    if (!res.ok) throw new Error(`Failed to pause task: ${res.status}`)
}

export async function fetchTaskLogs(params: TaskLogParams = {}): Promise<TaskLog[]> {
    const qs = new URLSearchParams()
    if (params.task) qs.set('task', params.task)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.since_id) qs.set('since_id', String(params.since_id))
    const res = await fetch(`${API_BASE}/api/task-logs?${qs}`)
    if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`)
    return res.json()
}

export function streamTaskLogs(): EventSource {
    return new EventSource(`${API_BASE}/api/task-logs/stream`)
}
