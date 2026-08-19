import React, { useState } from 'react'
import { WaterSystemLayout } from '@/components/hercules-sfms/WaterSystemLayout'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { useTheme } from '@/contexts/ThemeContext'
import { Activity, RefreshCw, ShieldAlert, Filter } from 'lucide-react'

interface LogEntry {
  id: number
  timestamp: string
  source: string
  action: string
  status: string
  details?: string
  operator?: string
  duration_ms?: number
  created_at: string
  shift?: string
  log_metadata?: Record<string, unknown>
}

export function UserActivityLog() {
  const { theme } = useTheme()
  const [operatorFilter, setOperatorFilter] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const { data: currentUserData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    retry: false
  })

  const currentUser = currentUserData?.user || null
  const isAdmin = currentUser?.roles?.includes('admin') ?? false

  const queryParams = new URLSearchParams()
  queryParams.set('limit', '200')
  queryParams.set('offset', '0')
  if (operatorFilter.trim()) queryParams.set('operator', operatorFilter.trim())
  if (startDate) queryParams.set('start_date', startDate + 'T00:00:00Z')
  if (endDate) queryParams.set('end_date', endDate + 'T23:59:59Z')

  const { data: activityData, isLoading, refetch } = useQuery({
    queryKey: ['/api/admin/activity-log', queryParams.toString()],
    queryFn: () => apiRequest('GET', `/api/admin/activity-log?${queryParams.toString()}`),
    enabled: isAdmin,
    retry: false
  })

  const logs: LogEntry[] = activityData?.logs ?? []
  const isForbidden = !currentUserData && !isAdmin

  const formatTimestamp = (ts: string) => {
    if (!ts) return '—'
    try {
      const d = new Date(ts)
      return d.toLocaleString(undefined, {
        dateStyle: 'short',
        timeStyle: 'medium'
      })
    }
    catch {
      return ts
    }
  }

  if (!isAdmin && currentUserData) {
    return (
      <WaterSystemLayout title="User Activity" subtitle="Operator actions (Admin only)">
        <div className={`p-6 rounded-lg border ${theme === 'light' ? 'bg-amber-50 border-amber-200' : 'bg-amber-900/20 border-amber-700/50'}`}>
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-8 w-8 text-amber-500" />
            <div>
              <h3 className="font-semibold text-amber-800 dark:text-amber-200">Admin only</h3>
              <p className="text-sm text-amber-700 dark:text-amber-300">This page is visible only to administrators.</p>
            </div>
          </div>
        </div>
      </WaterSystemLayout>
    )
  }

  return (
    <WaterSystemLayout title="User Activity" subtitle="Operator actions (Admin only)">
      <div className={`rounded-lg border p-4 ${theme === 'light' ? 'bg-white border-gray-200' : 'bg-slate-800/50 border-slate-700'}`}>
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 opacity-70" />
            <span className="text-sm font-medium">Filters</span>
          </div>
          <input
            type="text"
            placeholder="Operator name"
            value={operatorFilter}
            onChange={(e) => setOperatorFilter(e.target.value)}
            className={`px-3 py-1.5 rounded-md border text-sm ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600'}`}
          />
          <input
            type="date"
            placeholder="Start date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={`px-3 py-1.5 rounded-md border text-sm ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600'}`}
          />
          <input
            type="date"
            placeholder="End date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className={`px-3 py-1.5 rounded-md border text-sm ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600'}`}
          />
          <button
            type="button"
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-cyan-600 text-white text-sm hover:bg-cyan-700"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {isLoading ? (
            <p className="py-8 text-center text-gray-500 dark:text-slate-400">Loading activity log...</p>
          ) : logs.length === 0 ? (
            <p className="py-8 text-center text-gray-500 dark:text-slate-400">No operator actions recorded yet.</p>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className={`border-b ${theme === 'light' ? 'border-gray-200' : 'border-slate-600'}`}>
                  <th className={`text-left py-2 px-3 font-medium ${theme === 'light' ? 'text-gray-700' : 'text-slate-300'}`}>Timestamp</th>
                  <th className={`text-left py-2 px-3 font-medium ${theme === 'light' ? 'text-gray-700' : 'text-slate-300'}`}>User</th>
                  <th className={`text-left py-2 px-3 font-medium ${theme === 'light' ? 'text-gray-700' : 'text-slate-300'}`}>Action</th>
                  <th className={`text-left py-2 px-3 font-medium ${theme === 'light' ? 'text-gray-700' : 'text-slate-300'}`}>Details</th>
                  <th className={`text-left py-2 px-3 font-medium ${theme === 'light' ? 'text-gray-700' : 'text-slate-300'}`}>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className={`border-b ${theme === 'light' ? 'border-gray-100' : 'border-slate-700/50'}`}
                  >
                    <td className="py-2 px-3 whitespace-nowrap text-gray-600 dark:text-slate-400">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="py-2 px-3 font-medium">{log.operator || '—'}</td>
                    <td className="py-2 px-3">{log.action}</td>
                    <td className="py-2 px-3 max-w-xs truncate" title={log.details || ''}>
                      {log.details || '—'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                          log.status === 'Success'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                            : log.status === 'Error'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                            : 'bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {logs.length > 0 && (
          <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
            Showing {logs.length} entries. Actions: priority change, validate, reject, pause, sync.
          </p>
        )}
      </div>
    </WaterSystemLayout>
  )
}
