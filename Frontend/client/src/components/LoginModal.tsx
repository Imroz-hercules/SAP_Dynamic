import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { useToast } from '@/hooks/use-toast'
import { User, Lock, AlertCircle, X, Eye, EyeOff } from 'lucide-react'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
  onLoginSuccess: (user: any) => void
}

export function LoginModal({ isOpen, onClose, onLoginSuccess }: LoginModalProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const loginMutation = useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      apiRequest('POST', '/api/auth/login', credentials),
    onSuccess: (data) => {
      localStorage.setItem('auth_token', data.token)
      toast({
        title: '✅ Login successful!',
        description: `Welcome back, ${data.user.full_name || data.user.username}`,
        duration: 3000
      })
      onLoginSuccess(data.user)
      handleClose()
    },
    onError: (error: any) => {
      toast({
        title: '❌ Login failed',
        description: error?.message || 'Invalid username or password',
        duration: 5000,
        variant: 'destructive'
      })
    }
  })

  const handleClose = () => {
    setUsername('')
    setPassword('')
    setShowPassword(false)
    onClose()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (username && password) {
      loginMutation.mutate({ username, password })
    }
  }

  const handleQuickLogin = (type: 'admin' | 'manager' | 'user') => {
    const credentials = {
      admin: { username: 'admin', password: 'admin123' },
      manager: { username: 'manager', password: 'manager123' },
      user: { username: 'user', password: 'user123' }
    }
    
    const creds = credentials[type]
    setUsername(creds.username)
    setPassword(creds.password)
    loginMutation.mutate(creds)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center z-50 p-4" style={{ alignItems: 'flex-start', paddingTop: '10vh' }}>
      <div className="w-full max-w-md">
        <Card className="bg-slate-800/95 border-slate-700 shadow-2xl backdrop-blur-md animate-in slide-in-from-top-4 duration-300">
          <CardHeader className="relative">
            <Button
              onClick={handleClose}
              variant="ghost"
              size="sm"
              className="absolute right-4 top-4 h-8 w-8 p-0 text-slate-400 hover:text-white hover:bg-slate-700"
            >
              <X className="h-4 w-4" />
            </Button>
            <CardTitle className="text-white text-2xl flex items-center justify-center gap-3 pr-8">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center">
                <User className="h-5 w-5 text-white" />
              </div>
              Hercules SFMS
            </CardTitle>
            <p className="text-slate-400 text-center text-sm">
              Smart Factory Management System
            </p>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="username" className="text-slate-300 text-sm font-medium">
                  Username
                </Label>
                <div className="relative mt-1">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="bg-slate-700/50 border-slate-600 text-white pl-10 focus:border-cyan-500 focus:ring-cyan-500/20"
                    placeholder="Enter your username"
                    required
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="password" className="text-slate-300 text-sm font-medium">
                  Password
                </Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-slate-700/50 border-slate-600 text-white pl-10 pr-10 focus:border-cyan-500 focus:ring-cyan-500/20"
                    placeholder="Enter your password"
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0 text-slate-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  </Button>
                </div>
              </div>

              {loginMutation.isError && (
                <Alert className="border-red-500/50 bg-red-900/20">
                  <AlertCircle className="h-4 w-4 text-red-400" />
                  <AlertDescription className="text-red-400">
                    {loginMutation.error?.message || 'Login failed'}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                disabled={loginMutation.isPending || !username || !password}
                className="w-full !bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 !text-white font-medium py-2.5 transition-all duration-200"
              >
                {loginMutation.isPending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4 mr-2" />
                    Sign In
                  </>
                )}
              </Button>
            </form>

            {/* Quick Login Options */}
            <div className="space-y-3">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-600" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-slate-800 text-slate-400">Quick Login</span>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-2">
                <Button
                  onClick={() => handleQuickLogin('admin')}
                  variant="outline"
                  size="sm"
                  className="!border-cyan-500/30 !text-cyan-400 hover:!bg-cyan-500/10 hover:!border-cyan-500 text-xs"
                >
                  Admin
                </Button>
                <Button
                  onClick={() => handleQuickLogin('manager')}
                  variant="outline"
                  size="sm"
                  className="!border-blue-500/30 !text-blue-400 hover:!bg-blue-500/10 hover:!border-blue-500 text-xs"
                >
                  Manager
                </Button>
                <Button
                  onClick={() => handleQuickLogin('user')}
                  variant="outline"
                  size="sm"
                  className="!border-green-500/30 !text-green-400 hover:!bg-green-500/10 hover:!border-green-500 text-xs"
                >
                  User
                </Button>
              </div>
            </div>

            {/* Demo Credentials */}
            <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/50">
              <h3 className="text-slate-300 text-sm font-medium mb-2 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-400" />
                Demo Credentials
              </h3>
              <div className="text-xs text-slate-400 space-y-1">
                <p><strong className="text-cyan-400">Admin:</strong> admin / admin123</p>
                <p><strong className="text-blue-400">Manager:</strong> manager / manager123</p>
                <p><strong className="text-green-400">User:</strong> user / user123</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
