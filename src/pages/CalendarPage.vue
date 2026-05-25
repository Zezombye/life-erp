<template>
    <div class="min-h-screen bg-zinc-900 text-zinc-100 p-3">
        <!-- Month navigation -->
        <div class="cal-nav">
            <Button icon="pi pi-chevron-left" severity="secondary" text size="small" @click="prevMonth" />
            <h2 class="cal-month-title">{{ monthLabel }}</h2>
            <Button icon="pi pi-chevron-right" severity="secondary" text size="small" @click="nextMonth" />
            <Button label="Today" severity="secondary" size="small" class="ml-2" @click="goToday" />
        </div>

        <!-- Weekday headers -->
        <div class="cal-grid cal-header">
            <div v-for="d in weekdays" :key="d" class="cal-header-cell">{{ d }}</div>
        </div>

        <!-- Day cells -->
        <div class="cal-grid cal-body">
            <div v-for="cell in cells" :key="cell.key" class="cal-cell" :class="{
                'cal-cell--other': !cell.current,
                'cal-cell--today': cell.isToday,
                'cal-cell--weekend': cell.isWeekend,
            }" @click="quickAdd(cell.date)">
                <div class="cal-day-num">{{ cell.day }}</div>
                <div class="cal-events">
                    <div v-for="evt in calendarStore.eventsForDate(cell.date)" :key="evt.id" class="cal-event" :class="'cal-event--' + evt.category" @click.stop>
                        <span class="cal-event-text">
                            <span v-if="evt.time" class="cal-event-time">{{ evt.time }}</span>
                            {{ evt.title }}
                        </span>
                        <Button v-if="!evt.auto" icon="pi pi-times" severity="secondary" text size="small" class="cal-event-del-btn" @click="removeEvent(evt.id)" />
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick-add dialog -->
        <Dialog v-model:visible="addDialogVisible" :header="'Add event on ' + addingDate" modal :style="{width: '360px'}">
            <div class="flex flex-col gap-3">
                <InputText ref="addInput" v-model="newTitle" placeholder="Event title" class="w-full" @keydown.enter="submitAdd" />
                <div class="flex gap-2">
                    <InputText v-model="newTime" type="time" class="w-30" />
                    <Select v-model="newCategory" :options="categoryOptions" optionLabel="label" optionValue="value" class="flex-1" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancel" severity="secondary" size="small" @click="addDialogVisible = false" />
                <Button label="Add" severity="primary" size="small" @click="submitAdd" :disabled="!newTitle.trim()" />
            </template>
        </Dialog>
    </div>
</template>

<script setup lang="ts">
import {ref, computed, watch, onMounted, nextTick} from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import {useCalendarStore} from '../stores/calendar'

const calendarStore = useCalendarStore()

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const categoryOptions = [
    {label: 'Personal', value: 'personal'},
    {label: 'Work', value: 'work'},
    {label: 'Economic', value: 'economic'},
]

const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth()) // 0-indexed

const monthLabel = computed(() => {
    const d = new Date(viewYear.value, viewMonth.value, 1)
    return d.toLocaleString('en-US', {month: 'long', year: 'numeric'})
})

function pad(n: number) {return String(n).padStart(2, '0')}

const cells = computed(() => {
    const year = viewYear.value
    const month = viewMonth.value
    const firstDay = new Date(year, month, 1)
    // Monday=0 start
    let startOffset = (firstDay.getDay() + 6) % 7
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    const result = []
    const todayStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

    // Previous month fill
    const prevMonth = month === 0 ? 11 : month - 1
    const prevYear = month === 0 ? year - 1 : year
    const daysInPrev = new Date(prevYear, prevMonth + 1, 0).getDate()
    for (let i = startOffset - 1; i >= 0; i--) {
        const d = daysInPrev - i
        const dateStr = `${prevYear}-${pad(prevMonth + 1)}-${pad(d)}`
        const dayOfWeek = (startOffset - i - 1 + 7) % 7
        result.push({key: dateStr, day: d, date: dateStr, current: false, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5})
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${year}-${pad(month + 1)}-${pad(d)}`
        const dayOfWeek = (startOffset + d - 1) % 7
        result.push({key: dateStr, day: d, date: dateStr, current: true, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5})
    }

    // Next month fill (complete last row)
    const remaining = 7 - (result.length % 7)
    if (remaining < 7) {
        const nextMonth = month === 11 ? 0 : month + 1
        const nextYear = month === 11 ? year + 1 : year
        for (let d = 1; d <= remaining; d++) {
            const dateStr = `${nextYear}-${pad(nextMonth + 1)}-${pad(d)}`
            const dayOfWeek: number = (result.length) % 7
            result.push({key: dateStr, day: d, date: dateStr, current: false, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5})
        }
    }

    return result
})

// Range for loading events
const rangeStart = computed(() => cells.value[0]?.date)
const rangeEnd = computed(() => cells.value[cells.value.length - 1]?.date)

watch([rangeStart, rangeEnd], ([s, e]) => {
    if (s && e) calendarStore.load(s, e)
}, {immediate: true})

function prevMonth() {
    if (viewMonth.value === 0) {viewMonth.value = 11; viewYear.value--}
    else viewMonth.value--
}
function nextMonth() {
    if (viewMonth.value === 11) {viewMonth.value = 0; viewYear.value++}
    else viewMonth.value++
}
function goToday() {
    viewYear.value = today.getFullYear()
    viewMonth.value = today.getMonth()
}

// Quick-add
const addingDate = ref<string | null>(null)
const addDialogVisible = ref(false)
const newTitle = ref('')
const newTime = ref('')
const newCategory = ref('personal')
const addInput = ref<InstanceType<typeof InputText> | null>(null)

function quickAdd(dateStr: string) {
    addingDate.value = dateStr
    newTitle.value = ''
    newTime.value = ''
    newCategory.value = 'personal'
    addDialogVisible.value = true
    nextTick(() => addInput.value?.focus())
}

async function submitAdd(): Promise<void> {
    if (!newTitle.value.trim()) return
    await calendarStore.addEvent({
        title: newTitle.value.trim(),
        date: addingDate.value!,
        time: newTime.value || null,
        category: newCategory.value,
    })
    addDialogVisible.value = false
    addingDate.value = null
}

async function removeEvent(id: number): Promise<void> {
    await calendarStore.removeEvent(id)
}
</script>

<style lang="scss">
.cal-nav {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.cal-month-title {
    font-size: 1.125rem;
    font-weight: 600;
    min-width: 200px;
    text-align: center;
}

.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
}

.cal-header-cell {
    padding: 0.25rem;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 600;
    color: #a1a1aa;
    text-transform: uppercase;
}

.cal-body {
    border-top: 1px solid #27272a;
    border-left: 1px solid #27272a;
}

.cal-cell {
    min-height: 100px;
    border-right: 1px solid #27272a;
    border-bottom: 1px solid #27272a;
    padding: 0.25rem;
    cursor: pointer;
    background: #18181b;
    transition: background 0.1s;

    &:hover {
        background: #1e1e22;
    }
}

.cal-cell--other {
    opacity: 0.35;
}

.cal-cell--today {
    background: #1a2332;

    .cal-day-num {
        color: #3b82f6;
        font-weight: 700;
    }
}

.cal-cell--weekend {
    background: #1b1b1f;
}

.cal-cell--today.cal-cell--weekend {
    background: #1a2332;
}

.cal-day-num {
    font-size: 0.8125rem;
    font-weight: 500;
    color: #d4d4d8;
    margin-bottom: 0.125rem;
}

.cal-events {
    display: flex;
    flex-direction: column;
    gap: 1px;
}

.cal-event {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.25rem;
    padding: 0.0625rem 0.25rem;
    border-radius: 0.1875rem;
    font-size: 0.6875rem;
    line-height: 1.3;
    cursor: default;
}

.cal-event--personal {
    background: #1e3a5f;
    color: #93c5fd;
}

.cal-event--work {
    background: #3b2f1e;
    color: #fbbf24;
}

.cal-event--fomc {
    background: #3b1e2e;
    color: #f472b6;
}

.cal-event--opex {
    background: #2e1e3b;
    color: #c084fc;
}

.cal-event--economic {
    background: #1e3b2e;
    color: #6ee7b7;
}

.cal-event-time {
    opacity: 0.7;
    margin-right: 0.125rem;
}

.cal-event-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
}

.cal-event-del-btn {
    flex-shrink: 0;
    opacity: 0;
    width: 14px !important;
    height: 14px !important;
    padding: 0 !important;
}

.cal-event:hover .cal-event-del-btn {
    opacity: 0.7;
}
</style>
