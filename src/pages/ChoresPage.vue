<template>
  <div class="chores-page">
    <div class="dashboard-panel">
      <div class="panel-header">
        <h2 class="panel-title">Manage Chores</h2>
        <button class="panel-btn" @click="choreStore.load()" :disabled="choreStore.loading">↻</button>
      </div>

      <div v-if="choreStore.error" class="panel-error">{{ choreStore.error }}</div>

      <!-- Add new chore -->
      <div class="chore-add-row">
        <input
          v-model="newTitle"
          class="chore-input chore-input--title"
          placeholder="Chore title"
          @keydown.enter="addChore"
        />
        <input
          v-model.number="newInterval"
          class="chore-input chore-input--interval"
          type="number"
          min="1"
          placeholder="Days"
        />
        <button class="chore-btn chore-btn--add" @click="addChore">Add</button>
      </div>

      <!-- Chore list -->
      <div class="chore-list">
        <div
          v-for="chore in choreStore.chores"
          :key="chore.id"
          class="chore-edit-row"
        >
          <template v-if="editingId === chore.id">
            <input
              v-model="editTitle"
              class="chore-input chore-input--title"
              @keydown.enter="saveEdit"
              @keydown.escape="cancelEdit"
            />
            <input
              v-model.number="editInterval"
              class="chore-input chore-input--interval"
              type="number"
              min="1"
              @keydown.enter="saveEdit"
              @keydown.escape="cancelEdit"
            />
            <button class="chore-btn chore-btn--save" @click="saveEdit">✓</button>
            <button class="chore-btn chore-btn--cancel" @click="cancelEdit">✕</button>
          </template>
          <template v-else>
            <span class="chore-title">{{ chore.title }}</span>
            <span class="chore-interval">{{ chore.interval_days }}d</span>
            <span class="chore-last-done">{{ chore.last_done || 'never' }}</span>
            <button class="chore-btn chore-btn--edit" @click="startEdit(chore)">✎</button>
            <button class="chore-btn chore-btn--delete" @click="removeChore(chore.id)">🗑</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChoreStore } from '../stores/chores.js'

const choreStore = useChoreStore()

const newTitle = ref('')
const newInterval = ref(30)

const editingId = ref(null)
const editTitle = ref('')
const editInterval = ref(30)

onMounted(() => { choreStore.load() })

async function addChore() {
  const t = newTitle.value.trim()
  if (!t || !newInterval.value) return
  await choreStore.add(t, newInterval.value)
  newTitle.value = ''
  newInterval.value = 30
}

function startEdit(chore) {
  editingId.value = chore.id
  editTitle.value = chore.title
  editInterval.value = chore.interval_days
}

async function saveEdit() {
  if (!editTitle.value.trim() || !editInterval.value) return
  await choreStore.update(editingId.value, editTitle.value.trim(), editInterval.value)
  editingId.value = null
}

function cancelEdit() {
  editingId.value = null
}

async function removeChore(id) {
  await choreStore.remove(id)
}
</script>
