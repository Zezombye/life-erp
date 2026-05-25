import type {
    Stock, Task, TaskLog, TaskLogParams,
} from '../types'

const API_BASE = 'http://localhost:8000'

// ── Stocks (server-only, not synced) ──

export async function fetchStocks(): Promise<Stock[]> {
    const res = await fetch(`${API_BASE}/api/stocks`)
    if (!res.ok) throw new Error(`Failed to fetch stocks: ${res.status}`)
    return res.json()
}

// ── Tasks (server-only, not synced) ──

export async function fetchTasks(): Promise<Task[]> {
    const res = await fetch(`${API_BASE}/api/tasks`)
    if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`)
    return res.json()
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
