<template>
    <Dialog :visible="true" modal :header="todo?.title ?? 'Todo'" :style="{width: '720px'}" @update:visible="$emit('close')">
        <!-- Header content -->
        <div class="todo-detail-header-left mb-3">
            <template v-if="editingTitle">
                <InputText ref="titleInputEl" v-model="titleDraft" class="w-full" @keydown.enter="saveTitle" @keydown.escape="editingTitle = false" @blur="saveTitle" />
            </template>
            <template v-else>
                <h2 class="todo-detail-title" @click="startEditTitle">{{ todo?.title }}</h2>
                <Tag :value="todo?.status" :severity="todo?.status === 'open' ? 'success' : 'info'" />
            </template>
        </div>

        <div class="todo-detail-meta">
            Opened {{ todo?.created_at }}
            <template v-if="todo?.closed_at"> · Closed {{ todo.closed_at }}</template>
        </div>

        <!-- Messages -->
        <div class="todo-detail-messages">
            <div v-for="msg in todoStore.messages[todoId] || []" :key="msg.id" class="todo-msg">
                <div class="todo-msg-header">
                    <span class="todo-msg-date">{{ msg.created_at }}</span>
                    <span v-if="msg.updated_at !== msg.created_at" class="todo-msg-edited">(edited)</span>
                    <div class="todo-msg-actions">
                        <Button icon="pi pi-pencil" severity="secondary" text size="small" @click="startEditMessage(msg)" />
                        <Button icon="pi pi-trash" severity="danger" text size="small" @click="deleteMessage(msg.id)" />
                    </div>
                </div>
                <template v-if="editingMsgId === msg.id">
                    <Textarea v-model="msgEditDraft" rows="4" class="w-full" @keydown.escape="editingMsgId = null" />
                    <div class="todo-msg-edit-actions">
                        <Button label="Save" severity="success" size="small" @click="saveMessageEdit" />
                        <Button label="Cancel" severity="secondary" size="small" @click="editingMsgId = null" />
                    </div>
                </template>
                <div v-else class="todo-msg-body" v-html="renderMd(msg.content)"></div>
            </div>
        </div>

        <!-- New message -->
        <div class="todo-msg-compose">
            <Textarea v-model="newMessage" rows="3" class="w-full" placeholder="Write a message (Markdown supported)..." />
            <div class="todo-msg-compose-footer">
                <Button label="Comment" severity="success" size="small" @click="postMessage" :disabled="!newMessage.trim()" />
            </div>
        </div>
    </Dialog>
</template>

<script setup lang="ts">
import {ref, computed, watch, nextTick, onMounted} from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import {useTodoStore} from '../stores/todos'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({linkify: true, breaks: true})

const props = defineProps<{
    todoId: number
}>()
defineEmits<{
    close: []
}>()

const todoStore = useTodoStore()

const todo = computed(() => todoStore.todos.find(t => t.id === props.todoId))

// Title editing
const editingTitle = ref(false)
const titleDraft = ref('')
const titleInputEl = ref<InstanceType<typeof InputText> | null>(null)

function startEditTitle(): void {
    titleDraft.value = todo.value?.title || ''
    editingTitle.value = true
    nextTick(() => titleInputEl.value?.focus())
}

async function saveTitle(): Promise<void> {
    if (!editingTitle.value) return
    editingTitle.value = false
    const t = titleDraft.value.trim()
    if (t && t !== todo.value?.title) {
        await todoStore.rename(props.todoId, t)
    }
}

// Message editing
const editingMsgId = ref<number | null>(null)
const msgEditDraft = ref('')

function startEditMessage(msg: {id: number; content: string}): void {
    editingMsgId.value = msg.id
    msgEditDraft.value = msg.content
}

async function saveMessageEdit(): Promise<void> {
    if (!msgEditDraft.value.trim()) return
    await todoStore.editMessage(props.todoId, editingMsgId.value!, msgEditDraft.value)
    editingMsgId.value = null
}

async function deleteMessage(msgId: number): Promise<void> {
    await todoStore.removeMessage(props.todoId, msgId)
}

// New message
const newMessage = ref('')

async function postMessage(): Promise<void> {
    const c = newMessage.value.trim()
    if (!c) return
    await todoStore.addMessage(props.todoId, c)
    newMessage.value = ''
}

function renderMd(content: string): string {
    return md.render(content || '')
}

// Load messages when opened
onMounted(() => {
    todoStore.loadMessages(props.todoId)
})

watch(() => props.todoId, (id) => {
    if (id) todoStore.loadMessages(id)
})
</script>

<style lang="scss">
.todo-detail-header-left {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
}

.todo-detail-title {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    &:hover {
        color: #93c5fd;
    }
}

.todo-detail-meta {
    padding: 0.375rem 1rem;
    font-size: 0.75rem;
    color: #71717a;
    border-bottom: 1px solid #27272a;
    flex-shrink: 0;
}

.todo-detail-messages {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem 0;
}

.todo-msg {
    padding: 0.5rem 1rem;
    border-bottom: 1px solid #27272a;
}

.todo-msg-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.375rem;
}

.todo-msg-date {
    font-size: 0.75rem;
    color: #71717a;
}

.todo-msg-edited {
    font-size: 0.6875rem;
    color: #52525b;
    font-style: italic;
}

.todo-msg-actions {
    margin-left: auto;
    display: flex;
    gap: 0.25rem;
    opacity: 0;
    transition: opacity 0.15s;
}

.todo-msg:hover .todo-msg-actions {
    opacity: 1;
}

.todo-msg-body {
    font-size: 0.875rem;
    line-height: 1.6;
    color: #d4d4d8;

    p {
        margin: 0 0 0.5rem;
    }

    p:last-child {
        margin-bottom: 0;
    }

    code {
        background: #27272a;
        padding: 0.125rem 0.375rem;
        border-radius: 3px;
        font-size: 0.8125rem;
    }

    pre {
        background: #27272a;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        overflow-x: auto;
        margin: 0.5rem 0;
    }

    pre code {
        background: none;
        padding: 0;
    }

    blockquote {
        border-left: 3px solid #3f3f46;
        padding-left: 0.75rem;
        color: #a1a1aa;
        margin: 0.5rem 0;
    }

    ul,
    ol {
        padding-left: 1.5rem;
        margin: 0.25rem 0;
    }

    a {
        color: #60a5fa;
        text-decoration: none;

        &:hover {
            text-decoration: underline;
        }
    }

    h1,
    h2,
    h3,
    h4 {
        margin: 0.75rem 0 0.25rem;
        font-weight: 600;
    }

    h1 {
        font-size: 1.25rem;
    }

    h2 {
        font-size: 1.125rem;
    }

    h3 {
        font-size: 1rem;
    }

    img {
        max-width: 100%;
        border-radius: 4px;
    }
}

.todo-msg-edit-actions {
    display: flex;
    gap: 0.25rem;
    margin-top: 0.25rem;
}

.todo-msg-compose {
    padding: 0.75rem 1rem;
    border-top: 1px solid #3f3f46;
    flex-shrink: 0;
}

.todo-msg-compose-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.375rem;
}
</style>
