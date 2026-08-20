import React from 'react'
import { Link, useLocation } from 'wouter'
import {
  LayoutDashboard,
  Database,
  ChevronLeft,
  ChevronRight,
  Settings,
  Calendar,
  BarChart3,
  Monitor,
  ScrollText,
  Package,
  ClipboardList,
  CheckSquare,
  Activity,
  BookUserIcon,
  Layers,
  FileEdit, // ✅ NEW ICON for Offline Validation
  Users,
  Shield
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import herculesLogo from "@/assets/Hercules_New.png"

interface UserInfo {
  id: number
  username: string
  roles: string[]
}


interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}


const menuItems = [
  {
    path: '/sap-dashboard',
    icon: BarChart3,
    label: 'SAP Dashboard',
    description: 'Real-Time SAP Production Insights'
  },
  {
    path: '/kpi-calculations',
    icon: BarChart3,
    label: 'KPI Readings',
    description: 'Live KPI Calculations from SCADA Data'
  },
  {
    path: '/material-map',
    icon: Package,
    label: 'Material Mapping',
    description: 'Material to Line Mapping Management'
  },
  {
    path: '/palletizer-mapping',
    icon: Layers,
    label: 'Palletizer Mapping',
    description: 'Palletizer Configuration Management'
  },
  // { 
  //   path: '/process-orders', 
  //   icon: ClipboardList, 
  //   label: 'Process Orders',
  //   description: 'SAP Process Orders Management'
  // },
  {
    path: '/process-validation',
    icon: CheckSquare,
    label: 'Orders Validation',
    description: 'Process Order Validation & Approval'
  },
  {
    path: '/live-monitor',
    icon: Monitor,
    label: 'Live Monitor',
    description: 'Real-time SCADA Data Monitoring'
  },
  // ✅ NEW: Offline Validation Menu Item
  // { 
  //   path: '/offline-validation', 
  //   icon: FileEdit, 
  //   label: 'Offline Validation',
  //   description: 'Manual Order Validation with Scrap Tracking'
  // },
  {
    path: '/reports',
    icon: BookUserIcon,
    label: 'Reports',
    description: 'Reports'
  },
  // { 
  //   path: '/logs', 
  //   icon: ScrollText, 
  //   label: 'Sync Logs',
  //   description: 'System Sync & Operator Activity Logs'
  // },
  {
    path: '/user-management',
    icon: Users,
    label: 'User Management',
    description: 'Manage Users & Roles (Admin Only)'
  },
  {
    path: '/activity-log',
    icon: Activity,
    label: 'User Activity',
    description: 'Operator actions log (Admin Only)'
  },
  {
    // A8: plant connection configuration. Previously .env only.
    path: '/engineering',
    icon: Settings,
    label: 'Engineering',
    description: 'SAP & SQL Server connection (Admin Only)'
  },
]


export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const [location] = useLocation()

  // Fetch current user info to check admin role
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  })

  const currentUser = userData as UserInfo | null
  const isAdmin = currentUser?.roles?.includes('admin') || false
  const isMillingOperator = currentUser?.roles?.includes('milling_operator') || false
  const isPackingOperator = currentUser?.roles?.includes('packing_operator') || false

  // Filter menu items - hide User Management and User Activity for non-admin users
  // Material Mapping: admin or milling_operator only; Palletizer Mapping: admin or packing_operator only
  const visibleMenuItems = menuItems.filter(item => {
    if (item.path === '/user-management' || item.path === '/activity-log'
        || item.path === '/engineering') {
      return isAdmin
    }
    if (item.path === '/material-map') {
      return isAdmin || isMillingOperator
    }
    if (item.path === '/palletizer-mapping') {
      return isAdmin || isPackingOperator
    }
    return true
  })

  return (
    <div className={`bg-slate-900/95 light:bg-white border-r border-slate-700/50 light:border-gray-200 backdrop-blur-sm 
                     transition-all duration-300 flex flex-col relative h-screen shadow-lg light:shadow-xl
                     ${collapsed ? 'w-16' : 'w-64'}`}>

      {/* Header */}
      <div className="p-4 border-b border-slate-700/50 light:border-gray-200">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center space-x-3">
              <img
                src={herculesLogo}
                alt="Hercules v2.0"
                className="h-20 w-40 object-contain dark:brightness-0 dark:invert"
                style={{
                  opacity: 1,
                  imageRendering: 'auto'
                }}
              />
            </div>
          )}
          {collapsed && (
            <img
              src={herculesLogo}
              alt="Hercules v2.0"
              className="h-14 w-28 object-contain mx-auto dark:brightness-0 dark:invert"
              style={{
                opacity: 1,
                imageRendering: 'auto'
              }}
            />
          )}
          <button
            onClick={onToggle}
            className="p-2 rounded-lg bg-slate-800/50 light:bg-gray-100 hover:bg-slate-700/50 light:hover:bg-gray-200
                       text-slate-400 light:text-gray-600 hover:text-cyan-400 light:hover:text-blue-600 transition-colors"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>
      </div>


      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {visibleMenuItems.map((item) => {
          const Icon = item.icon
          const isActive = location === item.path

          return (
            <Link key={item.path} href={item.path}>
              <div className={`flex items-center p-3 rounded-lg transition-all duration-200 group cursor-pointer
                             ${isActive
                  ? 'bg-gradient-to-r from-cyan-600/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400'
                  : 'text-slate-400 hover:text-cyan-400 hover:bg-slate-800/50'
                }`}>
                <Icon className={`h-5 w-5 ${collapsed ? 'mx-auto' : 'mr-3'} flex-shrink-0`} />
                {!collapsed && (
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{item.label}</div>
                    {isActive && (
                      <div className="text-xs text-slate-400 truncate mt-0.5">
                        {item.description}
                      </div>
                    )}
                  </div>
                )}
                {!collapsed && isActive && (
                  <div className="w-2 h-2 bg-cyan-400 rounded-full flex-shrink-0"></div>
                )}
              </div>
            </Link>
          )
        })}
      </nav>

      {/* Scanning Line Animation */}
      <div className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent 
                      via-cyan-500/50 to-transparent opacity-30">
        <div className="absolute inset-0 bg-gradient-to-b from-cyan-400/0 via-cyan-400/80 to-cyan-400/0 
                        h-8 animate-pulse"></div>
      </div>
    </div>
  )
}
