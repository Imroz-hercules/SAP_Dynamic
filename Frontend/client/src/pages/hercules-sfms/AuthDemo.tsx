import React from 'react'
import { WaterSystemLayout } from '@/components/hercules-sfms/WaterSystemLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAuth } from '@/contexts/AuthContext'
import { LoginForm } from '@/components/LoginForm'
import { 
  User, 
  Shield, 
  Settings, 
  LogOut,
  CheckCircle,
  XCircle,
  Info
} from 'lucide-react'

export function AuthDemo() {
  const { user, isAuthenticated, logout, hasPermission, hasRole } = useAuth()

  if (!isAuthenticated) {
    return <LoginForm onLoginSuccess={() => {}} />
  }

  return (
    <WaterSystemLayout 
      title="Authentication Demo" 
      subtitle="Role-based access control demonstration"
    >
      <div className="p-6 space-y-6 max-w-4xl mx-auto">
        
        {/* User Info Card */}
        <Card className="bg-slate-800/30 light:bg-white border-slate-700 light:border-gray-200 light:shadow-md">
          <CardHeader>
            <CardTitle className="text-white light:text-gray-900 flex items-center gap-3">
              <User className="h-6 w-6 text-cyan-400 light:text-blue-600" />
              Current User Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-slate-300 light:text-gray-700 text-sm font-medium mb-2">User Details</h3>
                <div className="space-y-1 text-sm">
                  <p className="text-white light:text-gray-900">
                    <strong>Name:</strong> {user?.full_name || 'N/A'}
                  </p>
                  <p className="text-white light:text-gray-900">
                    <strong>Username:</strong> {user?.username}
                  </p>
                  <p className="text-white light:text-gray-900">
                    <strong>Email:</strong> {user?.email}
                  </p>
                </div>
              </div>
              <div>
                <h3 className="text-slate-300 light:text-gray-700 text-sm font-medium mb-2">Roles</h3>
                <div className="flex flex-wrap gap-2">
                  {user?.roles?.map((role) => (
                    <span
                      key={role}
                      className="px-2 py-1 bg-cyan-900/30 text-cyan-400 border border-cyan-500/30 rounded text-xs font-medium"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button
                onClick={logout}
                variant="outline"
                className="!border-red-600 !text-red-600 hover:!bg-red-600 hover:!text-white"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Permissions Card */}
        <Card className="bg-slate-800/30 light:bg-white border-slate-700 light:border-gray-200 light:shadow-md">
          <CardHeader>
            <CardTitle className="text-white light:text-gray-900 flex items-center gap-3">
              <Shield className="h-6 w-6 text-cyan-400 light:text-blue-600" />
              Permission Matrix
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-slate-300 light:text-gray-700 text-sm font-medium mb-3">Sync Interval Permissions</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-white light:text-gray-900 text-sm">View Sync Interval</span>
                    {hasPermission('view_sync_interval') ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white light:text-gray-900 text-sm">Change Sync Interval</span>
                    {hasPermission('change_sync_interval') ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-slate-300 light:text-gray-700 text-sm font-medium mb-3">System Permissions</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-white light:text-gray-900 text-sm">View All Data</span>
                    {hasPermission('view_all_data') ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white light:text-gray-900 text-sm">Manage Users</span>
                    {hasPermission('manage_users') ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white light:text-gray-900 text-sm">System Admin</span>
                    {hasPermission('system_admin') ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Role Information */}
        <Card className="bg-slate-800/30 light:bg-white border-slate-700 light:border-gray-200 light:shadow-md">
          <CardHeader>
            <CardTitle className="text-white light:text-gray-900 flex items-center gap-3">
              <Info className="h-6 w-6 text-cyan-400 light:text-blue-600" />
              Role-Based Access Control
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Alert className="border-blue-500 bg-blue-900/20">
                <Info className="h-4 w-4 text-blue-400" />
                <AlertDescription className="text-blue-400">
                  This system implements role-based access control for sync interval settings.
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4">
                  <h4 className="text-white light:text-gray-900 font-medium mb-2">Admin</h4>
                  <ul className="text-xs text-slate-300 light:text-gray-700 space-y-1">
                    <li>• Full system access</li>
                    <li>• Can modify sync intervals</li>
                    <li>• Can manage users</li>
                    <li>• Can view all data</li>
                  </ul>
                </div>
                
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4">
                  <h4 className="text-white light:text-gray-900 font-medium mb-2">Manager</h4>
                  <ul className="text-xs text-slate-300 light:text-gray-700 space-y-1">
                    <li>• Can modify sync intervals</li>
                    <li>• Can view all data</li>
                    <li>• Cannot manage users</li>
                    <li>• Limited admin access</li>
                  </ul>
                </div>
                
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4">
                  <h4 className="text-white light:text-gray-900 font-medium mb-2">User</h4>
                  <ul className="text-xs text-slate-300 light:text-gray-700 space-y-1">
                    <li>• Can view sync intervals</li>
                    <li>• Cannot modify settings</li>
                    <li>• Limited data access</li>
                    <li>• Read-only access</li>
                  </ul>
                </div>
                
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4">
                  <h4 className="text-white light:text-gray-900 font-medium mb-2">Guest</h4>
                  <ul className="text-xs text-slate-300 light:text-gray-700 space-y-1">
                    <li>• No sync interval access</li>
                    <li>• Very limited access</li>
                    <li>• Cannot view settings</li>
                    <li>• Minimal permissions</li>
                  </ul>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Navigation to Admin Panel */}
        <Card className="bg-slate-800/30 light:bg-white border-slate-700 light:border-gray-200 light:shadow-md">
          <CardHeader>
            <CardTitle className="text-white light:text-gray-900 flex items-center gap-3">
              <Settings className="h-6 w-6 text-cyan-400 light:text-blue-600" />
              Test Sync Interval Settings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-slate-300 light:text-gray-700">
                Navigate to the Admin Panel to test the sync interval settings with role-based access control.
              </p>
              
              <div className="flex gap-3">
                <Button
                  onClick={() => window.location.href = '/admin'}
                  className="!bg-cyan-600 hover:!bg-cyan-700 !text-white"
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Go to Admin Panel
                </Button>
              </div>
              
              {!hasPermission('view_sync_interval') && (
                <Alert className="border-yellow-500 bg-yellow-900/20">
                  <XCircle className="h-4 w-4 text-yellow-400" />
                  <AlertDescription className="text-yellow-400">
                    Your current role does not have permission to view sync interval settings.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </WaterSystemLayout>
  )
}
