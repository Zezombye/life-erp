import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import {fetchTasks, fetchTaskLogs} from '../services/api'
import {setTaskLogHandler, startTask as wsStartTask, pauseTask as wsPauseTask} from '../services/sync-engine'
import type {Task, TaskLog, TaskLogParams} from '../types'

export const useTaskStore = defineStore('tasks', () => {
    const tasks = ref<Task[]>([])
    const logs = ref<TaskLog[]>([])
    const filterTask = ref<string | null>(null)

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
        wsStartTask(name)
        await loadTasks()
    }

    async function togglePause(name: string, paused: boolean): Promise<void> {
        wsPauseTask(name, paused)
        await loadTasks()
    }

    // Receive live task logs via WebSocket
    setTaskLogHandler((log: TaskLog) => {
        logs.value.push(log)
        loadTasks()
    })

    return {tasks, logs, filterTask, filteredLogs, taskNames, loadTasks, loadLogs, runTask, togglePause}
})
