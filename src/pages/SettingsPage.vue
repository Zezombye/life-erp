<template>
    <div class="min-h-screen bg-zinc-900 text-zinc-100 p-4 md:p-6">
        <div class="max-w-xl mx-auto">
            <Panel header="Settings">
                <div class="flex flex-col gap-4">
                    <Message v-if="settingsStore.error" severity="error">{{ settingsStore.error }}</Message>

                    <div class="setting-row">
                        <label for="work-mn" class="setting-label">Work target (minutes/day)</label>
                        <InputNumber id="work-mn" :modelValue="settingsStore.getNumber('work_mn', 300)" @update:modelValue="v => settingsStore.update('work_mn', String(v))" :useGrouping="false" />
                    </div>

                    <div class="setting-row">
                        <label for="watchlist" class="setting-label">Stock watchlist (comma-separated)</label>
                        <InputText id="watchlist" :modelValue="settingsStore.get('watchlist', '')" @update:modelValue="v => settingsStore.update('watchlist', v!)" class="setting-input--wide" />
                    </div>
                </div>
            </Panel>

            <Panel header="Debug" class="mt-4">
                <div class="flex flex-col gap-4">
                    <div class="setting-row">
                        <span class="setting-label">Wipe local database and re-sync all data from the server</span>
                        <Button label="Wipe &amp; Resync" severity="danger" @click="wipeAndResync" :loading="resyncing" />
                    </div>
                </div>
            </Panel>
        </div>
    </div>
</template>

<script setup lang="ts">
import {onMounted, ref} from 'vue'
import Panel from 'primevue/panel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Button from 'primevue/button'
import {useSettingsStore} from '../stores/settings'
import {forceResync} from '../services/sync-engine'

const settingsStore = useSettingsStore()
const resyncing = ref(false)

function wipeAndResync() {
    resyncing.value = true
    try {
        forceResync()
    } finally {
        // Give it a moment so the user sees the loading state
        setTimeout(() => {resyncing.value = false}, 1000)
    }
}

onMounted(() => {
    settingsStore.load()
})
</script>

<style lang="scss">
.setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

.setting-label {
    font-size: 0.875rem;
    color: #a1a1aa;
}

.setting-input--wide {
    width: 240px;
    text-align: left;
}
</style>
