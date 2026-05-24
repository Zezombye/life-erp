<template>
  <div class="min-h-screen bg-zinc-900 text-zinc-100 p-4 md:p-6">
    <div class="max-w-xl mx-auto">
      <div class="dashboard-panel">
        <div class="panel-header">
          <h2 class="panel-title">Settings</h2>
        </div>
        <div class="p-4 flex flex-col gap-4">
          <div v-if="settingsStore.error" class="panel-error">
            {{ settingsStore.error }}
          </div>

          <label class="setting-row">
            <span class="setting-label">Work target (minutes/day)</span>
            <input
              type="number"
              class="setting-input"
              :value="settingsStore.getNumber('work_mn', 300)"
              @change="e => settingsStore.update('work_mn', e.target.value)"
            />
          </label>

          <label class="setting-row">
            <span class="setting-label">Stock watchlist (comma-separated)</span>
            <input
              type="text"
              class="setting-input setting-input--wide"
              :value="settingsStore.get('watchlist', '')"
              @change="e => settingsStore.update('watchlist', e.target.value)"
            />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useSettingsStore } from '../stores/settings.js'

const settingsStore = useSettingsStore()

onMounted(() => {
  settingsStore.load()
})
</script>
