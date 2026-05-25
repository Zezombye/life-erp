import {ref} from 'vue'
import * as localDb from './local-db'
import type {Change, Schema} from './local-db'
import type {TaskLog, Stock} from '../types'

export type ConnectionState = 'offline' | 'connecting' | 'syncing' | 'online'

const API_BASE = 'http://localhost:8000'
const WS_BASE = 'ws://localhost:8000'

const connectionState = ref<ConnectionState>('offline')
const pendingCount = ref(0)

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectDelay = 1000
const MAX_RECONNECT_DELAY = 30000

// External handlers for non-sync messages
let onTaskLog: ((log: TaskLog) => void) | null = null
let onStockUpdate: ((data: Stock[]) => void) | null = null

export function getConnectionState() {
    return connectionState
}

export function getPendingCount() {
    return pendingCount
}

export function setTaskLogHandler(handler: (log: TaskLog) => void): void {
    onTaskLog = handler
}

export function setStockUpdateHandler(handler: (data: Stock[]) => void): void {
    onStockUpdate = handler
}

export async function init(): Promise<void> {
    // Initialize local database
    await localDb.initLocalDb()

    // Try fetching schema and applying it
    try {
        const res = await fetch(`${API_BASE}/api/schema`)
        if (res.ok) {
            const schema: Schema = await res.json()
            localDb.syncSchema(schema)
        }
    } catch {
        // Offline — schema will be synced when WebSocket connects
    }

    // Update pending count
    pendingCount.value = localDb.getPendingChanges().length

    // Listen for local changes to send via WebSocket
    localDb.onChange(() => {
        pendingCount.value = localDb.getPendingChanges().length
        flushPendingChanges()
    })

    // Start WebSocket connection
    connect()

    // Notify all stores to re-read the now-loaded DB
    // (child onMounted fires before App.vue's, so stores loaded before DB was ready)
    localDb.notifyAll()

    // Reconnect on online/offline events
    window.addEventListener('online', () => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            connect()
        }
    })
    window.addEventListener('offline', () => {
        connectionState.value = 'offline'
    })
}

function connect(): void {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return
    }

    connectionState.value = 'connecting'
    const clientId = localDb.getClientId()

    try {
        ws = new WebSocket(`${WS_BASE}/ws?client_id=${encodeURIComponent(clientId)}`)
    } catch {
        scheduleReconnect()
        return
    }

    ws.onopen = () => {
        reconnectDelay = 1000 // Reset backoff
        // Schema message will come first, then we send sync request
    }

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data)
            handleMessage(msg)
        } catch {
            // Ignore malformed messages
        }
    }

    ws.onclose = () => {
        ws = null
        if (connectionState.value !== 'offline') {
            connectionState.value = 'offline'
        }
        scheduleReconnect()
    }

    ws.onerror = () => {
        // onclose will fire after this
    }
}

function scheduleReconnect(): void {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        if (navigator.onLine !== false) {
            connect()
        }
    }, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
}

function handleMessage(msg: Record<string, unknown>): void {
    const type = msg.type as string

    switch (type) {
        case 'schema': {
            const schema = msg.schema as Schema
            localDb.syncSchema(schema)
            // Now send sync request
            sendSyncRequest()
            break
        }

        case 'sync_response': {
            const changes = msg.changes as Change[]
            const lastSeq = msg.last_seq as number

            // Batch notifications to avoid per-row store reloads
            localDb.beginBatch()
            for (const change of changes) {
                localDb.applyRemoteChange(change)
            }
            localDb.setLastSeq(lastSeq)
            localDb.endBatch()

            // Clear pending changes that were sent during sync
            localDb.clearPendingChanges()
            pendingCount.value = 0

            // Mark sync completed and persist DB immediately
            localDb.markSyncCompleted()

            connectionState.value = 'online'
            break
        }

        case 'change': {
            const change = msg.change as Change
            localDb.applyRemoteChange(change)
            if (change.seq) {
                localDb.setLastSeq(change.seq)
            }
            break
        }

        case 'ack': {
            const lastSeq = msg.last_seq as number
            localDb.setLastSeq(lastSeq)
            localDb.clearPendingChanges()
            pendingCount.value = 0
            break
        }

        case 'log': {
            const log = msg.log as TaskLog
            if (onTaskLog) onTaskLog(log)
            break
        }

        case 'stock': {
            const data = msg.data as Stock[]
            if (onStockUpdate) onStockUpdate(data)
            break
        }

        case 'ping':
            // Keepalive, ignore
            break
    }
}

function sendSyncRequest(): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    connectionState.value = 'syncing'
    const lastSeq = localDb.getLastSeq()
    const pending = localDb.getPendingChanges()

    ws.send(JSON.stringify({
        type: 'sync',
        last_seq: lastSeq,
        pending_changes: pending,
    }))
}

function flushPendingChanges(): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (connectionState.value !== 'online') return

    const pending = localDb.getPendingChanges()
    if (pending.length === 0) return

    ws.send(JSON.stringify({
        type: 'changes',
        changes: pending,
    }))
}

// ── Task control via WebSocket ──

export function startTask(taskName: string): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: 'task_start', task_name: taskName}))
    }
}

export function pauseTask(taskName: string, paused: boolean): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: 'task_pause', task_name: taskName, paused}))
    }
}

export function forceResync(): void {
    localDb.wipeLocalData()
    pendingCount.value = 0

    if (ws && ws.readyState === WebSocket.OPEN) {
        // Already connected — just send a fresh sync request (last_seq is now 0)
        sendSyncRequest()
    } else {
        // Reconnect
        connect()
    }
}
