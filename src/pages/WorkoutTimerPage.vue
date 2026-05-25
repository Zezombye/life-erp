<template>
    <div class="wt-page">
        <!-- Editor mode -->
        <div v-if="!running" class="wt-editor">
            <Textarea v-model="workoutText" class="wt-textarea" :spellcheck="false" placeholder='Title "My Workout"

"Exercise" 10 30s 60 3x
Rest 2mn
"Other" 15 45s 60 countup' autoResize />
            <div class="wt-editor-bar">
                <span class="wt-summary">{{ phaseSummary }}</span>
                <Button label="START" icon="pi pi-play" severity="success" size="large" @click="startTimer" :disabled="phases.length === 0" />
            </div>
        </div>

        <!-- Timer mode -->
        <div v-else class="wt-timer" :class="'wt-timer--' + phase.type" @click="togglePause">
            <div class="wt-timer-top">
                <Button icon="pi pi-times" severity="secondary" rounded text @click.stop="stop" class="wt-stop-btn" />
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
                <div class="wt-time-display" :class="{'wt-time-warn': isWarning}">
                    {{ displayTime }}
                </div>
                <div v-if="paused" class="wt-paused-label">PAUSED</div>
            </div>

            <div class="wt-timer-bottom">
                <ProgressBar :value="progressPct" :showValue="false" class="wt-progress-bar" />
                <div class="wt-next-label" v-if="nextLabel">Next: {{ nextLabel }}</div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, computed, watch, onUnmounted} from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import ProgressBar from 'primevue/progressbar'

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
let intervalId: ReturnType<typeof setInterval> | null = null

interface TimerPhase {
    type: string
    title: string
    duration: number
    setNum: number
    totalSets: number
    countup: boolean
}

interface ExerciseEntry {
    type: 'exercise'
    title: string
    prepare: number
    work: number
    rest: number
    sets: number
    countup: boolean
}

interface RestEntry {
    type: 'rest'
    duration: number
}

type WorkoutEntry = ExerciseEntry | RestEntry

interface ExerciseGroup {
    type: 'group'
    title: string
    sets: {prepare: number; work: number; rest: number; countup: boolean}[]
}

interface FlatSet {
    type: 'set'
    title: string
    prepare: number
    work: number
    rest: number
    countup: boolean
    setNum: number
    totalSets: number
}

type FlatItem = RestEntry | FlatSet

// ── Time Parsing ──
function parseTime(str: string): number {
    str = str.trim()
    const m = str.match(/^(\d+)mn?(\d+)?s?$/)
    if (m) return parseInt(m[1]!) * 60 + (parseInt(m[2] ?? '0') || 0)
    return parseInt(str) || 0
}

// ── Workout Parsing ──
const parsedWorkout = computed(() => {
    return parseWorkout(workoutText.value)
})

const workoutTitle = computed(() => parsedWorkout.value.title)

const phases = computed((): TimerPhase[] => {
    return buildPhases(parsedWorkout.value.entries)
})

function parseWorkout(text: string): {title: string; entries: WorkoutEntry[]} {
    let title = 'Workout'
    const entries: WorkoutEntry[] = []

    for (const rawLine of text.split('\n')) {
        const line = rawLine.trim()
        if (!line) continue

        if (/^Title\s/i.test(line)) {
            const m = line.match(/Title\s+"([^"]+)"/i)
            if (m) title = m[1]!
            continue
        }

        if (/^Rest\s/i.test(line)) {
            entries.push({type: 'rest', duration: parseTime(line.replace(/^Rest\s+/i, ''))})
            continue
        }

        // Exercise line
        let exTitle: string, remainder: string
        const qm = line.match(/^"([^"]+)"\s*(.*)$/)
        if (qm) {
            exTitle = qm[1]!
            remainder = qm[2]!
        } else {
            const idx = line.indexOf(' ')
            exTitle = idx > 0 ? line.slice(0, idx) : line
            remainder = idx > 0 ? line.slice(idx + 1) : ''
        }

        const tokens = remainder.split(/\s+/).filter(Boolean)
        let countup = false
        let sets = 1
        const timeTokens: string[] = []

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

    return {title, entries}
}

function buildPhases(entries: WorkoutEntry[]): TimerPhase[] {
    // 1) Merge consecutive same-title exercises into groups
    const merged: (RestEntry | ExerciseGroup)[] = []
    for (const entry of entries) {
        if (entry.type === 'rest') {
            merged.push(entry)
            continue
        }
        const last = merged[merged.length - 1]
        if (last && last.type === 'group' && last.title === entry.title) {
            for (let i = 0; i < entry.sets; i++) {
                last.sets.push({prepare: entry.prepare, work: entry.work, rest: entry.rest, countup: entry.countup})
            }
        } else {
            const sets: {prepare: number; work: number; rest: number; countup: boolean}[] = []
            for (let i = 0; i < entry.sets; i++) {
                sets.push({prepare: entry.prepare, work: entry.work, rest: entry.rest, countup: entry.countup})
            }
            merged.push({type: 'group', title: entry.title, sets})
        }
    }

    // 2) Flatten into individual set items + rest items
    const flat: FlatItem[] = []
    for (const item of merged) {
        if (item.type === 'rest') {
            flat.push(item)
        } else {
            const total = item.sets.length
            for (let i = 0; i < total; i++) {
                const s = item.sets[i]!
                flat.push({type: 'set', title: item.title, prepare: s.prepare, work: s.work, rest: s.rest, countup: s.countup, setNum: i + 1, totalSets: total})
            }
        }
    }

    // 3) Build phase sequence, merging rest/prepare times
    const result: TimerPhase[] = []
    for (let i = 0; i < flat.length; i++) {
        const item = flat[i]!

        if (item.type === 'rest') {
            // Explicit rest: subtract next exercise's prepare time
            let nextPrepare = 0
            for (let j = i + 1; j < flat.length; j++) {
                const fj = flat[j]!
                if (fj.type === 'set') {nextPrepare = fj.prepare; break}
            }
            const d = item.duration - nextPrepare
            if (d > 0) result.push({type: 'rest', duration: d, title: 'Rest', setNum: 0, totalSets: 0, countup: false})
            continue
        }

        // Prepare
        result.push({type: 'prepare', title: item.title, duration: item.prepare, setNum: item.setNum, totalSets: item.totalSets, countup: false})

        // Work
        result.push({type: 'work', title: item.title, duration: item.work, setNum: item.setNum, totalSets: item.totalSets, countup: item.countup})

        // Rest after work (skip if last item or explicit rest follows)
        const next = flat[i + 1]
        if (!next) continue
        if (next.type === 'rest') continue
        const restDur = item.rest - next.prepare
        if (restDur > 0) {
            result.push({type: 'rest', title: item.title, duration: restDur, setNum: item.setNum, totalSets: item.totalSets, countup: false})
        }
    }

    return result
}

// ── Computed Display ──
const phase = computed((): TimerPhase => phases.value[phaseIndex.value] || {type: 'rest', title: 'Done', duration: 0, setNum: 0, totalSets: 0, countup: false})

const displaySetCount = computed((): string | number => {
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

const phaseSummary = computed((): string => {
    const p = phases.value
    if (p.length === 0) return 'No exercises'
    const total = p.reduce((s: number, ph: TimerPhase) => s + ph.duration, 0)
    return `${p.length} phases · ${fmtTime(total)} total`
})

function fmtTime(s: number): string {
    if (s < 0) s = 0
    const m = Math.floor(s / 60)
    const sec = s % 60
    if (m > 0) return `${m}:${String(sec).padStart(2, '0')}`
    return String(sec)
}

// ── Timer Controls ──
function startTimer(): void {
    if (phases.value.length === 0) return
    running.value = true
    paused.value = false
    phaseIndex.value = 0
    elapsed.value = 0
    playBeep()
    intervalId = setInterval(tick, 1000)
}

function stop(): void {
    running.value = false
    paused.value = false
    if (intervalId) {clearInterval(intervalId); intervalId = null}
}

function togglePause(): void {
    paused.value = !paused.value
}

function tick(): void {
    if (paused.value) return
    elapsed.value++
    if (elapsed.value >= phase.value.duration) {
        advancePhase()
    }
}

function advancePhase(): void {
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
let audioCtx: AudioContext | null = null
function playBeep(): void {
    try {
        if (!audioCtx) audioCtx = new AudioContext()
        const osc = audioCtx.createOscillator()
        const gain = audioCtx.createGain()
        osc.connect(gain)
        gain.connect(audioCtx.destination)
        osc.frequency.value = 830
        gain.gain.value = 0.25
        osc.start()
        osc.stop(audioCtx.currentTime + 0.15)
    } catch { }
}

// ── Cleanup ──
onUnmounted(() => {
    if (intervalId) clearInterval(intervalId)
})
</script>

<style lang="scss">
.wt-page {
    height: calc(100vh - 2.75rem);
    display: flex;
    flex-direction: column;
}

.wt-editor {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 0.75rem;
    gap: 0.5rem;
}

.wt-textarea {
    flex: 1;
    background: #18181b;
    color: #e4e4e7;
    border: 1px solid #27272a;
    border-radius: 0.5rem;
    padding: 0.75rem;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
    resize: none;
    outline: none;

    &:focus {
        border-color: #3b82f6;
    }

    &::placeholder {
        color: #52525b;
    }
}

.wt-editor-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.wt-summary {
    font-size: 0.8125rem;
    color: #71717a;
}

.wt-timer {
    flex: 1;
    display: flex;
    flex-direction: column;
    cursor: pointer;
    user-select: none;
    transition: background 0.3s;
}

.wt-timer--prepare {
    background: #b45309;
}

.wt-timer--work {
    background: #15803d;
}

.wt-timer--rest {
    background: #1d4ed8;
}

.wt-timer-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    opacity: 0.8;
}

.wt-workout-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
}

.wt-phase-counter {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.6);
}

.wt-timer-center {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}

.wt-phase-label {
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.7);
}

.wt-exercise-name {
    font-size: 1.75rem;
    font-weight: 700;
    color: white;
    text-align: center;
    padding: 0 1rem;
}

.wt-time-display {
    font-size: 8rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    color: white;
    line-height: 1;
    transition: color 0.2s;

    @media (max-width: 480px) {
        font-size: 5rem;
    }
}

.wt-time-warn {
    color: #fde047;
    animation: wt-pulse 0.5s ease-in-out infinite alternate;
}

@keyframes wt-pulse {
    from {
        transform: scale(1);
    }

    to {
        transform: scale(1.05);
    }
}

.wt-paused-label {
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: rgba(255, 255, 255, 0.5);
    margin-top: 0.5rem;
}

.wt-timer-bottom {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.wt-progress-bar {
    height: 6px;

    .p-progressbar-value {
        background: rgba(255, 255, 255, 0.5) !important;
        transition: width 1s linear;
    }
}

.wt-next-label {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
    text-align: center;
}
</style>
