import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { useToast } from '@/hooks/use-toast'
import { User, Lock, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

interface LoginFormProps {
  onLoginSuccess?: (user: any) => void
}

export function LoginForm({ onLoginSuccess }: LoginFormProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { toast } = useToast()
  const { login } = useAuth()

  const loginMutation = useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      apiRequest('POST', '/api/auth/login', credentials),
    onSuccess: (data) => {
      // Store token in localStorage
      localStorage.setItem('auth_token', data.token)
      
      // Update API client with token
      // This would typically be done in your API client configuration
      
      toast({
        title: '✅ Login successful!',
        description: `Welcome back, ${data.user.full_name || data.user.username}`,
        duration: 3000
      })
      
      // Update authentication context
      login(data.user)
      
      // Call onLoginSuccess if provided
      if (onLoginSuccess) {
        onLoginSuccess(data.user)
      }
      
      // Redirect to dashboard immediately
      window.location.href = '/sap-dashboard'
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (username && password) {
      loginMutation.mutate({ username, password })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
      <Card className="w-full max-w-md bg-slate-800/30 border-slate-700">
        <CardHeader className="text-center">
          <CardTitle className="text-white text-2xl flex items-center justify-center gap-2">
            <User className="h-6 w-6 text-cyan-400" />
            Hercules SFMS Login
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username" className="text-slate-300">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="bg-slate-700 border-slate-600 text-white mt-1"
                placeholder="Enter your username"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="password" className="text-slate-300">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-slate-700 border-slate-600 text-white mt-1"
                placeholder="Enter your password"
                required
              />
            </div>

            {loginMutation.isError && (
              <Alert className="border-red-500 bg-red-900/20">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <AlertDescription className="text-red-400">
                  {loginMutation.error?.message || 'Login failed'}
                </AlertDescription>
              </Alert>
            )}

            <Button
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full !bg-cyan-600 hover:!bg-cyan-700 !text-white"
            >
              {loginMutation.isPending ? (
                <>
                  <Lock className="h-4 w-4 mr-2 animate-spin" />
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

          <div className="mt-6 p-4 bg-slate-700/30 rounded-lg">
            <h3 className="text-slate-300 text-sm font-medium mb-2">Demo Credentials:</h3>
            <div className="text-xs text-slate-400 space-y-1">
              <p><strong>Admin:</strong> admin / admin123</p>
              <p><strong>Role:</strong> Full access to all features</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
