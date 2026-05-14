import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

function readStoredUser() {
  const rawUser = localStorage.getItem('user')
  if (!rawUser) {
    return null
  }
  try {
    return JSON.parse(rawUser)
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(readStoredUser())

  const login = (payload) => {
    localStorage.setItem('token', payload.access_token)
    localStorage.setItem('user', JSON.stringify(payload.user))
    setToken(payload.access_token)
    setUser(payload.user)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ token, user, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
