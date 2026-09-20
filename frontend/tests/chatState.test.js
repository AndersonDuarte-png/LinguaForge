import test from 'node:test'
import assert from 'node:assert/strict'
import { useChats } from '../src/chatState.js'

const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body })
const deferred = () => { let resolve; const promise = new Promise((r) => { resolve = r }); return { promise, resolve } }
const turn = (chatId) => ({ user_message: { id: `${chatId}-user`, chat_id: chatId }, assistant_message: { id: `${chatId}-assistant`, chat_id: chatId } })
function setup(handler) {
  const state = useChats(handler)
  state.chats.value = [{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }]
  return state
}

test('a late history response never replaces the newly selected chat', async () => {
  const a = deferred()
  const state = setup((url) => url.includes('/a/') ? a.promise : Promise.resolve(response([{ id: 'b-existing' }])))
  const old = state.selectChat('a')
  await state.selectChat('b')
  a.resolve(response([{ id: 'a-existing' }]))
  await old
  assert.equal(state.selectedChatId.value, 'b')
  assert.deepEqual(state.messages.value, [{ id: 'b-existing' }])
  assert.equal(state.messagesLoading.value, false)
})

test('sending into A while visiting B keeps both history and drafts isolated', async () => {
  const post = deferred()
  let payload
  const state = setup((url, options) => {
    if (options?.method === 'POST') { payload = JSON.parse(options.body); return post.promise }
    return Promise.resolve(response([]))
  })
  await state.selectChat('a')
  state.draft.value = 'Hello from A'
  const sending = state.sendMessage(false)
  await state.selectChat('b')
  state.draft.value = 'Draft B'
  post.resolve(response(turn('a'), 201))
  await sending
  assert.deepEqual(payload, { text: 'Hello from A', include_reply: false })
  assert.equal(state.draft.value, 'Draft B')
  assert.deepEqual(state.messages.value, [])
  await state.selectChat('a')
  assert.equal(state.draft.value, '')
})

test('drafts are restored when switching conversations', async () => {
  const state = setup(async () => response([]))
  await state.selectChat('a')
  state.draft.value = 'Draft A'
  await state.selectChat('b')
  assert.equal(state.draft.value, '')
  state.draft.value = 'Draft B'
  await state.selectChat('a')
  assert.equal(state.draft.value, 'Draft A')
})

test('deleting an unselected chat does not reload or clear current messages', async () => {
  const calls = []
  const state = setup(async (url, options) => { calls.push([url, options?.method]); return response([{ id: 'a-existing' }]) })
  await state.selectChat('a')
  state.draft.value = 'Draft A'
  await state.removeChat('b')
  assert.deepEqual(state.messages.value, [{ id: 'a-existing' }])
  assert.equal(state.draft.value, 'Draft A')
  assert.equal(calls.length, 2)
})

for (const status of [502, 503, 409]) {
  test(`a ${status} response preserves the draft and allows retry`, async () => {
    let fail = true
    const state = setup(async (url, options) => options?.method === 'POST'
      ? (fail ? response({ detail: 'Try again' }, status) : response(turn('a'), 201))
      : response([]))
    await state.selectChat('a')
    state.draft.value = 'Please correct this'
    await state.sendMessage(true)
    assert.equal(state.draft.value, 'Please correct this')
    assert.deepEqual(state.messages.value, [])
    assert.equal(state.tutorUnavailable.value, status === 503)
    fail = false
    await state.sendMessage(true)
    assert.equal(state.draft.value, '')
    assert.equal(state.messages.value.length, 2)
  })
}

test('rapid double send creates only one request', async () => {
  const post = deferred()
  let requests = 0
  const state = setup((url, options) => {
    if (options?.method === 'POST') { requests++; return post.promise }
    return Promise.resolve(response([]))
  })
  await state.selectChat('a')
  state.draft.value = 'Hello'
  const first = state.sendMessage(true)
  await state.sendMessage(true)
  assert.equal(requests, 1)
  post.resolve(response(turn('a'), 201))
  await first
})

test('returning to a chat during generation does not accept stale history', async () => {
  const post = deferred()
  const stale = deferred()
  let reads = 0
  const state = setup((url, options) => {
    if (options?.method === 'POST') return post.promise
    if (url.includes('/a/')) {
      reads++
      if (reads === 2) return stale.promise
      if (reads === 3) return Promise.resolve(response(Object.values(turn('a'))))
    }
    return Promise.resolve(response([]))
  })
  await state.selectChat('a')
  state.draft.value = 'Hello'
  const sending = state.sendMessage(true)
  await state.selectChat('b')
  const returning = state.selectChat('a')
  post.resolve(response(turn('a'), 201))
  await sending
  stale.resolve(response([]))
  await returning
  assert.equal(state.messages.value.length, 2)
  assert.equal(state.messagesLoading.value, false)
})

test('a failed history load prevents sending with an unknown conversation', async () => {
  let posts = 0
  const state = setup(async (url, options) => {
    if (options?.method === 'POST') posts++
    return response({}, 500)
  })
  await state.selectChat('a')
  state.draft.value = 'Hello'
  await state.sendMessage(true)
  assert.equal(posts, 0)
  assert.match(state.chatError.value, /load/)
})

test('creating a new chat invalidates an older pending history request', async () => {
  const old = deferred()
  const state = setup((url, options) => options?.method === 'POST' ? Promise.resolve(response({ id: 'c', title: 'New Chat' })) : old.promise)
  const loading = state.selectChat('a')
  await state.createChat()
  old.resolve(response([{ id: 'a-old' }]))
  await loading
  assert.equal(state.selectedChatId.value, 'c')
  assert.deepEqual(state.messages.value, [])
  assert.equal(state.messagesLoading.value, false)
})

test('rename updates both the list and computed title after the server saves', async () => {
  const state = setup(async (url, options) => options?.method === 'PATCH' ? response({ id: 'a', title: 'Travel' }) : response([]))
  await state.selectChat('a')
  await state.renameChat('a', 'Travel')
  assert.equal(state.selectedChat.value.title, 'Travel')
  assert.equal(state.chats.value[0].title, 'Travel')
  assert.equal(state.chats.value[1].title, 'B')
})
