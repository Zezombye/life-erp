<template>
  <div class="workout-page">
    <div class="dashboard-panel habit-panel">
      <div class="panel-header">
        <h2 class="panel-title">Workouts</h2>
        <div class="panel-header-actions">
          <button
            class="panel-btn"
            @click="reload"
            :disabled="workoutStore.loading"
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
      <div v-if="workoutStore.error" class="panel-error">
        {{ workoutStore.error }}
      </div>
      <WorkoutTable
        :rows="workoutStore.rows"
        :loading="workoutStore.loading"
        @cell-update="onCellUpdate"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import WorkoutTable from '../components/WorkoutTable.vue'
import { useWorkoutStore, WORKOUT_COLUMNS } from '../stores/workouts.js'

const workoutStore = useWorkoutStore()
const menuOpen = ref(false)

function closeMenu() { menuOpen.value = false }

onMounted(() => {
  workoutStore.load()
  document.addEventListener('click', closeMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
})

function onCellUpdate({ date, column, value }) {
  workoutStore.setValue(date, column, value)
}

function reload() {
  workoutStore.load()
}

function exportData(separator, ext) {
  menuOpen.value = false
  const headers = WORKOUT_COLUMNS.map(c => c.label).join(separator)
  const lines = [headers]
  for (const row of workoutStore.rows) {
    const values = WORKOUT_COLUMNS.map(c => {
      const v = row[c.key]
      return v == null ? '' : String(v)
    })
    lines.push(values.join(separator))
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `workouts.${ext}`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
