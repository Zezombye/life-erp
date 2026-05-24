import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchTasks, startTask, pauseTask, fetchTaskLogs, streamTaskLogs } from '../services/api.js'

export const useTaskStore = defineStore('tasks', () => {
    const tasks = ref([])
    const logs = ref([])
    const filterTask = ref(null) // null = all
    let eventSource = null

    const filteredLogs = computed(() => {
        if (!filterTask.value) return logs.value
        return logs.value.filter(l => l.task_name === filterTask.value)
    })

    const taskNames = computed(() => tasks.value.map(t => t.name))

    async function loadTasks() {
        tasks.value = await fetchTasks()
    }

    async function loadLogs(params = {}) {
        logs.value = await fetchTaskLogs(params)
    }

    async function runTask(name) {
        await startTask(name)
        await loadTasks()
    }

    async function togglePause(name, paused) {
        await pauseTask(name, paused)
        await loadTasks()
    }

    function startStream() {
        if (eventSource) return
        eventSource = streamTaskLogs()
        eventSource.onmessage = (evt) => {
            try {
                const row = JSON.parse(evt.data)
                logs.value.push(row)
                // Refresh task list to update running status
                loadTasks()
            } catch { }
        }
        eventSource.onerror = () => {
            stopStream()
            // Reconnect after 3s
            setTimeout(() => startStream(), 3000)
        }
    }

    function stopStream() {
        if (eventSource) {
            eventSource.close()
            eventSource = null
        }
    }

    return { tasks, logs, filterTask, filteredLogs, taskNames, loadTasks, loadLogs, runTask, togglePause, startStream, stopStream }
})
