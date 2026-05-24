<template>
  <div class="dashboard-panel habit-panel">
    <div class="panel-header">
      <h2 class="panel-title">Habits</h2>
      <div class="panel-header-actions">
        <button
          class="panel-btn"
          @click="reload"
          :disabled="habitStore.loading"
        >↻</button>
        <div class="dropdown-wrapper">
          <button class="panel-btn" @click.stop="menuOpen = !menuOpen">⋮</button>
          <div v-show="menuOpen" class="dropdown-menu">
            <button class="dropdown-item" @click="exportData(',', 'csv')">Export CSV</button>
            <button class="dropdown-item" @click="exportData('\t', 'tsv')">Export TSV</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="habitStore.error" class="panel-error">
      {{ habitStore.error }}
    </div>
    <HabitTable
      :rows="habitStore.rows"
      :loading="habitStore.loading"
      @cell-update="onCellUpdate"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import HabitTable from '../components/HabitTable.vue'
import { useHabitStore, HABIT_COLUMNS } from '../stores/habits.js'

const habitStore = useHabitStore()
const menuOpen = ref(false)

function closeMenu() { menuOpen.value = false }

onMounted(() => {
  habitStore.load()
  document.addEventListener('click', closeMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
})

function onCellUpdate({ date, column, value }) {
  habitStore.setValue(date, column, value)
}

function reload() {
  habitStore.load()
}

function exportData(separator, ext) {
  menuOpen.value = false
  const headers = HABIT_COLUMNS.map(c => c.label).join(separator)
  const lines = [headers]
  for (const row of habitStore.rows) {
    const values = HABIT_COLUMNS.map(c => {
      const v = row[c.key]
      return v == null ? '' : String(v)
    })
    lines.push(values.join(separator))
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `habits.${ext}`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
