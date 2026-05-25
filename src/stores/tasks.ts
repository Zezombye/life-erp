import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import {fetchTasks, startTask, pauseTask, fetchTaskLogs, streamTaskLogs} from '../services/api'
import type {Task, TaskLog, TaskLogParams} from '../types'

export const useTaskStore = defineStore('tasks', () => {
    const tasks = ref<Task[]>([])
    const logs = ref<TaskLog[]>([])
    const filterTask = ref<string | null>(null)
    let eventSource: EventSource | null = null

    const filteredLogs = computed((): TaskLog[] => {
        if (!filterTask.value) return logs.value
        return logs.value.filter(l => l.task_name === filterTask.value)
    })

    const taskNames = computed((): string[] => tasks.value.map(t => t.name))

    async function loadTasks(): Promise<void> {
        tasks.value = await fetchTasks()
    }

    async function loadLogs(params: TaskLogParams = {}): Promise<void> {
        logs.value = await fetchTaskLogs(params)
    }

    async function runTask(name: string): Promise<void> {
        await startTask(name)
        await loadTasks()
    }

    async function togglePause(name: string, paused: boolean): Promise<void> {
        await pauseTask(name, paused)
        await loadTasks()
    }

    function startStream(): void {
        if (eventSource) return
        eventSource = streamTaskLogs()
        eventSource.onmessage = (evt: MessageEvent) => {
            try {
                const row: TaskLog = JSON.parse(evt.data)
                logs.value.push(row)
                loadTasks()
            } catch { }
        }
        eventSource.onerror = () => {
            stopStream()
            setTimeout(() => startStream(), 3000)
        }
    }

    function stopStream(): void {
        if (eventSource) {
            eventSource.close()
            eventSource = null
        }
    }

    return {tasks, logs, filterTask, filteredLogs, taskNames, loadTasks, loadLogs, runTask, togglePause, startStream, stopStream}
})
