<template>
  <td
    class="habit-cell"
    :class="{ 'editing': isEditing, 'editable': editable }"
    :style="cellStyle"
    @click="startEdit"
  >
    <input
      v-if="isEditing"
      ref="inputEl"
      v-model="editValue"
      type="text"
      class="cell-input"
      @blur="commit"
      @keydown.enter="commit"
      @keydown.escape="cancel"
      @keydown.tab="commitAndTab"
    />
    <span v-else class="cell-display">{{ displayValue }}</span>
  </td>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  modelValue: { default: null },
  editable: { type: Boolean, default: true },
  displayFormat: { type: String, default: null },
  width: { type: Number, default: 69 },
  bgColor: { type: String, default: null },
  textColor: { type: String, default: null },
})

const emit = defineEmits(['update:modelValue', 'tab'])

const isEditing = ref(false)
const editValue = ref('')
const inputEl = ref(null)

const cellStyle = computed(() => ({
  width: props.width + 'px',
  minWidth: props.width + 'px',
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

function startEdit() {
  if (!props.editable) return
  isEditing.value = true
  editValue.value = props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue)
  nextTick(() => {
    inputEl.value?.select()
  })
}

function commit() {
  if (!isEditing.value) return
  isEditing.value = false
  const raw = editValue.value.trim()
  const value = raw === '' ? null : Number(raw)
  if (value !== props.modelValue) {
    emit('update:modelValue', value)
  }
}

function cancel() {
  isEditing.value = false
}

function commitAndTab(e) {
  e.preventDefault()
  commit()
  emit('tab', e.shiftKey ? -1 : 1)
}
</script>
