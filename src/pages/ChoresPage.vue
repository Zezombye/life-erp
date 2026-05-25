<template>
    <div class="chores-page">
        <div class="dashboard-panel">
            <div class="panel-header">
                <h2 class="panel-title">Manage Chores</h2>
                <Button icon="pi pi-refresh" severity="secondary" text size="small" @click="choreStore.load()" :loading="choreStore.loading" />
            </div>

            <Message v-if="choreStore.error" severity="error" :closable="false">{{ choreStore.error }}</Message>

            <!-- Add new chore -->
            <div class="chore-add-row">
                <InputText v-model="newTitle" placeholder="Chore title" class="flex-1" size="small" @keydown.enter="addChore" />
                <InputNumber v-model="newInterval" placeholder="Days" :min="1" :useGrouping="false" size="small" class="chore-input--interval" />
                <Button label="Add" icon="pi pi-plus" severity="success" size="small" @click="addChore" />
            </div>

            <!-- Chore list -->
            <div class="chore-list">
                <div v-for="chore in choreStore.chores" :key="chore.id" class="chore-edit-row">
                    <template v-if="editingId === chore.id">
                        <InputText v-model="editTitle" class="flex-1" size="small" @keydown.enter="saveEdit" @keydown.escape="cancelEdit" />
                        <InputNumber v-model="editInterval" :min="1" :useGrouping="false" size="small" class="chore-input--interval" @keydown.enter="saveEdit" @keydown.escape="cancelEdit" />
                        <Button icon="pi pi-check" severity="success" size="small" @click="saveEdit" />
                        <Button icon="pi pi-times" severity="secondary" size="small" @click="cancelEdit" />
                    </template>
                    <template v-else>
                        <span class="chore-title">{{ chore.title }}</span>
                        <span class="chore-interval">{{ chore.interval_days }}d</span>
                        <span class="chore-last-done">{{ chore.last_done || 'never' }}</span>
                        <Button icon="pi pi-pencil" severity="secondary" text size="small" @click="startEdit(chore)" />
                        <Button icon="pi pi-trash" severity="danger" text size="small" @click="removeChore(chore.id)" />
                    </template>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {ref, onMounted} from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import {useChoreStore} from '../stores/chores'

const choreStore = useChoreStore()

const newTitle = ref('')
const newInterval = ref(30)

const editingId = ref<string | null>(null)
const editTitle = ref('')
const editInterval = ref(30)

onMounted(() => {choreStore.load()})

function addChore(): void {
    const t = newTitle.value.trim()
    if (!t || !newInterval.value) return
    choreStore.add(t, newInterval.value)
    newTitle.value = ''
    newInterval.value = 30
}

function startEdit(chore: {id: string; title: string; interval_days: number}): void {
    editingId.value = chore.id
    editTitle.value = chore.title
    editInterval.value = chore.interval_days
}

function saveEdit(): void {
    if (!editTitle.value.trim() || !editInterval.value) return
    choreStore.update(editingId.value!, editTitle.value.trim(), editInterval.value)
    editingId.value = null
}

function cancelEdit(): void {
    editingId.value = null
}

function removeChore(id: string): void {
    choreStore.remove(id)
}
</script>

<style lang="scss">
.chores-page {
    padding: 0.75rem;
    height: calc(100vh - 2.75rem);
    overflow-y: auto;
}

.chore-add-row,
.chore-edit-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
}

.chore-add-row {
    border-bottom: 1px solid #3f3f46;
    padding-bottom: 0.5rem;
    margin-bottom: 0.25rem;
}

.chore-input--interval {
    width: 4.5rem;
    text-align: center;
}

.chore-title {
    flex: 1;
    font-size: 0.875rem;
}

.chore-interval {
    width: 3rem;
    text-align: center;
    color: #a1a1aa;
    font-size: 0.8125rem;
}

.chore-last-done {
    width: 6rem;
    text-align: center;
    color: #71717a;
    font-size: 0.8125rem;
}
</style>
