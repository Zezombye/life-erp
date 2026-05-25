<template>
    <td class="habit-cell" :class="{'editing': isEditing, 'editable': editable}" :style="cellStyle" @click="startEdit">
        <input v-if="isEditing" ref="inputEl" v-model="editValue" type="text" class="cell-input" @blur="commit" @keydown.enter="commit" @keydown.escape="cancel" @keydown.tab="commitAndTab" />
        <span v-else class="cell-display">{{ displayValue }}</span>
    </td>
</template>

<script setup lang="ts">
import {ref, computed, nextTick} from 'vue'

const props = defineProps<{
    modelValue?: string | number | null
    editable?: boolean
    displayFormat?: string | null
    width?: number
    bgColor?: string | null
    textColor?: string | null
}>()

const emit = defineEmits<{
    'update:modelValue': [value: number | null]
    tab: [direction: number]
}>()

const isEditing = ref(false)
const editValue = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

const cellStyle = computed(() => ({
    width: (props.width ?? 69) + 'px',
    minWidth: (props.width ?? 69) + 'px',
    backgroundColor: props.bgColor || undefined,
    color: props.textColor || undefined,
}))

const displayValue = computed(() => {
    const v = props.modelValue
    if (v === null || v === undefined || v === '') return ''

    const n = Number(v)
    if (isNaN(n)) return String(v)

    if (props.displayFormat === 'percentage') {
        return `${n.toFixed(2)}%`
    }
    if (props.displayFormat === 'minutes') {
        return `${n % 1 === 0 ? String(n) : n.toFixed(0)} mn`
    }
    if (props.displayFormat === 'hours') {
        const h = Math.floor(n / 60)
        const m = Math.round(n % 60)
        return `${h}h${String(m).padStart(2, '0')}mn`
    }
    // Default: raw number
    return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
})

function startEdit(): void {
    if (!(props.editable ?? true)) return
    isEditing.value = true
    editValue.value = props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue)
    nextTick(() => {
        inputEl.value?.select()
    })
}

function commit(): void {
    if (!isEditing.value) return
    isEditing.value = false
    const raw = editValue.value.trim()
    const value = raw === '' ? null : Number(raw)
    if (value !== props.modelValue) {
        emit('update:modelValue', value)
    }
}

function cancel(): void {
    isEditing.value = false
}

function commitAndTab(e: KeyboardEvent): void {
    e.preventDefault()
    commit()
    emit('tab', e.shiftKey ? -1 : 1)
}
</script>
