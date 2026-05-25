<template>
    <div class="timer-bar">
        <!-- Quick increment buttons -->
        <div class="timer-section quick-increments">
            <select v-model="selectedColumn" class="column-select">
                <option v-for="col in TIMER_ACTIVITIES" :key="col.key" :value="col.key">{{ col.label }}</option>
            </select>
            <div class="increment-btns">
                <button v-for="delta in DELTAS" :key="delta" class="incr-btn" :class="delta < 0 ? 'neg' : 'pos'" @click="emit('quickAdd', {column: selectedColumn, delta})">
                    {{ delta > 0 ? '+' : '' }}{{ delta }}
                </button>
            </div>
        </div>

        <!-- Timer start buttons -->
        <div class="timer-section">
            <span class="timer-section-label">Start</span>
            <div class="timer-start-btns">
                <button v-for="act in TIMER_ACTIVITIES" :key="act.key" class="timer-btn start-btn" @click="timerStore.start(act.key)">
                    {{ act.label }}
                </button>
            </div>
        </div>

        <!-- Active timers as blocks -->
        <div v-if="timerStore.timers.length" class="timer-blocks">
            <div v-for="t in timerStore.timers" :key="t.id" class="timer-block" :class="{paused: t.paused_at}">
                <span class="timer-block-activity">{{ timerStore.getActivityLabel(t.activity) }}</span>
                <span class="timer-block-elapsed">{{ formatTimer(t) }}</span>
                <div class="timer-block-actions">
                    <button v-if="!t.paused_at" class="timer-btn pause-btn" @click="timerStore.pause(t.id)" title="Pause">⏸</button>
                    <button v-else class="timer-btn resume-btn" @click="timerStore.resume(t.id)" title="Resume">▶</button>
                    <button class="timer-btn stop-btn" @click="stopTimer(t.id)" title="Stop">⏹</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, onMounted, onUnmounted} from 'vue'
import {useTimerStore, TIMER_ACTIVITIES} from '../stores/timer'
import type {TimerState} from '../stores/timer'

const timerStore = useTimerStore()

const DELTAS = [-10, -5, -2, -1, 1, 2, 5, 10]
const selectedColumn = ref('job')

// Reactive tick to force elapsed time updates
const now = ref(Date.now())
let tickTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {tickTimer = setInterval(() => {now.value = Date.now()}, 1000)})
onUnmounted(() => {if (tickTimer) clearInterval(tickTimer)})

function formatTimer(t: TimerState): string {
    // Touch now.value to create reactivity dependency
    const _now = now.value
    void _now
    return timerStore.formatElapsed(timerStore.getElapsedMs(t))
}

const emit = defineEmits<{
    quickAdd: [payload: {column: string; delta: number}]
    timerStopped: []
}>()

function stopTimer(timerId: string) {
    timerStore.stop(timerId)
    emit('timerStopped')
}
</script>

<style lang="scss">
.timer-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid #27272a;
    flex-shrink: 0;
    flex-wrap: wrap;
}

.timer-section {
    display: flex;
    align-items: center;
    gap: 0.375rem;
}

.timer-section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #71717a;
    font-weight: 500;
    white-space: nowrap;
}

.column-select {
    padding: 0.125rem 0.25rem;
    font-size: 0.7rem;
    background: #27272a;
    color: #d4d4d8;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    font-family: inherit;
    cursor: pointer;
    outline: none;

    &:hover {
        background: #3f3f46;
    }
}

.increment-btns {
    display: flex;
    gap: 2px;
}

.incr-btn {
    padding: 0.125rem 0.375rem;
    font-size: 0.7rem;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    background: #27272a;
    color: #d4d4d8;
    cursor: pointer;
    font-family: inherit;
    font-variant-numeric: tabular-nums;
    line-height: 1.4;

    &:hover {
        background: #3f3f46;
    }

    &.neg {
        color: #fca5a5;

        &:hover {
            background: #3b1414;
        }
    }

    &.pos {
        color: #86efac;

        &:hover {
            background: #14301b;
        }
    }
}

.timer-start-btns {
    display: flex;
    gap: 2px;
}

.timer-btn {
    padding: 0.125rem 0.5rem;
    font-size: 0.7rem;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    cursor: pointer;
    font-family: inherit;
    line-height: 1.4;
}

.start-btn {
    background: #1e3a5f;
    color: #93c5fd;
    border-color: #2563eb44;

    &:hover {
        background: #1e40af;
    }
}

.timer-blocks {
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
}

.timer-block {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.5rem;
    background: #14332a;
    border: 1px solid #166534;
    border-radius: 4px;

    &.paused {
        background: #332814;
        border-color: #854d0e;
    }
}

.timer-block-activity {
    font-size: 0.75rem;
    font-weight: 600;
    color: #86efac;

    .paused & {
        color: #fcd34d;
    }
}

.timer-block-elapsed {
    font-size: 0.8rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: #fafafa;
    min-width: 3rem;

    .paused & {
        color: #fcd34d;
        animation: blink 1s step-end infinite;
    }
}

.timer-block-actions {
    display: flex;
    gap: 2px;
}

@keyframes blink {
    50% {
        opacity: 0.4;
    }
}

.pause-btn {
    background: #854d0e;
    color: #fef08a;
    border-color: #a16207;

    &:hover {
        background: #a16207;
    }
}

.resume-btn {
    background: #166534;
    color: #86efac;
    border-color: #16a34a;

    &:hover {
        background: #15803d;
    }
}

.stop-btn {
    background: #7f1d1d;
    color: #fca5a5;
    border-color: #991b1b;

    &:hover {
        background: #991b1b;
    }
}
</style>
