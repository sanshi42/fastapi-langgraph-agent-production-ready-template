import type {
  ChatMessage,
  ChatResponse,
  RuntimeState,
  sendChat,
  streamChat,
} from '../api/client'
import type { Preferences, StoredSession } from './storage'

type RuntimeApproval = RuntimeState['approvals'][number]

type SendChatTurnInput = {
  messages: ChatMessage[]
  preferences: Preferences
  refreshSessionData: (session: StoredSession) => Promise<void>
  sendChat: typeof sendChat
  session: StoredSession
  setMessages: (messages: ChatMessage[]) => void
  setRuntime: (updater: (current: RuntimeState | null) => RuntimeState | null) => void
  streamChat: typeof streamChat
}

type SendChatTurnResult = {
  error?: string
}

export async function sendChatTurn(input: SendChatTurnInput): Promise<SendChatTurnResult> {
  if (!input.preferences.streaming) {
    return sendStandardChat(input)
  }

  let streamed = false
  try {
    let assistantContent = ''
    await input.streamChat(input.session, input.messages, (chunk) => {
      streamed = true
      if (chunk.content) {
        assistantContent += chunk.content
        input.setMessages([...input.messages, { role: 'assistant', content: assistantContent }])
      }
      if (chunk.status === 'pending_approval') {
        input.setRuntime((current) => addPendingApproval(current, chunk))
      }
    })
  } catch (err) {
    if (streamed) return { error: errorMessage(err) }
    return retryWithStandardChat(input)
  }

  try {
    await input.refreshSessionData(input.session)
  } catch (err) {
    return { error: errorMessage(err) }
  }

  return {}
}

async function sendStandardChat(input: SendChatTurnInput): Promise<SendChatTurnResult> {
  try {
    const response = await input.sendChat(input.session, input.messages)
    input.setMessages(withoutSystemMessages(response.messages))
    await input.refreshSessionData(input.session)
    return {}
  } catch (err) {
    return { error: errorMessage(err) }
  }
}

async function retryWithStandardChat(input: SendChatTurnInput): Promise<SendChatTurnResult> {
  try {
    const response = await input.sendChat(input.session, input.messages)
    input.setMessages(withoutSystemMessages(response.messages))
    return { error: 'Streaming failed. Retried with standard chat.' }
  } catch (err) {
    return { error: errorMessage(err) }
  }
}

function withoutSystemMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.filter((message) => message.role !== 'system')
}

function addPendingApproval(
  current: RuntimeState | null,
  chunk: ChatResponse & { content?: string; done?: boolean },
): RuntimeState | null {
  if (!current) return current

  const approval: RuntimeApproval = {
    id: parseApprovalId(chunk.approval_id),
    tool_name: chunk.tool_name ?? 'tool',
    tool_args: {},
    risk_reason: chunk.risk_reason ?? 'approval required',
    status: 'pending',
    created_at: new Date().toISOString(),
  }
  return {
    ...current,
    approvals: [approval, ...current.approvals],
  }
}

function parseApprovalId(value?: string | null): number | null {
  if (!value) return null
  const match = value.match(/\d+/)
  return match ? Number(match[0]) : null
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Unknown error'
}
