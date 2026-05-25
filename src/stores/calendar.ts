import {defineStore} from 'pinia'
import {ref} from 'vue'
import * as localDb from '../services/local-db'
import type {CalendarEvent, CalendarEventInput} from '../types'

export const useCalendarStore = defineStore('calendar', () => {
    const events = ref<CalendarEvent[]>([])
    const loading = ref(false)
    let lastStart = ''
    let lastEnd = ''

    function load(start: string, end: string): void {
        loading.value = true
        lastStart = start
        lastEnd = end
        try {
            const rows = localDb.query(
                "SELECT * FROM calendar_events WHERE date >= ? AND date <= ? ORDER BY date, time",
                [start, end]
            )
            events.value = rows
        } finally {
            loading.value = false
        }
    }

    function addEvent(data: CalendarEventInput): CalendarEvent {
        const id = crypto.randomUUID()
        const row: CalendarEvent = {id, ...data, auto: false}
        localDb.upsert('calendar_events', {id}, {
            title: data.title, date: data.date, time: data.time,
            category: data.category, auto: 0,
        })
        events.value.push(row)
        return row
    }

    function removeEvent(id: string): void {
        localDb.remove('calendar_events', {id})
        events.value = events.value.filter(e => e.id !== id)
    }

    function eventsForDate(dateStr: string): CalendarEvent[] {
        return events.value.filter(e => e.date === dateStr)
    }

    localDb.onChange((table) => {
        if (table === 'calendar_events' && lastStart && lastEnd) {
            load(lastStart, lastEnd)
        }
    })

    return {events, loading, load, addEvent, removeEvent, eventsForDate}
})
