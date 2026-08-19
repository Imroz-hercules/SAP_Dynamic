import React, { useState } from 'react'
import { WaterSystemLayout } from '@/components/hercules-sfms/WaterSystemLayout'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { 
  Plus, 
  Trash2,
  Eye,
  EyeOff,
  RefreshCw,
  Lock,
  User as UserIcon,
  ShieldAlert,
  ChevronDown
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { useToast } from '@/hooks/use-toast'
import { LoginModal } from '@/components/LoginModal'
import { useTheme } from '@/contexts/ThemeContext'

// Types
interface UserInfo {
  id: number
  username: string
  email: string
  full_name: string
  roles: string[]
  is_active: boolean
  created_at: string | null
}

interface CurrentUser {
  id: number
  username: string
  roles: string[]
  permissions: Record<string, boolean>
}

// Available roles
const AVAILABLE_ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'operator', label: 'Operator' },
  { value: 'milling_operator', label: 'Milling Operator' },
  { value: 'packing_operator', label: 'Packing Operator' },
]

export function UserManagement() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const { theme } = useTheme()
  
  // State
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedUser, setSelectedUser] = useState<UserInfo | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [showRoleDropdown, setShowRoleDropdown] = useState(false)
  
  // Form state
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  
  // Fetch current user
  const { data: currentUserData, isLoading: isLoadingUser } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    retry: false
  })
  
  const currentUser: CurrentUser | null = currentUserData?.user || null
  const isAdmin = currentUser?.roles?.includes('admin') || false
  
  // Fetch all users (admin only)
  const { data: usersData, isLoading: isLoadingUsers } = useQuery({
    queryKey: ['/api/auth/users'],
    queryFn: () => apiRequest('GET', '/api/auth/users'),
    enabled: isAdmin,
    retry: false
  })
  
  const users: UserInfo[] = usersData?.users || []
  
  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: (userData: { username: string; password: string; email: string; roles: string[] }) => 
      apiRequest('POST', '/api/auth/users', userData),
    onSuccess: () => {
      toast({
        title: '✅ User Created',
        description: 'New user has been created successfully.',
        duration: 3000
      })
      resetForm()
      queryClient.invalidateQueries({ queryKey: ['/api/auth/users'] })
    },
    onError: (error: any) => {
      toast({
        title: '❌ Error',
        description: error?.message || 'Failed to create user',
        variant: 'destructive',
        duration: 5000
      })
    }
  })
  
  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: number) => 
      apiRequest('DELETE', `/api/auth/users/${userId}`),
    onSuccess: () => {
      toast({
        title: '✅ User Deleted',
        description: 'User has been deleted successfully.',
        duration: 3000
      })
      queryClient.invalidateQueries({ queryKey: ['/api/auth/users'] })
    },
    onError: (error: any) => {
      toast({
        title: '❌ Error',
        description: error?.message || 'Failed to delete user',
        variant: 'destructive',
        duration: 5000
      })
    }
  })
  
  // Reset form
  const resetForm = () => {
    setUsername('')
    setPassword('')
    setSelectedRole('')
    setShowPassword(false)
  }
  
  // Handle create user
  const handleCreateUser = () => {
    if (!username || !password) {
      toast({
        title: '⚠️ Validation Error',
        description: 'Username and password are required.',
        variant: 'destructive',
        duration: 3000
      })
      return
    }
    
    createUserMutation.mutate({
      username: username,
      password: password,
      email: `${username.toLowerCase().replace(/\s+/g, '')}@hercules.local`,
      roles: selectedRole ? [selectedRole] : []
    })
  }
  
  // Handle delete click
  const handleDeleteClick = (user: UserInfo) => {
    setSelectedUser(user)
    setShowDeleteDialog(true)
  }
  
  // Handle login success
  const handleLoginSuccess = () => {
    setShowLoginModal(false)
    queryClient.invalidateQueries({ queryKey: ['/api/auth/me'] })
    queryClient.invalidateQueries({ queryKey: ['/api/auth/users'] })
  }
  
  // Get primary role for display
  const getPrimaryRole = (userRoles: string[] | undefined): string => {
    if (!userRoles || userRoles.length === 0) return '-'
    return userRoles[0]
  }

  // Handle role selection
  const handleRoleSelect = (role: string) => {
    setSelectedRole(role)
    setShowRoleDropdown(false)
  }
  
  // Loading state
  if (isLoadingUser) {
    return (
      <WaterSystemLayout title="User Management" subtitle="Manage Users & Roles">
        <div className="flex items-center justify-center min-h-[60vh]">
          <RefreshCw className="w-8 h-8 animate-spin text-cyan-500" />
          <span className="ml-3 text-lg text-gray-900 dark:text-white">Loading...</span>
        </div>
      </WaterSystemLayout>
    )
  }
  
  // Not logged in
  if (!currentUser) {
    return (
      <WaterSystemLayout title="User Management" subtitle="Manage Users & Roles">
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card className="p-8 bg-white dark:bg-slate-800/90 border-yellow-500/50 shadow-lg">
            <div className="text-center">
              <Lock className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
              <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">Authentication Required</h2>
              <p className="text-gray-600 dark:text-slate-400 mb-4">Please log in to access User Management.</p>
              <Button onClick={() => setShowLoginModal(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white">
                <UserIcon className="w-4 h-4 mr-2" />
                Login
              </Button>
            </div>
          </Card>
        </div>
        
        <LoginModal
          isOpen={showLoginModal}
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={handleLoginSuccess}
        />
      </WaterSystemLayout>
    )
  }
  
  // Access denied for non-admin
  if (!isAdmin) {
    return (
      <WaterSystemLayout title="User Management" subtitle="Manage Users & Roles">
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card className="p-8 bg-white dark:bg-slate-800/90 border-red-500/50 shadow-lg">
            <div className="text-center">
              <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">Access Denied</h2>
              <p className="text-gray-600 dark:text-slate-400 mb-2">
                Only administrators can manage users.
              </p>
              <p className="text-sm text-gray-500 dark:text-slate-500">
                Current user: <span className="font-semibold text-gray-900 dark:text-white">{currentUser.username}</span>
              </p>
            </div>
          </Card>
        </div>
      </WaterSystemLayout>
    )
  }
  
  // Admin view - Full page layout
  return (
    <WaterSystemLayout title="User Management" subtitle="Manage Users & Roles">
      <div className="w-full min-h-[calc(100vh-120px)] p-6">
        {/* User Management Card - Full Width */}
        <Card className="w-full bg-white dark:bg-slate-800/90 border-gray-200 dark:border-slate-600 shadow-xl">
          <CardContent className="p-8">
            {/* Header */}
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-8 text-center">
              User Management
            </h1>
            
            {/* Form Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              {/* Username Input */}
              <div className="md:col-span-1">
                <Label htmlFor="username" className="text-sm text-gray-700 dark:text-slate-300 mb-2 block">
                  Username
                </Label>
                <Input
                  id="username"
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="bg-white dark:bg-slate-700 text-gray-900 dark:text-white border-gray-300 dark:border-slate-500 h-11
                             placeholder:text-gray-400 dark:placeholder:text-slate-400
                             focus:border-cyan-500 focus:ring-cyan-500"
                />
              </div>
              
              {/* Password Input */}
              <div className="md:col-span-1">
                <Label htmlFor="password" className="text-sm text-gray-700 dark:text-slate-300 mb-2 block">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-white dark:bg-slate-700 text-gray-900 dark:text-white border-gray-300 dark:border-slate-500 pr-10 h-11
                               placeholder:text-gray-400 dark:placeholder:text-slate-400
                               focus:border-cyan-500 focus:ring-cyan-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              {/* Role Dropdown - Custom */}
              <div className="md:col-span-1">
                <Label className="text-sm text-gray-700 dark:text-slate-300 mb-2 block">
                  Role
                </Label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowRoleDropdown(!showRoleDropdown)}
                    className="w-full h-11 px-3 bg-white dark:bg-slate-700 text-left border border-gray-300 dark:border-slate-500 rounded-md
                               flex items-center justify-between
                               hover:border-gray-400 dark:hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
                  >
                    <span className={selectedRole ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-slate-400'}>
                      {selectedRole ? AVAILABLE_ROLES.find(r => r.value === selectedRole)?.label : 'Select Role'}
                    </span>
                    <ChevronDown className={`w-4 h-4 text-gray-500 dark:text-slate-400 transition-transform ${showRoleDropdown ? 'rotate-180' : ''}`} />
                  </button>
                  
                  {/* Dropdown Menu */}
                  {showRoleDropdown && (
                    <div 
                      className="absolute z-50 w-full mt-1 rounded-md shadow-lg overflow-hidden border"
                      style={{ 
                        backgroundColor: theme === 'dark' ? '#374151' : '#ffffff',
                        borderColor: theme === 'dark' ? '#4b5563' : '#d1d5db'
                      }}
                    >
                      {AVAILABLE_ROLES.map((role) => (
                        <button
                          key={role.value}
                          type="button"
                          onClick={() => handleRoleSelect(role.value)}
                          style={{ 
                            backgroundColor: selectedRole === role.value 
                              ? (theme === 'dark' ? '#4b5563' : '#e5e7eb')
                              : (theme === 'dark' ? '#374151' : '#ffffff'),
                            color: theme === 'dark' ? '#ffffff' : '#000000'
                          }}
                          className={`w-full px-3 py-2 text-left transition-colors
                                     ${selectedRole === role.value ? 'font-medium' : ''}`}
                          onMouseEnter={(e) => {
                            if (selectedRole !== role.value) {
                              e.currentTarget.style.backgroundColor = theme === 'dark' ? '#4b5563' : '#f3f4f6'
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (selectedRole !== role.value) {
                              e.currentTarget.style.backgroundColor = theme === 'dark' ? '#374151' : '#ffffff'
                            }
                          }}
                        >
                          {role.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Add Button */}
              <div className="md:col-span-1 flex items-end">
                <Button
                  onClick={handleCreateUser}
                  disabled={createUserMutation.isPending}
                  className="h-11 w-11 rounded-full bg-cyan-600 hover:bg-cyan-700 dark:bg-cyan-600 dark:hover:bg-cyan-500 
                             text-white
                             border-2 border-cyan-500 dark:border-cyan-500
                             flex items-center justify-center"
                >
                  {createUserMutation.isPending ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Plus className="w-5 h-5" />
                  )}
                </Button>
              </div>
            </div>
            
            {/* Users Table */}
            <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-100 dark:bg-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700 border-b border-gray-200 dark:border-slate-600">
                    <TableHead className="text-gray-900 dark:text-white font-semibold w-20 py-3">ID</TableHead>
                    <TableHead className="text-gray-900 dark:text-white font-semibold py-3">Username</TableHead>
                    <TableHead className="text-gray-900 dark:text-white font-semibold text-center py-3">Role</TableHead>
                    <TableHead className="text-gray-900 dark:text-white font-semibold text-right w-24 py-3">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoadingUsers ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-8 bg-white dark:bg-slate-800">
                        <RefreshCw className="w-6 h-6 animate-spin text-cyan-500 mx-auto" />
                        <span className="block mt-2 text-gray-500 dark:text-slate-400">Loading users...</span>
                      </TableCell>
                    </TableRow>
                  ) : users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-8 text-gray-500 dark:text-slate-400 bg-white dark:bg-slate-800">
                        No users found. Create a new user above.
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((user, index) => (
                      <TableRow 
                        key={user.id} 
                        className={`border-b border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50
                                   ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-gray-50 dark:bg-slate-800/50'}`}
                      >
                        <TableCell className="text-gray-700 dark:text-slate-300 font-medium py-3">
                          {user.id}
                        </TableCell>
                        <TableCell className="text-gray-900 dark:text-white font-medium py-3">
                          {user.username}
                        </TableCell>
                        <TableCell className="text-center text-gray-700 dark:text-slate-300 py-3">
                          {getPrimaryRole(user.roles)}
                        </TableCell>
                        <TableCell className="text-right py-3">
                          <Button 
                            variant="ghost" 
                            size="icon"
                            className="hover:bg-red-50 dark:hover:bg-red-900/30 h-8 w-8 disabled:opacity-30"
                            onClick={() => handleDeleteClick(user)}
                            disabled={user.id === currentUser?.id}
                            title={user.id === currentUser?.id ? "Cannot delete yourself" : "Delete user"}
                          >
                            <Trash2 className="w-5 h-5 text-red-500 hover:text-red-600" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Click outside to close dropdown */}
      {showRoleDropdown && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowRoleDropdown(false)}
        />
      )}
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-600">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-gray-900 dark:text-white">Delete User</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-600 dark:text-slate-400">
              Are you sure you want to delete user <span className="font-semibold text-gray-900 dark:text-white">{selectedUser?.username}</span>? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => { setShowDeleteDialog(false); setSelectedUser(null); }}
              className="px-4 py-2 rounded-md font-medium transition-colors"
              style={{
                backgroundColor: theme === 'dark' ? '#334155' : '#e5e7eb',
                color: theme === 'dark' ? '#ffffff' : '#111827',
                border: theme === 'dark' ? '1px solid #475569' : '1px solid #9ca3af'
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deleteUserMutation.isPending}
              onClick={() => {
                if (selectedUser) {
                  deleteUserMutation.mutate(selectedUser.id)
                }
                setShowDeleteDialog(false)
                setSelectedUser(null)
              }}
              className="px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50"
              style={{
                backgroundColor: '#dc2626',
                color: '#ffffff',
                border: '1px solid #dc2626'
              }}
            >
              {deleteUserMutation.isPending ? 'Deleting...' : 'Delete'}
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* Login Modal */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </WaterSystemLayout>
  )
}

export default UserManagement
