import {
  Activity,
  Bot,
  Check,
  ChevronRight,
  Clock3,
  Gauge,
  GitBranch,
  LogOut,
  MessageSquare,
  Moon,
  Play,
  Plus,
  RefreshCw,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  createSession,
  getMessages,
  getRuntimeState,
  listSessions,
  loginUser,
  registerUser,
  sendChat,
  streamChat,
  type ChatMessage,
  type ChatResponse,
  type RuntimeState,
  type SessionResponse,
} from './api/client'
import {
  clearStoredAuth,
  readActiveSession,
  readPreferences,
  readUserToken,
  type Preferences,
  type StoredSession,
  writeActiveSession,
  writePreferences,
  writeUserToken,
} from './lib/storage'
import { sendChatTurn } from './lib/chatFlow'

type AuthMode = 'login' | 'register'
type View = 'console' | 'settings'

function toStoredSession(session: SessionResponse): StoredSession {
  return {
    id: session.session_id,
    name: session.name || 'Untitled session',
    token: session.token.access_token,
  }
}

function App() {
  const [userToken, setUserToken] = useState(readUserToken)
  const [session, setSession] = useState<StoredSession | null>(readActiveSession)
  const [sessions, setSessions] = useState<StoredSession[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [runtime, setRuntime] = useState<RuntimeState | null>(null)
  const [preferences, setPreferences] = useState<Preferences>(readPreferences)
  const [view, setView] = useState<View>('console')
  const [input, setInput] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState('')

  const pendingApproval = useMemo(() => {
    return runtime?.approvals.find((approval) => approval.status === 'pending') ?? null
  }, [runtime])

  useEffect(() => {
    document.documentElement.dataset.reduceMotion = preferences.reduceMotion ? 'true' : 'false'
    writePreferences(preferences)
  }, [preferences])

  useEffect(() => {
    if (!userToken) return

    async function run() {
      try {
        setError('')
        const existing = (await listSessions(userToken)).map(toStoredSession)
        if (existing.length === 0) {
          const created = toStoredSession(await createSession(userToken))
          setSessions([created])
          setSession(created)
          return
        }

        setSessions(existing)
        const active = readActiveSession()
        setSession(existing.find((item) => item.id === active?.id) ?? existing[0])
      } catch (err) {
        setError(errorMessage(err))
        clearStoredAuth()
        setUserToken('')
        setSession(null)
      }
    }

    void run()
  }, [userToken])

  const refreshSessionData = useCallback(async (activeSession = session) => {
    if (!activeSession) return

    try {
      const [history, state] = await Promise.all([
        getMessages(activeSession.token).catch(() => ({ messages: [], status: 'completed' }) satisfies ChatResponse),
        getRuntimeState(activeSession.token),
      ])
      setMessages(history.messages.filter((message) => message.role !== 'system'))
      setRuntime(state)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [session])

  useEffect(() => {
    if (!session) return

    writeActiveSession(session)
    queueMicrotask(() => {
      void refreshSessionData(session)
    })
  }, [refreshSessionData, session])

  async function handleAuth(input: { mode: AuthMode; email: string; password: string; username: string }) {
    setIsBusy(true)
    setError('')
    try {
      const token =
        input.mode === 'register'
          ? (await registerUser({ email: input.email, password: input.password, username: input.username })).token
          : await loginUser(input.email, input.password)
      writeUserToken(token.access_token)
      setUserToken(token.access_token)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setIsBusy(false)
    }
  }

  async function handleCreateSession() {
    if (!userToken) return

    setIsBusy(true)
    try {
      const created = toStoredSession(await createSession(userToken))
      setSessions((current) => [created, ...current])
      setSession(created)
      setMessages([])
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setIsBusy(false)
    }
  }

  async function handleSend(content = input.trim()) {
    if (!session || !content) return

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content }]
    setMessages(nextMessages)
    setInput('')
    setIsBusy(true)
    setError('')

    const result = await sendChatTurn({
      messages: nextMessages,
      preferences,
      refreshSessionData,
      sendChat,
      session,
      setMessages,
      setRuntime,
      streamChat,
    })
    if (result.error) {
      setError(result.error)
    }
    setIsBusy(false)
  }

  function handleLogout() {
    clearStoredAuth()
    setUserToken('')
    setSession(null)
    setSessions([])
    setMessages([])
    setRuntime(null)
  }

  if (!userToken) {
    return <AuthScreen busy={isBusy} error={error} onSubmit={handleAuth} />
  }

  return (
    <main className="workspace-root min-h-dvh overflow-hidden text-[var(--color-foreground)]">
      <div className="console-shell">
        <Sidebar
          activeSession={session}
          busy={isBusy}
          sessions={sessions}
          view={view}
          onCreateSession={handleCreateSession}
          onSelectSession={setSession}
          onViewChange={setView}
        />

        {view === 'settings' ? (
          <SettingsView
            preferences={preferences}
            runtime={runtime}
            onLogout={handleLogout}
            onPreferencesChange={setPreferences}
            onRefresh={() => void refreshSessionData()}
          />
        ) : (
          <ChatWorkspace
            busy={isBusy}
            error={error}
            input={input}
            messages={messages}
            pendingApproval={pendingApproval}
            runtime={runtime}
            session={session}
            onApproval={(decision) => void handleSend(decision)}
            onInputChange={setInput}
            onRefresh={() => void refreshSessionData()}
            onSend={() => void handleSend()}
          />
        )}
      </div>
    </main>
  )
}

function AuthScreen({
  busy,
  error,
  onSubmit,
}: {
  busy: boolean
  error: string
  onSubmit: (input: { mode: AuthMode; email: string; password: string; username: string }) => void
}) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    onSubmit({ mode, email, password, username })
  }

  return (
    <main className="auth-screen">
      <section className="auth-card glass-panel">
        <div className="brand-mark">
          <Bot aria-hidden="true" />
        </div>
        <p className="eyebrow">Agent Workspace Console</p>
        <h1>进入你的 Agent 工作台</h1>
        <p className="auth-copy">
          登录后选择 session，使用流式聊天、工具审批和 runtime 状态栏管理 Agent 工作。
        </p>

        <form className="auth-form" onSubmit={submit}>
          <label>
            Email
            <input
              autoComplete="email"
              inputMode="email"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          {mode === 'register' ? (
            <label>
              Username
              <input
                autoComplete="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
          ) : null}
          <label>
            Password
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {mode === 'register' ? (
            <p className="helper">密码需包含大小写字母、数字和特殊字符。</p>
          ) : null}
          {error ? <p className="form-error">服务暂时不可用，请稍后再试。</p> : null}
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? <RefreshCw className="spin" aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}
            {mode === 'login' ? '登录' : '注册并进入'}
          </button>
        </form>

        <button className="ghost-button" type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? '没有账号？创建一个' : '已有账号？返回登录'}
        </button>
      </section>
    </main>
  )
}

function Sidebar({
  activeSession,
  busy,
  sessions,
  view,
  onCreateSession,
  onSelectSession,
  onViewChange,
}: {
  activeSession: StoredSession | null
  busy: boolean
  sessions: StoredSession[]
  view: View
  onCreateSession: () => void
  onSelectSession: (session: StoredSession) => void
  onViewChange: (view: View) => void
}) {
  return (
    <aside className="sidebar glass-panel" aria-label="Console navigation">
      <div className="sidebar-brand">
        <div className="brand-mark small">
          <Bot aria-hidden="true" />
        </div>
        <div>
          <strong>my-agent</strong>
          <span>Workspace Console</span>
        </div>
      </div>

      <nav className="nav-stack" aria-label="Primary">
        <button className={view === 'console' ? 'nav-item active' : 'nav-item'} onClick={() => onViewChange('console')}>
          <MessageSquare aria-hidden="true" />
          Console
        </button>
        <button className={view === 'settings' ? 'nav-item active' : 'nav-item'} onClick={() => onViewChange('settings')}>
          <Settings aria-hidden="true" />
          Settings
        </button>
      </nav>

      <div className="sessions-header">
        <span>Sessions</span>
        <button aria-label="Create session" className="icon-button" disabled={busy} onClick={onCreateSession}>
          <Plus aria-hidden="true" />
        </button>
      </div>
      <div className="session-list">
        {sessions.map((item) => (
          <button
            className={item.id === activeSession?.id ? 'session-pill active' : 'session-pill'}
            key={item.id}
            onClick={() => onSelectSession(item)}
          >
            <span>{item.name}</span>
            <ChevronRight aria-hidden="true" />
          </button>
        ))}
      </div>
    </aside>
  )
}

function ChatWorkspace({
  busy,
  error,
  input,
  messages,
  pendingApproval,
  runtime,
  session,
  onApproval,
  onInputChange,
  onRefresh,
  onSend,
}: {
  busy: boolean
  error: string
  input: string
  messages: ChatMessage[]
  pendingApproval: RuntimeState['approvals'][number] | null
  runtime: RuntimeState | null
  session: StoredSession | null
  onApproval: (decision: string) => void
  onInputChange: (value: string) => void
  onRefresh: () => void
  onSend: () => void
}) {
  return (
    <>
      <section className="chat-panel glass-panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Active session</p>
            <h1>{session?.name ?? 'No session selected'}</h1>
          </div>
          <button className="icon-button" aria-label="Refresh session" onClick={onRefresh}>
            <RefreshCw aria-hidden="true" />
          </button>
        </header>

        <div className="message-list" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Sparkles aria-hidden="true" />
              <h2>开始一个 Agent 任务</h2>
              <p>描述你要完成的工作。需要审批的工具调用会出现在右侧状态栏。</p>
            </div>
          ) : (
            messages.map((message, index) => <MessageBubble key={`${message.role}-${index}`} message={message} />)
          )}
          {busy ? <div className="typing">Agent 正在处理...</div> : null}
        </div>

        {pendingApproval ? <ApprovalCard approval={pendingApproval} onApproval={onApproval} /> : null}
        {error ? <p className="form-error">{error}</p> : null}

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault()
            onSend()
          }}
        >
          <label className="sr-only" htmlFor="message">
            Message
          </label>
          <textarea
            id="message"
            placeholder="让 Agent 修改文件、运行检查、拆分任务..."
            rows={3}
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) onSend()
            }}
          />
          <button className="send-button" disabled={busy || !input.trim()} type="submit">
            <Send aria-hidden="true" />
            Send
          </button>
        </form>
      </section>

      <RuntimeRail runtime={runtime} />
    </>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={message.role === 'user' ? 'message user' : 'message assistant'}>
      <div className="message-role">{message.role === 'user' ? 'You' : 'Agent'}</div>
      <p>{message.content}</p>
    </article>
  )
}

function ApprovalCard({
  approval,
  onApproval,
}: {
  approval: RuntimeState['approvals'][number]
  onApproval: (decision: string) => void
}) {
  return (
    <section className="approval-card" role="alert">
      <div>
        <p className="eyebrow">Pending Approval</p>
        <h2>{approval.tool_name}</h2>
        <p>{approval.risk_reason}</p>
      </div>
      <div className="approval-actions">
        <button className="danger-button" onClick={() => onApproval('deny')} type="button">
          <X aria-hidden="true" />
          Reject
        </button>
        <button className="primary-button" onClick={() => onApproval('approve')} type="button">
          <Check aria-hidden="true" />
          Approve
        </button>
      </div>
    </section>
  )
}

function RuntimeRail({ runtime }: { runtime: RuntimeState | null }) {
  return (
    <aside className="runtime-rail glass-panel" aria-label="Runtime state">
      <header className="rail-header">
        <p className="eyebrow">Runtime</p>
        <h2>Session state</h2>
      </header>
      <div className="metric-grid">
        <Metric icon={<ShieldCheck />} label="Approvals" value={runtime?.approvals.length ?? 0} />
        <Metric icon={<Play />} label="Jobs" value={runtime?.jobs.length ?? 0} />
        <Metric icon={<Activity />} label="Tasks" value={runtime?.tasks.length ?? 0} />
        <Metric icon={<GitBranch />} label="Worktrees" value={runtime?.worktrees.length ?? 0} />
      </div>
      <StateSection
        empty="No pending approvals"
        icon={<ShieldCheck />}
        items={runtime?.approvals.filter((item) => item.status === 'pending').map((item) => item.tool_name) ?? []}
        title="Pending Approval"
      />
      <StateSection
        empty="No runtime jobs"
        icon={<Clock3 />}
        items={runtime?.jobs.map((item) => `${item.kind} · ${item.status}`) ?? []}
        title="Runtime Jobs"
      />
      <StateSection
        empty="No active tasks"
        icon={<Gauge />}
        items={runtime?.tasks.map((item) => `${item.subject} · ${item.status}`) ?? []}
        title="Task Board"
      />
      <StateSection
        empty="No teammates"
        icon={<Users />}
        items={runtime?.teammates.map((item) => `${item.name} · ${item.status}`) ?? []}
        title="Teammates"
      />
    </aside>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="metric-card">
      <span aria-hidden="true">{icon}</span>
      <strong>{value}</strong>
      <small>{label}</small>
    </div>
  )
}

function StateSection({
  empty,
  icon,
  items,
  title,
}: {
  empty: string
  icon: React.ReactNode
  items: string[]
  title: string
}) {
  return (
    <section className="state-section">
      <h3>
        <span aria-hidden="true">{icon}</span>
        {title}
      </h3>
      {items.length ? (
        <ul>
          {items.slice(0, 4).map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{empty}</p>
      )}
    </section>
  )
}

function SettingsView({
  preferences,
  runtime,
  onLogout,
  onPreferencesChange,
  onRefresh,
}: {
  preferences: Preferences
  runtime: RuntimeState | null
  onLogout: () => void
  onPreferencesChange: (preferences: Preferences) => void
  onRefresh: () => void
}) {
  return (
    <section className="settings-panel glass-panel">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Console preferences</h1>
        </div>
        <button className="icon-button" aria-label="Refresh runtime state" onClick={onRefresh}>
          <RefreshCw aria-hidden="true" />
        </button>
      </header>

      <div className="settings-grid">
        <PreferenceSwitch
          checked={preferences.streaming}
          description="默认通过 SSE 展示模型输出；失败时回退普通聊天。"
          icon={<MessageSquare />}
          label="Streaming responses"
          onChange={(streaming) => onPreferencesChange({ ...preferences, streaming })}
        />
        <PreferenceSwitch
          checked={preferences.reduceMotion}
          description="减少玻璃层过渡和环境光移动，适合容易被动效干扰的用户。"
          icon={<Moon />}
          label="Reduced motion"
          onChange={(reduceMotion) => onPreferencesChange({ ...preferences, reduceMotion })}
        />
      </div>

      <section className="runtime-config">
        <h2>Runtime visibility</h2>
        <dl>
          <div>
            <dt>Tool approval</dt>
            <dd>{runtime?.runtime.approval_enabled ? 'enabled' : 'disabled'}</dd>
          </div>
          <div>
            <dt>Worker</dt>
            <dd>{runtime?.runtime.worker_enabled ? 'enabled' : 'disabled'}</dd>
          </div>
          <div>
            <dt>Workspace root</dt>
            <dd>{runtime?.runtime.workspace_root ?? 'not loaded'}</dd>
          </div>
        </dl>
      </section>

      <button className="danger-button logout-button" onClick={onLogout} type="button">
        <LogOut aria-hidden="true" />
        Logout
      </button>
    </section>
  )
}

function PreferenceSwitch({
  checked,
  description,
  icon,
  label,
  onChange,
}: {
  checked: boolean
  description: string
  icon: React.ReactNode
  label: string
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="preference-card">
      <span aria-hidden="true">{icon}</span>
      <span>
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
      <input checked={checked} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
    </label>
  )
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Unknown error'
}

export default App
