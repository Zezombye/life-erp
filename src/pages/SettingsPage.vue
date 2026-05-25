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
        </div>
    </div>
</template>

<script setup lang="ts">
import {onMounted} from 'vue'
import Panel from 'primevue/panel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import {useSettingsStore} from '../stores/settings'

const settingsStore = useSettingsStore()

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
