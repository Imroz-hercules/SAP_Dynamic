import React, { useState, useRef, useEffect } from 'react'
import { useLocation } from 'wouter'
import { WaterSystemLayout } from '@/components/hercules-sfms/WaterSystemLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  Upload, 
  Settings, 
  Mail, 
  Clock, 
  Shield, 
  Plus,
  Send,
  Calendar,
  Database,
  BarChart3,
  FileText,
  Trash2,
  Edit,
  Save,
  PieChart,
  TrendingUp,
  Package,
  ListChecks,
  Download,
  Network,
  WifiIcon,
  AlertCircle,
  CheckCircle,
  Timer,
  RefreshCw,
  Lock,
  Unlock,
  User,
  Server,
  Play,
  Square,
  Zap,
  Activity,
  RotateCcw,
  Gauge,
  Power,
  ToggleLeft,
  ToggleRight,
  Copy,
  Type
} from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Slider } from '@/components/ui/slider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { useToast } from '@/hooks/use-toast'
import { LoginModal } from '@/components/LoginModal'
import { shiftApi, type ShiftMaster, timeApi, type ServerTimeInfo } from '@/lib/api'
import { useTextPreferences, FONT_FAMILY_OPTIONS } from '@/contexts/TextPreferencesContext'

interface SMTPProfile {
  id: string
  name: string
  host: string
  port: string
  username: string
  password: string
  sender: string
}

interface EmailSchedule {
  enabled: boolean
  senderEmail: string
  recipientEmail: string
  sendTime: string
  includeDailyReport: boolean
  includeWeeklyReport: boolean
  includeMonthlyReport: boolean
  includeMaterialConsumptionReport: boolean
  includeDetailedReport: boolean
}

interface PLCConnectionSettings {
  ipAddress: string
  port: string
  rackNumber: string
  slotNumber: string
  connectionType: 'S7-300' | 'S7-400' | 'S7-1200' | 'S7-1500'
  timeout: string
  retryAttempts: string
  isConnected: boolean
  lastConnectionTest: string | null
}

interface SyncIntervalSetting {
  id: number
  sync_type: string
  sync_time: string
  sync_date: string | null
  sync_start_date: string | null
  include_shifts: number
  sync_interval_minutes?: number | null
  is_enabled: boolean
  last_sync: string | null
  next_sync: string | null
  created_at: string
  updated_at: string
  description: string
}

interface SyncStatus {
  sync_type: string
  status: string
  start_time: string | null
  end_time: string | null
  duration_ms: number | null
  records_processed: number
  records_successful: number
  records_failed: number
  error_message: string | null
  triggered_by: string | null
  created_at: string | null
}

interface UserInfo {
  id: number
  username: string
  email: string
  full_name: string
  roles: string[]
  permissions: Record<string, boolean>
}

interface ShiftInfo {
  start: string
  end: string
  name: string
}

type ShiftType = 'milling' | 'packing'

// Shift schedule definitions
const SHIFT_SCHEDULES = {
  milling: {
    'Shift A': { start: '07:00', end: '15:00', name: 'Day Shift' },
    'Shift B': { start: '15:00', end: '23:00', name: 'Evening Shift' },
    'Shift C': { start: '23:00', end: '07:00', name: 'Night Shift' }
  },
  packing: {
    'Shift A': { start: '07:30', end: '15:30', name: 'Day Shift' },
    'Shift B': { start: '15:30', end: '23:30', name: 'Evening Shift' }
  }
}

// Helper function to get shift information (will be redefined inside component to use state)
const getShiftInfoBase = (schedules: Record<string, ShiftInfo>, syncType: string, currentTime: Date = new Date()) => {
  
  const currentHour = currentTime.getHours()
  const currentMinute = currentTime.getMinutes()
  const currentTimeMinutes = currentHour * 60 + currentMinute
  
  for (const [shiftName, shiftInfo] of Object.entries(schedules)) {
    const [startHour, startMin] = shiftInfo.start.split(':').map(Number)
    const [endHour, endMin] = shiftInfo.end.split(':').map(Number)
    
    let startMinutes = startHour * 60 + startMin
    let endMinutes = endHour * 60 + endMin
    
    // Handle overnight shifts (e.g., 23:00 - 07:00)
    if (endMinutes < startMinutes) {
      if (currentTimeMinutes >= startMinutes || currentTimeMinutes < endMinutes) {
        return {
          currentShift: shiftName,
          shiftInfo,
          isShiftEnd: false,
          nextShiftEnd: getNextShiftEnd(schedules, shiftName, currentTime)
        }
      }
    } else {
      if (currentTimeMinutes >= startMinutes && currentTimeMinutes < endMinutes) {
        return {
          currentShift: shiftName,
          shiftInfo,
          isShiftEnd: false,
          nextShiftEnd: getNextShiftEnd(schedules, shiftName, currentTime)
        }
      }
    }
  }
  
  return {
    currentShift: 'Between Shifts',
    shiftInfo: null,
    isShiftEnd: true,
    nextShiftEnd: getNextShiftEnd(schedules, null, currentTime)
  }
}

const getNextShiftEnd = (schedules: any, currentShift: string | null, currentTime: Date) => {
  const shiftEntries = Object.entries(schedules)
  
  // Handle empty schedules
  if (!shiftEntries || shiftEntries.length === 0) {
    return {
      shiftName: null,
      endTime: null
    }
  }
  
  const currentIndex = currentShift ? shiftEntries.findIndex(([name]) => name === currentShift) : -1
  const nextIndex = (currentIndex + 1) % shiftEntries.length
  const nextEntry = shiftEntries[nextIndex]
  
  // Safety check
  if (!nextEntry || !nextEntry[1]) {
    return {
      shiftName: null,
      endTime: null
    }
  }
  
  const [nextShiftName, nextShiftInfo] = nextEntry
  
  // Type guard to check if nextShiftInfo has the expected structure
  if (!nextShiftInfo || typeof nextShiftInfo !== 'object' || !('end' in nextShiftInfo)) {
    return {
      shiftName: nextShiftName || null,
      endTime: null
    }
  }
  
  const shiftInfo = nextShiftInfo as ShiftInfo
  if (!shiftInfo.end) {
    return {
      shiftName: nextShiftName || null,
      endTime: null
    }
  }
  
  const [endHour, endMin] = shiftInfo.end.split(':').map(Number)
  const nextEnd = new Date(currentTime)
  nextEnd.setHours(endHour, endMin, 0, 0)
  
  // If the next shift end is tomorrow
  if (endHour < currentTime.getHours() || (endHour === currentTime.getHours() && endMin <= currentTime.getMinutes())) {
    nextEnd.setDate(nextEnd.getDate() + 1)
  }
  
  return {
    shiftName: nextShiftName,
    endTime: nextEnd
  }
}

// Mock data for demonstration
const mockSMTPProfiles: SMTPProfile[] = []

const mockEmailSchedule: EmailSchedule = {
  enabled: false,
  senderEmail: 'sender@example.com',
  recipientEmail: 'recipient@example.com',
  sendTime: '09:00',
  includeDailyReport: true,
  includeWeeklyReport: false,
  includeMonthlyReport: false,
  includeMaterialConsumptionReport: true,
  includeDetailedReport: false
}

function SystemTextFormatSection() {
  const { preferences, setFontSizeScale, setFontFamily, setBold, setItalic, setUnderline } = useTextPreferences()
  const percent = Math.round(preferences.fontSizeScale * 100)
  return (
    <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
      <h3 className="text-white light:text-gray-900 font-semibold mb-4 flex items-center gap-2">
        <Type className="h-4 w-4 text-cyan-400 light:text-blue-600" />
        System text format
      </h3>
      <div className="flex flex-col space-y-4">
        <div className="space-y-2">
          <Label className="text-slate-300 light:text-gray-700 text-sm font-medium">Text format (font family)</Label>
          <Select value={preferences.fontFamily} onValueChange={setFontFamily}>
            <SelectTrigger className="w-full max-w-xs border-slate-600 light:border-gray-300 bg-slate-800/50 light:bg-white text-white light:text-gray-900">
              <SelectValue placeholder="Select format" />
            </SelectTrigger>
            <SelectContent className="bg-popover text-popover-foreground border-slate-600 light:border-gray-200">
              {FONT_FAMILY_OPTIONS.map((opt) => (
                <SelectItem
                  key={opt.value}
                  value={opt.value}
                  className="focus:bg-accent focus:text-accent-foreground cursor-pointer"
                >
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label className="text-slate-300 light:text-gray-700 text-sm font-medium">Font size: {percent}%</Label>
          <Slider
            value={[preferences.fontSizeScale]}
            onValueChange={([v]) => setFontSizeScale(v ?? 1)}
            min={0.8}
            max={1.5}
            step={0.05}
            className="w-full max-w-xs"
          />
        </div>
        <div className="flex flex-wrap gap-6">
          <div className="flex items-center gap-2">
            <Switch
              id="text-bold"
              checked={preferences.bold}
              onCheckedChange={setBold}
            />
            <Label htmlFor="text-bold" className="text-slate-300 light:text-gray-700 text-sm font-medium cursor-pointer">Bold</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="text-italic"
              checked={preferences.italic}
              onCheckedChange={setItalic}
            />
            <Label htmlFor="text-italic" className="text-slate-300 light:text-gray-700 text-sm font-medium cursor-pointer">Italic</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="text-underline"
              checked={preferences.underline}
              onCheckedChange={setUnderline}
            />
            <Label htmlFor="text-underline" className="text-slate-300 light:text-gray-700 text-sm font-medium cursor-pointer">Underline</Label>
          </div>
        </div>
      </div>
    </div>
  )
}

export function Admin() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [location] = useLocation()
  
  // Get tab from URL query parameter (e.g., /admin?tab=demo)
  const getTabFromUrl = () => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get('tab')
    const validTabs = ['system', 'shifts', 'sap', 'email', 'branding', 'demo', 'logs']
    return tab && validTabs.includes(tab) ? tab : 'system'
  }
  
  const [activeTab, setActiveTab] = useState(getTabFromUrl)
  
  // Update active tab when URL changes
  useEffect(() => {
    setActiveTab(getTabFromUrl())
  }, [location])
  
  const [currentLogo, setCurrentLogo] = useState<string | null>(null)
  const [smtpProfiles, setSMTPProfiles] = useState<SMTPProfile[]>(mockSMTPProfiles)
  const [emailSchedule, setEmailSchedule] = useState<EmailSchedule>(mockEmailSchedule)
  const [newProfile, setNewProfile] = useState<Omit<SMTPProfile, 'id'>>({
    name: '',
    host: '',
    port: '',
    username: '',
    password: '',
    sender: ''
  })
  const [testEmail, setTestEmail] = useState('')
  const [editingProfile, setEditingProfile] = useState<string | null>(null)
  const [plcConnection, setPLCConnection] = useState<PLCConnectionSettings>({
    ipAddress: '',
    port: '102',
    rackNumber: '0',
    slotNumber: '2',
    connectionType: 'S7-1500',
    timeout: '5000',
    retryAttempts: '3',
    isConnected: false,
    lastConnectionTest: null
  })
  const [connectionTestStatus, setConnectionTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [connectionTestMessage, setConnectionTestMessage] = useState<string>('')
  const [rawDataSyncStatus, setRawDataSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle')
  const [kpiSyncStatus, setKpiSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle')
  const [syncIntervalSettings, setSyncIntervalSettings] = useState<SyncIntervalSetting[]>([])
  const [sapReceivingInterval, setSapReceivingInterval] = useState<number | ''>('')
  const [sapIntervalLoading, setSapIntervalLoading] = useState(false)
  const [sapIntervalSaving, setSapIntervalSaving] = useState(false)
  
  // SAP Endpoint Configuration (Demo - stores locally, will connect to backend later)
  const [sapBaseUrl, setSapBaseUrl] = useState('https://vhmioqs4ci.sap.mc3.com.sa:44300')
  const [sapClient, setSapClient] = useState('250')
  const [sapOrdersEndpoint, setSapOrdersEndpoint] = useState('/zmi_get_orders/GETORD')
  const [sapMillingEndpoint, setSapMillingEndpoint] = useState('/zmi_kpi_mill/MKPI')
  const [sapPackingEndpoint, setSapPackingEndpoint] = useState('/zmi_kpi_pack/PKPI')
  const [sapHerculesEndpoint, setSapHerculesEndpoint] = useState('/zmi_raw_hercl/HERC')
  const [sapConfirmOnlineEndpoint, setSapConfirmOnlineEndpoint] = useState('/zmi_conf_online/CONF')
  const [sapConfirmOfflineEndpoint, setSapConfirmOfflineEndpoint] = useState('/zmi_conf_offlin/CONFOFF')
  const [sapEndpointsSaving, setSapEndpointsSaving] = useState(false)
  const [sapConnectionTesting, setSapConnectionTesting] = useState(false)
  
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null)
  const [editingSyncSetting, setEditingSyncSetting] = useState<string | null>(null)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [localSyncSettings, setLocalSyncSettings] = useState<SyncIntervalSetting[]>([])
  const [unsavedChanges, setUnsavedChanges] = useState<Set<string>>(new Set())
  // No countdown timers needed since we only sync at specific date/time
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Demo Mode State
  const [demoMode, setDemoMode] = useState({
    demo_mode: true,
    mock_sap: true,
    emulator_auto_start: true,
    emulator_running: false,
    emulator_active_scales: 0,
    emulator_last_update: null as string | null,
  })
  const [emulatorConfig, setEmulatorConfig] = useState({
    interval: 10,
    step_min: 1,
    step_max: 10,
    running: false,
    active_scale_count: 0,
    total_scale_count: 0,
  })
  const [emulatorScales, setEmulatorScales] = useState<{
    scales: Record<string, { value: number; active: boolean }>;
    categories: Record<string, { name: string; fields: string[]; color: string; description: string }>;
    active_count: number;
    total_count: number;
  } | null>(null)
  const [systemStats, setSystemStats] = useState<Record<string, number>>({})
  const [demoModeLoading, setDemoModeLoading] = useState(false)
  const [emulatorActionLoading, setEmulatorActionLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState<string | null>(null)
  const [showAutoValidationButton, setShowAutoValidationButton] = useState(
    () => localStorage.getItem('show_auto_validation_button') === 'true'
  )

  // SAP Logs State
  const [expandedLogRows, setExpandedLogRows] = useState<Set<number>>(new Set())
  const [sapLogsClearing, setSapLogsClearing] = useState(false)

  const isLoggedIn = !!localStorage.getItem('auth_token')
  
  // Shift Mappings State
  const [shiftMappings, setShiftMappings] = useState<Record<ShiftType, Record<string, ShiftInfo>>>(SHIFT_SCHEDULES)
  const [showAddShiftModal, setShowAddShiftModal] = useState(false)
  const [showEditShiftModal, setShowEditShiftModal] = useState(false)
  const [showDeleteShiftModal, setShowDeleteShiftModal] = useState(false)
  const [editingShift, setEditingShift] = useState<{ type: ShiftType; name: string } | null>(null)
  const [deletingShift, setDeletingShift] = useState<{ type: ShiftType; name: string } | null>(null)
  const [newShift, setNewShift] = useState<{ type: ShiftType; name: string; start: string; end: string; displayName: string }>({
    type: 'milling',
    name: '',
    start: '07:00',
    end: '15:00',
    displayName: ''
  })

  // Fetch current PLC connection settings (disabled until endpoint exists)
  const { data: plcSettingsData } = useQuery({
    queryKey: ['/api/plc/connection-settings'],
    enabled: false,
    retry: 0
  })

  // Fetch sync interval settings - only if authenticated
  const { data: syncSettingsData } = useQuery({
    queryKey: ['/api/sync-interval/settings'],
    queryFn: () => apiRequest('GET', '/api/sync-interval/settings'),
    select: (data) => data.settings || [],
    enabled: !!localStorage.getItem('auth_token')
  })

  // Fetch sync status - only if authenticated
  const { data: syncStatusData, refetch: refetchSyncStatus } = useQuery({
    queryKey: ['/api/sync-interval/status'],
    queryFn: () => apiRequest('GET', '/api/sync-interval/status'),
    select: (data) => data.status_list || [],
    enabled: !!localStorage.getItem('auth_token'),
    refetchInterval: 5000 // Refetch every 5 seconds for real-time updates
  })

  // Fetch current user info - only if token exists
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  })

  // Fetch shifts from API
  const { data: shiftsData, refetch: refetchShifts } = useQuery({
    queryKey: ['/api/shifts'],
    queryFn: async () => {
      try {
        return await shiftApi.getShifts()
      } catch (error) {
        console.error('Error fetching shifts:', error)
        return []
      }
    },
    select: (data) => data || []
  })

  // Fetch server time
  const { data: serverTimeData, refetch: refetchServerTime } = useQuery({
    queryKey: ['/api/time'],
    queryFn: async () => {
      try {
        return await timeApi.getServerTime()
      } catch (error) {
        console.error('Error fetching server time:', error)
        throw error
      }
    },
    refetchInterval: 1000 // Update every second
  })

  // Fetch system mode (demo/production)
  const { data: systemModeData, refetch: refetchSystemMode } = useQuery({
    queryKey: ['/api/system/mode'],
    queryFn: () => apiRequest('GET', '/api/system/mode'),
    refetchInterval: 5000
  })

  // Fetch emulator status
  const { data: emulatorStatusData, refetch: refetchEmulatorStatus, error: emulatorStatusError } = useQuery({
    queryKey: ['/api/emulator/status'],
    queryFn: () => apiRequest('GET', '/api/emulator/status'),
    refetchInterval: 2000
  })

  // Fetch emulator scales
  const { data: emulatorScalesData, refetch: refetchEmulatorScales, error: emulatorScalesError } = useQuery({
    queryKey: ['/api/emulator/scales'],
    queryFn: () => apiRequest('GET', '/api/emulator/scales'),
    refetchInterval: emulatorConfig.running ? 1000 : 3000,
  })

  // Fetch live emulator values - poll when emulator is running
  const { data: emulatorLiveData } = useQuery({
    queryKey: ['/api/emulator/latest'],
    queryFn: () => apiRequest('GET', '/api/emulator/latest'),
    refetchInterval: emulatorConfig.running ? 1000 : false, // Poll every 1s when running
    enabled: demoMode.demo_mode
  })

  // Fetch system stats
  const { data: systemStatsData, refetch: refetchSystemStats } = useQuery({
    queryKey: ['/api/system/stats'],
    queryFn: () => apiRequest('GET', '/api/system/stats'),
    refetchInterval: 10000
  })

  // Fetch SAP confirmation logs from JSON file
  const { data: sapLogsData, refetch: refetchSapLogs } = useQuery({
    queryKey: ['/api/sap-logs/confirmations'],
    queryFn: () => apiRequest('GET', '/api/sap-logs/confirmations?limit=200'),
    refetchInterval: 15000 // Refresh every 15 seconds
  })

  // Client time (updates every second)
  const [clientTime, setClientTime] = React.useState<string>('')
  
  React.useEffect(() => {
    const updateTimes = () => {
      const now = new Date()
      setClientTime(now.toLocaleString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }))
      
    }
    
    updateTimes()
    const interval = setInterval(updateTimes, 1000)
    return () => clearInterval(interval)
  }, [serverTimeData])

  // Transform API shifts data to local state format
  React.useEffect(() => {
    if (shiftsData && shiftsData.length > 0) {
      const transformed: Record<ShiftType, Record<string, ShiftInfo>> = {
        milling: {},
        packing: {}
      }

      // Sort shifts by sort_order before processing
      const sortedShifts = [...shiftsData].sort((a, b) => a.sort_order - b.sort_order)

      sortedShifts.forEach((shift: ShiftMaster) => {
        const department = shift.department.toUpperCase()
        const shiftType: ShiftType = department === 'MILLING' ? 'milling' : 'packing'
        const shiftName = shift.shift_code

        transformed[shiftType][shiftName] = {
          start: shift.start_time,
          end: shift.end_time,
          name: shiftName // You can add a display_name field to ShiftMaster if needed
        }
      })

      setShiftMappings(transformed)
    } else if (shiftsData && shiftsData.length === 0) {
      // If no shifts in database, use empty mappings
      setShiftMappings({ milling: {}, packing: {} })
    }
  }, [shiftsData])

  // Update local state when data is fetched
  React.useEffect(() => {
    if (plcSettingsData && typeof plcSettingsData === 'object') {
      setPLCConnection({
        ipAddress: (plcSettingsData as any).ipAddress || '',
        port: (plcSettingsData as any).port?.toString() || '102',
        rackNumber: (plcSettingsData as any).rackNumber?.toString() || '0',
        slotNumber: (plcSettingsData as any).slotNumber?.toString() || '2',
        connectionType: (plcSettingsData as any).connectionType || 'S7-1500',
        timeout: (plcSettingsData as any).timeout?.toString() || '5000',
        retryAttempts: (plcSettingsData as any).retryAttempts?.toString() || '3',
        isConnected: (plcSettingsData as any).isConnected || false,
        lastConnectionTest: (plcSettingsData as any).lastConnectionTest || null
      })
    }
  }, [plcSettingsData])

  // Update sync interval settings state
  React.useEffect(() => {
    if (syncSettingsData) {
      setSyncIntervalSettings(syncSettingsData)
      setLocalSyncSettings(syncSettingsData)
      const processOrders = syncSettingsData.find((s: SyncIntervalSetting) => s.sync_type === 'process_orders')
      if (processOrders) {
        setSapReceivingInterval(processOrders.sync_interval_minutes ?? '')
      }
      // Clear unsaved changes when data is refreshed from server
      setUnsavedChanges(new Set())
    }
  }, [syncSettingsData])

  // No countdown timers needed since we only sync at specific date/time

  // Debug function to log time information
  const debugTimeInfo = (setting: SyncIntervalSetting) => {
    console.log(`Debug for ${setting.sync_type}:`, {
      last_sync: setting.last_sync,
      next_sync: setting.next_sync,
      sync_time: setting.sync_time,
      is_enabled: setting.is_enabled,
      current_time: new Date().toISOString(),
      sync_date: setting.sync_date
    })
  }

  // Update current user state
  React.useEffect(() => {
    if (userData) {
      setCurrentUser(userData)
    }
  }, [userData])

  // Update demo mode state
  React.useEffect(() => {
    if (systemModeData) {
      setDemoMode({
        demo_mode: systemModeData.demo_mode ?? true,
        mock_sap: systemModeData.mock_sap ?? true,
        emulator_auto_start: systemModeData.emulator_auto_start ?? true,
        emulator_running: systemModeData.emulator_running ?? false,
        emulator_active_scales: systemModeData.emulator_active_scales ?? 0,
        emulator_last_update: systemModeData.emulator_last_update ?? null,
      })
    }
  }, [systemModeData])

  // Track if we've loaded config from API initially
  const [configInitialized, setConfigInitialized] = React.useState(false)
  
  // Update emulator config state from API
  React.useEffect(() => {
    if (emulatorStatusData) {
      // On first load, get config from API
      if (!configInitialized) {
        setEmulatorConfig({
          interval: emulatorStatusData.config?.interval ?? 10,
          step_min: emulatorStatusData.config?.step_min ?? 1,
          step_max: emulatorStatusData.config?.step_max ?? 10,
          running: emulatorStatusData.running ?? false,
          active_scale_count: emulatorStatusData.active_scales ?? 0,
          total_scale_count: emulatorStatusData.total_scales ?? 0,
        })
        setConfigInitialized(true)
      } else {
        // After first load, only update running state and counts (not user-editable fields)
        setEmulatorConfig(prev => ({
          ...prev,
          running: emulatorStatusData.running ?? false,
          active_scale_count: emulatorStatusData.active_scales ?? 0,
          total_scale_count: emulatorStatusData.total_scales ?? 0,
        }))
      }
    }
  }, [emulatorStatusData, configInitialized])

  // Update emulator scales state
  React.useEffect(() => {
    if (emulatorScalesData) {
      setEmulatorScales(emulatorScalesData)
    }
  }, [emulatorScalesData])

  // Update system stats
  React.useEffect(() => {
    if (systemStatsData) {
      setSystemStats(systemStatsData)
    }
  }, [systemStatsData])

  // Force delete buttons to be visible in both light and dark modes
  React.useEffect(() => {
    const styleDeleteButtons = () => {
      const deleteButtons = document.querySelectorAll('.delete-button-red')
      deleteButtons.forEach((button) => {
        const btn = button as HTMLElement
        btn.style.setProperty('background-color', '#dc2626', 'important')
        btn.style.setProperty('color', '#ffffff', 'important')
        btn.style.setProperty('border-color', '#dc2626', 'important')
        btn.style.setProperty('opacity', '1', 'important')
        btn.style.setProperty('visibility', 'visible', 'important')
        
        // Style all child elements
        const children = btn.querySelectorAll('*')
        children.forEach((child) => {
          const el = child as HTMLElement
          el.style.setProperty('color', '#ffffff', 'important')
          if (el.tagName === 'svg' || el.querySelector('svg')) {
            el.style.setProperty('fill', '#ffffff', 'important')
            el.style.setProperty('stroke', '#ffffff', 'important')
          }
        })
      })
    }

    // Run immediately and on any changes
    styleDeleteButtons()
    
    // Use MutationObserver to catch dynamically added buttons
    const observer = new MutationObserver(styleDeleteButtons)
    observer.observe(document.body, {
      childList: true,
      subtree: true
    })

    // Also run on interval to catch any missed updates (less frequent to avoid performance issues)
    const interval = setInterval(styleDeleteButtons, 500)

    return () => {
      observer.disconnect()
      clearInterval(interval)
    }
  }, [shiftMappings, smtpProfiles])

  // Mutation for saving PLC connection settings
  const savePlcSettingsMutation = useMutation({
    mutationFn: (settings: Partial<PLCConnectionSettings>) => 
      apiRequest('PUT', '/api/plc/connection-settings', {
        ...settings,
        port: parseInt(settings.port || '102'),
        rackNumber: parseInt(settings.rackNumber || '0'),
        slotNumber: parseInt(settings.slotNumber || '2'),
        timeout: parseInt(settings.timeout || '5000'),
        retryAttempts: parseInt(settings.retryAttempts || '3')
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/plc/connection-settings'] })
      alert('PLC connection settings saved successfully!')
    },
    onError: () => {
      alert('Failed to save PLC connection settings')
    }
  })

  // Mutation for testing PLC connection
  const testPLCConnectionMutation = useMutation({
    mutationFn: () => 
      apiRequest('POST', '/api/plc/connection-settings/test', {
        ipAddress: plcConnection.ipAddress,
        port: parseInt(plcConnection.port),
        connectionType: plcConnection.connectionType,
        rackNumber: parseInt(plcConnection.rackNumber),
        slotNumber: parseInt(plcConnection.slotNumber)
      }),
    onMutate: () => {
      setConnectionTestStatus('testing')
      setConnectionTestMessage('Testing connection to PLC...')
    },
    onSuccess: (data: any) => {
      if (data.success) {
        setConnectionTestStatus('success')
        setConnectionTestMessage(data.message)
        setPLCConnection({
          ...plcConnection,
          isConnected: true,
          lastConnectionTest: data.timestamp
        })
      } else {
        setConnectionTestStatus('error')
        setConnectionTestMessage(data.message)
      }
      
      // Reset status after 5 seconds
      setTimeout(() => {
        setConnectionTestStatus('idle')
        setConnectionTestMessage('')
      }, 5000)
      
      queryClient.invalidateQueries({ queryKey: ['/api/plc/connection-settings'] })
    },
    onError: () => {
      setConnectionTestStatus('error')
      setConnectionTestMessage('Failed to test connection. Please check network settings.')
      
      setTimeout(() => {
        setConnectionTestStatus('idle')
        setConnectionTestMessage('')
      }, 5000)
    }
  })

  // Mutation for sending raw data to SAP
  const sendRawDataMutation = useMutation({
    mutationFn: () => 
      apiRequest('POST', '/api/sap-sync/send-raw-data', {}),
    onMutate: () => {
      setRawDataSyncStatus('syncing')
      toast({
        title: '🔄 Synchronizing data with SAP...',
        description: 'Fetching latest 20 records and sending to SAP system',
        duration: 30000
      })
    },
    onSuccess: (data: any) => {
      if (data.ok) {
        setRawDataSyncStatus('success')
        toast({
          title: '✅ Data synchronized successfully!',
          description: `Successfully sent ${data.records_sent} records to SAP system`,
          duration: 5000
        })
      } else {
        setRawDataSyncStatus('error')
        // Extract user-friendly error message
        let errorMessage = 'Failed to send data to SAP'
        if (data.message) {
          if (data.message.includes('Failed to connect')) {
            errorMessage = 'Unable to connect to SAP server. Please check network connectivity.'
          } else if (data.message.includes('timeout')) {
            errorMessage = 'SAP server request timed out. Please try again.'
          } else if (data.message.includes('JSON serializable')) {
            errorMessage = 'Data format error. Please contact system administrator.'
          } else {
            errorMessage = 'SAP synchronization failed. Please try again.'
          }
        }
        
        toast({
          title: '❌ Synchronization failed',
          description: errorMessage,
          duration: 8000,
          variant: 'destructive'
        })
      }
      
      // Reset status after 8 seconds
      setTimeout(() => {
        setRawDataSyncStatus('idle')
      }, 8000)
    },
    onError: (error: any) => {
      setRawDataSyncStatus('error')
      
      // Extract user-friendly error message
      let errorMessage = 'Network or server error occurred'
      if (error?.message) {
        if (error.message.includes('Failed to fetch')) {
          errorMessage = 'Unable to connect to server. Please check your connection.'
        } else if (error.message.includes('500')) {
          errorMessage = 'Server error occurred. Please try again later.'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timed out. Please try again.'
        } else {
          errorMessage = 'An unexpected error occurred. Please try again.'
        }
      }
      
      toast({
        title: '❌ Synchronization failed',
        description: errorMessage,
        duration: 8000,
        variant: 'destructive'
      })
      
      setTimeout(() => {
        setRawDataSyncStatus('idle')
      }, 8000)
    }
  })

  // Mutation for sending KPIs to SAP
  const sendKpiToSapMutation = useMutation({
    mutationFn: () => 
      apiRequest('POST', '/api/kpi/send-all-to-sap', {}),
    onMutate: () => {
      setKpiSyncStatus('syncing')
      toast({
        title: '🔄 Sending KPIs to SAP...',
        description: 'Sending both milling and packing KPIs to SAP system',
        duration: 30000
      })
    },
    onSuccess: (data: any) => {
      if (data.success === true) {
        setKpiSyncStatus('success')
        toast({
          title: '✅ KPIs sent successfully!',
          description: data.message || 'Both milling and packing KPIs sent to SAP successfully',
          duration: 5000
        })
      } else {
        setKpiSyncStatus('error')
        toast({
          title: '❌ Failed to send KPIs',
          description: data.message || 'Failed to send KPIs to SAP',
          duration: 8000,
          variant: 'destructive'
        })
      }
      
      // Reset status after 8 seconds
      setTimeout(() => {
        setKpiSyncStatus('idle')
      }, 8000)
    },
    onError: (error: any) => {
      setKpiSyncStatus('error')
      
      // Extract user-friendly error message
      let errorMessage = 'Network or server error occurred'
      if (error?.message) {
        if (error.message.includes('Failed to fetch')) {
          errorMessage = 'Unable to connect to server. Please check your connection.'
        } else if (error.message.includes('500')) {
          errorMessage = 'Server error occurred. Please try again later.'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timed out. Please try again.'
        } else if (error.message.includes('CSRF')) {
          errorMessage = 'SAP authentication failed. Please check SAP server configuration.'
        } else {
          errorMessage = 'An unexpected error occurred. Please try again.'
        }
      }
      
      toast({
        title: '❌ Failed to send KPIs',
        description: errorMessage,
        duration: 8000,
        variant: 'destructive'
      })
      
      setTimeout(() => {
        setKpiSyncStatus('idle')
      }, 8000)
    }
  })


  const handleLogoUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        setCurrentLogo(e.target?.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleAddProfile = () => {
    if (newProfile.name && newProfile.host && newProfile.port) {
      const profile: SMTPProfile = {
        ...newProfile,
        id: Date.now().toString()
      }
      setSMTPProfiles([...smtpProfiles, profile])
      setNewProfile({
        name: '',
        host: '',
        port: '',
        username: '',
        password: '',
        sender: ''
      })
    }
  }

  const handleDeleteProfile = (id: string) => {
    setSMTPProfiles(smtpProfiles.filter(profile => profile.id !== id))
  }

  const handleSendTestEmail = () => {
    if (testEmail) {
      // Simulate sending test email
      alert(`Test email would be sent to: ${testEmail}`)
    }
  }

  const handleSaveSchedule = () => {
    // Simulate saving email schedule
    alert('Email schedule saved successfully!')
  }

  const handleTestPLCConnection = async () => {
    testPLCConnectionMutation.mutate()
  }

  const handleSavePLCConnection = () => {
    savePlcSettingsMutation.mutate(plcConnection)
  }

  const [showConfirmDialog, setShowConfirmDialog] = useState(false)

  const handleSendRawData = () => {
    setShowConfirmDialog(true)
  }

  const handleConfirmSend = () => {
    setShowConfirmDialog(false)
    sendRawDataMutation.mutate()
  }

  const handleCancelSend = () => {
    setShowConfirmDialog(false)
  }

  const handleSendKpiToSap = () => {
    sendKpiToSapMutation.mutate()
  }


  // Mutation for updating sync interval settings
  const updateSyncIntervalMutation = useMutation({
    mutationFn: ({ syncType, syncTime, syncStartDate, includeShifts, isEnabled, syncIntervalMinutes }: { 
      syncType: string, 
      syncTime?: string, 
      syncStartDate?: string,
      includeShifts?: number,
      isEnabled?: boolean,
      syncIntervalMinutes?: number | null
    }) => 
      apiRequest('PUT', `/api/sync-interval/settings/${syncType}`, {
        sync_time: syncTime,
        sync_start_date: syncStartDate,
        include_shifts: includeShifts,
        is_enabled: isEnabled,
        sync_interval_minutes: syncIntervalMinutes
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/sync-interval/settings'] })
      toast({
        title: '✅ Sync interval updated successfully!',
        description: 'The sync interval setting has been updated',
        duration: 3000
      })
    },
    onError: (error: any) => {
      toast({
        title: '❌ Failed to update sync interval',
        description: error?.message || 'An error occurred while updating the sync interval',
        duration: 5000,
        variant: 'destructive'
      })
    }
  })

  // Mutation for saving sync settings
  const saveSyncMutation = useMutation({
    mutationFn: ({ syncType, syncTime, syncStartDate, includeShifts, isEnabled, syncIntervalMinutes }: { 
      syncType: string, 
      syncTime: string, 
      syncStartDate?: string,
      includeShifts?: number,
      isEnabled: boolean,
      syncIntervalMinutes?: number | null
    }) => 
      apiRequest('POST', `/api/sync-interval/settings/${syncType}/save`, {
        sync_time: syncTime,
        sync_start_date: syncStartDate,
        include_shifts: includeShifts,
        is_enabled: isEnabled,
        sync_interval_minutes: syncIntervalMinutes
      }),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['/api/sync-interval/settings'] })
      // Clear unsaved changes for this sync type
      setUnsavedChanges(prev => {
        const newSet = new Set(prev)
        newSet.delete(variables.syncType)
        return newSet
      })
      toast({
        title: '✅ Sync settings saved!',
        description: 'The sync settings have been saved and scheduler updated',
        duration: 3000
      })
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.message || error?.message || 'An error occurred while saving the sync settings'
      const errorDetails = error?.response?.data?.details || ''
      
      toast({
        title: '❌ Failed to save sync settings',
        description: `${errorMessage}${errorDetails ? ` - ${errorDetails}` : ''}`,
        duration: 7000,
        variant: 'destructive'
      })
      
      // Reset local state to server state on error
      if (syncSettingsData) {
        setLocalSyncSettings(syncSettingsData)
      }
    }
  })

  // Helper functions for role-based access
  const canViewSyncInterval = () => {
    return currentUser?.permissions?.view_sync_interval || false
  }

  const canChangeSyncInterval = () => {
    return currentUser?.permissions?.change_sync_interval || false
  }

  const isAdmin = () => {
    return currentUser?.roles?.includes('admin') || false
  }

  const isManager = () => {
    return currentUser?.roles?.includes('manager') || false
  }

  // Handler functions for sync interval management
  const handleUpdateSyncInterval = (syncType: string, syncTime: string, syncStartDate: string, includeShifts: number, isEnabled: boolean, syncIntervalMinutes: number | null = null) => {
    updateSyncIntervalMutation.mutate({ syncType, syncTime, syncStartDate, includeShifts, isEnabled, syncIntervalMinutes })
  }

  const handleSaveSync = (syncType: string, syncTime: string, syncStartDate: string, includeShifts: number, isEnabled: boolean, syncIntervalMinutes: number | null = null) => {
    saveSyncMutation.mutate({ syncType, syncTime, syncStartDate, includeShifts, isEnabled, syncIntervalMinutes })
  }

  // Quick-save SAP receiving interval (process_orders)
  const saveSapReceivingInterval = async () => {
    if (sapReceivingInterval === '' || sapReceivingInterval < 1 || sapReceivingInterval > 1440) {
      toast({
        title: '❌ Invalid interval',
        description: 'Please enter a value between 1 and 1440 minutes.',
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    const processSetting = getLocalSyncSetting('process_orders')
    setSapIntervalSaving(true)
    try {
      const data = await apiRequest('PUT', `/api/sync-interval/settings/process_orders`, {
        sync_interval_minutes: Number(sapReceivingInterval),
        // keep existing fields intact
        sync_time: processSetting?.sync_time,
        sync_date: processSetting?.sync_date,
        is_enabled: true // always enable when saving interval so auto-sync runs
      })

      const minutes = data?.setting?.sync_interval_minutes
      if (minutes !== undefined) {
        setSapReceivingInterval(minutes)
        setLocalSyncSettings(prev =>
          prev.map(s =>
            s.sync_type === 'process_orders'
              ? { ...s, sync_interval_minutes: minutes }
              : s
          )
        )
        // Also update the main sync settings state
        setSyncIntervalSettings(prev =>
          prev.map(s =>
            s.sync_type === 'process_orders'
              ? { ...s, sync_interval_minutes: minutes }
              : s
          )
        )
      }

      // ✅ CRITICAL: Invalidate the query cache to ensure fresh data on next fetch
      queryClient.invalidateQueries({ queryKey: ['/api/sync-interval/settings'] })

      toast({
        title: '✅ SAP receiving interval updated',
        description: `Sync will now run every ${minutes} minute(s)`,
        duration: 3000
      })
    } catch (err: any) {
      toast({
        title: '❌ Failed to update interval',
      description: err?.status === 401 ? 'Please log in to change SAP receiving interval.' : (err?.message || 'Please try again.'),
        duration: 4000,
        variant: 'destructive'
      })
    if (err?.status === 401) setShowLoginModal(true)
    } finally {
      setSapIntervalSaving(false)
    }
  }

  // Demo: Save SAP Endpoints (will connect to backend later)
  const saveSapEndpoints = async () => {
    setSapEndpointsSaving(true)
    try {
      // Demo: Simulate save delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const config = {
        baseUrl: sapBaseUrl,
        client: sapClient,
        endpoints: {
          orders: sapOrdersEndpoint,
          millingKpi: sapMillingEndpoint,
          packingKpi: sapPackingEndpoint,
          hercules: sapHerculesEndpoint,
          confirmOnline: sapConfirmOnlineEndpoint,
          confirmOffline: sapConfirmOfflineEndpoint
        }
      }
      
      console.log('📡 SAP Configuration Saved (Demo):', config)
      
      toast({
        title: '✅ SAP Endpoints Saved',
        description: 'Configuration saved locally. Backend integration coming soon!',
        duration: 3000
      })
    } catch (err: any) {
      toast({
        title: '❌ Failed to save endpoints',
        description: err?.message || 'Please try again.',
        duration: 4000,
        variant: 'destructive'
      })
    } finally {
      setSapEndpointsSaving(false)
    }
  }

  // Demo: Test SAP Connection
  const testSapConnection = async () => {
    setSapConnectionTesting(true)
    try {
      const fullUrl = `${sapBaseUrl}${sapOrdersEndpoint}?sap-client=${sapClient}`
      console.log('🔗 Testing SAP Connection (Demo):', fullUrl)
      
      // Demo: Simulate connection test delay
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      toast({
        title: '🔗 Connection Test (Demo)',
        description: `Would test: ${fullUrl}`,
        duration: 4000
      })
    } catch (err: any) {
      toast({
        title: '❌ Connection test failed',
        description: err?.message || 'Please try again.',
        duration: 4000,
        variant: 'destructive'
      })
    } finally {
      setSapConnectionTesting(false)
    }
  }

  // Helper functions for local state management
  const updateLocalSyncSetting = (syncType: string, field: 'sync_time' | 'sync_start_date' | 'include_shifts' | 'is_enabled', value: any) => {
    setLocalSyncSettings(prev => 
      prev.map(setting => 
        setting.sync_type === syncType 
          ? { 
              ...setting, 
              [field]: value
            }
          : setting
      )
    )
    
    // Track unsaved changes
    setUnsavedChanges(prev => new Set(prev).add(syncType))
  }

  const getLocalSyncSetting = (syncType: string) => {
    return localSyncSettings.find(s => s.sync_type === syncType) || 
           syncIntervalSettings.find(s => s.sync_type === syncType)
  }

  const getSyncStatus = (syncType: string): SyncStatus | null => {
    return syncStatusData?.find((status: SyncStatus) => status.sync_type === syncType) || null
  }


  // Helper function to format datetime strings with proper timezone handling
  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'Never'
    
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) {
        console.warn(`Invalid date string: ${dateString}`)
        return 'Invalid Date'
      }
      
      return date.toLocaleString('en-US', {
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    } catch (error) {
      console.error(`Error formatting date: ${dateString}`, error)
      return 'Invalid Date'
    }
  }


  // No countdown time calculation needed since we only sync at specific date/time

  // No countdown time formatting needed since we only sync at specific date/time

  // Helper function to format sync status
  const formatSyncStatus = (status: SyncStatus | null) => {
    if (!status) {
      return {
        status: 'never_run',
        statusText: 'Never Run',
        statusColor: 'text-slate-400',
        statusBg: 'bg-slate-800/30',
        lastRun: 'Never',
        nextRun: 'N/A',
        records: '0',
        duration: 'N/A'
      }
    }

    const statusMap = {
      'running': { text: 'Running', color: 'text-blue-400', bg: 'bg-blue-800/30' },
      'success': { text: 'Success', color: 'text-green-400', bg: 'bg-green-800/30' },
      'error': { text: 'Error', color: 'text-red-400', bg: 'bg-red-800/30' },
      'failed': { text: 'Failed', color: 'text-orange-400', bg: 'bg-orange-800/30' },
      'never_run': { text: 'Never Run', color: 'text-slate-400', bg: 'bg-slate-800/30' }
    }

    const statusInfo = statusMap[status.status as keyof typeof statusMap] || statusMap['never_run']
    
    const lastRun = status.end_time 
      ? formatDateTime(status.end_time)
      : status.start_time 
        ? formatDateTime(status.start_time) + ' (running)'
        : 'Never'
    
    const duration = status.duration_ms 
      ? `${(status.duration_ms / 1000).toFixed(1)}s`
      : status.status === 'running' 
        ? 'Running...'
        : 'N/A'
    
    const records = status.records_processed > 0 
      ? `${status.records_successful}/${status.records_processed}`
      : '0'

    return {
      status: status.status,
      statusText: statusInfo.text,
      statusColor: statusInfo.color,
      statusBg: statusInfo.bg,
      lastRun,
      nextRun: 'N/A', // Will be calculated based on interval
      records,
      duration,
      errorMessage: status.error_message
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    setCurrentUser(null)
    queryClient.invalidateQueries({ queryKey: ['/api/auth/me'] })
    toast({
      title: '👋 Logged out',
      description: 'You have been logged out successfully',
      duration: 3000
    })
  }

  // Shift Mappings Handlers
  const handleOpenAddModal = () => {
    setNewShift({
      type: 'milling',
      name: '',
      start: '07:00',
      end: '15:00',
      displayName: ''
    })
    setShowAddShiftModal(true)
  }

  const handleCloseAddModal = () => {
    setShowAddShiftModal(false)
    setNewShift({
      type: 'milling',
      name: '',
      start: '07:00',
      end: '15:00',
      displayName: ''
    })
  }

  // Mutation for creating/updating shift
  const createShiftMutation = useMutation({
    mutationFn: (payload: {
      plant: string
      department: string
      shift_code: string
      start_time: string
      end_time: string
      sort_order: number
    }) => shiftApi.createOrUpdateShift(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/shifts'] })
      toast({
        title: '✅ Shift Added',
        description: `Shift ${newShift.name} added successfully`,
        duration: 3000
      })
      handleCloseAddModal()
    },
    onError: (error: any) => {
      toast({
        title: '❌ Failed to Add Shift',
        description: error?.message || 'An error occurred while adding the shift',
        duration: 5000,
        variant: 'destructive'
      })
    }
  })

  // Mutation for updating shift
  const updateShiftMutation = useMutation({
    mutationFn: (payload: {
      id?: number
      plant: string
      department: string
      shift_code: string
      start_time: string
      end_time: string
      sort_order: number
    }) => shiftApi.createOrUpdateShift(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/shifts'] })
      toast({
        title: '✅ Shift Updated',
        description: `Shift ${editingShift?.name} updated successfully`,
        duration: 3000
      })
      handleCloseEditModal()
    },
    onError: (error: any) => {
      toast({
        title: '❌ Failed to Update Shift',
        description: error?.message || 'An error occurred while updating the shift',
        duration: 5000,
        variant: 'destructive'
      })
    }
  })

  // Mutation for deleting shift
  const deleteShiftMutation = useMutation({
    mutationFn: (shiftId: number) => shiftApi.deleteShift(shiftId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/shifts'] })
      toast({
        title: '✅ Shift Deleted',
        description: `Shift ${deletingShift?.name} deleted successfully`,
        duration: 3000
      })
      handleCloseDeleteModal()
    },
    onError: (error: any) => {
      toast({
        title: '❌ Failed to Delete Shift',
        description: error?.message || 'An error occurred while deleting the shift',
        duration: 5000,
        variant: 'destructive'
      })
    }
  })

  const handleAddShift = () => {
    if (!newShift.name || !newShift.start || !newShift.end) {
      toast({
        title: '❌ Validation Error',
        description: 'Please fill in all required fields',
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    // Validate time format
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/
    if (!timeRegex.test(newShift.start) || !timeRegex.test(newShift.end)) {
      toast({
        title: '❌ Invalid Time Format',
        description: 'Please use HH:MM format (24-hour)',
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    // Check if shift name already exists in local state
    if (shiftMappings[newShift.type][newShift.name]) {
      toast({
        title: '❌ Shift Already Exists',
        description: `Shift ${newShift.name} already exists for ${newShift.type}`,
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    // Determine plant and department
    const department = newShift.type === 'milling' ? 'MILLING' : 'PACKING'
    // Get plant from existing shifts of same department, or use default
    const existingDeptShifts = shiftsData?.filter(
      (s: ShiftMaster) => s.department.toUpperCase() === department
    ) || []
    const plant = existingDeptShifts.length > 0 ? existingDeptShifts[0].plant : (newShift.type === 'milling' ? '3130' : '3131')

    // Calculate sort_order based on existing shifts of the same type
    const existingShifts = existingDeptShifts
    const maxSortOrder = existingShifts.length > 0
      ? Math.max(...existingShifts.map((s: ShiftMaster) => s.sort_order))
      : 0

    // Create shift via API
    createShiftMutation.mutate({
      plant,
      department,
      shift_code: newShift.name,
      start_time: newShift.start,
      end_time: newShift.end,
      sort_order: maxSortOrder + 1
    })
  }

  const handleOpenEditModal = (type: ShiftType, shiftName: string) => {
    const shift = shiftMappings[type][shiftName]
    if (shift) {
      setEditingShift({ type, name: shiftName })
      setNewShift({
        type,
        name: shiftName,
        start: shift.start,
        end: shift.end,
        displayName: shift.name
      })
      setShowEditShiftModal(true)
    }
  }

  const handleCloseEditModal = () => {
    setShowEditShiftModal(false)
    setEditingShift(null)
    setNewShift({
      type: 'milling',
      name: '',
      start: '07:00',
      end: '15:00',
      displayName: ''
    })
  }

  const handleUpdateShift = () => {
    if (!editingShift || !newShift.start || !newShift.end) {
      toast({
        title: '❌ Validation Error',
        description: 'Please fill in all required fields',
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    // Validate time format
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/
    if (!timeRegex.test(newShift.start) || !timeRegex.test(newShift.end)) {
      toast({
        title: '❌ Invalid Time Format',
        description: 'Please use HH:MM format (24-hour)',
        duration: 3000,
        variant: 'destructive'
      })
      return
    }

    // Find the shift ID from API data - match by department and shift_code (plant is less important)
    const department = editingShift.type === 'milling' ? 'MILLING' : 'PACKING'
    const existingShift = shiftsData?.find(
      (s: ShiftMaster) => 
        s.department.toUpperCase() === department && 
        s.shift_code === editingShift.name
    )

    if (!existingShift) {
      toast({
        title: '❌ Shift Not Found',
        description: `Could not find shift "${editingShift.name}" for ${department}. Please refresh the page.`,
        duration: 5000,
        variant: 'destructive'
      })
      return
    }

    // Update shift via API - preserve original plant value
    updateShiftMutation.mutate({
      id: existingShift.id,
      plant: existingShift.plant,
      department,
      shift_code: editingShift.name,
      start_time: newShift.start,
      end_time: newShift.end,
      sort_order: existingShift.sort_order
    })
  }

  const handleOpenDeleteModal = (type: ShiftType, shiftName: string) => {
    setDeletingShift({ type, name: shiftName })
    setShowDeleteShiftModal(true)
  }

  const handleCloseDeleteModal = () => {
    setShowDeleteShiftModal(false)
    setDeletingShift(null)
  }

  const handleConfirmDelete = () => {
    if (!deletingShift) return

    // Find the shift ID from API data - match by department and shift_code (plant is less important)
    const department = deletingShift.type === 'milling' ? 'MILLING' : 'PACKING'
    const existingShift = shiftsData?.find(
      (s: ShiftMaster) => 
        s.department.toUpperCase() === department && 
        s.shift_code === deletingShift.name
    )

    if (!existingShift) {
      toast({
        title: '❌ Shift Not Found',
        description: `Could not find shift "${deletingShift.name}" for ${department}. Please refresh the page.`,
        duration: 5000,
        variant: 'destructive'
      })
      handleCloseDeleteModal()
      return
    }

    // Delete shift via API
    deleteShiftMutation.mutate(existingShift.id)
  }

  // Helper function to get shift information using current state
  const getShiftInfo = (syncType: string, currentTime: Date = new Date()) => {
    const isMilling = syncType.toLowerCase().includes('milling') || syncType.toLowerCase().includes('raw_data')
    const schedules = isMilling ? shiftMappings.milling : shiftMappings.packing
    return getShiftInfoBase(schedules, syncType, currentTime)
  }

  const formatShiftTime = (value: Date | null) => {
    if (!value) return '—'
    return value.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  const millingShiftInfo = getShiftInfo('milling')
  const packingShiftInfo = getShiftInfo('packing')

  // Demo Mode Handlers
  const handleToggleDemoMode = async (enabled: boolean) => {
    setDemoModeLoading(true)
    try {
      await apiRequest('PUT', '/api/system/mode', { demo_mode: enabled })
      toast({
        title: enabled ? '🧪 Demo Mode Enabled' : '🏭 Production Mode Enabled',
        description: enabled 
          ? 'System is now using embedded SCADA emulator' 
          : 'System is now using production MSSQL database',
        duration: 3000,
      })
      refetchSystemMode()
      refetchEmulatorStatus()
    } catch (error: any) {
      toast({
        title: '❌ Failed to switch mode',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    } finally {
      setDemoModeLoading(false)
    }
  }

  const handleToggleMockSap = async (enabled: boolean) => {
    try {
      await apiRequest('PUT', '/api/system/mode', { mock_sap: enabled })
      toast({
        title: enabled ? '🧪 Mock SAP Enabled' : '📡 Real SAP Enabled',
        description: enabled 
          ? 'KPIs will be sent to mock server (localhost:6000)' 
          : 'KPIs will be sent to real SAP endpoint',
        duration: 3000,
      })
      refetchSystemMode()
    } catch (error: any) {
      toast({
        title: '❌ Failed to toggle Mock SAP',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    }
  }

  const handleEmulatorStart = async () => {
    setEmulatorActionLoading(true)
    try {
      await apiRequest('POST', '/api/emulator/start')
      toast({
        title: '🚀 Emulator Started',
        description: 'SCADA emulator is now generating data',
        duration: 3000,
      })
      refetchEmulatorStatus()
      refetchEmulatorScales()
    } catch (error: any) {
      toast({
        title: '❌ Failed to start emulator',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    } finally {
      setEmulatorActionLoading(false)
    }
  }

  const handleEmulatorStop = async () => {
    setEmulatorActionLoading(true)
    try {
      await apiRequest('POST', '/api/emulator/stop')
      toast({
        title: '⏹️ Emulator Stopped',
        description: 'SCADA emulator has been stopped',
        duration: 3000,
      })
      refetchEmulatorStatus()
      refetchEmulatorScales()
    } catch (error: any) {
      toast({
        title: '❌ Failed to stop emulator',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    } finally {
      setEmulatorActionLoading(false)
    }
  }

  const handleEmulatorConfigUpdate = async () => {
    try {
      const response = await apiRequest('PUT', '/api/emulator/config', {
        interval: emulatorConfig.interval,
        step_min: emulatorConfig.step_min,
        step_max: emulatorConfig.step_max,
      })
      
      // Update local state with confirmed values from server
      if (response) {
        setEmulatorConfig(prev => ({
          ...prev,
          interval: response.interval ?? prev.interval,
          step_min: response.step_min ?? prev.step_min,
          step_max: response.step_max ?? prev.step_max,
        }))
      }
      
      toast({
        title: '✅ Settings Applied',
        description: `Interval: ${emulatorConfig.interval}s, Step: ${emulatorConfig.step_min}-${emulatorConfig.step_max}`,
        duration: 3000,
      })
      refetchEmulatorStatus()
    } catch (error: any) {
      // #region agent log
      console.error('⚙️ DEBUG: Config update FAILED:', error);
      // #endregion
      toast({
        title: '❌ Failed to update config',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    }
  }

  const handleResetDemo = async (type: string) => {
    setResetLoading(type)
    try {
      let endpoint = ''
      let message = ''
      
      switch (type) {
        case 'kpi-tracking':
          endpoint = '/api/system/reset/kpi-tracking'
          message = 'KPI tracking baselines cleared'
          break
        case 'scada-aggregate':
          endpoint = '/api/system/reset/scada-aggregate'
          message = 'SCADA aggregate values cleared'
          break
        case 'kpi-snapshots':
          endpoint = '/api/system/reset/kpi-snapshots'
          message = 'KPI snapshots cleared'
          break
        case 'all-demo-data':
          endpoint = '/api/system/reset/all-demo-data'
          message = 'All demo data cleared and emulator reset'
          break
        case 'emulator-zero':
          endpoint = '/api/emulator/reset/zero'
          message = 'Emulator values reset to zero'
          break
        case 'emulator-realistic':
          endpoint = '/api/emulator/reset/realistic'
          message = 'Emulator values reset to realistic values'
          break
        case 'refresh-baselines':
          endpoint = '/api/emulator/refresh-baselines'
          message = 'Order baselines refreshed to current SCADA values'
          break
        case 'reset-order-tracking':
          endpoint = '/api/emulator/reset-order-tracking'
          message = 'All order tracking values reset to 0'
          break
        case 'delete-all-orders':
          endpoint = '/api/emulator/delete-all-orders'
          message = 'All orders deleted from process orders table'
          break
        default:
          return
      }
      
      const res = await apiRequest('POST', endpoint)
      const desc = res?.deleted_count != null ? `${message} (${res.deleted_count} deleted)` : message
      toast({
        title: type === 'delete-all-orders' ? '🗑️ Delete Complete' : '🔄 Reset Complete',
        description: desc,
        duration: 3000,
      })
      refetchSystemStats()
      refetchEmulatorScales()
      refetchEmulatorStatus()
    } catch (error: any) {
      toast({
        title: '❌ Reset Failed',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    } finally {
      setResetLoading(null)
    }
  }

  const handleToggleCategory = async (category: string, active: boolean) => {
    try {
      await apiRequest('PUT', `/api/emulator/category/${category}`, { active })
      toast({
        title: active ? '✅ Category Enabled' : '⏹️ Category Disabled',
        description: `${category} scales ${active ? 'activated' : 'deactivated'}`,
        duration: 2000,
      })
      refetchEmulatorScales()
      refetchEmulatorStatus()
    } catch (error: any) {
      toast({
        title: '❌ Failed to toggle category',
        description: error?.message || 'An error occurred',
        variant: 'destructive',
        duration: 5000,
      })
    }
  }

  return (
    <WaterSystemLayout 
      title="Admin Panel" 
      subtitle="System administration and configuration"
      onLogout={handleLogout}
    >
      <div className="p-4 w-full h-full overflow-hidden flex flex-col">
        
        {/* Authentication Status - Always visible at top */}
        {!currentUser && (
          <Card className="bg-slate-800/30 light:bg-white border-slate-700 light:border-gray-200 light:shadow-md mb-4 flex-shrink-0">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-white light:text-gray-900 font-medium mb-1">
                    🔐 Authentication Required
                  </h3>
                  <p className="text-slate-400 light:text-gray-600 text-sm">
                    Please login to access sync interval settings and other admin features.
                  </p>
                </div>
                <Button
                  onClick={() => setShowLoginModal(true)}
                  className="!bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 !text-white shadow-lg"
                >
                  <Shield className="h-4 w-4 mr-2" />
                  Login
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* User Info Bar - Always visible when logged in */}
        {currentUser && (
          <div className="bg-slate-800/50 light:bg-gray-100 rounded-lg p-3 mb-4 flex-shrink-0 border border-slate-700/50 light:border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-cyan-600 rounded-full flex items-center justify-center">
                  <User className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="text-white light:text-gray-900 font-medium text-sm">
                    {currentUser.full_name || currentUser.username}
                  </p>
                  <p className="text-slate-400 light:text-gray-600 text-xs">
                    {currentUser.roles?.join(', ')}
                  </p>
                </div>
              </div>
              <Button
                onClick={handleLogout}
                size="sm"
                className="!bg-red-600 hover:!bg-red-700 !text-white"
              >
                Logout
              </Button>
            </div>
          </div>
        )}

        {/* Main Tabbed Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="flex-shrink-0 w-full justify-start gap-1 mb-4 flex-wrap h-auto p-1">
            <TabsTrigger value="system" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span className="hidden sm:inline">System</span>
            </TabsTrigger>
            <TabsTrigger value="shifts" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">Shifts</span>
            </TabsTrigger>
            <TabsTrigger value="sap" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              <span className="hidden sm:inline">SAP Integration</span>
            </TabsTrigger>
            <TabsTrigger value="email" className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              <span className="hidden sm:inline">Email</span>
            </TabsTrigger>
            <TabsTrigger value="branding" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              <span className="hidden sm:inline">Branding</span>
            </TabsTrigger>
            <TabsTrigger value="demo" className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              <span className="hidden sm:inline">Demo Mode</span>
            </TabsTrigger>
            <TabsTrigger value="logs" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              <span className="hidden sm:inline">SAP Logs</span>
            </TabsTrigger>
          </TabsList>

          {/* SYSTEM TAB */}
          <TabsContent value="system" className="flex-1 overflow-y-auto mt-0">
            <div className="space-y-4">
              {/* Time Sync Status */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <h3 className="text-white light:text-gray-900 font-semibold mb-4 flex items-center gap-2">
                  <Clock className="h-5 w-5 text-cyan-400 light:text-blue-600" />
                  System Time Synchronization
                </h3>
                {serverTimeData ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-600/30 light:bg-white rounded-lg p-3 border border-slate-500/30 light:border-gray-200">
                        <div className="flex items-center gap-2 mb-1">
                          <Database className="h-3.5 w-3.5 text-cyan-400 light:text-blue-600" />
                          <span className="text-slate-300 light:text-gray-700 text-xs font-medium">Server Time</span>
                        </div>
                        <p className="text-white light:text-gray-900 text-base font-mono font-bold">
                          {serverTimeData.server_time_formatted}
                        </p>
                        <p className="text-slate-400 light:text-gray-600 text-xs mt-1">
                          {serverTimeData.server_timezone}
                        </p>
                      </div>
                      <div className="bg-slate-600/30 light:bg-white rounded-lg p-3 border border-slate-500/30 light:border-gray-200">
                        <div className="flex items-center gap-2 mb-1">
                          <Clock className="h-3.5 w-3.5 text-cyan-400 light:text-blue-600" />
                          <span className="text-slate-300 light:text-gray-700 text-xs font-medium">Client Time (PC)</span>
                        </div>
                        <p className="text-white light:text-gray-900 text-base font-mono font-bold">
                          {clientTime || 'Loading...'}
                        </p>
                        <p className="text-slate-400 light:text-gray-600 text-xs mt-1">
                          {Intl.DateTimeFormat().resolvedOptions().timeZone}
                        </p>
                      </div>
                    </div>
                    <div className="rounded-lg p-3 border bg-slate-600/30 light:bg-white border-slate-500/30 light:border-gray-200">
                      <div className="flex items-center gap-2 mb-2">
                        <Timer className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                        <p className="text-slate-300 light:text-gray-700 text-xs font-medium">Current Shift Status</p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="space-y-1">
                          <p className="text-slate-300 light:text-gray-700 font-medium">Milling</p>
                          <p className="text-white light:text-gray-900 font-mono font-bold">
                            {millingShiftInfo.currentShift}
                          </p>
                          <p className="text-slate-300 light:text-gray-700">
                            {millingShiftInfo.shiftInfo
                              ? `Start ${millingShiftInfo.shiftInfo.start} - End ${millingShiftInfo.shiftInfo.end}`
                              : 'No active shift'}
                          </p>
                          <p className="text-slate-400 light:text-gray-600">
                            Next end: {formatShiftTime(millingShiftInfo.nextShiftEnd?.endTime ?? null)}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-slate-300 light:text-gray-700 font-medium">Packing</p>
                          <p className="text-white light:text-gray-900 font-mono font-bold">
                            {packingShiftInfo.currentShift}
                          </p>
                          <p className="text-slate-300 light:text-gray-700">
                            {packingShiftInfo.shiftInfo
                              ? `Start ${packingShiftInfo.shiftInfo.start} - End ${packingShiftInfo.shiftInfo.end}`
                              : 'No active shift'}
                          </p>
                          <p className="text-slate-400 light:text-gray-600">
                            Next end: {formatShiftTime(packingShiftInfo.nextShiftEnd?.endTime ?? null)}
                          </p>
                        </div>
                      </div>
                    </div>
                    <Button
                      onClick={() => refetchServerTime()}
                      size="sm"
                      variant="outline"
                      className="!border-cyan-600 !text-cyan-600 hover:!bg-cyan-600 hover:!text-white"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh Time
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-slate-400 light:text-gray-600">Loading time information...</p>
                  </div>
                )}
              </div>

            {/* System text format */}
            <SystemTextFormatSection />
            </div>
          </TabsContent>

          {/* SHIFTS TAB */}
          <TabsContent value="shifts" className="flex-1 overflow-y-auto mt-0">
            <div className="space-y-4">
              {/* Info Banner */}
              <div className="bg-slate-700/50 light:bg-blue-50 border border-cyan-500/30 light:border-blue-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Settings className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  <h3 className="text-cyan-400 light:text-blue-800 font-semibold text-sm">Shift Configuration</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <p className="text-slate-300 light:text-blue-700">
                    • <strong>Milling:</strong> Typically 3 shifts (A, B, C)
                  </p>
                  <p className="text-slate-300 light:text-blue-700">
                    • <strong>Packing:</strong> Typically 2 shifts (A, B)
                  </p>
                  <p className="text-slate-300 light:text-blue-700">
                    • <strong>Format:</strong> 24-hour (HH:MM)
                  </p>
                  <p className="text-slate-300 light:text-blue-700">
                    • <strong>Overnight:</strong> End time can be earlier than start
                  </p>
                </div>
              </div>

              {/* Add Shift Button */}
              <div className="flex justify-end">
                <Button
                  onClick={handleOpenAddModal}
                  className="!bg-cyan-600 hover:!bg-cyan-700 !text-white"
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add New Shift
                </Button>
              </div>
              
              {/* Shifts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Milling Shifts */}
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                  <h4 className="text-cyan-400 light:text-blue-800 font-semibold mb-3 flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    Milling Shifts
                  </h4>
                  {Object.keys(shiftMappings.milling).length === 0 ? (
                    <p className="text-slate-400 light:text-gray-600 text-sm">No shifts configured</p>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(shiftMappings.milling).map(([shiftName, shiftInfo]) => (
                        <div key={shiftName} className="bg-slate-600/30 light:bg-white rounded-lg p-3 border border-slate-600 light:border-gray-200 hover:border-cyan-500/50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-white light:text-gray-900 font-semibold">{shiftName}</span>
                              </div>
                              <div className="flex items-center gap-4 text-xs">
                                <span className="text-slate-300 light:text-gray-700">
                                  <span className="font-medium">Start:</span> <span className="text-white light:text-gray-900">{shiftInfo.start}</span>
                                </span>
                                <span className="text-slate-300 light:text-gray-700">
                                  <span className="font-medium">End:</span> <span className="text-white light:text-gray-900">{shiftInfo.end}</span>
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenEditModal('milling', shiftName)}
                                className="h-8 w-8 p-0 hover:bg-cyan-600/20"
                              >
                                <Edit className="h-3.5 w-3.5 text-cyan-400" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenDeleteModal('milling', shiftName)}
                                className="h-8 w-8 p-0 hover:bg-red-600/20"
                              >
                                <Trash2 className="h-3.5 w-3.5 text-red-400" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Packing Shifts */}
                <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                  <h4 className="text-cyan-400 light:text-blue-800 font-semibold mb-3 flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    Packing Shifts
                  </h4>
                  {Object.keys(shiftMappings.packing).length === 0 ? (
                    <p className="text-slate-400 light:text-gray-600 text-sm">No shifts configured</p>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(shiftMappings.packing).map(([shiftName, shiftInfo]) => (
                        <div key={shiftName} className="bg-slate-600/30 light:bg-white rounded-lg p-3 border border-slate-600 light:border-gray-200 hover:border-cyan-500/50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-white light:text-gray-900 font-semibold">{shiftName}</span>
                              </div>
                              <div className="flex items-center gap-4 text-xs">
                                <span className="text-slate-300 light:text-gray-700">
                                  <span className="font-medium">Start:</span> <span className="text-white light:text-gray-900">{shiftInfo.start}</span>
                                </span>
                                <span className="text-slate-300 light:text-gray-700">
                                  <span className="font-medium">End:</span> <span className="text-white light:text-gray-900">{shiftInfo.end}</span>
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenEditModal('packing', shiftName)}
                                className="h-8 w-8 p-0 hover:bg-cyan-600/20"
                              >
                                <Edit className="h-3.5 w-3.5 text-cyan-400" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenDeleteModal('packing', shiftName)}
                                className="h-8 w-8 p-0 hover:bg-red-600/20"
                              >
                                <Trash2 className="h-3.5 w-3.5 text-red-400" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* SAP INTEGRATION TAB */}
          <TabsContent value="sap" className="flex-1 overflow-y-auto mt-0">
            <div className="space-y-4">
              {/* Info Banner */}
              <div className="bg-slate-700/50 light:bg-blue-50 border border-cyan-500/30 light:border-blue-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  <h3 className="text-cyan-400 light:text-blue-800 font-semibold text-sm">SAP Integration</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <p className="text-slate-300 light:text-blue-700">• <strong>KPI Sync:</strong> Send calculated KPIs to SAP</p>
                  <p className="text-slate-300 light:text-blue-700">• <strong>Endpoints:</strong> Milling, Packing KPI APIs</p>
                  <p className="text-slate-300 light:text-blue-700">• <strong>Auto-retry:</strong> Built-in error handling</p>
                </div>
              </div>

              {/* SAP Connection Toggle - Real SAP vs Mock */}
              <div className="flex items-center justify-between bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <div className="flex items-center gap-3">
                  {demoMode.mock_sap ? (
                    <Server className="h-5 w-5 text-amber-400" />
                  ) : (
                    <Network className="h-5 w-5 text-green-400" />
                  )}
                  <div>
                    <span className="text-white light:text-gray-900 text-sm font-medium">
                      SAP Connection: {demoMode.mock_sap ? 'Mock Server' : 'Real SAP'}
                    </span>
                    <p className="text-slate-400 light:text-gray-600 text-xs">
                      {demoMode.mock_sap ? 'KPIs sent to localhost:6000' : 'KPIs sent to production SAP'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleToggleMockSap(!demoMode.mock_sap)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    demoMode.mock_sap ? 'bg-amber-500' : 'bg-green-500'
                  }`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    demoMode.mock_sap ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>

              {/* SAP Connection Settings */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <Server className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  <h3 className="text-white light:text-gray-900 font-semibold text-sm">SAP Connection Settings</h3>
                  <span className="text-xs text-amber-400 light:text-amber-600 ml-2">(Demo)</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Base URL */}
                  <div>
                    <label className="text-slate-300 light:text-gray-700 text-xs mb-1 block">SAP Base URL</label>
                    <Input
                      value={sapBaseUrl}
                      onChange={(e) => setSapBaseUrl(e.target.value)}
                      placeholder="https://vhmioqs4ci.sap.mc3.com.sa:44300"
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900"
                    />
                  </div>
                  
                  {/* SAP Client */}
                  <div>
                    <label className="text-slate-300 light:text-gray-700 text-xs mb-1 block">SAP Client</label>
                    <Input
                      value={sapClient}
                      onChange={(e) => setSapClient(e.target.value)}
                      placeholder="250"
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900"
                    />
                  </div>
                </div>
              </div>

              {/* SAP Order Sync Interval */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <Timer className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  <h3 className="text-white light:text-gray-900 font-semibold text-sm">SAP Order Sync Interval</h3>
                </div>
                <p className="text-slate-400 light:text-gray-600 text-xs mb-3">
                  Configure how often the system automatically syncs orders from SAP. Value in minutes (1-1440).
                </p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 max-w-xs">
                    <Input
                      type="number"
                      value={sapReceivingInterval}
                      onChange={(e) => setSapReceivingInterval(e.target.value === '' ? '' : Number(e.target.value))}
                      min={1}
                      max={1440}
                      placeholder="Enter minutes (1-1440)"
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900"
                      disabled={!canChangeSyncInterval() && !isAdmin()}
                    />
                  </div>
                  <Button
                    onClick={saveSapReceivingInterval}
                    disabled={sapIntervalSaving || sapReceivingInterval === '' || (!canChangeSyncInterval() && !isAdmin())}
                    className={`${
                      sapIntervalSaving
                        ? '!bg-slate-600 !text-slate-400 cursor-not-allowed'
                        : '!bg-green-600 hover:!bg-green-700 !text-white'
                    }`}
                    size="sm"
                  >
                    {sapIntervalSaving ? (
                      <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Saving...</>
                    ) : (
                      <><Save className="h-4 w-4 mr-2" />Save</>
                    )}
                  </Button>
                </div>
                {getLocalSyncSetting('process_orders')?.sync_interval_minutes && (
                  <p className="text-slate-400 light:text-gray-600 text-xs mt-2">
                    Current: <span className="text-cyan-400 light:text-blue-600 font-medium">{getLocalSyncSetting('process_orders')?.sync_interval_minutes} min</span>
                  </p>
                )}
                {!canChangeSyncInterval() && !isAdmin() && (
                  <p className="text-amber-400 light:text-amber-600 text-xs mt-2">
                    ⚠️ You don't have permission to change the sync interval.
                  </p>
                )}
              </div>
            </div>
          </TabsContent>

          {/* EMAIL TAB */}
          <TabsContent value="email" className="flex-1 overflow-y-auto mt-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* SMTP Profiles */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <h3 className="text-white light:text-gray-900 font-semibold mb-3 flex items-center gap-2">
                  <Mail className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  SMTP Profiles
                </h3>
                
                <div className="space-y-3">
                  {smtpProfiles.length === 0 ? (
                    <p className="text-slate-400 light:text-gray-600 text-sm">No profiles added yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {smtpProfiles.map((profile) => (
                        <div key={profile.id} className="flex items-center justify-between bg-slate-600/30 light:bg-white rounded p-2 border border-slate-600 light:border-gray-200">
                          <div>
                            <p className="text-white light:text-gray-900 font-medium text-sm">{profile.name}</p>
                            <p className="text-slate-400 light:text-gray-600 text-xs">{profile.host}:{profile.port}</p>
                          </div>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0"><Edit className="h-3 w-3" /></Button>
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-400"><Trash2 className="h-3 w-3" /></Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="border-t border-slate-600 light:border-gray-200 pt-3 mt-3">
                    <p className="text-slate-300 light:text-gray-700 text-xs font-medium mb-2">Add New Profile</p>
                    <div className="grid grid-cols-2 gap-2">
                      <Input placeholder="Name" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                      <Input placeholder="Host" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                      <Input placeholder="Port" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                      <Input placeholder="Username" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                      <Input type="password" placeholder="Password" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                      <Input placeholder="Sender Email" className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8" />
                    </div>
                    <Button className="!bg-cyan-600 hover:!bg-cyan-700 !text-white mt-2 w-full" size="sm">
                      <Plus className="h-3 w-3 mr-1" />Add Profile
                    </Button>
                  </div>
                </div>
              </div>

              {/* Email Scheduler */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <h3 className="text-white light:text-gray-900 font-semibold mb-3 flex items-center gap-2">
                  <Settings className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                  Email Report Scheduler
                </h3>
                
                <div className="space-y-3">
                  {/* Enable Toggle */}
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setEmailSchedule({...emailSchedule, enabled: !emailSchedule.enabled})}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-all ${
                        emailSchedule.enabled ? 'bg-cyan-600' : 'bg-slate-600'
                      }`}
                    >
                      <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-all ${
                        emailSchedule.enabled ? 'translate-x-5' : 'translate-x-1'
                      }`} />
                    </button>
                    <Label className="text-white light:text-gray-900 text-sm">Enable Daily Reports</Label>
                  </div>

                  {/* Email Fields */}
                  <div className="grid grid-cols-1 gap-2">
                    <Input
                      value={emailSchedule.senderEmail}
                      onChange={(e) => setEmailSchedule({...emailSchedule, senderEmail: e.target.value})}
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8"
                      placeholder="Sender Email"
                    />
                    <Input
                      value={emailSchedule.recipientEmail}
                      onChange={(e) => setEmailSchedule({...emailSchedule, recipientEmail: e.target.value})}
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8"
                      placeholder="Recipient Email"
                    />
                    <Input
                      type="time"
                      value={emailSchedule.sendTime}
                      onChange={(e) => setEmailSchedule({...emailSchedule, sendTime: e.target.value})}
                      className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 text-xs h-8"
                    />
                  </div>

                  {/* Report Toggles */}
                  <div className="space-y-2">
                    <p className="text-slate-300 light:text-gray-700 text-xs font-medium">Include in Report:</p>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { key: 'includeDailyReport', label: 'Daily', icon: Calendar },
                        { key: 'includeWeeklyReport', label: 'Weekly', icon: BarChart3 },
                        { key: 'includeMonthlyReport', label: 'Monthly', icon: PieChart },
                        { key: 'includeMaterialConsumptionReport', label: 'Materials', icon: Package },
                        { key: 'includeDetailedReport', label: 'Detailed', icon: ListChecks },
                      ].map(({ key, label, icon: Icon }) => (
                        <div key={key} className="flex items-center space-x-2">
                          <button
                            onClick={() => setEmailSchedule({...emailSchedule, [key]: !emailSchedule[key as keyof typeof emailSchedule]})}
                            className={`relative inline-flex h-4 w-7 items-center rounded-full transition-all ${
                              emailSchedule[key as keyof typeof emailSchedule] ? 'bg-cyan-600' : 'bg-slate-600'
                            }`}
                          >
                            <span className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-all ${
                              emailSchedule[key as keyof typeof emailSchedule] ? 'translate-x-4' : 'translate-x-0.5'
                            }`} />
                          </button>
                          <Label className="text-slate-300 light:text-gray-700 text-xs flex items-center gap-1">
                            <Icon className="h-3 w-3" />{label}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Button onClick={handleSaveSchedule} className="!bg-cyan-600 hover:!bg-cyan-700 !text-white w-full" size="sm">
                    <Save className="h-3 w-3 mr-1" />Save Schedule
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* BRANDING TAB */}
          <TabsContent value="branding" className="flex-1 overflow-y-auto mt-0">
            <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
              <h3 className="text-white light:text-gray-900 font-semibold mb-4 flex items-center gap-2">
                <Upload className="h-4 w-4 text-cyan-400 light:text-blue-600" />
                Upload Logo
              </h3>
              
              <div className="flex flex-col space-y-4">
                <div className="flex gap-3">
                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    className="!bg-cyan-600 hover:!bg-cyan-700 !text-white"
                    size="sm"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Choose File
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleLogoUpload}
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    disabled={!currentLogo}
                    className="!border-cyan-600 !text-cyan-600 hover:!bg-cyan-600 hover:!text-white disabled:!border-slate-600 disabled:!text-slate-400"
                    size="sm"
                  >
                    Upload Logo
                  </Button>
                </div>
                
                <div>
                  <p className="text-slate-300 light:text-gray-700 text-sm font-medium mb-2">Current Logo:</p>
                  {currentLogo ? (
                    <img 
                      src={currentLogo} 
                      alt="Current Logo" 
                      className="max-w-xs max-h-24 object-contain border border-slate-600 light:border-gray-300 rounded"
                    />
                  ) : (
                    <div className="w-48 h-12 bg-slate-700/50 light:bg-gray-100 rounded border border-slate-600 light:border-gray-300 flex items-center justify-center">
                      <span className="text-slate-400 light:text-gray-500 text-xs">No logo uploaded</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* DEMO MODE TAB */}
          <TabsContent value="demo" className="flex-1 overflow-y-auto mt-0">
            <div className="space-y-4">
              
              {/* Header with Mode Toggle */}
              <div className="flex items-center justify-between bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <div className="flex items-center gap-3">
                  {demoMode.demo_mode ? (
                    <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                      <Zap className="h-5 w-5 text-amber-400" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Database className="h-5 w-5 text-green-400" />
                    </div>
                  )}
                  <div>
                    <h3 className="text-white light:text-gray-900 font-semibold">
                      {demoMode.demo_mode ? 'Demo Mode Active' : 'Production Mode'}
                    </h3>
                    <p className="text-slate-400 light:text-gray-600 text-xs">
                      {demoMode.demo_mode ? 'Using SCADA emulator' : 'Using real database'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {/* Emulator Status */}
                  {demoMode.demo_mode && (
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${emulatorConfig.running ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
                      <span className="text-slate-400 light:text-gray-600 text-xs">
                        {emulatorConfig.running ? 'Emulator Running' : 'Emulator Stopped'}
                      </span>
                    </div>
                  )}
                  <button
                    onClick={() => handleToggleDemoMode(!demoMode.demo_mode)}
                    disabled={demoModeLoading}
                    className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                      demoMode.demo_mode 
                        ? 'bg-amber-500 hover:bg-amber-600 text-white' 
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    } ${demoModeLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {demoModeLoading ? 'Switching...' : (demoMode.demo_mode ? 'Switch to Production' : 'Switch to Demo')}
                  </button>
                </div>
              </div>

              {/* Show Auto Validation button on Order Validation page (frontend-only, localStorage) */}
              <div className="flex items-center justify-between bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200">
                <div>
                  <h3 className="text-white light:text-gray-900 font-semibold">Show Auto Validation button</h3>
                  <p className="text-slate-400 light:text-gray-600 text-xs mt-0.5">
                    When enabled, the Start/Stop Auto Validation buttons appear on the Order Validation page.
                  </p>
                </div>
                <Switch
                  checked={showAutoValidationButton}
                  onCheckedChange={(checked) => {
                    setShowAutoValidationButton(checked)
                    localStorage.setItem('show_auto_validation_button', checked ? 'true' : 'false')
                  }}
                />
              </div>

              {/* Emulator Settings - Only visible in Demo Mode */}
              {demoMode.demo_mode && (
                <>
                  {/* Emulator Controls */}
                  <div className="bg-white dark:bg-slate-700/30 rounded-lg p-4 border border-gray-200 dark:border-slate-600">
                    <div className="flex flex-wrap items-center gap-4">
                      {/* Start/Stop Button */}
                      <button
                        onClick={() => {
                          console.log('🔴 DEBUG: Start/Stop button clicked, running =', emulatorConfig.running);
                          emulatorConfig.running ? handleEmulatorStop() : handleEmulatorStart();
                        }}
                        disabled={emulatorActionLoading}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                          emulatorConfig.running 
                            ? 'bg-red-500 hover:bg-red-600 text-white' 
                            : 'bg-green-500 hover:bg-green-600 text-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {emulatorConfig.running ? (
                            <Square className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                          {emulatorConfig.running ? 'Stop' : 'Start'}
                        </div>
                      </button>

                      <div className="h-8 w-px bg-gray-300 dark:bg-slate-600" />
                      
                      {/* Interval Setting */}
                      <div className="flex items-center gap-2">
                        <label className="text-gray-700 dark:text-slate-300 text-sm font-medium">Interval:</label>
                        <Input
                          type="number"
                          min="1"
                          max="60"
                          value={emulatorConfig.interval}
                          onChange={(e) => setEmulatorConfig({...emulatorConfig, interval: parseFloat(e.target.value) || 10})}
                          className="bg-gray-50 dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white h-8 text-sm w-16"
                        />
                        <span className="text-gray-500 dark:text-slate-400 text-sm">sec</span>
                      </div>

                      <div className="h-8 w-px bg-gray-300 dark:bg-slate-600" />

                      {/* Step Setting */}
                      <div className="flex items-center gap-2">
                        <label className="text-gray-700 dark:text-slate-300 text-sm font-medium">Step:</label>
                        <Input
                          type="number"
                          min="1"
                          max="100"
                          value={emulatorConfig.step_min}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 1
                            setEmulatorConfig({...emulatorConfig, step_min: val, step_max: Math.max(val, emulatorConfig.step_max)})
                          }}
                          className="bg-gray-50 dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white h-8 text-sm w-16"
                        />
                        <span className="text-gray-500 dark:text-slate-400 text-sm">to</span>
                        <Input
                          type="number"
                          min="1"
                          max="1000"
                          value={emulatorConfig.step_max}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 10
                            setEmulatorConfig({...emulatorConfig, step_max: val, step_min: Math.min(val, emulatorConfig.step_min)})
                          }}
                          className="bg-gray-50 dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white h-8 text-sm w-16"
                        />
                        <span className="text-gray-500 dark:text-slate-400 text-sm">per tick</span>
                      </div>

                      <div className="h-8 w-px bg-gray-300 dark:bg-slate-600" />

                      {/* Apply Button */}
                      <button
                        onClick={handleEmulatorConfigUpdate}
                        className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-600 text-white font-medium text-sm transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Save className="h-4 w-4" />
                          Apply
                        </div>
                      </button>

                      {/* Reset to Zero Button */}
                      <button
                        onClick={() => handleResetDemo('emulator-zero')}
                        disabled={resetLoading === 'emulator-zero'}
                        className="px-4 py-2 rounded-lg bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-700 dark:text-red-300 font-medium text-sm transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          {resetLoading === 'emulator-zero' ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <RotateCcw className="h-4 w-4" />
                          )}
                          Reset to 0
                        </div>
                      </button>

                      {/* Reset to Realistic Button */}
                      <button
                        onClick={() => handleResetDemo('emulator-realistic')}
                        disabled={resetLoading === 'emulator-realistic'}
                        className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-slate-600 hover:bg-gray-200 dark:hover:bg-slate-500 text-gray-700 dark:text-slate-200 font-medium text-sm transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          {resetLoading === 'emulator-realistic' ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <RotateCcw className="h-4 w-4" />
                          )}
                          Reset Realistic
                        </div>
                      </button>

                      {/* Refresh Baselines Button - for when orders are stuck */}
                      <button
                        onClick={() => handleResetDemo('refresh-baselines')}
                        disabled={resetLoading === 'refresh-baselines'}
                        className="px-4 py-2 rounded-lg bg-cyan-100 dark:bg-cyan-900/30 hover:bg-cyan-200 dark:hover:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300 font-medium text-sm transition-colors"
                        title="Refresh baselines for in-progress orders to current SCADA values. Use when orders are stuck because current values are less than baselines."
                      >
                        <div className="flex items-center gap-2">
                          {resetLoading === 'refresh-baselines' ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
                          Refresh Baselines
                        </div>
                      </button>

                      {/* Reset Order Tracking Button - Only visible in Demo Mode */}
                      {demoMode.demo_mode && (
                        <button
                          onClick={() => handleResetDemo('reset-order-tracking')}
                          disabled={resetLoading === 'reset-order-tracking'}
                          className="px-4 py-2 rounded-lg bg-orange-100 dark:bg-orange-900/30 hover:bg-orange-200 dark:hover:bg-orange-900/50 text-orange-700 dark:text-orange-300 font-medium text-sm transition-colors"
                          title="Reset all order tracking values to 0 (confirmed_qty, shift weights, byproduct quantities, baselines). Validated orders will be set back to Pending."
                        >
                          <div className="flex items-center gap-2">
                            {resetLoading === 'reset-order-tracking' ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <RotateCcw className="h-4 w-4" />
                            )}
                            Reset Order Tracking
                          </div>
                        </button>
                      )}

                      {/* Delete All Orders Button - Only visible in Demo Mode */}
                      {demoMode.demo_mode && (
                        <button
                          onClick={() => {
                            if (window.confirm('Delete all orders from the in-process order table? This cannot be undone.')) {
                              handleResetDemo('delete-all-orders')
                            }
                          }}
                          disabled={resetLoading === 'delete-all-orders'}
                          className="px-4 py-2 rounded-lg bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-700 dark:text-red-300 font-medium text-sm transition-colors"
                          title="Permanently remove all orders from the process orders table."
                        >
                          <div className="flex items-center gap-2">
                            {resetLoading === 'delete-all-orders' ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                            Delete All Orders
                          </div>
                        </button>
                      )}
                    </div>

                    {/* Settings hint */}
                    <p className="text-gray-500 dark:text-slate-400 text-xs mt-2">
                      Values increase by {emulatorConfig.step_min}-{emulatorConfig.step_max} every {emulatorConfig.interval}s. Click "Apply" to save changes.
                    </p>
                  </div>

                  {/* Totalizer Controls by Category */}
                  <div className="bg-white dark:bg-slate-700/30 rounded-lg p-4 border border-gray-200 dark:border-slate-600">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-gray-900 dark:text-white font-semibold flex items-center gap-2">
                        <Gauge className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
                        Totalizer Configuration
                      </h3>
                      <p className="text-gray-500 dark:text-slate-400 text-xs">Toggle which values are increasing</p>
                    </div>

                    {/* Debug info */}
                    {!emulatorScales && (
                      <div className="text-center py-8">
                        <p className="text-gray-500 dark:text-slate-400">Loading scales...</p>
                        {emulatorScalesError && (
                          <p className="text-red-500 text-sm mt-2">Error: {(emulatorScalesError as Error).message}</p>
                        )}
                      </div>
                    )}

                    {emulatorScales && !emulatorScales.categories && (
                      <div className="text-center py-8">
                        <p className="text-amber-500">No categories found in API response</p>
                        <pre className="text-xs text-left bg-gray-100 dark:bg-slate-800 p-2 mt-2 rounded overflow-auto max-h-32">
                          {JSON.stringify(emulatorScales, null, 2)}
                        </pre>
                      </div>
                    )}

                    {emulatorScales?.categories && Object.keys(emulatorScales.categories).length === 0 && (
                      <div className="text-center py-8">
                        <p className="text-amber-500">Categories object is empty</p>
                      </div>
                    )}

                    {emulatorScales?.categories && Object.keys(emulatorScales.categories).length > 0 && (
                      <div className="space-y-4">
                        {Object.entries(emulatorScales.categories).map(([categoryKey, category]) => {
                          const categoryFields = category.fields || []
                          
                          // Group HI/LO pairs into logical totalizers
                          const totalizers: { name: string, displayName: string, fields: string[] }[] = []
                          const processed = new Set<string>()
                          
                          categoryFields.forEach((field: string) => {
                            if (processed.has(field)) return
                            
                            const baseName = field.replace('_HI', '').replace('_LO', '').replace('_TOT', '')
                            const hiField = categoryFields.find((f: string) => f === `${baseName}_HI`)
                            const loField = categoryFields.find((f: string) => f === `${baseName}_LO`)
                            const totField = categoryFields.find((f: string) => f === `${baseName}_TOT`)
                            
                            const relatedFields = [hiField, loField, totField].filter(Boolean) as string[]
                            
                            if (relatedFields.length > 0) {
                              relatedFields.forEach(f => processed.add(f))
                              // Format display name nicely
                              const displayName = baseName
                                .replace(/_/g, ' ')
                                .replace(/DM (\d+)/, 'DM $1')
                                .replace(/PALLETIZER/i, 'Palletizer')
                                .replace(/WM (\d+)/, 'Water Meter $1')
                              totalizers.push({ name: baseName, displayName, fields: relatedFields })
                            } else if (!field.endsWith('_HI') && !field.endsWith('_LO') && !field.endsWith('_TOT')) {
                              // Standalone field
                              processed.add(field)
                              const displayName = field.replace(/_/g, ' ')
                              totalizers.push({ name: field, displayName, fields: [field] })
                            }
                          })
                          
                          // Count active totalizers (a totalizer is active if any of its fields are active)
                          const activeTotalizers = totalizers.filter(t => 
                            t.fields.some(f => emulatorScales.scales?.[f]?.active)
                          ).length
                          const allActive = activeTotalizers === totalizers.length && totalizers.length > 0
                          
                          return (
                            <div key={categoryKey} className="bg-white dark:bg-slate-600/20 rounded-lg p-3 border border-gray-200 dark:border-slate-500/20">
                              {/* Category Header */}
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                  <div 
                                    className="w-4 h-4 rounded-full" 
                                    style={{ backgroundColor: category.color }}
                                  />
                                  <div>
                                    <span className="text-gray-900 dark:text-white font-medium text-sm">{category.name}</span>
                                    <p className="text-gray-500 dark:text-slate-400 text-xs">{totalizers.length} totalizers</p>
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleToggleCategory(categoryKey, !allActive)}
                                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                                    allActive 
                                      ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-500/30' 
                                      : 'bg-gray-100 dark:bg-slate-500/20 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-500/30'
                                  }`}
                                >
                                  {allActive ? 'All ON' : activeTotalizers > 0 ? `${activeTotalizers} ON` : 'All OFF'}
                                </button>
                              </div>
                              
                              {/* Totalizer Grid */}
                              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                                {totalizers.map((totalizer) => {
                                  // A totalizer is active if ALL its fields are active
                                  const isActive = totalizer.fields.every(f => emulatorScales.scales?.[f]?.active)
                                  const isPartial = totalizer.fields.some(f => emulatorScales.scales?.[f]?.active) && !isActive
                                  
                                  // Get live values from API
                                  const rawScales = emulatorLiveData?.raw_scales || {}
                                  const combinedScales = emulatorLiveData?.scales || {}
                                  const baseName = totalizer.name
                                  
                                  // For scales with HI/LO: show just LO value (that's what increments)
                                  // For other scales: show combined value
                                  const loField = `${baseName}_LO`
                                  const hasLoField = totalizer.fields.includes(loField)
                                  const liveValue = hasLoField 
                                    ? (rawScales[loField] ?? emulatorScales.scales?.[loField]?.value ?? 0)
                                    : (combinedScales[baseName] ?? emulatorScales.scales?.[totalizer.fields[0]]?.value ?? 0)
                                  
                                  return (
                                    <button
                                      key={totalizer.name}
                                      onClick={async () => {
                                        const newState = !isActive
                                        try {
                                          const payload = newState ? { on: totalizer.fields } : { off: totalizer.fields }
                                          await apiRequest('PUT', '/api/emulator/scales/bulk', payload)
                                          refetchEmulatorScales()
                                        } catch (err: any) {
                                          console.error('Failed to toggle:', err)
                                          toast({
                                            title: '❌ Toggle Failed',
                                            description: err?.message || 'Failed to toggle totalizer',
                                            variant: 'destructive',
                                          })
                                        }
                                      }}
                                      className={`p-3 rounded-lg text-sm transition-all border text-left ${
                                        isActive 
                                          ? 'bg-green-50 dark:bg-green-900/30 border-green-400 dark:border-green-500/50' 
                                          : isPartial
                                            ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-400 dark:border-amber-500/40'
                                            : 'bg-gray-50 dark:bg-slate-800/50 border-gray-300 dark:border-slate-600/40'
                                      } hover:shadow-md`}
                                    >
                                      <div className="flex items-center justify-between mb-1">
                                        <span className={`font-semibold text-sm ${
                                          isActive ? 'text-green-800 dark:text-white' : isPartial ? 'text-amber-700 dark:text-amber-300' : 'text-gray-600 dark:text-slate-300'
                                        }`}>
                                          {totalizer.displayName}
                                        </span>
                                        <div className={`w-2 h-2 rounded-full ${
                                          isActive ? 'bg-green-500 dark:bg-green-400 animate-pulse' : isPartial ? 'bg-amber-500 dark:bg-amber-400' : 'bg-gray-400 dark:bg-slate-600'
                                        }`} />
                                      </div>
                                      {/* Live Value Display */}
                                      <div className={`text-lg font-mono font-bold ${
                                        isActive ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-slate-500'
                                      }`}>
                                        {typeof liveValue === 'number' ? liveValue.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '—'}
                                      </div>
                                      <p className={`text-xs ${
                                        isActive ? 'text-green-600 dark:text-green-300/80' : 'text-gray-500 dark:text-slate-500'
                                      }`}>
                                        {isActive ? '▲ Increasing' : 'Stopped'}
                                      </p>
                                    </button>
                                  )
                                })}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Mock SAP Toggle - Compact */}
              <div className="flex items-center justify-between bg-slate-700/30 light:bg-gray-50 rounded-lg p-3 border border-slate-600 light:border-gray-200">
                <div className="flex items-center gap-3">
                  {demoMode.mock_sap ? (
                    <Server className="h-5 w-5 text-amber-400" />
                  ) : (
                    <Network className="h-5 w-5 text-green-400" />
                  )}
                  <div>
                    <span className="text-white light:text-gray-900 text-sm font-medium">
                      SAP Connection: {demoMode.mock_sap ? 'Mock Server' : 'Real SAP'}
                    </span>
                    <p className="text-slate-400 light:text-gray-600 text-xs">
                      {demoMode.mock_sap ? 'KPIs sent to localhost:6000' : 'KPIs sent to production SAP'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleToggleMockSap(!demoMode.mock_sap)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    demoMode.mock_sap ? 'bg-amber-500' : 'bg-green-500'
                  }`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    demoMode.mock_sap ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>

              {/* Data Stats - Collapsed by default */}
              <details className="bg-slate-700/30 light:bg-gray-50 rounded-lg border border-slate-600 light:border-gray-200">
                <summary className="p-3 cursor-pointer text-slate-300 light:text-gray-700 text-sm font-medium flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Database Statistics
                  <span className="text-slate-500 light:text-gray-500 text-xs ml-auto">Click to expand</span>
                </summary>
                <div className="p-3 pt-0 border-t border-slate-600/50 light:border-gray-200">
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-3">
                    {[
                      { key: 'kpi_send_tracking', label: 'KPI Tracking', action: 'kpi-tracking' },
                      { key: 'scada_aggregate_values', label: 'SCADA Data', action: 'scada-aggregate' },
                      { key: 'milling_kpi_snapshots', label: 'Milling KPIs', action: null },
                      { key: 'packing_kpi_snapshots', label: 'Packing KPIs', action: null },
                      { key: 'shift_master', label: 'Shifts', action: null },
                    ].map(({ key, label, action }) => (
                      <div key={key} className="bg-slate-600/30 light:bg-white rounded p-2 text-center">
                        <p className="text-slate-400 light:text-gray-600 text-xs">{label}</p>
                        <p className="text-white light:text-gray-900 text-lg font-mono font-bold">
                          {systemStats[key]?.toLocaleString() ?? '—'}
                        </p>
                        {action && (
                          <button
                            onClick={() => handleResetDemo(action)}
                            disabled={resetLoading === action}
                            className="text-red-400/60 hover:text-red-400 text-xs mt-1"
                          >
                            {resetLoading === action ? 'Clearing...' : 'Clear'}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <Button
                      onClick={() => refetchSystemStats()}
                      size="sm"
                      variant="ghost"
                      className="text-slate-400 hover:text-white"
                    >
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Refresh
                    </Button>
                    <Button
                      onClick={() => handleResetDemo('all-demo-data')}
                      disabled={resetLoading === 'all-demo-data'}
                      size="sm"
                      variant="ghost"
                      className="text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      {resetLoading === 'all-demo-data' ? 'Clearing...' : 'Clear All Demo Data'}
                    </Button>
                  </div>
                </div>
              </details>

            </div>
          </TabsContent>

          {/* SAP LOGS TAB */}
          <TabsContent value="logs" className="flex-1 overflow-y-auto mt-0">
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-white light:text-gray-900 font-semibold flex items-center gap-2">
                  <FileText className="h-5 w-5 text-cyan-400 light:text-blue-600" />
                  SAP Confirmation Logs
                  {sapLogsData?.total && (
                    <span className="text-xs text-slate-400 light:text-gray-500 font-normal">
                      ({sapLogsData.total} total entries)
                    </span>
                  )}
                </h3>
                <div className="flex gap-2">
                  <Button 
                    onClick={() => refetchSapLogs()} 
                    size="sm" 
                    variant="outline"
                    className="border-slate-600 light:border-gray-300"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                  <Button 
                    onClick={async () => {
                      if (window.confirm('Are you sure you want to clear all SAP confirmation logs?')) {
                        setSapLogsClearing(true)
                        try {
                          await apiRequest('POST', '/api/sap-logs/confirmations/clear')
                          refetchSapLogs()
                        } finally {
                          setSapLogsClearing(false)
                        }
                      }
                    }} 
                    size="sm" 
                    variant="outline"
                    disabled={sapLogsClearing}
                    className="text-red-400 hover:text-red-300 border-red-500/50 hover:border-red-500"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    {sapLogsClearing ? 'Clearing...' : 'Clear Logs'}
                  </Button>
                </div>
              </div>

              {/* Logs Table */}
              <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg border border-slate-600 light:border-gray-200 overflow-hidden">
                <div className="overflow-x-auto max-h-[650px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-600/50 light:bg-gray-100 sticky top-0 z-10">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">ID</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">PO Number</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Material</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Qty</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Final</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Source</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Status</th>
                        <th className="px-4 py-3 text-left text-slate-300 light:text-gray-700 font-semibold">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sapLogsData?.logs?.length === 0 && (
                        <tr>
                          <td colSpan={8} className="px-4 py-8 text-center text-slate-400 light:text-gray-500">
                            No SAP confirmation logs found
                          </td>
                        </tr>
                      )}
                      {sapLogsData?.logs?.map((log: any, index: number) => {
                        const isExpanded = expandedLogRows.has(log.id || index)
                        // Extract the specific payload for this PO number
                        // Payload can be an object or an array - if array, find the matching PO
                        const getOrderPayload = () => {
                          if (!log.payload) return null
                          if (Array.isArray(log.payload)) {
                            // Find the payload item matching this log's po_number
                            return log.payload.find((p: any) => 
                              p.PROCESS_ORDER === log.po_number || p.AUFNR === log.po_number
                            ) || log.payload[0]
                          }
                          return log.payload
                        }
                        const orderPayload = getOrderPayload()
                        
                        return (
                          <React.Fragment key={log.id || index}>
                            <tr 
                              className={`border-t border-slate-600/50 light:border-gray-200 hover:bg-slate-600/20 light:hover:bg-gray-100 cursor-pointer ${isExpanded ? 'bg-slate-600/30 light:bg-blue-50' : ''}`}
                              onClick={() => {
                                const newExpanded = new Set(expandedLogRows)
                                if (isExpanded) {
                                  newExpanded.delete(log.id || index)
                                } else {
                                  newExpanded.add(log.id || index)
                                }
                                setExpandedLogRows(newExpanded)
                              }}
                            >
                              <td className="px-4 py-2 text-slate-300 light:text-gray-700 font-mono text-xs">
                                {log.id || index + 1}
                              </td>
                              <td className="px-4 py-2 text-white light:text-gray-900 font-mono font-medium">
                                {log.po_number || orderPayload?.PROCESS_ORDER || orderPayload?.AUFNR || '-'}
                              </td>
                              <td className="px-4 py-2 text-slate-300 light:text-gray-700 font-mono text-xs">
                                {orderPayload?.MATERIAL || orderPayload?.MATNR || '-'}
                              </td>
                              <td className="px-4 py-2 text-white light:text-gray-900 font-medium">
                                {orderPayload?.CONFIRMED_WEIGHT || orderPayload?.LMNGA || orderPayload?.XMNGA || '-'}
                              </td>
                              <td className="px-4 py-2">
                                {orderPayload?.FINAL_CONFIRMATION === 'X' ? (
                                  <span className="px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400 light:bg-green-100 light:text-green-700">X</span>
                                ) : (
                                  <span className="text-slate-400 light:text-gray-500">-</span>
                                )}
                              </td>
                              <td className="px-4 py-2">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  log.source === 'auto_shift_end_confirmation' 
                                    ? 'bg-blue-500/20 text-blue-400 light:bg-blue-100 light:text-blue-700'
                                    : log.source === 'MANUAL'
                                      ? 'bg-amber-500/20 text-amber-400 light:bg-amber-100 light:text-amber-700'
                                      : 'bg-green-500/20 text-green-400 light:bg-green-100 light:text-green-700'
                                }`}>
                                  {log.source === 'auto_shift_end_confirmation' ? 'AUTO' : log.source || 'ONLINE'}
                                </span>
                              </td>
                              <td className="px-4 py-2">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  log.status === 'SUCCESS' 
                                    ? 'bg-green-500/20 text-green-400 light:bg-green-100 light:text-green-700'
                                    : log.status === 'PENDING'
                                      ? 'bg-amber-500/20 text-amber-400 light:bg-amber-100 light:text-amber-700'
                                      : 'bg-red-500/20 text-red-400 light:bg-red-100 light:text-red-700'
                                }`}>
                                  {log.status || 'UNKNOWN'}
                                </span>
                              </td>
                              <td className="px-4 py-2 text-slate-300 light:text-gray-600 font-mono text-xs whitespace-nowrap">
                                {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                              </td>
                            </tr>
                            {/* Expanded Payload Row - Shows only this order's payload */}
                            {isExpanded && (
                              <tr className="bg-slate-800/50 light:bg-gray-50">
                                <td colSpan={8} className="px-4 py-3">
                                  <div className="rounded-lg bg-slate-900/50 light:bg-white border border-slate-600 light:border-gray-300 p-3">
                                    <div className="flex items-center justify-between mb-2">
                                      <span className="text-cyan-400 light:text-blue-600 font-semibold text-sm">
                                        Payload for PO: {log.po_number}
                                      </span>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          navigator.clipboard.writeText(JSON.stringify(orderPayload, null, 2))
                                        }}
                                        className="text-xs text-slate-400 hover:text-white light:text-gray-500 light:hover:text-gray-700"
                                      >
                                        <Copy className="h-3 w-3 mr-1" />
                                        Copy
                                      </Button>
                                    </div>
                                    <pre className="text-xs text-slate-300 light:text-gray-700 overflow-x-auto font-mono whitespace-pre-wrap">
                                      {JSON.stringify(orderPayload, null, 2)}
                                    </pre>
                                    {log.sap_response && (
                                      <>
                                        <div className="mt-3 pt-3 border-t border-slate-600 light:border-gray-300">
                                          <span className="text-amber-400 light:text-amber-600 font-semibold text-sm">SAP Response</span>
                                        </div>
                                        <pre className="mt-2 text-xs text-slate-300 light:text-gray-700 overflow-x-auto font-mono whitespace-pre-wrap">
                                          {typeof log.sap_response === 'string' ? log.sap_response : JSON.stringify(log.sap_response, null, 2)}
                                        </pre>
                                      </>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

        </Tabs>
      </div>

      {/* Modern Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 custom-popup-overlay">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-700 p-6 max-w-md w-full mx-4 custom-popup-content">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-cyan-100 dark:bg-cyan-900/30 rounded-full flex items-center justify-center">
                <Database className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Send to SAP?
              </h3>
            </div>
            
            <p className="text-gray-600 dark:text-slate-300 mb-6 text-base leading-relaxed">
              Send latest 20 records from <span className="font-mono text-sm bg-gray-100 dark:bg-slate-700 px-2 py-1 rounded">ASMReporting_5</span> to SAP?
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancelSend}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSend}
                className="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors duration-200 flex items-center gap-2"
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Shift Modal */}
      {showAddShiftModal && (
        <div className="fixed inset-0 bg-black/50 z-50 overflow-y-auto" data-top-modal onClick={handleCloseAddModal} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '2rem', paddingBottom: '2rem' }}>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-700 p-6 max-w-lg w-full mx-4 max-h-[calc(100vh-4rem)] overflow-y-auto" onClick={(e) => e.stopPropagation()} style={{ marginTop: '0' }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-cyan-100 dark:bg-cyan-900/30 rounded-full flex items-center justify-center">
                <Plus className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Add New Shift
              </h3>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Shift Type</Label>
                  <select
                    value={newShift.type}
                    onChange={(e) => setNewShift({...newShift, type: e.target.value as ShiftType})}
                    className="w-full bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
                  >
                    <option value="milling">Milling</option>
                    <option value="packing">Packing</option>
                  </select>
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Shift Name *</Label>
                  <Input
                    value={newShift.name}
                    onChange={(e) => setNewShift({...newShift, name: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                    placeholder="e.g., Shift A, Shift B"
                  />
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Start Time (24h) *</Label>
                  <Input
                    type="time"
                    value={newShift.start}
                    onChange={(e) => setNewShift({...newShift, start: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">End Time (24h) *</Label>
                  <Input
                    type="time"
                    value={newShift.end}
                    onChange={(e) => setNewShift({...newShift, end: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Display Name (Optional)</Label>
                  <Input
                    value={newShift.displayName}
                    onChange={(e) => setNewShift({...newShift, displayName: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                    placeholder="e.g., Day Shift, Evening Shift, Night Shift"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex gap-3 justify-end mt-6">
              <Button
                onClick={handleCloseAddModal}
                variant="outline"
                className="border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddShift}
                disabled={createShiftMutation.isPending}
                className="bg-cyan-600 hover:bg-cyan-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createShiftMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Shift
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Shift Modal */}
      {showEditShiftModal && editingShift && (
        <div className="fixed inset-0 bg-black/50 z-50 overflow-y-auto" data-top-modal onClick={handleCloseEditModal} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '2rem', paddingBottom: '2rem' }}>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-700 p-6 max-w-lg w-full mx-4 max-h-[calc(100vh-4rem)] overflow-y-auto" onClick={(e) => e.stopPropagation()} style={{ marginTop: '0' }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-cyan-100 dark:bg-cyan-900/30 rounded-full flex items-center justify-center">
                <Edit className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Edit Shift: {editingShift.name}
              </h3>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Shift Type</Label>
                  <select
                    value={newShift.type}
                    disabled
                    className="w-full bg-gray-100 dark:bg-slate-700 border border-gray-300 dark:border-slate-600 text-gray-500 dark:text-slate-400 rounded-lg px-3 py-2 cursor-not-allowed"
                  >
                    <option value="milling">Milling</option>
                    <option value="packing">Packing</option>
                  </select>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Cannot be changed</p>
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Shift Name</Label>
                  <Input
                    value={newShift.name}
                    disabled
                    className="bg-gray-100 dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-500 dark:text-slate-400 cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Cannot be changed</p>
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Start Time (24h) *</Label>
                  <Input
                    type="time"
                    value={newShift.start}
                    onChange={(e) => setNewShift({...newShift, start: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">End Time (24h) *</Label>
                  <Input
                    type="time"
                    value={newShift.end}
                    onChange={(e) => setNewShift({...newShift, end: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label className="text-gray-700 dark:text-slate-300 text-sm font-medium mb-1 block">Display Name (Optional)</Label>
                  <Input
                    value={newShift.displayName}
                    onChange={(e) => setNewShift({...newShift, displayName: e.target.value})}
                    className="bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white"
                    placeholder="e.g., Day Shift, Evening Shift, Night Shift"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex gap-3 justify-end mt-6">
              <Button
                onClick={handleCloseEditModal}
                variant="outline"
                className="border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdateShift}
                disabled={updateShiftMutation.isPending}
                className="bg-cyan-600 hover:bg-cyan-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {updateShiftMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Update Shift
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Shift Confirmation Modal */}
      {showDeleteShiftModal && deletingShift && (
        <div className="fixed inset-0 bg-black/50 z-50 overflow-y-auto" data-top-modal onClick={handleCloseDeleteModal} style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '2rem', paddingBottom: '2rem' }}>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-700 p-6 max-w-md w-full mx-4 max-h-[calc(100vh-4rem)] overflow-y-auto custom-popup-content" onClick={(e) => e.stopPropagation()} style={{ marginTop: '0' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <Trash2 className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Delete Shift?
              </h3>
            </div>
            
            <p className="text-gray-600 dark:text-slate-300 mb-2 text-base leading-relaxed">
              Are you sure you want to delete <span className="font-semibold text-gray-900 dark:text-white">{deletingShift.name}</span> from <span className="font-semibold text-gray-900 dark:text-white capitalize">{deletingShift.type}</span>?
            </p>
            <p className="text-sm text-red-600 dark:text-red-400 mb-6">
              This action cannot be undone.
            </p>
            
            <div className="flex gap-3 justify-end">
              <Button
                onClick={handleCloseDeleteModal}
                variant="outline"
                className="border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmDelete}
                disabled={deleteShiftMutation.isPending}
                className="delete-button-red transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ 
                  backgroundColor: '#dc2626', 
                  color: '#ffffff', 
                  borderColor: '#dc2626',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  opacity: 1,
                  visibility: 'visible'
                }}
                onMouseEnter={(e) => {
                  if (!deleteShiftMutation.isPending) {
                    e.currentTarget.style.backgroundColor = '#b91c1c'
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#dc2626'
                }}
              >
                {deleteShiftMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" style={{ color: '#ffffff' }} />
                    <span style={{ color: '#ffffff' }}>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4 mr-2" style={{ color: '#ffffff' }} />
                    <span style={{ color: '#ffffff' }}>Delete</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Login Modal */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onLoginSuccess={(user) => {
          setCurrentUser(user as UserInfo)
          queryClient.invalidateQueries({ queryKey: ['/api/auth/me'] })
          queryClient.invalidateQueries({ queryKey: ['/api/sync-interval/settings'] })
        }}
      />

      {/* Custom CSS for popup positioning and delete buttons */}
      <style>{`
        .custom-popup-overlay {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          z-index: 9999 !important;
        }

        .custom-popup-overlay:not([data-top-modal]) {
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
        }

        [data-top-modal] {
          display: flex !important;
          align-items: flex-start !important;
          justify-content: center !important;
          padding-top: 2rem !important;
          padding-bottom: 2rem !important;
        }

        .custom-popup-content {
          position: relative !important;
          z-index: 10000 !important;
          transform: none !important;
        }

        /* Ensure delete buttons are always red with white text in both light and dark modes */
        .delete-button-red,
        button.delete-button-red,
        .delete-button-red.bg-primary,
        .delete-button-red.bg-background,
        .delete-button-red[class*="bg-"] {
          --background: #dc2626 !important;
          --primary: #dc2626 !important;
          --primary-foreground: #ffffff !important;
          --foreground: #ffffff !important;
          background-color: #dc2626 !important;
          background: #dc2626 !important;
          color: #ffffff !important;
          border-color: #dc2626 !important;
          border: 1px solid #dc2626 !important;
          opacity: 1 !important;
          visibility: visible !important;
        }

        .delete-button-red:hover,
        button.delete-button-red:hover,
        .delete-button-red.bg-primary:hover,
        .delete-button-red.bg-background:hover,
        .delete-button-red[class*="bg-"]:hover {
          background-color: #b91c1c !important;
          background: #b91c1c !important;
        }

        .delete-button-red svg,
        .delete-button-red span,
        .delete-button-red *,
        button.delete-button-red svg,
        button.delete-button-red span,
        button.delete-button-red * {
          color: #ffffff !important;
          fill: #ffffff !important;
        }

        /* Override any theme-specific styles and Button component variants */
        .light .delete-button-red,
        .dark .delete-button-red,
        [data-theme="light"] .delete-button-red,
        [data-theme="dark"] .delete-button-red,
        .light button.delete-button-red,
        .dark button.delete-button-red,
        [data-theme="light"] button.delete-button-red,
        [data-theme="dark"] button.delete-button-red {
          background-color: #dc2626 !important;
          background: #dc2626 !important;
          color: #ffffff !important;
          border-color: #dc2626 !important;
          border: 1px solid #dc2626 !important;
        }

        /* Override text-primary-foreground and other text color classes */
        .delete-button-red.text-primary-foreground,
        .delete-button-red.text-foreground,
        .delete-button-red[class*="text-"] {
          color: #ffffff !important;
        }

        /* Ultra-specific overrides for light mode visibility */
        html:not(.dark) .delete-button-red,
        html:not([data-theme="dark"]) .delete-button-red,
        body:not(.dark) .delete-button-red,
        [class*="light"] .delete-button-red {
          background-color: #dc2626 !important;
          background: #dc2626 !important;
          color: #ffffff !important;
          border-color: #dc2626 !important;
          border: 1px solid #dc2626 !important;
        }

        /* Force all child elements to be white in delete buttons */
        .delete-button-red * {
          color: #ffffff !important;
          fill: #ffffff !important;
          stroke: #ffffff !important;
        }
      `}</style>
    </WaterSystemLayout>
  )
}