<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useChats } from './chatState.js'
import AppDialog from './AppDialog.vue'

const chatState = useChats()
const {
  chats, selectedChatId, selectedChat, messages, messagesLoading, chatsLoading, creating,
  draft, sending, error, chatError, tutorUnavailable, historyLoadedChatId,
  loadChats, selectChat, createChat,
} = chatState
const activeView = ref('chats')
const chatPendingDeletion = ref(null)
const deleting = ref(false)
const settingsOpen = ref(false)
const settingsError = ref('')
const replyEnabled = ref(true)
try {
  replyEnabled.value = localStorage.getItem('linguaforge.replyEnabled') !== 'false'
} catch {
  // O tutor funciona mesmo quando o navegador bloqueia armazenamento local.
}
const titleEditingChat = ref(null)
const titleDraft = ref('')
const renaming = ref(false)
const modalError = ref('')
const translationText = ref('')
const sourceLanguage = ref('en')
const targetLanguage = computed({
  get: () => sourceLanguage.value === 'en' ? 'pt' : 'en',
  set: (value) => { sourceLanguage.value = value === 'en' ? 'pt' : 'en' },
})
const translationResult = ref(null)
const translationError = ref('')
const translating = ref(false)
const translatorUnavailable = ref(false)
const messageList = ref(null)
const serverUnavailable = computed(() => tutorUnavailable.value || translatorUnavailable.value)
let availabilityTimer = null
let availabilityRequest = null
let disposed = false

function requestDeletion(chat) {
  modalError.value = ''
  chatPendingDeletion.value = chat
}

function openTitleEditor(chat) {
  modalError.value = ''
  titleEditingChat.value = chat
  titleDraft.value = chat.title
}

async function renameChat() {
  const chat = titleEditingChat.value
  if (!chat || !titleDraft.value.trim() || renaming.value) return
  renaming.value = true
  modalError.value = ''
  try {
    await chatState.renameChat(chat.id, titleDraft.value)
    titleEditingChat.value = null
  } catch (requestError) {
    modalError.value = requestError instanceof TypeError ? 'Could not connect to LinguaForge.' : requestError.message
  } finally {
    renaming.value = false
  }
}

async function deleteChat() {
  const chat = chatPendingDeletion.value
  if (!chat || deleting.value) return
  deleting.value = true
  modalError.value = ''
  try {
    await chatState.removeChat(chat.id)
    chatPendingDeletion.value = null
  } catch (requestError) {
    modalError.value = requestError instanceof TypeError ? 'Could not connect to LinguaForge.' : requestError.message
  } finally {
    deleting.value = false
  }
}

async function sendMessage() {
  await chatState.sendMessage(replyEnabled.value)
}

function handleMessageKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey && !event.isComposing) {
    event.preventDefault()
    sendMessage()
  }
}

function clearServerUnavailable() {
  tutorUnavailable.value = false
  translatorUnavailable.value = false
}

function saveReplySetting() {
  settingsError.value = ''
  try {
    localStorage.setItem('linguaforge.replyEnabled', String(replyEnabled.value))
  } catch {
    settingsError.value = 'This preference applies now but could not be saved in this browser.'
  }
}

function stopAvailabilityCheck() {
  clearTimeout(availabilityTimer)
  availabilityTimer = null
  availabilityRequest?.abort()
}

async function checkServerAvailability() {
  if (disposed || !serverUnavailable.value || availabilityRequest) return
  const controller = new AbortController()
  availabilityRequest = controller
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch('/api/tutor/availability', { signal: controller.signal })
    if (response.ok && (await response.json()).available === true) clearServerUnavailable()
  } catch {
    // A próxima tentativa verifica novamente o servidor local.
  } finally {
    clearTimeout(timeout)
    availabilityRequest = null
    if (!disposed && serverUnavailable.value) availabilityTimer = setTimeout(checkServerAvailability, 5000)
  }
}

watch(serverUnavailable, (unavailable) => {
  if (unavailable) checkServerAvailability()
  else stopAvailabilityCheck()
})

function swapTranslationLanguages() {
  if (!translating.value) sourceLanguage.value = targetLanguage.value
}

watch([translationText, sourceLanguage], () => {
  translationResult.value = null
  translationError.value = ''
})

async function translateText() {
  if (!translationText.value.trim() || translating.value) return
  translating.value = true
  translationResult.value = null
  translationError.value = ''
  try {
    const response = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: translationText.value, source_language: sourceLanguage.value, target_language: targetLanguage.value }),
    })
    if (response.status === 503) {
      translatorUnavailable.value = true
      return
    }
    const result = await response.json()
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not translate this text.')
    translationResult.value = result
    clearServerUnavailable()
  } catch (requestError) {
    translationError.value = requestError instanceof TypeError
      ? 'Could not connect to LinguaForge. Check that the app is running and try again.'
      : requestError.message
  } finally {
    translating.value = false
  }
}

onMounted(loadChats)
watch([messages, activeView, messagesLoading], async () => {
  await nextTick()
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' })
}, { deep: true })
onUnmounted(() => {
  disposed = true
  stopAvailabilityCheck()
})
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar" aria-label="LinguaForge navigation">
      <div class="sidebar-header">
        <span class="brand">LinguaForge</span>
        <nav class="primary-nav" aria-label="Main navigation">
          <button :class="{ active: activeView === 'chats' }" type="button" @click="activeView = 'chats'">Chats</button>
          <button :class="{ active: activeView === 'translate' }" type="button" @click="activeView = 'translate'">Translate</button>
        </nav>
        <button v-if="activeView === 'chats'" class="new-chat" type="button" aria-label="New chat" :disabled="creating || chatsLoading" @click="createChat">+ New Chat</button>
        <button class="settings-button" type="button" aria-label="Settings" @click="settingsOpen = true">Settings</button>
      </div>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <nav v-if="activeView === 'chats'" class="chat-list" aria-label="Chat history">
        <div v-for="chat in chats" :key="chat.id" class="chat-row" :class="{ selected: chat.id === selectedChatId }">
          <button class="chat-item" type="button" :title="chat.title" :aria-current="chat.id === selectedChatId ? 'page' : undefined" @click="selectChat(chat.id)">
            {{ chat.title }}
          </button>
          <button class="delete-chat" type="button" :aria-label="`Delete ${chat.title}`" @click="requestDeletion(chat)">×</button>
        </div>
      </nav>
    </aside>

    <section v-if="activeView === 'chats'" class="chat-panel" aria-live="polite">
      <template v-if="selectedChatId">
        <header class="chat-header">
          <h1 :title="selectedChat?.title">{{ selectedChat?.title }}</h1>
          <button class="edit-title" type="button" @click="openTitleEditor(selectedChat)">Edit title</button>
        </header>
        <div v-if="messagesLoading" class="empty-state">
          <p>Loading messages...</p>
        </div>
        <div v-else ref="messageList" class="message-list">
          <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
            <p v-if="message.role === 'user'">{{ message.text }}</p>
            <template v-else>
              <section class="tutor-section">
                <h2>Corrected text</h2>
                <p>{{ message.response.corrected_text }}</p>
              </section>
              <section class="tutor-section">
                <h2>Explanation</h2>
                <p>{{ message.response.explanation_pt }}</p>
              </section>
              <section v-if="replyEnabled && message.response.reply_en" class="tutor-section">
                <h2>Reply</h2>
                <p>{{ message.response.reply_en }}</p>
              </section>
            </template>
          </article>
          <p v-if="!messages.length && !sending" class="empty-history">No messages yet.</p>
          <p v-if="sending" class="assistant-loading">LinguaForge is thinking...</p>
        </div>
      </template>
      <div v-else class="empty-state">
        <h1>Start learning with LinguaForge</h1>
        <p>Create a new chat to begin.</p>
      </div>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea
          v-model="draft"
          rows="1"
          placeholder="Type a message..."
          aria-label="Message"
          :disabled="!selectedChatId || sending || messagesLoading"
          @keydown="handleMessageKeydown"
        ></textarea>
        <button type="submit" :disabled="!selectedChatId || !draft.trim() || sending || messagesLoading || historyLoadedChatId !== selectedChatId">
          {{ sending ? 'Sending...' : 'Send' }}
        </button>
      </form>
      <p v-if="chatError" class="chat-error" role="alert">{{ chatError }} <button type="button" @click="selectChat(selectedChatId)">Reload chat</button></p>
      <p v-if="tutorUnavailable" class="tutor-unavailable" role="alert">
        Tutor is unavailable. Start llama-server and try again.
      </p>
    </section>

    <section v-else class="translation-panel" aria-live="polite">
      <header class="translation-header">
        <h1>Translate</h1>
        <p>Translate a message without saving it to a chat.</p>
      </header>
      <form class="translation-form" @submit.prevent="translateText">
        <div class="translation-languages">
          <label>
            From
            <select v-model="sourceLanguage" :disabled="translating">
              <option value="en">English</option>
              <option value="pt">Portuguese</option>
            </select>
          </label>
          <button type="button" class="swap-languages" :disabled="translating" aria-label="Swap languages" @click="swapTranslationLanguages">⇄</button>
          <label>
            To
            <select v-model="targetLanguage" :disabled="translating">
              <option value="pt">Portuguese</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        <textarea v-model="translationText" :disabled="translating" rows="7" placeholder="Paste text to translate..." aria-label="Text to translate"></textarea>
        <button class="translate-button" type="submit" :disabled="!translationText.trim() || translating">
          {{ translating ? 'Translating...' : 'Translate' }}
        </button>
      </form>
      <p v-if="translationError" class="error translation-error" role="alert">{{ translationError }}</p>
      <p v-if="translatorUnavailable" class="tutor-unavailable" role="alert">
        Translator is unavailable. Start llama-server and try again.
      </p>
      <div v-if="translationResult" class="translation-result">
        <section>
          <h2>Translation</h2>
          <p>{{ translationResult.translation }}</p>
        </section>
        <section v-if="translationResult.interpretation_pt">
          <h2>Meaning</h2>
          <p>{{ translationResult.interpretation_pt }}</p>
        </section>
      </div>
    </section>

    <AppDialog v-if="chatPendingDeletion" labelled-by="delete-chat-title" :busy="deleting" @close="chatPendingDeletion = null">
      <h2 id="delete-chat-title">Delete chat?</h2>
      <p>This will permanently remove this chat and its messages.</p>
      <p v-if="modalError" class="error" role="alert">{{ modalError }}</p>
      <div class="modal-actions">
        <button type="button" :disabled="deleting" @click="chatPendingDeletion = null">Cancel</button>
        <button class="danger" type="button" :disabled="deleting" @click="deleteChat">{{ deleting ? 'Deleting...' : 'Delete' }}</button>
      </div>
    </AppDialog>

    <AppDialog v-if="titleEditingChat" labelled-by="edit-title-title" :busy="renaming" @close="titleEditingChat = null">
      <form @submit.prevent="renameChat">
        <h2 id="edit-title-title">Edit chat title</h2>
        <label class="title-input">
          Title
          <input v-model="titleDraft" :disabled="renaming" maxlength="80" required aria-label="Chat title" autofocus>
        </label>
        <p v-if="modalError" class="error" role="alert">{{ modalError }}</p>
        <div class="modal-actions">
          <button type="button" :disabled="renaming" @click="titleEditingChat = null">Cancel</button>
          <button type="submit" :disabled="!titleDraft.trim() || renaming">{{ renaming ? 'Saving...' : 'Save' }}</button>
        </div>
      </form>
    </AppDialog>

    <AppDialog v-if="settingsOpen" labelled-by="settings-title" @close="settingsOpen = false">
      <h2 id="settings-title">Settings</h2>
      <label class="setting-option">
        <input v-model="replyEnabled" type="checkbox" @change="saveReplySetting">
        <span>
          <strong>Enable Reply</strong>
          <small>Generate a follow-up question in English after each correction.</small>
        </span>
      </label>
      <p v-if="settingsError" class="error" role="alert">{{ settingsError }}</p>
      <div class="modal-actions">
        <button type="button" @click="settingsOpen = false">Done</button>
      </div>
    </AppDialog>
  </main>
</template>
