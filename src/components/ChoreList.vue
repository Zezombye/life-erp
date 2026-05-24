<template>
  <div class="dashboard-panel chore-dashboard-panel">
    <div class="panel-header">
      <h2 class="panel-title">Chores</h2>
      <button class="panel-btn" @click="choreStore.load()" :disabled="choreStore.loading">↻</button>
    </div>
    <div v-if="choreStore.loading && choreStore.chores.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
      Loading...
    </div>
    <div v-else-if="choreStore.chores.length === 0" class="flex-1 flex items-center justify-center opacity-30 text-sm">
      No chores configured
    </div>
    <div v-else class="chore-dashboard-list">
      <div
        v-for="item in sortedChores"
        :key="item.id"
        class="chore-dashboard-item"
        :class="{ 'chore-dashboard-item--overdue': item.overdue }"
      >
        <div class="chore-dashboard-info">
          <span class="chore-dashboard-title">{{ item.title }}</span>
          <span class="chore-dashboard-due">
            <template v-if="!item.lastDone">Never done</template>
            <template v-else-if="item.overdue">Overdue — was due {{ item.dueDate }}</template>
            <template v-else>Due {{ item.dueDate }}</template>
          </span>
        </div>
        <button class="chore-btn chore-btn--done" @click="markDone(item.id)">Done</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useChoreStore, getChoreNextDue, isChoreOverdue } from '../stores/chores.js'

const choreStore = useChoreStore()

onMounted(() => {
  if (choreStore.chores.length === 0) choreStore.load()
})

const sortedChores = computed(() => {
  return choreStore.chores
    .map(c => ({
      id: c.id,
      title: c.title,
      interval: c.interval_days,
      lastDone: c.last_done,
      dueDate: getChoreNextDue(c),
      overdue: isChoreOverdue(c),
    }))
    .sort((a, b) => {
      // Overdue first, then by due date ascending
      if (a.overdue !== b.overdue) return a.overdue ? -1 : 1
      if (!a.dueDate) return -1
      if (!b.dueDate) return 1
      return a.dueDate.localeCompare(b.dueDate)
    })
})

async function markDone(id) {
  await choreStore.markDone(id)
}
</script>
