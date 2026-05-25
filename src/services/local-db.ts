import initSqlJs from 'sql.js'

interface SqlJsDatabase {
    run(sql: string, params?: any[]): void
    exec(sql: string, params?: any[]): Array<{columns: string[]; values: any[][]}>
    export(): Uint8Array
    close(): void
}

export interface Change {
    table: string
    pk: Record<string, unknown>
    op: 'upsert' | 'delete'
    data: Record<string, unknown> | null
    timestamp: string
    client_id?: string
    seq?: number
}

export interface SchemaTable {
    columns: Record<string, {type: string; primary_key?: boolean}>
    sync?: boolean
}

export type Schema = Record<string, SchemaTable>

type ChangeListener = (table: string) => void

let db: SqlJsDatabase | null = null
let schema: Schema | null = null
let clientId: string = ''
const listeners: ChangeListener[] = []

// OPFS persistence handle
let opfsHandle: FileSystemFileHandle | null = null
let persistTimer: ReturnType<typeof setTimeout> | null = null
const PERSIST_DEBOUNCE_MS = 500

export function getClientId(): string {
    return clientId
}

export async function initLocalDb(): Promise<void> {
    const SQL = await initSqlJs({
        locateFile: () => '/sql-wasm.wasm',
    })

    // Try to load existing DB from OPFS
    let existingData: Uint8Array | null = null
    try {
        const root = await navigator.storage.getDirectory()
        opfsHandle = await root.getFileHandle('life_erp.sqlite', {create: true})
        const file = await opfsHandle.getFile()
        console.log('[local-db] OPFS file size:', file.size)
        if (file.size > 0) {
            existingData = new Uint8Array(await file.arrayBuffer())
        }
    } catch (e) {
        // OPFS not available, run in-memory only
        console.warn('[local-db] OPFS not available:', e)
        opfsHandle = null
    }

    db = existingData ? new SQL.Database(existingData) : new SQL.Database()
    console.log('[local-db] DB loaded from OPFS:', !!existingData)

    // Create internal tables
    db.run(`
        CREATE TABLE IF NOT EXISTS _pending_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            pk_value TEXT NOT NULL,
            op TEXT NOT NULL,
            data TEXT,
            timestamp TEXT NOT NULL
        )
    `)
    db.run(`
        CREATE TABLE IF NOT EXISTS _sync_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    `)

    // Load or generate client ID
    const row = db.exec("SELECT value FROM _sync_state WHERE key = 'client_id'")
    if (row.length > 0 && row[0]!.values.length > 0) {
        clientId = row[0]!.values[0]![0] as string
    } else {
        clientId = crypto.randomUUID()
        db.run("INSERT INTO _sync_state (key, value) VALUES ('client_id', ?)", [clientId])
    }

    // Persist on page hide
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            persistToOpfs()
        }
    })
}

export function syncSchema(newSchema: Schema): void {
    if (!db) throw new Error('DB not initialized')
    schema = newSchema

    for (const [tableName, tableDef] of Object.entries(newSchema)) {
        const columns = tableDef.columns

        // Check if table exists
        const exists = db.exec(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [tableName]
        )

        if (exists.length === 0 || exists[0]!.values.length === 0) {
            // Create table
            const colDefs: string[] = []
            const pkCols: string[] = []
            for (const [colName, colOpts] of Object.entries(columns)) {
                colDefs.push(`${colName} ${colOpts.type}`)
                if (colOpts.primary_key) pkCols.push(colName)
            }
            if (pkCols.length > 0) {
                colDefs.push(`PRIMARY KEY (${pkCols.join(', ')})`)
            }
            db.run(`CREATE TABLE ${tableName} (${colDefs.join(', ')})`)
        } else {
            // Get current columns
            const pragma = db.exec(`PRAGMA table_info(${tableName})`)
            const existingCols = new Set<string>()
            if (pragma.length > 0) {
                for (const row of pragma[0]!.values) {
                    existingCols.add(row[1] as string)
                }
            }
            const desiredCols = new Set(Object.keys(columns))

            // Add missing columns
            for (const colName of desiredCols) {
                if (!existingCols.has(colName)) {
                    const colType = columns[colName]!.type
                    db.run(`ALTER TABLE ${tableName} ADD COLUMN ${colName} ${colType}`)
                }
            }

            // Drop removed columns
            for (const colName of existingCols) {
                if (!desiredCols.has(colName)) {
                    db.run(`ALTER TABLE ${tableName} DROP COLUMN ${colName}`)
                }
            }
        }
    }

    schedulePersist()
}

export function wipeLocalData(): void {
    if (!db || !schema) return
    for (const tableName of Object.keys(schema)) {
        db.run(`DELETE FROM ${tableName}`)
    }
    db.run("DELETE FROM _pending_changes")
    db.run("INSERT OR REPLACE INTO _sync_state (key, value) VALUES ('last_server_seq', '0')")
    db.run("DELETE FROM _sync_state WHERE key = 'sync_completed'")
    schedulePersist()
    // Notify all tables so stores reload (empty)
    for (const tableName of Object.keys(schema)) {
        notifyListeners(tableName)
    }
}

export function getLastSeq(): number {
    if (!db) return 0

    const row = db.exec("SELECT value FROM _sync_state WHERE key = 'last_server_seq'")
    const seq = (row.length > 0 && row[0]!.values.length > 0)
        ? parseInt(row[0]!.values[0]![0] as string, 10) || 0
        : 0

    // If last_seq > 0 but we never completed an initial sync (flag not set),
    // the OPFS data was lost. Reset to 0 to force a full snapshot.
    if (seq > 0) {
        const flag = db.exec("SELECT value FROM _sync_state WHERE key = 'sync_completed'")
        const completed = flag.length > 0 && flag[0]!.values.length > 0 && flag[0]!.values[0]![0] === '1'
        console.log('[local-db] getLastSeq: stored seq =', seq, ', sync_completed =', completed)
        if (!completed) {
            db.run("INSERT OR REPLACE INTO _sync_state (key, value) VALUES ('last_server_seq', '0')")
            console.log('[local-db] getLastSeq: reset to 0 (sync never completed)')
            return 0
        }
    }

    console.log('[local-db] getLastSeq: returning', seq)
    return seq
}

/** Mark that a full sync has completed and persist immediately. */
export function markSyncCompleted(): void {
    if (!db) return
    db.run("INSERT OR REPLACE INTO _sync_state (key, value) VALUES ('sync_completed', '1')")
    // Persist immediately (not debounced) so the flag survives page close
    persistToOpfs()
}

export function setLastSeq(seq: number): void {
    if (!db) return
    db.run(
        "INSERT OR REPLACE INTO _sync_state (key, value) VALUES ('last_server_seq', ?)",
        [String(seq)]
    )
}

export function getAll(table: string): any[] {
    if (!db) return []
    const result = db.exec(`SELECT * FROM ${table}`)
    if (result.length === 0) return []
    const cols = result[0]!.columns
    return result[0]!.values.map(row => {
        const obj: Record<string, unknown> = {}
        for (let i = 0; i < cols.length; i++) {
            obj[cols[i]!] = row[i]
        }
        return obj
    })
}

export function query(sql: string, params?: unknown[]): any[] {
    if (!db) return []
    const result = db.exec(sql, params as never[])
    if (result.length === 0) return []
    const cols = result[0]!.columns
    return result[0]!.values.map(row => {
        const obj: Record<string, unknown> = {}
        for (let i = 0; i < cols.length; i++) {
            obj[cols[i]!] = row[i]
        }
        return obj
    })
}

export function getByPk(table: string, pk: Record<string, unknown>): Record<string, unknown> | null {
    if (!db) return null
    const where = Object.keys(pk).map(k => `${k} = ?`).join(' AND ')
    const vals = Object.values(pk)
    const result = db.exec(`SELECT * FROM ${table} WHERE ${where}`, vals as never[])
    if (result.length === 0 || result[0]!.values.length === 0) return null
    const cols = result[0]!.columns
    const row = result[0]!.values[0]!
    const obj: Record<string, unknown> = {}
    for (let i = 0; i < cols.length; i++) {
        obj[cols[i]!] = row[i]
    }
    return obj
}

function getPkColumns(table: string): string[] {
    if (!schema || !schema[table]) return []
    return Object.entries(schema[table].columns)
        .filter(([, opts]) => opts.primary_key)
        .map(([name]) => name)
}

export function upsert(
    table: string,
    pk: Record<string, unknown>,
    data: Record<string, unknown>,
    timestamp?: string
): void {
    if (!db) return
    const ts = timestamp || new Date().toISOString()
    const pkCols = getPkColumns(table)

    // Check if row exists
    const where = Object.keys(pk).map(k => `${k} = ?`).join(' AND ')
    const existing = db.exec(`SELECT * FROM ${table} WHERE ${where}`, Object.values(pk) as never[])

    if (existing.length > 0 && existing[0]!.values.length > 0) {
        // Update only changed fields
        const setCols = Object.keys(data).filter(k => !pkCols.includes(k))
        if (setCols.length > 0) {
            const setStr = setCols.map(k => `${k} = ?`).join(', ')
            const setVals = setCols.map(k => data[k])
            db.run(
                `UPDATE ${table} SET ${setStr} WHERE ${where}`,
                [...setVals, ...Object.values(pk)] as never[]
            )
        }
    } else {
        // Insert: merge pk + data
        const allData = {...pk, ...data}
        const cols = Object.keys(allData)
        const placeholders = cols.map(() => '?').join(', ')
        db.run(
            `INSERT INTO ${table} (${cols.join(', ')}) VALUES (${placeholders})`,
            Object.values(allData) as never[]
        )
    }

    // Record pending change
    db.run(
        "INSERT INTO _pending_changes (table_name, pk_value, op, data, timestamp) VALUES (?, ?, 'upsert', ?, ?)",
        [table, JSON.stringify(pk), JSON.stringify(data), ts]
    )

    schedulePersist()
    notifyListeners(table)
}

export function remove(table: string, pk: Record<string, unknown>, timestamp?: string): void {
    if (!db) return
    const ts = timestamp || new Date().toISOString()

    const where = Object.keys(pk).map(k => `${k} = ?`).join(' AND ')
    db.run(`DELETE FROM ${table} WHERE ${where}`, Object.values(pk) as never[])

    db.run(
        "INSERT INTO _pending_changes (table_name, pk_value, op, data, timestamp) VALUES (?, ?, 'delete', NULL, ?)",
        [table, JSON.stringify(pk), ts]
    )

    schedulePersist()
    notifyListeners(table)
}

export function applyRemoteChange(change: Change): void {
    if (!db) return

    const {table, pk, op, data} = change

    if (op === 'delete') {
        const where = Object.keys(pk).map(k => `${k} = ?`).join(' AND ')
        db.run(`DELETE FROM ${table} WHERE ${where}`, Object.values(pk) as never[])
    } else if (op === 'upsert' && data) {
        const pkCols = getPkColumns(table)
        const where = Object.keys(pk).map(k => `${k} = ?`).join(' AND ')
        const existing = db.exec(`SELECT 1 FROM ${table} WHERE ${where}`, Object.values(pk) as never[])

        if (existing.length > 0 && existing[0]!.values.length > 0) {
            const setCols = Object.keys(data).filter(k => !pkCols.includes(k))
            if (setCols.length > 0) {
                const setStr = setCols.map(k => `${k} = ?`).join(', ')
                const setVals = setCols.map(k => data[k])
                db.run(
                    `UPDATE ${table} SET ${setStr} WHERE ${where}`,
                    [...setVals, ...Object.values(pk)] as never[]
                )
            }
        } else {
            const allData = {...pk, ...data}
            const cols = Object.keys(allData)
            const placeholders = cols.map(() => '?').join(', ')
            db.run(
                `INSERT INTO ${table} (${cols.join(', ')}) VALUES (${placeholders})`,
                Object.values(allData) as never[]
            )
        }
    }

    schedulePersist()
    notifyListeners(table)
}

export function getPendingChanges(): Change[] {
    if (!db) return []
    const result = db.exec("SELECT * FROM _pending_changes ORDER BY id ASC")
    if (result.length === 0) return []
    const cols = result[0]!.columns
    return result[0]!.values.map(row => {
        const obj: Record<string, unknown> = {}
        for (let i = 0; i < cols.length; i++) {
            obj[cols[i]!] = row[i]
        }
        return {
            table: obj.table_name as string,
            pk: JSON.parse(obj.pk_value as string),
            op: obj.op as 'upsert' | 'delete',
            data: obj.data ? JSON.parse(obj.data as string) : null,
            timestamp: obj.timestamp as string,
            client_id: clientId,
        }
    })
}

export function clearPendingChanges(): void {
    if (!db) return
    db.run("DELETE FROM _pending_changes")
    schedulePersist()
}

export function runSql(sql: string, params?: unknown[]): void {
    if (!db) return
    db.run(sql, params as never[])
}

// ── Event system ──

let _batchMode = false
const _batchTables = new Set<string>()

export function beginBatch(): void {
    _batchMode = true
    _batchTables.clear()
}

export function endBatch(): void {
    _batchMode = false
    for (const table of _batchTables) {
        notifyListeners(table)
    }
    _batchTables.clear()
}

export function onChange(listener: ChangeListener): () => void {
    listeners.push(listener)
    return () => {
        const idx = listeners.indexOf(listener)
        if (idx !== -1) listeners.splice(idx, 1)
    }
}

/** Notify all listeners for every synced table so stores re-read the DB. */
export function notifyAll(): void {
    if (!schema) return
    for (const table of Object.keys(schema)) {
        notifyListeners(table)
    }
}

function notifyListeners(table: string): void {
    if (_batchMode) {
        _batchTables.add(table)
        return
    }
    for (const fn of listeners) {
        try {fn(table)} catch { /* ignore */}
    }
}

// ── Persistence ──

function schedulePersist(): void {
    if (persistTimer) clearTimeout(persistTimer)
    persistTimer = setTimeout(() => persistToOpfs(), PERSIST_DEBOUNCE_MS)
}

async function persistToOpfs(): Promise<void> {
    if (!db || !opfsHandle) return
    try {
        const data = db.export()
        const writable = await opfsHandle.createWritable()
        await writable.write(data.buffer as ArrayBuffer)
        await writable.close()
        console.log('[local-db] Persisted to OPFS, size:', data.length)
    } catch (e) {
        console.error('[local-db] OPFS write failed:', e)
    }
}

// ── Ensure rows helpers (ported from server) ──

export function ensureHabitRows(): void {
    if (!db) return
    const earliest = db.exec("SELECT MIN(date) as d FROM habits")
    const today = new Date()
    const todayStr = today.toISOString().slice(0, 10)

    let startDate: Date
    if (earliest.length > 0 && earliest[0]!.values[0]![0]) {
        startDate = new Date(earliest[0]!.values[0]![0] as string + 'T00:00:00')
    } else {
        startDate = today
    }

    const endDate = new Date(today)
    endDate.setDate(endDate.getDate() + 100)

    const current = new Date(startDate)
    while (current <= endDate) {
        const dateStr = current.toISOString().slice(0, 10)
        db.run("INSERT OR IGNORE INTO habits (date) VALUES (?)", [dateStr])
        current.setDate(current.getDate() + 1)
    }
}

export function ensureWorkoutRows(): void {
    if (!db) return
    const earliest = db.exec("SELECT MIN(date) as d FROM workouts")
    const today = new Date()

    let startDate: Date
    if (earliest.length > 0 && earliest[0]!.values[0]![0]) {
        startDate = new Date(earliest[0]!.values[0]![0] as string + 'T00:00:00')
    } else {
        startDate = today
    }

    const endDate = new Date(today)
    endDate.setDate(endDate.getDate() + 100)

    const current = new Date(startDate)
    while (current <= endDate) {
        const dateStr = current.toISOString().slice(0, 10)
        db.run("INSERT OR IGNORE INTO workouts (date) VALUES (?)", [dateStr])
        current.setDate(current.getDate() + 1)
    }
}
