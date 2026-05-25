import {defineStore} from 'pinia'
import {ref} from 'vue'
import {fetchCalendarEvents, createCalendarEvent, deleteCalendarEvent} from '../services/api'
import type {CalendarEvent, CalendarEventInput} from '../types'

export const useCalendarStore = defineStore('calendar', () => {
    const events = ref<CalendarEvent[]>([])
    const loading = ref(false)

    async function load(start: string, end: string): Promise<void> {
        loading.value = true
        try {
            events.value = await fetchCalendarEvents(start, end)
        } finally {
            loading.value = false
        }
    }

    async function addEvent(data: CalendarEventInput): Promise<CalendarEvent> {
        const row = await createCalendarEvent(data)
        events.value.push(row)
        return row
    }

    async function removeEvent(id: number): Promise<void> {
        await deleteCalendarEvent(id)
        events.value = events.value.filter(e => e.id !== id)
    }

    function eventsForDate(dateStr: string): CalendarEvent[] {
        return events.value.filter(e => e.date === dateStr)
    }

    return {events, loading, load, addEvent, removeEvent, eventsForDate}
})
