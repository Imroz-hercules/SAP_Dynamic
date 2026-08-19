import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'

interface User {
  id: number
  username: string
  email: string
  full_name: string
  roles: string[]
  permissions: Record<string, boolean>
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  /** @deprecated Prefer isAuthResolved — v5 isLoading can be misleading with select() */
  isLoading: boolean
  /** False only while we have a token and /api/auth/me has not finished (success or error) */
  isAuthResolved: boolean
  /** True when /me failed with 401 but token not yet cleared (AuthGuard should wait, not mount the app) */
  isSessionInvalid: boolean
  login: (user: User) => void
  logout: () => void
  hasPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const queryClient = useQueryClient()

  const hasStoredToken = typeof window !== 'undefined' && !!localStorage.getItem('auth_token')

  // Session check: do not refetch on every layout mount (Sidebar, WaterSystemLayout, etc.) — avoids 401 spam
  const { data: userData, isLoading, status, isError, error } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: hasStoredToken,
    refetchOnMount: false,
    refetchOnReconnect: false,
  })

  const isAuthResolved =
    !hasStoredToken || status === 'success' || status === 'error'

  const msg = isError && error ? String((error as Error).message || '') : ''
  const wasUnauthorized =
    msg.startsWith('401:') || /\b401\b/.test(msg)
  const isSessionInvalid =
    isAuthResolved && wasUnauthorized && !!localStorage.getItem('auth_token')

  useEffect(() => {
    if (userData) {
      setUser(userData)
      setIsAuthenticated(true)
    } else {
      setUser(null)
      setIsAuthenticated(false)
    }
  }, [userData])

  // Expired or invalid JWT: stop calling APIs with bad Bearer token and send user to login
  useEffect(() => {
    if (!isError || !error) return
    const errMsg = String((error as Error).message || '')
    const unauthorized = errMsg.startsWith('401:') || /\b401\b/.test(errMsg)
    if (!unauthorized || !localStorage.getItem('auth_token')) return
    localStorage.removeItem('auth_token')
    queryClient.removeQueries({ queryKey: ['/api/auth/me'] })
    if (window.location.pathname !== '/auth') {
      window.location.replace('/auth')
    }
  }, [isError, error, queryClient])

  const login = (userData: User) => {
    setUser(userData)
    setIsAuthenticated(true)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    setIsAuthenticated(false)
    // Redirect to login page after logout
    window.location.href = '/auth'
  }

  const hasPermission = (permission: string): boolean => {
    return user?.permissions?.[permission] || false
  }

  const hasRole = (role: string): boolean => {
    return user?.roles?.includes(role) || false
  }

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    isAuthResolved,
    isSessionInvalid,
    login,
    logout,
    hasPermission,
    hasRole
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
