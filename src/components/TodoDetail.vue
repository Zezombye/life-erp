<template>
  <div class="todo-detail-overlay" @click.self="$emit('close')">
    <div class="todo-detail">
      <!-- Header -->
      <div class="todo-detail-header">
        <div class="todo-detail-header-left">
          <template v-if="editingTitle">
            <input
              ref="titleInputEl"
              v-model="titleDraft"
              class="todo-detail-title-input"
              @keydown.enter="saveTitle"
              @keydown.escape="editingTitle = false"
              @blur="saveTitle"
            />
          </template>
          <template v-else>
            <h2 class="todo-detail-title" @click="startEditTitle">{{ todo?.title }}</h2>
            <span class="todo-detail-status" :class="'todo-detail-status--' + todo?.status">
              {{ todo?.status }}
            </span>
          </template>
        </div>
        <button class="panel-btn" @click="$emit('close')">✕</button>
      </div>

      <div class="todo-detail-meta">
        Opened {{ todo?.created_at }}
        <template v-if="todo?.closed_at"> · Closed {{ todo.closed_at }}</template>
      </div>

      <!-- Messages -->
      <div class="todo-detail-messages">
        <div
          v-for="msg in todoStore.messages[todoId] || []"
          :key="msg.id"
          class="todo-msg"
        >
          <div class="todo-msg-header">
            <span class="todo-msg-date">{{ msg.created_at }}</span>
            <span v-if="msg.updated_at !== msg.created_at" class="todo-msg-edited">(edited)</span>
            <div class="todo-msg-actions">
              <button class="todo-msg-btn" @click="startEditMessage(msg)">✎</button>
              <button class="todo-msg-btn" @click="deleteMessage(msg.id)">🗑</button>
            </div>
          </div>
          <template v-if="editingMsgId === msg.id">
            <textarea
              ref="msgEditEl"
              v-model="msgEditDraft"
              class="todo-msg-textarea"
              rows="4"
              @keydown.escape="editingMsgId = null"
            ></textarea>
            <div class="todo-msg-edit-actions">
              <button class="chore-btn chore-btn--save" @click="saveMessageEdit">Save</button>
              <button class="chore-btn" @click="editingMsgId = null">Cancel</button>
            </div>
          </template>
          <div v-else class="todo-msg-body" v-html="renderMd(msg.content)"></div>
        </div>
      </div>

      <!-- New message -->
      <div class="todo-msg-compose">
        <textarea
          v-model="newMessage"
          class="todo-msg-textarea"
          rows="3"
          placeholder="Write a message (Markdown supported)..."
        ></textarea>
        <div class="todo-msg-compose-footer">
          <button class="chore-btn chore-btn--add" @click="postMessage" :disabled="!newMessage.trim()">
            Comment
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useTodoStore } from '../stores/todos.js'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ linkify: true, breaks: true })

const props = defineProps({
  todoId: { type: Number, required: true },
})
defineEmits(['close'])

const todoStore = useTodoStore()

const todo = computed(() => todoStore.todos.find(t => t.id === props.todoId))

// Title editing
const editingTitle = ref(false)
const titleDraft = ref('')
const titleInputEl = ref(null)

function startEditTitle() {
  titleDraft.value = todo.value?.title || ''
  editingTitle.value = true
  nextTick(() => titleInputEl.value?.focus())
}

async function saveTitle() {
  if (!editingTitle.value) return
  editingTitle.value = false
  const t = titleDraft.value.trim()
  if (t && t !== todo.value?.title) {
    await todoStore.rename(props.todoId, t)
  }
}

// Message editing
const editingMsgId = ref(null)
const msgEditDraft = ref('')

function startEditMessage(msg) {
  editingMsgId.value = msg.id
  msgEditDraft.value = msg.content
}

async function saveMessageEdit() {
  if (!msgEditDraft.value.trim()) return
  await todoStore.editMessage(props.todoId, editingMsgId.value, msgEditDraft.value)
  editingMsgId.value = null
}

async function deleteMessage(msgId) {
  await todoStore.removeMessage(props.todoId, msgId)
}

// New message
const newMessage = ref('')

async function postMessage() {
  const c = newMessage.value.trim()
  if (!c) return
  await todoStore.addMessage(props.todoId, c)
  newMessage.value = ''
}

function renderMd(content) {
  return md.render(content || '')
}

// Load messages when opened
onMounted(() => {
  todoStore.loadMessages(props.todoId)
})

watch(() => props.todoId, (id) => {
  if (id != null) todoStore.loadMessages(id)
})
</script>
