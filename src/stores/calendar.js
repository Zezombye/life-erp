import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchCalendarEvents, createCalendarEvent, deleteCalendarEvent } from '../services/api.js'

export const useCalendarStore = defineStore('calendar', () => {
    const events = ref([])
    const loading = ref(false)

    async function load(start, end) {
        loading.value = true
        try {
            events.value = await fetchCalendarEvents(start, end)
        } finally {
            loading.value = false
        }
    }

    async function addEvent(data) {
        const row = await createCalendarEvent(data)
        events.value.push(row)
        return row
    }

    async function removeEvent(id) {
        await deleteCalendarEvent(id)
        events.value = events.value.filter(e => e.id !== id)
    }

    function eventsForDate(dateStr) {
        return events.value.filter(e => e.date === dateStr)
    }

    return { events, loading, load, addEvent, removeEvent, eventsForDate }
})
