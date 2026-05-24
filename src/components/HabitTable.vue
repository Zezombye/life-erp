<template>
  <div class="habit-table-outer">
    <div ref="wrapperEl" class="habit-table-wrapper">
      <table class="habit-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              class="habit-th"
              :style="{ width: col.width + 'px', minWidth: col.width + 'px' }"
            >{{ col.label }}</th>
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

<script setup>
import { ref, watch, onMounted } from 'vue'
import { HABIT_COLUMNS, getCellColor, getDateColor } from '../stores/habits.js'

const props = defineProps({
  rows: { type: Array, required: true },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['cellUpdate'])

const columns = HABIT_COLUMNS
const nonDateColumns = HABIT_COLUMNS.filter(c => c.key !== 'date')
const ROW_HEIGHT = 36
const POOL_SIZE = 50

const wrapperEl = ref(null)
const tbodyEl = ref(null)
const trackEl = ref(null)
const thumbEl = ref(null)

let scrollIdx = 0
let visibleCount = 20
let shouldScrollToToday = true

// Pool DOM references
const poolTrs = []
const poolDateTds = []
const poolValueTds = [] // [rowIdx][colIdx] = td

// ── Format helpers ──
const dateFormatCache = new Map()
function formatDateCached(dateStr) {
  let v = dateFormatCache.get(dateStr)
  if (v !== undefined) return v
  const d = new Date(dateStr + 'T00:00:00')
  v = d.toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
  dateFormatCache.set(dateStr, v)
  return v
}

function formatValue(value, format) {
  if (value === null || value === undefined || value === '') return ''
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
    default: return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
  }
}

// ── Editing ──
let editTd = null
let editInput = null

function startEdit(td) {
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

function onEditKey(e) {
  if (e.key === 'Enter') commitEdit()
  else if (e.key === 'Escape') cancelEdit()
  else if (e.key === 'Tab') { e.preventDefault(); commitEdit() }
}

function commitEdit() {
  if (!editTd) return
  const td = editTd
  const input = editInput
  editTd = null
  editInput = null

  input.removeEventListener('blur', commitEdit)
  input.removeEventListener('keydown', onEditKey)

  const raw = input.value.trim()
  const newVal = raw === '' ? null : Number(raw)
  const oldVal = td._rawValue
  const changed = newVal !== oldVal

  if (changed) td._rawValue = newVal
  restoreCell(td)
  if (changed) {
    emit('cellUpdate', { date: td._date, column: td._colKey, value: newVal })
  }
}

function cancelEdit() {
  if (!editTd) return
  const td = editTd
  editTd = null
  editInput.removeEventListener('blur', commitEdit)
  editInput.removeEventListener('keydown', onEditKey)
  editInput = null
  restoreCell(td)
}

function restoreCell(td) {
  td.classList.remove('editing')
  td.textContent = ''
  const span = document.createElement('span')
  span.className = 'cell-display'
  span.textContent = formatValue(td._rawValue, td._colFormat)
  td.appendChild(span)
}

// ── Pool management ──
function createPool() {
  const tbody = tbodyEl.value
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
    const w0 = columns[0].width + 'px'
    dateTd.style.cssText = `width:${w0};min-width:${w0}`
    tr.appendChild(dateTd)

    const tds = []
    for (let j = 0; j < nonDateColumns.length; j++) {
      const col = nonDateColumns[j]
      const td = document.createElement('td')
      td.className = col.editable ? 'habit-cell editable' : 'habit-cell'
      const w = col.width + 'px'
      td.style.cssText = `width:${w};min-width:${w}`

      const span = document.createElement('span')
      span.className = 'cell-display'
      td.appendChild(span)

      td._colKey = col.key
      td._colFormat = col.displayFormat
      td._editable = col.editable

      tds.push(td)
      tr.appendChild(td)
    }

    poolTrs.push(tr)
    poolDateTds.push(dateTd)
    poolValueTds.push(tds)
    tbody.appendChild(tr)
  }
}

function updateVisibleRows() {
  const rows = props.rows
  const total = rows.length

  for (let i = 0; i < POOL_SIZE; i++) {
    const dataIdx = scrollIdx + i
    const tr = poolTrs[i]

    if (dataIdx >= total) {
      tr.style.display = 'none'
      continue
    }

    tr.style.display = ''
    const row = rows[dataIdx]

    // Date cell
    const dateTd = poolDateTds[i]
    const dc = getDateColor(row.date)
    dateTd.style.backgroundColor = dc ? dc.bg : ''
    dateTd.style.color = dc ? dc.text : ''
    dateTd.textContent = formatDateCached(row.date)

    // Value cells
    const tds = poolValueTds[i]
    for (let j = 0; j < nonDateColumns.length; j++) {
      const col = nonDateColumns[j]
      const td = tds[j]

      if (td === editTd) continue

      const cc = getCellColor(row, col)
      td.style.backgroundColor = cc ? cc.bg : ''
      td.style.color = cc ? cc.text : ''

      td._rawValue = row[col.key]
      td._date = row.date

      const child = td.firstElementChild
      if (child && child.tagName === 'SPAN') {
        child.textContent = formatValue(row[col.key], col.displayFormat)
      }
    }
  }

  updateScrollbar()
}

// ── Scrollbar ──
function updateScrollbar() {
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

function onTrackClick(e) {
  const rect = trackEl.value.getBoundingClientRect()
  const clickY = e.clientY - rect.top
  const trackH = rect.height
  const total = props.rows.length
  const maxIdx = Math.max(0, total - visibleCount)
  const thumbH = thumbEl.value.clientHeight
  const scrollable = trackH - thumbH
  const targetTop = clickY - thumbH / 2
  const ratio = Math.max(0, Math.min(targetTop / scrollable, 1))

  scrollIdx = Math.round(ratio * maxIdx / 3) * 3
  scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
  if (editTd) cancelEdit()
  updateVisibleRows()
}

function onThumbDown(e) {
  e.preventDefault()
  const startY = e.clientY
  const startIdx = scrollIdx
  const trackH = trackEl.value.clientHeight
  const thumbH = thumbEl.value.clientHeight
  const total = props.rows.length
  const maxIdx = Math.max(0, total - visibleCount)
  const scrollable = trackH - thumbH

  function onMove(ev) {
    const dy = ev.clientY - startY
    const idxDelta = scrollable > 0 ? (dy / scrollable) * maxIdx : 0
    scrollIdx = Math.round((startIdx + idxDelta) / 3) * 3
    scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
    if (editTd) cancelEdit()
    updateVisibleRows()
  }

  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// ── Scroll to today ──
function scrollToToday() {
  const rows = props.rows
  if (rows.length === 0) return

  const d = new Date()
  d.setDate(d.getDate() - 10)
  const anchorDate = d.toISOString().slice(0, 10)

  let anchorIdx = rows.findIndex(r => r.date >= anchorDate)
  if (anchorIdx < 0) anchorIdx = Math.max(0, rows.length - visibleCount)

  const maxIdx = Math.max(0, rows.length - visibleCount)
  scrollIdx = Math.round(anchorIdx / 3) * 3
  scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
  updateVisibleRows()
}

// ── Lifecycle ──
onMounted(() => {
  const tbody = tbodyEl.value
  const wrapper = wrapperEl.value

  createPool()

  // Event delegation for cell clicks
  tbody.addEventListener('click', (e) => {
    const td = e.target.closest('td')
    if (!td || !td._editable) return
    startEdit(td)
  })

  // Wheel: jump 3 rows at a time
  wrapper.addEventListener('wheel', (e) => {
    e.preventDefault()
    if (editTd) cancelEdit()
    const dir = e.deltaY > 0 ? 1 : -1
    const maxIdx = Math.max(0, props.rows.length - visibleCount)
    scrollIdx += dir * 3
    scrollIdx = Math.max(0, Math.min(scrollIdx, maxIdx))
    updateVisibleRows()
  }, { passive: false })

  // Calculate visible count after layout
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
}, { deep: true })
</script>
