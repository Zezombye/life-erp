<template>
    <div class="habit-table-outer">
        <div ref="wrapperEl" class="habit-table-wrapper">
            <table class="habit-table">
                <thead>
                    <tr>
                        <th v-for="col in columns" :key="col.key" class="habit-th" :style="{width: col.width + 'px', minWidth: col.width + 'px'}">{{ col.label }}</th>
                    </tr>
                </thead>
                <tbody ref="tbodyEl"></tbody>
            </table>
        </div>
        <div ref="trackEl" class="vscroll-track" @mousedown="onTrackClick">
            <div ref="thumbEl" class="vscroll-thumb" @mousedown.stop="onThumbDown"></div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, watch, onMounted} from 'vue'
import {getDateColor} from '../stores/habits'

interface Column {
    key: string
    label: string
    editable: boolean
    width: number
    displayFormat?: string
    colType?: string
    [k: string]: any
}

interface CellTd extends HTMLTableCellElement {
    _rawValue: string | number | null
    _date: string
    _colKey: string
    _colFormat: string | undefined
    _colType: string | undefined
    _editable: boolean
}

type Row = Record<string, any>

const props = defineProps<{
    rows: Row[]
    columns: Column[]
    getCellColor?: (row: Row, col: Column) => {bg: string; text: string} | null
    loading?: boolean
}>()

const emit = defineEmits<{
    cellUpdate: [payload: {date: string; column: string; value: string | number | null}]
}>()

const columns = props.columns
const nonDateColumns = props.columns.filter(c => c.key !== 'date')
const ROW_HEIGHT = 36
const POOL_SIZE = 50

const wrapperEl = ref<HTMLDivElement | null>(null)
const tbodyEl = ref<HTMLTableSectionElement | null>(null)
const trackEl = ref<HTMLDivElement | null>(null)
const thumbEl = ref<HTMLDivElement | null>(null)

let scrollIdx = 0
let visibleCount = 20
let shouldScrollToToday = true

const poolTrs: HTMLTableRowElement[] = []
const poolDateTds: HTMLTableCellElement[] = []
const poolValueTds: CellTd[][] = []

// ── Format helpers ──
const dateFormatCache = new Map<string, string>()
function formatDateCached(dateStr: string): string {
    let v = dateFormatCache.get(dateStr)
    if (v !== undefined) return v
    const d = new Date(dateStr + 'T00:00:00')
    v = d.toLocaleDateString('fr-FR', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })
    dateFormatCache.set(dateStr, v)
    return v
}

function formatValue(value: string | number | null | undefined, format: string | undefined, colType: string | undefined): string {
    if (value === null || value === undefined || value === '') return ''
    if (colType === 'text') return String(value)
    const n = Number(value)
    if (isNaN(n)) return String(value)
    switch (format) {
        case 'percentage': return `${n.toFixed(2)}%`
        case 'minutes': return `${Math.round(n)} mn`
        case 'hours': {
            const h = Math.floor(n / 60)
            const m = Math.round(n % 60)
            return `${h}h${String(m).padStart(2, '0')}mn`
        }
        case 'kg': return `${n.toFixed(1)} kg`
        default: return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
    }
}

// ── Editing ──
let editTd: CellTd | null = null
let editInput: HTMLInputElement | null = null

function startEdit(td: CellTd): void {
    if (editTd) commitEdit()
    const raw = td._rawValue
    const input = document.createElement('input')
    input.type = 'text'
    input.className = 'cell-input'
    input.value = raw === null || raw === undefined ? '' : String(raw)

    td.textContent = ''
    td.appendChild(input)
    td.classList.add('editing')
    input.focus()
    input.select()

    editTd = td
    editInput = input

    input.addEventListener('blur', commitEdit)
    input.addEventListener('keydown', onEditKey)
}

function onEditKey(e: KeyboardEvent): void {
    if (e.key === 'Enter') commitEdit()
    else if (e.key === 'Escape') cancelEdit()
    else if (e.key === 'Tab') {e.preventDefault(); commitEdit()}
}

function commitEdit(): void {
    if (!editTd) return
    const td = editTd
    const input = editInput!
    editTd = null
    editInput = null

    input.removeEventListener('blur', commitEdit)
    input.removeEventListener('keydown', onEditKey)

    const raw = input.value.trim()
    let newVal: string | number | null
    if (td._colType === 'text') {
        newVal = raw === '' ? null : raw
    } else {
        newVal = raw === '' ? null : Number(raw)
    }
    const oldVal = td._rawValue
    const changed = newVal !== oldVal

    if (changed) td._rawValue = newVal
    restoreCell(td)
    if (changed) {
        emit('cellUpdate', {date: td._date, column: td._colKey, value: newVal})
    }
}

function cancelEdit(): void {
    if (!editTd) return
    const td = editTd
    editTd = null
    editInput!.removeEventListener('blur', commitEdit)
    editInput!.removeEventListener('keydown', onEditKey)
    editInput = null
    restoreCell(td)
}

function restoreCell(td: CellTd): void {
    td.classList.remove('editing')
    td.textContent = ''
    const span = document.createElement('span')
    span.className = 'cell-display'
    span.textContent = formatValue(td._rawValue, td._colFormat, td._colType)
    td.appendChild(span)
}

// ── Pool management ──
function createPool(): void {
    const tbody = tbodyEl.value!
    tbody.textContent = ''
    poolTrs.length = 0
    poolDateTds.length = 0
    poolValueTds.length = 0

    for (let i = 0; i < POOL_SIZE; i++) {
        const tr = document.createElement('tr')
        tr.className = 'habit-row'
        tr.style.display = 'none'

        const dateTd = document.createElement('td')
        dateTd.className = 'habit-cell date-cell'
        const w0 = columns[0]!.width + 'px'
        dateTd.style.cssText = `width:${w0};min-width:${w0}`
        tr.appendChild(dateTd)

        const tds = []
        for (let j = 0; j < nonDateColumns.length; j++) {
            const col = nonDateColumns[j]!
            const td = document.createElement('td')
            td.className = col.editable ? 'habit-cell editable' : 'habit-cell'
            const w = col.width + 'px'
            td.style.cssText = `width:${w};min-width:${w}`

            const span = document.createElement('span')
            span.className = 'cell-display'
            td.appendChild(span)

                ; (td as CellTd)._colKey = col.key
                ; (td as CellTd)._colFormat = col.displayFormat
                ; (td as CellTd)._colType = col.colType
                ; (td as CellTd)._editable = col.editable

            tds.push(td as CellTd)
            tr.appendChild(td)
        }

        poolTrs.push(tr)
        poolDateTds.push(dateTd)
        poolValueTds.push(tds)
        tbody.appendChild(tr)
    }
}

function updateVisibleRows(): void {
    const rows = props.rows
    const total = rows.length
    const colorFn = props.getCellColor

    for (let i = 0; i < POOL_SIZE; i++) {
        const dataIdx = scrollIdx + i
        const tr = poolTrs[i]!

        if (dataIdx >= total) {
            tr.style.display = 'none'
            continue
        }

        tr.style.display = ''
        const row = rows[dataIdx]!

        // Date cell
        const dateTd = poolDateTds[i]!
        const dc = getDateColor(row.date)
        dateTd.style.backgroundColor = dc ? dc.bg : ''
        dateTd.style.color = dc ? dc.text : ''
        dateTd.textContent = formatDateCached(row.date)

        // Value cells
        const tds = poolValueTds[i]!
        for (let j = 0; j < nonDateColumns.length; j++) {
            const col = nonDateColumns[j]!
            const td = tds[j]!

            if (td === editTd) continue

            const cc = colorFn ? colorFn(row, col) : null
            td.style.backgroundColor = cc ? cc.bg : ''
            td.style.color = cc ? cc.text : ''

            td._rawValue = row[col.key] ?? null
            td._date = row.date

            const child = td.firstElementChild
            if (child && child.tagName === 'SPAN') {
                child.textContent = formatValue(row[col.key], col.displayFormat, col.colType)
            }
        }
    }

    updateScrollbar()
}

// ── Scrollbar ──
function updateScrollbar(): void {
    const track = trackEl.value
    const thumb = thumbEl.value
    if (!track || !thumb) return

    const total = props.rows.length
    if (total <= visibleCount) {
        track.style.display = 'none'
        return
    }
    track.style.display = ''

    const trackH = track.clientHeight
    const ratio = visibleCount / total
    const thumbH = Math.max(ratio * trackH, 20)
    const maxIdx = total - visibleCount
    const scrollRatio = maxIdx > 0 ? scrollIdx / maxIdx : 0
    const thumbTop = scrollRatio * (trackH - thumbH)

    thumb.style.height = thumbH + 'px'
    thumb.style.top = thumbTop + 'px'
}

function onTrackClick(e: MouseEvent): void {
    const rect = trackEl.value!.getBoundingClientRect()
    const clickY = e.clientY - rect.top
    const trackH = rect.height
    const total = props.rows.length
    const maxIdx = Math.max(0, total - visibleCount)
    const thumbH = thumbEl.value!.clientHeight
    const scrollable = trackH - thumbH
    const targetTop = clickY - thumbH / 2
    const ratio = Math.max(0, Math.min(targetTop / scrollable, 1))

    scrollIdx = Math.round(ratio * maxIdx / 3) * 3
    scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
    if (editTd) cancelEdit()
    updateVisibleRows()
}

function onThumbDown(e: MouseEvent): void {
    e.preventDefault()
    const startY = e.clientY
    const startIdx = scrollIdx
    const trackH = trackEl.value!.clientHeight
    const thumbH = thumbEl.value!.clientHeight
    const total = props.rows.length
    const maxIdx = Math.max(0, total - visibleCount)
    const scrollable = trackH - thumbH

    function onMove(ev: MouseEvent): void {
        const dy = ev.clientY - startY
        const idxDelta = scrollable > 0 ? (dy / scrollable) * maxIdx : 0
        scrollIdx = Math.round((startIdx + idxDelta) / 3) * 3
        scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
        if (editTd) cancelEdit()
        updateVisibleRows()
    }

    function onUp(): void {
        document.removeEventListener('mousemove', onMove)
        document.removeEventListener('mouseup', onUp)
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
}

// ── Scroll to today ──
function scrollToToday(): void {
    const rows = props.rows
    if (rows.length === 0) return

    const d = new Date()
    d.setDate(d.getDate() - 10)
    const anchorDate = d.toISOString().slice(0, 10)

    let anchorIdx = rows.findIndex((r: Row) => r.date >= anchorDate)
    if (anchorIdx < 0) anchorIdx = Math.max(0, rows.length - visibleCount)

    const maxIdx = Math.max(0, rows.length - visibleCount)
    scrollIdx = Math.round(anchorIdx / 3) * 3
    scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
    updateVisibleRows()
}

// ── Lifecycle ──
onMounted(() => {
    const tbody = tbodyEl.value!
    const wrapper = wrapperEl.value!

    createPool()

    tbody.addEventListener('click', (e: MouseEvent) => {
        const td = (e.target as HTMLElement).closest('td') as CellTd | null
        if (!td || !td._editable) return
        startEdit(td)
    })

    wrapper.addEventListener('wheel', (e: WheelEvent) => {
        e.preventDefault()
        if (editTd) cancelEdit()
        const dir = e.deltaY > 0 ? 1 : -1
        const maxIdx = Math.max(0, props.rows.length - visibleCount)
        scrollIdx += dir * 3
        scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
        updateVisibleRows()
    }, {passive: false})

    requestAnimationFrame(() => {
        const theadEl = wrapper.querySelector('thead')
        const theadH = theadEl ? theadEl.offsetHeight : 0
        const availH = wrapper.clientHeight - theadH
        visibleCount = Math.max(1, Math.floor(availH / ROW_HEIGHT))

        if (props.rows.length > 0 && shouldScrollToToday) {
            shouldScrollToToday = false
            scrollToToday()
        }
    })
})

watch(() => props.rows, () => {
    if (props.rows.length === 0) return

    const maxIdx = Math.max(0, props.rows.length - visibleCount)
    scrollIdx = Math.min(scrollIdx, maxIdx)

    if (shouldScrollToToday) {
        shouldScrollToToday = false
        scrollToToday()
    } else {
        updateVisibleRows()
    }
}, {deep: true})
</script>
