<template>
    <div class="dashboard-panel task-panel">
        <div class="panel-header">
            <h2 class="panel-title">Tasks</h2>
            <div class="panel-header-actions">
                <Button v-for="t in taskStore.tasks" :key="t.name" :label="t.name" icon="pi pi-play" severity="secondary" size="small" :disabled="t.running || t.paused" @click="taskStore.runTask(t.name)" v-tooltip="t.description" />
                <Button v-for="t in taskStore.tasks" :key="'p' + t.name" :icon="t.paused ? 'pi pi-play' : 'pi pi-pause'" :severity="t.paused ? 'danger' : 'secondary'" text size="small" @click="taskStore.togglePause(t.name, !t.paused)" v-tooltip="t.paused ? 'Resume ' + t.name : 'Pause ' + t.name" />
            </div>
        </div>

        <!-- Log filter buttons -->
        <div class="task-log-filters">
            <SelectButton :modelValue="taskStore.filterTask" @update:modelValue="v => taskStore.filterTask = v" :options="logFilterOptions" optionLabel="label" optionValue="value" size="small" :allowEmpty="false" />
        </div>

        <!-- Log viewer -->
        <div ref="logContainer" class="task-log-viewer">
            <div v-if="taskStore.filteredLogs.length === 0" class="task-log-empty">No logs yet</div>
            <div v-for="log in taskStore.filteredLogs" :key="log.id" class="task-log-line">
                <span class="task-log-date">{{ formatDate(log.created_at) }}</span>
                <span class="task-log-task">{{ log.task_name }}</span>
                <span class="task-log-msg" v-html="ansiToHtml(log.message)"></span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, computed, watch, nextTick, onMounted} from 'vue'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import {useTaskStore} from '../stores/tasks'

const taskStore = useTaskStore()
const logContainer = ref<HTMLDivElement | null>(null)

const logFilterOptions = computed(() => [
    {label: 'All', value: null},
    ...taskStore.taskNames.map(n => ({label: n, value: n})),
])

onMounted(async () => {
    await taskStore.loadTasks()
    await taskStore.loadLogs()
    scrollToBottom()
})

// Auto-scroll on new logs
watch(() => taskStore.filteredLogs.length, () => {
    nextTick(() => scrollToBottom())
})

function scrollToBottom(): void {
    if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
}

function formatDate(iso: string): string {
    if (!iso) return ''
    // Show just time portion if today
    return iso.replace('T', ' ').slice(5, 19)
}

// ANSI color code to HTML converter
const ANSI_COLORS: Record<string, string> = {
    '30': '#1e1e1e', '31': '#f87171', '32': '#4ade80', '33': '#fbbf24',
    '34': '#60a5fa', '35': '#c084fc', '36': '#22d3ee', '37': '#d4d4d8',
    '90': '#71717a', '91': '#fca5a5', '92': '#86efac', '93': '#fde68a',
    '94': '#93c5fd', '95': '#d8b4fe', '96': '#67e8f9', '97': '#f4f4f5',
}

function ansiToHtml(str: string): string {
    if (!str) return ''
    // Escape HTML first
    let s = str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Replace ANSI codes
    const parts = []
    let openTags = 0
    let i = 0
    const re = /\x1b\[([0-9;]*)m/g
    let last = 0
    let match: RegExpExecArray | null
    while ((match = re.exec(s)) !== null) {
        // Push text before this escape
        if (match.index > last) {
            parts.push(s.slice(last, match.index))
        }
        last = match.index + match[0].length

        const codes = match[1]!.split(';').filter(Boolean)
        if (codes.length === 0 || codes.includes('0')) {
            // Reset
            for (let j = 0; j < openTags; j++) parts.push('</span>')
            openTags = 0
        } else {
            let style = ''
            for (const code of codes) {
                if (code === '1') style += 'font-weight:700;'
                else if (code === '3') style += 'font-style:italic;'
                else if (code === '4') style += 'text-decoration:underline;'
                else if (ANSI_COLORS[code]) style += `color:${ANSI_COLORS[code]};`
            }
            if (style) {
                parts.push(`<span style="${style}">`)
                openTags++
            }
        }
    }
    // Remaining text
    if (last < s.length) parts.push(s.slice(last))
    // Close any remaining open tags
    for (let j = 0; j < openTags; j++) parts.push('</span>')

    return parts.join('')
}
</script>

<style lang="scss">
.task-panel {
    max-height: 300px;
}

.task-log-viewer {
    flex: 1;
    overflow-y: auto;
    padding: 0.25rem 0.5rem;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.75rem;
    line-height: 1.5;
}

.task-log-empty {
    color: #52525b;
    text-align: center;
    padding: 1rem;
    font-size: 0.8125rem;
}

.task-log-line {
    white-space: pre-wrap;
    word-break: break-all;
}

.task-log-date {
    color: #52525b;
    margin-right: 0.5rem;
}

.task-log-task {
    color: #60a5fa;
    margin-right: 0.5rem;

    &::before {
        content: '[';
    }

    &::after {
        content: ']';
    }
}

.task-log-msg {
    color: #d4d4d8;
}
</style>
