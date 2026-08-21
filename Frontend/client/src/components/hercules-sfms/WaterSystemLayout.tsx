import React, { useState, useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { User, Settings, LogOut, LayoutDashboard, Wifi, WifiOff, Signal, LogIn, Zap, Database, Server } from 'lucide-react'
import { Link } from 'wouter'
import { useTheme } from '@/contexts/ThemeContext'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { apiFetch, getApiUrl } from '@/lib/apiConfig'
import { LoginModal } from '@/components/LoginModal'
import futuristicNeonVideo from '@assets/20250725_1923_Futuristic Neon Serenity_simple_compose_01k112wfdvfd5v7jndrbpsca92_1753707277024.mp4'
import asmLogo from '@/assets/Asm_Logo.png'
import modernMillsLogo from '@/assets/modern_millslogo.png'



interface WaterSystemLayoutProps {
  children: React.ReactNode
  title: string
  subtitle: string
  onLogout?: () => void
}

interface UserInfo {
  id: number
  username: string
  email: string
  full_name: string
  roles: string[]
  permissions: Record<string, boolean>
}

export function WaterSystemLayout({ children, title, subtitle, onLogout }: WaterSystemLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'stable' | 'unstable' | 'disconnected'>('stable')
  const [currentDateTime, setCurrentDateTime] = useState(new Date())
  const [showLogoutModal, setShowLogoutModal] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const { theme } = useTheme()
  const queryClient = useQueryClient()

  // Fetch current user info - only if token exists
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  })

  const currentUser = userData as UserInfo | null

  // Fetch system mode (demo/production)
  const { data: systemModeData } = useQuery({
    queryKey: ['/api/system/mode'],
    queryFn: () => apiRequest('GET', '/api/system/mode'),
    refetchInterval: 10000
  })

  const isDemoMode = systemModeData?.demo_mode ?? true
  const isEmulatorRunning = systemModeData?.emulator_running ?? false

  // Update current date and time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDateTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  // Format date and time
  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  const formatTimezone = (date: Date) => {
    const offset = date.getTimezoneOffset()
    const hours = Math.abs(Math.floor(offset / 60))
    const minutes = Math.abs(offset % 60)
    const sign = offset <= 0 ? '+' : '-'
    return `${sign}${hours.toString().padStart(2, '0')}${minutes.toString().padStart(2, '0')}`
  }

  // Real VPN connection monitoring - checks SAP VPN connectivity
  useEffect(() => {
    const checkVpnConnection = async () => {
      try {
        const response = await apiFetch(getApiUrl('/api/vpn/status'), {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        })

        if (response.ok) {
          const data = await response.json()
          if (data.connected) {
            setConnectionStatus('stable')
          } else {
            setConnectionStatus('disconnected')
          }
        } else {
          // Server is responding but endpoint error - mark as unstable
          setConnectionStatus('unstable')
        }
      } catch (error) {
        // Network/fetch error - server unreachable
        console.warn('VPN status check failed:', error)
        setConnectionStatus('disconnected')
      }
    }

    // Initial check
    checkVpnConnection()

    // Poll every 30 seconds (not too frequent to avoid overhead)
    const interval = setInterval(checkVpnConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 
                    light:bg-white
                    text-white light:text-gray-900 flex relative overflow-hidden">
      {/* Futuristic Video Background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <video
          key={theme}
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover"
          style={{
            opacity: theme === 'dark' ? 0.7 : 0.8,
            filter: theme === 'light' ? 'brightness(0.8) contrast(1.2)' : 'none'
          }}
        >
          <source src={futuristicNeonVideo} type="video/mp4" />
        </video>
        {theme === 'dark' && (
          <div className="absolute inset-0 bg-gradient-to-b from-slate-950/30 via-slate-950/20 to-slate-950/40"></div>
        )}
        {theme === 'light' && (
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-gray-50/20"></div>
        )}
      </div>
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      {/* Main Content */}
      <div className="flex-1 flex flex-col relative z-10">

        {/* Top Header */}
        <header className="bg-slate-900/95 light:bg-white border-b border-slate-700/50 light:border-gray-200 backdrop-blur-sm 
                          px-6 py-4 flex items-center justify-between shadow-lg light:shadow-xl relative">
          <div>
            <h1 className="text-xl font-bold text-white light:text-gray-900">Hercules - SFMS</h1>
            <p className="text-sm text-slate-400 light:text-gray-600 whitespace-nowrap">Smart Factory Management System</p>
          </div>
          <div className="flex items-center space-x-4">
            {/* Date and Time */}
            <div className="text-xs text-slate-500 light:text-gray-500 border-r border-slate-700 light:border-gray-300 pr-4">
              <div>{formatDate(currentDateTime)}</div>
              {/* <div className="text-cyan-400 light:text-blue-600">{formatTime(currentDateTime)} {formatTimezone(currentDateTime)}</div> */}
              <div className="text-cyan-400 light:text-blue-600">{formatTime(currentDateTime)}</div>
            </div>

            {/* System Mode Indicator - Clickable when Demo Mode is active */}
            {isDemoMode ? (
              <Link href="/engineering?tab=demo">
                <div 
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg backdrop-blur-sm border cursor-pointer transition-all hover:scale-105 hover:shadow-lg bg-amber-500/10 border-amber-500/30 hover:bg-amber-500/20 hover:border-amber-500/50`}
                  title="Click to open Demo Mode settings"
                >
                  <div className="relative flex items-center">
                    <Zap className="h-4 w-4 text-amber-400" />
                    {isEmulatorRunning && (
                      <div className="absolute inset-0 rounded-full bg-amber-400/20 animate-ping" />
                    )}
                  </div>
                  <div className="text-xs">
                    <div className="font-medium text-amber-400">DEMO</div>
                    <div className="text-amber-400/60 text-[10px]">
                      {isEmulatorRunning ? '● Emulator Running' : '○ Emulator Stopped'}
                    </div>
                  </div>
                </div>
              </Link>
            ) : (
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg backdrop-blur-sm border bg-green-500/10 border-green-500/30">
                <div className="relative flex items-center">
                  <Database className="h-4 w-4 text-green-400" />
                </div>
                <div className="text-xs">
                  <div className="font-medium text-green-400">PRODUCTION</div>
                </div>
              </div>
            )}

            {/* Connection Status Indicator */}
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/50 light:bg-gray-100 
                            border border-slate-700/50 light:border-gray-200 backdrop-blur-sm">
              <div className="relative flex items-center">
                {connectionStatus === 'stable' ? (
                  <Signal className="h-4 w-4 text-green-400 light:text-green-600" />
                ) : connectionStatus === 'unstable' ? (
                  <Wifi className="h-4 w-4 text-yellow-400 light:text-yellow-600 animate-pulse" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-400 light:text-red-600" />
                )}

                {/* Animated connection pulse */}
                {connectionStatus === 'stable' && (
                  <div className="absolute inset-0 rounded-full bg-green-400/20 animate-ping" />
                )}
              </div>

              {/* Signal bars */}
              <div className="flex items-end space-x-0.5 h-3">
                {[1, 2, 3, 4].map((bar) => (
                  <div
                    key={bar}
                    className={`w-1 rounded-sm transition-all duration-500 ${connectionStatus === 'stable'
                        ? bar <= 4 ? 'bg-green-400 light:bg-green-600' : 'bg-slate-600 light:bg-gray-300'
                        : connectionStatus === 'unstable'
                          ? bar <= 2 ? 'bg-yellow-400 light:bg-yellow-600' : 'bg-slate-600 light:bg-gray-300'
                          : 'bg-red-400 light:bg-red-600'
                      }`}
                    style={{ height: `${Math.max(2, bar * 2)}px` }}
                  />
                ))}
              </div>

              {/* Status text */}
              <div className="text-xs">
                <div className={`font-medium ${connectionStatus === 'stable'
                    ? 'text-green-400 light:text-green-600'
                    : connectionStatus === 'unstable'
                      ? 'text-yellow-400 light:text-yellow-600'
                      : 'text-red-400 light:text-red-600'
                  }`}>
                  {connectionStatus === 'stable' ? 'STABLE' :
                    connectionStatus === 'unstable' ? 'UNSTABLE' : 'DISCONNECTED'}
                </div>
              </div>
            </div>

            {/* User Info */}
            {currentUser && (
              <div className="flex items-center space-x-3 text-sm">
                <span className="text-slate-300 light:text-gray-700">
                  {currentUser.roles?.length > 0 ? currentUser.roles[0].charAt(0).toUpperCase() + currentUser.roles[0].slice(1) : 'User'}
                </span>
                <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 
                                rounded-full flex items-center justify-center">
                  <User className="h-4 w-4 text-white" />
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <ThemeToggle />
              {/* Settings button - Only visible for admin users */}
              {currentUser?.roles?.includes('admin') && (
                <Link href="/engineering">
                  <button
                    className="p-2 rounded-lg bg-slate-800/50 light:bg-gray-100 hover:bg-slate-700/50 light:hover:bg-gray-200
                               text-slate-400 light:text-gray-600 hover:text-cyan-400 light:hover:text-blue-600 transition-colors"
                    title="Engineering settings"
                  >
                    <Settings className="h-4 w-4" />
                  </button>
                </Link>
              )}
              {/* Login/Logout button - Dynamic based on auth state */}
              {currentUser ? (
                <button
                  onClick={() => setShowLogoutModal(true)}
                  className="p-2 rounded-lg bg-slate-800/50 light:bg-gray-100 hover:bg-slate-700/50 light:hover:bg-gray-200
                             text-slate-400 light:text-gray-600 hover:text-red-400 light:hover:text-red-600 transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={() => setShowLoginModal(true)}
                  className="p-2 rounded-lg bg-slate-800/50 light:bg-gray-100 hover:bg-slate-700/50 light:hover:bg-gray-200
                             text-slate-400 light:text-gray-600 hover:text-cyan-400 light:hover:text-blue-600 transition-colors"
                  title="Login"
                >
                  <LogIn className="h-4 w-4" />
                </button>
              )}
            </div>



            {/* Company Logos */}
            <div className="ml-4 border-l border-slate-700 light:border-gray-300 pl-4 flex items-center space-x-4">
              {/* ASM Logo */}
              <img
                src={asmLogo}
                alt="ASM Logo"
                className="h-8 w-24 opacity-90 hover:opacity-100 transition-opacity duration-200"
                style={{
                  filter: theme === 'dark'
                    ? 'brightness(1.2) contrast(1.1) drop-shadow(0 0 6px rgba(0, 188, 212, 0.2))'
                    : 'brightness(0.9) contrast(1.2) drop-shadow(0 0 3px rgba(0, 0, 0, 0.1))'
                }}
              />

              {/* Modern Mills Logo */}
              <img 
                src={modernMillsLogo} 
                alt="Modern Mills Logo" 
                className="h-8 w-auto opacity-90 hover:opacity-100 transition-opacity duration-200"
                style={{
                  filter: theme === 'dark'
                    ? 'brightness(0) invert(1) drop-shadow(0 0 6px rgba(0, 188, 212, 0.2))'
                    : 'brightness(0.9) contrast(1.2) drop-shadow(0 0 3px rgba(0, 0, 0, 0.1))'
                }}
              />
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 relative smooth-scroll
                         bg-transparent light:bg-gray-50">

          {/* Background Grid Pattern - Hidden in light mode */}
          <div className="absolute inset-0 pointer-events-none opacity-5 light:opacity-0">
            <div className="w-full h-full"
              style={{
                backgroundImage: `linear-gradient(rgba(0,188,212,0.1) 1px, transparent 1px),
                                    linear-gradient(90deg, rgba(0,188,212,0.1) 1px, transparent 1px)`,
                backgroundSize: '50px 50px'
              }}>
            </div>
          </div>

          {/* Content Container */}
          <div className="relative z-10 max-w-full page-transition page-transition-enter-active">
            {children}
          </div>

          {/* Floating Particles - Hidden in light mode */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden light:hidden">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="absolute w-1 h-1 bg-cyan-400/30 rounded-full animate-float"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 10}s`,
                  animationDuration: `${15 + Math.random() * 10}s`
                }}
              />
            ))}
          </div>
        </main>

        {/* Logout Confirmation Modal */}
        {showLogoutModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center z-50 p-4" style={{ alignItems: 'flex-start', paddingTop: '10vh' }}>
            <div className="w-full max-w-md">
              <div className="bg-slate-800/95 border-slate-700 shadow-2xl backdrop-blur-md rounded-xl animate-in slide-in-from-top-4 duration-300">
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                      <LogOut className="h-5 w-5 text-red-600 dark:text-red-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">
                      Confirm Logout
                    </h3>
                  </div>

                  <p className="text-slate-300 mb-6 text-base leading-relaxed">
                    Are you sure you want to logout? You'll need to login again to access admin features.
                  </p>

                  <div className="flex gap-3 justify-end">
                    <button
                      onClick={() => setShowLogoutModal(false)}
                      className="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors duration-200"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        setShowLogoutModal(false)
                        if (onLogout) {
                          onLogout()
                        } else {
                          // Default logout behavior
                          localStorage.removeItem('auth_token')
                          window.location.reload()
                        }
                      }}
                      className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors duration-200 flex items-center gap-2"
                    >
                      <LogOut className="h-4 w-4" />
                      Logout
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Login Modal */}
        <LoginModal
          isOpen={showLoginModal}
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={() => {
            setShowLoginModal(false)
            queryClient.invalidateQueries({ queryKey: ['/api/auth/me'] })
          }}
        />

      </div>
    </div>
  );
}