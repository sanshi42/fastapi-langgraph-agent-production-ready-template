import type { StoredSession } from '../lib/storage'

const API_PREFIX = '/api/v1'

export type UserResponse = {
  id: number
  email: string
  username?: string | null
  token: Token
}

export type Token = {
  access_token: string
  token_type: string
  expires_at: string
}

export type SessionResponse = {
  session_id: string
  name: string
  token: Token
}

export type ChatMessage = {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export type ChatStatus = 'completed' | 'pending_approval' | 'running' | 'error'

export type ChatResponse = {
  messages: ChatMessage[]
  status: ChatStatus
  approval_id?: string | null
  tool_name?: string | null
  risk_reason?: string | null
  job_id?: string | null
}

export type RuntimeState = {
  session_id: string
  runtime: {
    approval_enabled: boolean
    worker_enabled: boolean
    workspace_root: string
  }
  tasks: RuntimeTask[]
  jobs: RuntimeJob[]
  crons: RuntimeCron[]
  teammates: RuntimeTeammate[]
  worktrees: RuntimeWorktree[]
  approvals: RuntimeApproval[]
}

export type RuntimeTask = {
  id: number | null
  subject: string
  description: string
  status: string
  owner?: string | null
  updated_at: string
}

export type RuntimeJob = {
  id: number | null
  kind: string
  status: string
  result?: string | null
  updated_at: string
}

export type RuntimeCron = {
  id: number | null
  cron: string
  prompt: string
  recurring: boolean
  status: string
  last_fired_at?: string | null
  updated_at: string
}

export type RuntimeTeammate = {
  id: number | null
  name: string
  role: string
  status: string
  updated_at: string
}

export type RuntimeWorktree = {
  id: number | null
  name: string
  path: string
  branch: string
  task_id?: number | null
  status: string
  updated_at: string
}

export type RuntimeApproval = {
  id: number | null
  tool_name: string
  tool_args: Record<string, unknown>
  risk_reason: string
  status: string
  decision?: string | null
  decided_at?: string | null
  created_at: string
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `request failed with ${response.status}`)
  }

  return (await response.json()) as T
}

function bearer(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` }
}

export async function registerUser(input: {
  email: string
  password: string
  username?: string
}): Promise<UserResponse> {
  return request<UserResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function loginUser(email: string, password: string): Promise<Token> {
  const body = new FormData()
  body.set('email', email)
  body.set('password', password)
  body.set('grant_type', 'password')

  return request<Token>('/auth/login', {
    method: 'POST',
    body,
  })
}

export async function listSessions(userToken: string): Promise<SessionResponse[]> {
  return request<SessionResponse[]>('/auth/sessions', {
    headers: bearer(userToken),
  })
}

export async function createSession(userToken: string): Promise<SessionResponse> {
  return request<SessionResponse>('/auth/session', {
    method: 'POST',
    headers: bearer(userToken),
  })
}

export async function getMessages(sessionToken: string): Promise<ChatResponse> {
  return request<ChatResponse>('/chatbot/messages', {
    headers: bearer(sessionToken),
  })
}

export async function sendChat(session: StoredSession, messages: ChatMessage[]): Promise<ChatResponse> {
  return request<ChatResponse>('/chatbot/chat', {
    method: 'POST',
    headers: bearer(session.token),
    body: JSON.stringify({ messages }),
  })
}

export async function getRuntimeState(sessionToken: string): Promise<RuntimeState> {
  return request<RuntimeState>('/runtime/state', {
    headers: bearer(sessionToken),
  })
}

export async function streamChat(
  session: StoredSession,
  messages: ChatMessage[],
  onChunk: (chunk: ChatResponse & { content?: string; done?: boolean }) => void,
): Promise<void> {
  const response = await fetch(`${API_PREFIX}/chatbot/chat/stream`, {
    method: 'POST',
    headers: {
      ...bearer(session.token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ messages }),
  })

  if (!response.ok || !response.body) {
    throw new Error(await response.text())
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const event of events) {
      const line = event
        .split('\n')
        .find((item) => item.startsWith('data:'))
        ?.replace(/^data:\s*/, '')

      if (!line) continue
      onChunk(JSON.parse(line) as ChatResponse & { content?: string; done?: boolean })
    }
  }
}
