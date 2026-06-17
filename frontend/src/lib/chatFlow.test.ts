import { describe, expect, it, vi } from 'vitest'
import type { ChatMessage, ChatResponse } from '../api/client'
import type { StoredSession } from './storage'
import { sendChatTurn } from './chatFlow'

const session: StoredSession = {
  id: 'session-a',
  name: 'Console',
  token: 'session-token',
}

const userMessage: ChatMessage = {
  role: 'user',
  content: 'Run the task',
}

const assistantResponse: ChatResponse = {
  messages: [userMessage, { role: 'assistant', content: 'Done' }],
  status: 'completed',
}

describe('sendChatTurn', () => {
  it('does not retry standard chat when streaming succeeded but refresh failed', async () => {
    const sendChat = vi.fn().mockResolvedValue(assistantResponse)
    const streamChat = vi.fn().mockImplementation(async (_session, _messages, onChunk) => {
      onChunk({ messages: [], status: 'running', content: 'Done' })
    })
    const refreshSessionData = vi.fn().mockRejectedValue(new Error('runtime state failed'))
    const setMessages = vi.fn()
    const setRuntime = vi.fn()

    const result = await sendChatTurn({
      messages: [userMessage],
      preferences: { streaming: true, reduceMotion: false },
      refreshSessionData,
      sendChat,
      session,
      setMessages,
      setRuntime,
      streamChat,
    })

    expect(sendChat).not.toHaveBeenCalled()
    expect(streamChat).toHaveBeenCalledTimes(1)
    expect(refreshSessionData).toHaveBeenCalledTimes(1)
    expect(result).toEqual({ error: 'runtime state failed' })
  })

  it('falls back to standard chat when streaming fails before producing a chunk', async () => {
    const sendChat = vi.fn().mockResolvedValue(assistantResponse)
    const streamChat = vi.fn().mockRejectedValue(new Error('stream unavailable'))
    const refreshSessionData = vi.fn()
    const setMessages = vi.fn()
    const setRuntime = vi.fn()

    const result = await sendChatTurn({
      messages: [userMessage],
      preferences: { streaming: true, reduceMotion: false },
      refreshSessionData,
      sendChat,
      session,
      setMessages,
      setRuntime,
      streamChat,
    })

    expect(sendChat).toHaveBeenCalledTimes(1)
    expect(setMessages).toHaveBeenCalledWith(assistantResponse.messages)
    expect(result).toEqual({ error: 'Streaming failed. Retried with standard chat.' })
  })

  it('does not issue a second chat request when standard chat fails', async () => {
    const sendChat = vi.fn().mockRejectedValue(new Error('chat failed'))
    const streamChat = vi.fn()
    const refreshSessionData = vi.fn()
    const setMessages = vi.fn()
    const setRuntime = vi.fn()

    const result = await sendChatTurn({
      messages: [userMessage],
      preferences: { streaming: false, reduceMotion: false },
      refreshSessionData,
      sendChat,
      session,
      setMessages,
      setRuntime,
      streamChat,
    })

    expect(sendChat).toHaveBeenCalledTimes(1)
    expect(streamChat).not.toHaveBeenCalled()
    expect(result).toEqual({ error: 'chat failed' })
  })
})
