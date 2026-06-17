export type StoredSession = {
  id: string
  name: string
  token: string
}

export type Preferences = {
  reduceMotion: boolean
  streaming: boolean
}

const STORAGE_PREFIX = 'my-agent:v1'
const USER_TOKEN_KEY = `${STORAGE_PREFIX}:user-token`
const ACTIVE_SESSION_KEY = `${STORAGE_PREFIX}:active-session`
const PREFERENCES_KEY = `${STORAGE_PREFIX}:preferences`

export const defaultPreferences: Preferences = {
  reduceMotion: false,
  streaming: true,
}

export function readUserToken(): string {
  return localStorage.getItem(USER_TOKEN_KEY) ?? ''
}

export function writeUserToken(token: string): void {
  localStorage.setItem(USER_TOKEN_KEY, token)
}

export function readActiveSession(): StoredSession | null {
  const raw = localStorage.getItem(ACTIVE_SESSION_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as StoredSession
  } catch {
    localStorage.removeItem(ACTIVE_SESSION_KEY)
    return null
  }
}

export function writeActiveSession(session: StoredSession): void {
  localStorage.setItem(ACTIVE_SESSION_KEY, JSON.stringify(session))
}

export function readPreferences(): Preferences {
  const raw = localStorage.getItem(PREFERENCES_KEY)
  if (!raw) return defaultPreferences

  try {
    return { ...defaultPreferences, ...(JSON.parse(raw) as Partial<Preferences>) }
  } catch {
    localStorage.removeItem(PREFERENCES_KEY)
    return defaultPreferences
  }
}

export function writePreferences(preferences: Preferences): void {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences))
}

export function clearStoredAuth(): void {
  localStorage.removeItem(USER_TOKEN_KEY)
  localStorage.removeItem(ACTIVE_SESSION_KEY)
}
