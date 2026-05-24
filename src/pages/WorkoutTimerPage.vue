<template>
  <div class="wt-page">
    <!-- Editor mode -->
    <div v-if="!running" class="wt-editor">
      <textarea
        v-model="workoutText"
        class="wt-textarea"
        spellcheck="false"
        placeholder='Title "My Workout"

"Exercise" 10 30s 60 3x
Rest 2mn
"Other" 15 45s 60 countup'
      ></textarea>
      <div class="wt-editor-bar">
        <span class="wt-summary">{{ phaseSummary }}</span>
        <button class="wt-start-btn" @click="startTimer" :disabled="phases.length === 0">▶ START</button>
      </div>
    </div>

    <!-- Timer mode -->
    <div v-else class="wt-timer" :class="'wt-timer--' + phase.type" @click="togglePause">
      <div class="wt-timer-top">
        <button class="wt-stop-btn" @click.stop="stop">✕</button>
        <span class="wt-workout-title">{{ workoutTitle }}</span>
        <span class="wt-phase-counter">{{ phaseIndex + 1 }}/{{ phases.length }}</span>
      </div>

      <div class="wt-timer-center">
        <div class="wt-phase-label">{{ phase.type.toUpperCase() }}</div>
        <div class="wt-exercise-name">
          {{ phase.title }}
          <template v-if="phase.totalSets > 0">
            {{ displaySetCount }}/{{ phase.totalSets }}
          </template>
        </div>
        <div class="wt-time-display" :class="{ 'wt-time-warn': isWarning }">
          {{ displayTime }}
        </div>
        <div v-if="paused" class="wt-paused-label">PAUSED</div>
      </div>

      <div class="wt-timer-bottom">
        <div class="wt-progress">
          <div class="wt-progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
        <div class="wt-next-label" v-if="nextLabel">Next: {{ nextLabel }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const STORAGE_KEY = 'life-erp-workout-timer'

const DEFAULT_TEXT = `Title "Pull day"

"Dead Hang" 10 60s 1m50 3x
Rest 2mn30

"Farmer's hold" 15 60 75 3x countup
"Farmer's hold" 15 30 75 countup`

// ── State ──
const workoutText = ref(localStorage.getItem(STORAGE_KEY) || DEFAULT_TEXT)
watch(workoutText, (v) => localStorage.setItem(STORAGE_KEY, v))

const running = ref(false)
const paused = ref(false)
const phaseIndex = ref(0)
const elapsed = ref(0)
let intervalId = null

// ── Time Parsing ──
function parseTime(str) {
  str = str.trim()
  const m = str.match(/^(\d+)mn?(\d+)?s?$/)
  if (m) return parseInt(m[1]) * 60 + (parseInt(m[2]) || 0)
  return parseInt(str) || 0
}

// ── Workout Parsing ──
const workoutTitle = ref('Workout')

const phases = computed(() => {
  const { title, entries } = parseWorkout(workoutText.value)
  workoutTitle.value = title
  return buildPhases(entries)
})

function parseWorkout(text) {
  let title = 'Workout'
  const entries = []

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue

    if (/^Title\s/i.test(line)) {
      const m = line.match(/Title\s+"([^"]+)"/i)
      if (m) title = m[1]
      continue
    }

    if (/^Rest\s/i.test(line)) {
      entries.push({ type: 'rest', duration: parseTime(line.replace(/^Rest\s+/i, '')) })
      continue
    }

    // Exercise line
    let exTitle, remainder
    const qm = line.match(/^"([^"]+)"\s*(.*)$/)
    if (qm) {
      exTitle = qm[1]
      remainder = qm[2]
    } else {
      const idx = line.indexOf(' ')
      exTitle = idx > 0 ? line.slice(0, idx) : line
      remainder = idx > 0 ? line.slice(idx + 1) : ''
    }

    const tokens = remainder.split(/\s+/).filter(Boolean)
    let countup = false
    let sets = 1
    const timeTokens = []

    for (const tok of tokens) {
      if (tok.toLowerCase() === 'countup') countup = true
      else if (/^\d+x$/i.test(tok)) sets = parseInt(tok)
      else timeTokens.push(tok)
    }

    entries.push({
      type: 'exercise',
      title: exTitle,
      prepare: timeTokens[0] ? parseTime(timeTokens[0]) : 10,
      work: timeTokens[1] ? parseTime(timeTokens[1]) : 30,
      rest: timeTokens[2] ? parseTime(timeTokens[2]) : 30,
      sets,
      countup,
    })
  }

  return { title, entries }
}

function buildPhases(entries) {
  // 1) Merge consecutive same-title exercises into groups
  const merged = []
  for (const entry of entries) {
    if (entry.type === 'rest') {
      merged.push(entry)
      continue
    }
    const last = merged[merged.length - 1]
    if (last && last.type === 'group' && last.title === entry.title) {
      for (let i = 0; i < entry.sets; i++) {
        last.sets.push({ prepare: entry.prepare, work: entry.work, rest: entry.rest, countup: entry.countup })
      }
    } else {
      const sets = []
      for (let i = 0; i < entry.sets; i++) {
        sets.push({ prepare: entry.prepare, work: entry.work, rest: entry.rest, countup: entry.countup })
      }
      merged.push({ type: 'group', title: entry.title, sets })
    }
  }

  // 2) Flatten into individual set items + rest items
  const flat = []
  for (const item of merged) {
    if (item.type === 'rest') {
      flat.push(item)
    } else {
      const total = item.sets.length
      for (let i = 0; i < total; i++) {
        flat.push({ type: 'set', title: item.title, ...item.sets[i], setNum: i + 1, totalSets: total })
      }
    }
  }

  // 3) Build phase sequence, merging rest/prepare times
  const result = []
  for (let i = 0; i < flat.length; i++) {
    const item = flat[i]

    if (item.type === 'rest') {
      // Explicit rest: subtract next exercise's prepare time
      let nextPrepare = 0
      for (let j = i + 1; j < flat.length; j++) {
        if (flat[j].type === 'set') { nextPrepare = flat[j].prepare; break }
      }
      const d = item.duration - nextPrepare
      if (d > 0) result.push({ type: 'rest', duration: d, title: 'Rest', setNum: 0, totalSets: 0, countup: false })
      continue
    }

    // Prepare
    result.push({ type: 'prepare', title: item.title, duration: item.prepare, setNum: item.setNum, totalSets: item.totalSets, countup: false })

    // Work
    result.push({ type: 'work', title: item.title, duration: item.work, setNum: item.setNum, totalSets: item.totalSets, countup: item.countup })

    // Rest after work (skip if last item or explicit rest follows)
    const next = flat[i + 1]
    if (!next) continue
    if (next.type === 'rest') continue
    const restDur = item.rest - next.prepare
    if (restDur > 0) {
      result.push({ type: 'rest', title: item.title, duration: restDur, setNum: item.setNum, totalSets: item.totalSets, countup: false })
    }
  }

  return result
}

// ── Computed Display ──
const phase = computed(() => phases.value[phaseIndex.value] || { type: 'rest', title: 'Done', duration: 0, setNum: 0, totalSets: 0, countup: false })

const displaySetCount = computed(() => {
  const p = phase.value
  if (p.totalSets === 0) return ''
  return p.type === 'rest' ? p.setNum : p.setNum - 1
})

const displayTime = computed(() => {
  const p = phase.value
  const t = p.countup ? elapsed.value : Math.max(0, p.duration - elapsed.value)
  return fmtTime(t)
})

const progressPct = computed(() => {
  const p = phase.value
  if (p.duration <= 0) return 100
  return Math.min(100, (elapsed.value / p.duration) * 100)
})

const isWarning = computed(() => {
  const p = phase.value
  if (p.countup) return false
  const rem = p.duration - elapsed.value
  return rem <= 3 && rem > 0
})

const nextLabel = computed(() => {
  const next = phases.value[phaseIndex.value + 1]
  if (!next) return 'Finish'
  let s = `${next.type.toUpperCase()} — ${next.title}`
  if (next.totalSets > 0) s += ` ${next.type === 'rest' ? next.setNum : next.setNum - 1}/${next.totalSets}`
  return s
})

const phaseSummary = computed(() => {
  const p = phases.value
  if (p.length === 0) return 'No exercises'
  const total = p.reduce((s, ph) => s + ph.duration, 0)
  return `${p.length} phases · ${fmtTime(total)} total`
})

function fmtTime(s) {
  if (s < 0) s = 0
  const m = Math.floor(s / 60)
  const sec = s % 60
  if (m > 0) return `${m}:${String(sec).padStart(2, '0')}`
  return String(sec)
}

// ── Timer Controls ──
function startTimer() {
  if (phases.value.length === 0) return
  running.value = true
  paused.value = false
  phaseIndex.value = 0
  elapsed.value = 0
  playBeep()
  intervalId = setInterval(tick, 1000)
}

function stop() {
  running.value = false
  paused.value = false
  if (intervalId) { clearInterval(intervalId); intervalId = null }
}

function togglePause() {
  paused.value = !paused.value
}

function tick() {
  if (paused.value) return
  elapsed.value++
  if (elapsed.value >= phase.value.duration) {
    advancePhase()
  }
}

function advancePhase() {
  if (phaseIndex.value >= phases.value.length - 1) {
    playBeep()
    stop()
    return
  }
  phaseIndex.value++
  elapsed.value = 0
  playBeep()
}

// ── Audio ──
let audioCtx = null
function playBeep() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.frequency.value = 830
    gain.gain.value = 0.25
    osc.start()
    osc.stop(audioCtx.currentTime + 0.15)
  } catch {}
}

// ── Cleanup ──
onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>
