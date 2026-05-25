// ── Habits ──
export interface HabitRow {
    date: string
    weight: number | null
    job: number | null
    workout: number | null
    business: number | null
    reading_watching: number | null
    misc: number | null
    girls_family: number | null
    mma: number | null
    total: number | null
    total_hours: number | null
    [key: string]: string | number | null | undefined
}

export interface HabitColumn {
    key: string
    label: string
    editable: boolean
    width: number
    displayFormat?: string
    colorGroup?: string
}

export interface CellColor {
    bg: string
    text: string
    max?: number
}

// ── Stocks ──
export interface Candle {
    open: number
    close: number
    high: number
    low: number
}

export interface Stock {
    ticker: string
    price: number
    change: number
    change_pct: number
    candles: Candle[]
}

// ── Workouts ──
export interface WorkoutRow {
    date: string
    type: string | null
    notes: string | null
    [key: string]: string | number | null | undefined
}

export interface WorkoutColumn {
    key: string
    label: string
    editable: boolean
    width: number
    displayFormat?: string
    colType?: string
}

// ── Calendar ──
export interface CalendarEvent {
    id: string
    title: string
    date: string
    time: string | null
    category: string
    auto?: boolean
}

export interface CalendarEventInput {
    title: string
    date: string
    time: string | null
    category: string
}

// ── Chores ──
export interface Chore {
    id: string
    title: string
    interval_days: number
    last_done: string | null
}

// ── Todos ──
export interface Todo {
    id: string
    title: string
    status: 'open' | 'closed'
    created_at: string
    closed_at: string | null
}

export interface TodoMessage {
    id: string
    content: string
    created_at: string
    updated_at: string
}

// ── Tasks ──
export interface Task {
    name: string
    description: string
    running: boolean
    paused: boolean
}

export interface TaskLog {
    id: number
    task_name: string
    message: string
    created_at: string
}

export interface TaskLogParams {
    task?: string
    limit?: number
    since_id?: number
}

// ── Settings ──
export interface Settings {
    [key: string]: string
}
