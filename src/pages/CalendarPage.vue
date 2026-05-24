<template>
  <div class="min-h-screen bg-zinc-900 text-zinc-100 p-3">
    <!-- Month navigation -->
    <div class="cal-nav">
      <button class="panel-btn" @click="prevMonth">←</button>
      <h2 class="cal-month-title">{{ monthLabel }}</h2>
      <button class="panel-btn" @click="nextMonth">→</button>
      <button class="panel-btn ml-2" @click="goToday">Today</button>
    </div>

    <!-- Weekday headers -->
    <div class="cal-grid cal-header">
      <div v-for="d in weekdays" :key="d" class="cal-header-cell">{{ d }}</div>
    </div>

    <!-- Day cells -->
    <div class="cal-grid cal-body">
      <div
        v-for="cell in cells"
        :key="cell.key"
        class="cal-cell"
        :class="{
          'cal-cell--other': !cell.current,
          'cal-cell--today': cell.isToday,
          'cal-cell--weekend': cell.isWeekend,
        }"
        @click="quickAdd(cell.date)"
      >
        <div class="cal-day-num">{{ cell.day }}</div>
        <div class="cal-events">
          <div
            v-for="evt in calendarStore.eventsForDate(cell.date)"
            :key="evt.id"
            class="cal-event"
            :class="'cal-event--' + evt.category"
            @click.stop
          >
            <span class="cal-event-text">
              <span v-if="evt.time" class="cal-event-time">{{ evt.time }}</span>
              {{ evt.title }}
            </span>
            <button v-if="!evt.auto" class="cal-event-del" @click="removeEvent(evt.id)">×</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick-add modal -->
    <div v-if="addingDate" class="cal-modal-overlay" @click.self="addingDate = null">
      <div class="cal-modal">
        <h3 class="cal-modal-title">Add event on {{ addingDate }}</h3>
        <input
          ref="addInput"
          v-model="newTitle"
          class="cal-modal-input"
          placeholder="Event title"
          @keydown.enter="submitAdd"
          @keydown.escape="addingDate = null"
        />
        <div class="cal-modal-row">
          <input v-model="newTime" type="time" class="cal-modal-input cal-modal-input--time" />
          <select v-model="newCategory" class="cal-modal-input cal-modal-input--cat">
            <option value="personal">Personal</option>
            <option value="work">Work</option>
            <option value="economic">Economic</option>
          </select>
        </div>
        <div class="cal-modal-actions">
          <button class="panel-btn" @click="addingDate = null">Cancel</button>
          <button class="panel-btn cal-modal-submit" @click="submitAdd" :disabled="!newTitle.trim()">Add</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useCalendarStore } from '../stores/calendar.js'

const calendarStore = useCalendarStore()

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth()) // 0-indexed

const monthLabel = computed(() => {
  const d = new Date(viewYear.value, viewMonth.value, 1)
  return d.toLocaleString('en-US', { month: 'long', year: 'numeric' })
})

function pad(n) { return String(n).padStart(2, '0') }

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
    result.push({ key: dateStr, day: d, date: dateStr, current: false, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5 })
  }

  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${pad(month + 1)}-${pad(d)}`
    const dayOfWeek = (startOffset + d - 1) % 7
    result.push({ key: dateStr, day: d, date: dateStr, current: true, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5 })
  }

  // Next month fill (complete last row)
  const remaining = 7 - (result.length % 7)
  if (remaining < 7) {
    const nextMonth = month === 11 ? 0 : month + 1
    const nextYear = month === 11 ? year + 1 : year
    for (let d = 1; d <= remaining; d++) {
      const dateStr = `${nextYear}-${pad(nextMonth + 1)}-${pad(d)}`
      const dayOfWeek = (result.length) % 7
      result.push({ key: dateStr, day: d, date: dateStr, current: false, isToday: dateStr === todayStr, isWeekend: dayOfWeek >= 5 })
    }
  }

  return result
})

// Range for loading events
const rangeStart = computed(() => cells.value[0]?.date)
const rangeEnd = computed(() => cells.value[cells.value.length - 1]?.date)

watch([rangeStart, rangeEnd], ([s, e]) => {
  if (s && e) calendarStore.load(s, e)
}, { immediate: true })

function prevMonth() {
  if (viewMonth.value === 0) { viewMonth.value = 11; viewYear.value-- }
  else viewMonth.value--
}
function nextMonth() {
  if (viewMonth.value === 11) { viewMonth.value = 0; viewYear.value++ }
  else viewMonth.value++
}
function goToday() {
  viewYear.value = today.getFullYear()
  viewMonth.value = today.getMonth()
}

// Quick-add
const addingDate = ref(null)
const newTitle = ref('')
const newTime = ref('')
const newCategory = ref('personal')
const addInput = ref(null)

function quickAdd(dateStr) {
  addingDate.value = dateStr
  newTitle.value = ''
  newTime.value = ''
  newCategory.value = 'personal'
  nextTick(() => addInput.value?.focus())
}

async function submitAdd() {
  if (!newTitle.value.trim()) return
  await calendarStore.addEvent({
    title: newTitle.value.trim(),
    date: addingDate.value,
    time: newTime.value || null,
    category: newCategory.value,
  })
  addingDate.value = null
}

async function removeEvent(id) {
  await calendarStore.removeEvent(id)
}
</script>
