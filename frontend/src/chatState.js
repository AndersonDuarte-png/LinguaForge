import { computed, ref } from 'vue'

export function useChats(request = (...args) => fetch(...args)) {
  const chats = ref([])
  const selectedChatId = ref(null)
  const messages = ref([])
  const messagesLoading = ref(false)
  const chatsLoading = ref(false)
  const creating = ref(false)
  const error = ref('')
  const tutorUnavailable = ref(false)
  const drafts = ref({})
  const chatErrors = ref({})
  const sendingChatIds = ref(new Set())
  const historyLoadedChatId = ref(null)
  let selectionVersion = 0

  const selectedChat = computed(() => chats.value.find(({ id }) => id === selectedChatId.value))
  const sending = computed(() => sendingChatIds.value.has(selectedChatId.value))
  const chatError = computed(() => chatErrors.value[selectedChatId.value] ?? '')
  const draft = computed({
    get: () => drafts.value[selectedChatId.value] ?? '',
    set: (value) => { if (selectedChatId.value) drafts.value[selectedChatId.value] = value },
  })

  async function loadChats() {
    chatsLoading.value = true
    try {
      const response = await request('/api/chats')
      if (!response.ok) throw new Error('Could not load chats.')
      chats.value = await response.json()
      if (chats.value[0] && !selectedChatId.value) await selectChat(chats.value[0].id)
    } catch {
      error.value = 'Could not load chats. Reload the page to try again.'
    } finally {
      chatsLoading.value = false
    }
  }

  async function selectChat(chatId) {
    const version = ++selectionVersion
    selectedChatId.value = chatId
    messages.value = []
    historyLoadedChatId.value = null
    messagesLoading.value = Boolean(chatId)
    if (!chatId) return
    chatErrors.value[chatId] = ''
    try {
      const response = await request(`/api/chats/${chatId}/messages`)
      if (!response.ok) throw new Error('Could not load this chat. Select it again to retry.')
      const history = await response.json()
      if (version === selectionVersion) {
        messages.value = history
        historyLoadedChatId.value = chatId
      }
    } catch {
      if (version === selectionVersion) chatErrors.value[chatId] = 'Could not load this chat. Select it again to retry.'
    } finally {
      if (version === selectionVersion) messagesLoading.value = false
    }
  }

  async function createChat() {
    if (creating.value || chatsLoading.value) return
    creating.value = true
    error.value = ''
    try {
      const response = await request('/api/chats', { method: 'POST' })
      if (!response.ok) throw new Error('Could not create a new chat.')
      const chat = await response.json()
      chats.value.unshift(chat)
      ++selectionVersion
      selectedChatId.value = chat.id
      historyLoadedChatId.value = chat.id
      messages.value = []
      messagesLoading.value = false
    } catch {
      error.value = 'Could not create a new chat. Please try again.'
    } finally {
      creating.value = false
    }
  }

  async function removeChat(chatId) {
    const response = await request(`/api/chats/${chatId}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('Could not delete this chat. Please try again.')
    chats.value = chats.value.filter(({ id }) => id !== chatId)
    delete drafts.value[chatId]
    delete chatErrors.value[chatId]
    if (selectedChatId.value === chatId) await selectChat(chats.value[0]?.id ?? null)
  }

  async function renameChat(chatId, title) {
    const response = await request(`/api/chats/${chatId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    const result = await response.json()
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not rename this chat.')
    chats.value = chats.value.map((chat) => chat.id === result.id ? result : chat)
  }

  async function sendMessage(includeReply) {
    const chatId = selectedChatId.value
    const text = draft.value
    if (!chatId || !text.trim() || sending.value || messagesLoading.value || historyLoadedChatId.value !== chatId) return
    sendingChatIds.value.add(chatId)
    chatErrors.value[chatId] = ''
    try {
      const response = await request(`/api/chats/${chatId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, include_reply: includeReply }),
      })
      if (response.status === 503) {
        tutorUnavailable.value = true
        return
      }
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not send this message. Please try again.')
      if (drafts.value[chatId] === text) drafts.value[chatId] = ''
      tutorUnavailable.value = false
      if (selectedChatId.value === chatId) {
        if (messagesLoading.value) {
          // Recarrega após salvar para não aceitar um histórico obtido antes da resposta.
          await selectChat(chatId)
        } else {
          const incoming = [result.user_message, result.assistant_message]
          const ids = new Set(messages.value.map(({ id }) => id))
          messages.value.push(...incoming.filter(({ id }) => !ids.has(id)))
        }
      }
    } catch (requestError) {
      if (chats.value.some(({ id }) => id === chatId)) {
        chatErrors.value[chatId] = requestError instanceof TypeError
          ? 'Could not connect to LinguaForge. Check that the app is running and try again.'
          : requestError.message
      }
    } finally {
      sendingChatIds.value.delete(chatId)
    }
  }

  return {
    chats, selectedChatId, selectedChat, messages, messagesLoading, chatsLoading, creating,
    draft, sending, error, chatError, tutorUnavailable, historyLoadedChatId,
    loadChats, selectChat, createChat, removeChat, renameChat, sendMessage,
  }
}
