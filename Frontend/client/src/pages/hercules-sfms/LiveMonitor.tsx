import React, { useState, useEffect, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { apiFetch, getApiUrl } from '../../lib/apiConfig';
import { scadaConfigApi, ScadaTag } from '@/lib/api';
import {
  Activity,
  Wifi,
  WifiOff,
  AlertTriangle,
  RefreshCw,
  Scale,
  Droplets,
  Package
} from 'lucide-react';

interface UserInfo {
  id: number;
  username: string;
  roles: string[];
}

interface ScadaDataRow {
  timestamp: string;
  rawSignals: {
    [key: string]: number;
  };
}

interface ScaleStatus {
  tag: string;
  total: number;
  current: number;
  reset_base: number;
  custom_offset: number;
}

interface SignalConfig {
  key: string;
  label: string;
  unit: string;
  type: 'weight' | 'flow' | 'count' | 'other';
}

function tagsToConfigs(tags: ScadaTag[], category: string): SignalConfig[] {
  return tags
    .filter((t) => t.is_active && t.category === category)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((t) => ({
      key: t.tag,
      label: t.display_name || t.tag,
      unit: t.unit || (category === 'WATER' ? 'L' : category === 'PACKING' ? 'PALLETS' : 'KG'),
      type: category === 'WATER' ? 'flow' : category === 'PACKING' ? 'count' : 'weight',
    }));
}

// Bootstrap configs used only until /api/scada-config/tags responds
const WEIGHING_BOOTSTRAP: SignalConfig[] = [
  { key: 'WG101', label: 'Weight Gauge 101', unit: 'KG', type: 'weight' },
  { key: 'WG202', label: 'Weight Gauge 202', unit: 'KG', type: 'weight' },
  { key: 'WG302', label: 'Weight Gauge 302', unit: 'KG', type: 'weight' },
  { key: 'WG502', label: 'Weight Gauge 502', unit: 'KG', type: 'weight' },
  { key: 'WG201', label: 'Weight Gauge 201', unit: 'KG', type: 'weight' },
  { key: 'WG301', label: 'Weight Gauge 301', unit: 'KG', type: 'weight' },
  { key: 'WG501', label: 'Weight Gauge 501', unit: 'KG', type: 'weight' },
  { key: 'WG503', label: 'Weight Gauge 503', unit: 'KG', type: 'weight' },
];

const DOSING_BOOTSTRAP: SignalConfig[] = [
  { key: 'DM101', label: 'Dosing Module 101', unit: 'L', type: 'flow' },
  { key: 'DM102', label: 'Dosing Module 102', unit: 'L', type: 'flow' },
  { key: 'DM201', label: 'Dosing Module 201', unit: 'L', type: 'flow' },
  { key: 'DM202', label: 'Dosing Module 202', unit: 'L', type: 'flow' },
  { key: 'DM203', label: 'Dosing Module 203', unit: 'L', type: 'flow' },
];

const PACKING_BOOTSTRAP: SignalConfig[] = [
  { key: 'PL601_TOT', label: 'Packing Line 601', unit: 'PALLETS', type: 'count' },
  { key: 'PL602_TOT', label: 'Packing Line 602', unit: 'PALLETS', type: 'count' },
  { key: 'PL603_TOT', label: 'Packing Line 603', unit: 'PALLETS', type: 'count' },
  { key: 'SL606_TOT', label: 'Packing Line 606', unit: 'PALLETS', type: 'count' },
  { key: 'SL607_TOT', label: 'Packing Line 607', unit: 'PALLETS', type: 'count' },
];

// Weighing Module Card - Reference Design (White cards with large bold numbers)
const WeighingCard = ({
  config,
  value,
  theme,
  status
}: {
  config: SignalConfig;
  value: number;
  theme: 'light' | 'dark';
  status: 'online' | 'offline' | 'warning';
}) => {
  const statusColor = status === 'online' ? 'bg-green-500' : status === 'warning' ? 'bg-orange-500' : 'bg-red-500';
  
  // Format value - show decimals for smaller values, comma-separated for larger
  const formatValue = (val: number): string => {
    if (val >= 1000) {
      return val.toLocaleString(undefined, { maximumFractionDigits: 0 });
    }
    return val.toFixed(2);
  };

  return (
    <div className={`relative rounded-lg p-4 border shadow-sm h-full flex flex-col justify-between ${theme === 'light'
        ? 'bg-white border-slate-200'
        : 'bg-slate-800/50 border-slate-700'
      }`}>
      {/* Status Dot - Top Right */}
      <div className={`absolute top-3 right-3 w-2.5 h-2.5 rounded-full ${statusColor}`} />
      
      <div className="flex-1 flex flex-col">
        {/* Label - Scale Reading */}
        <div className={`text-sm font-semibold mb-3 uppercase ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`}>
          Scale Reading
        </div>
        
        {/* Module ID */}
        <div className={`text-base font-bold mb-4 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
          {config.key}
        </div>
      </div>
      
      {/* Value and Unit - Large Bold */}
      <div className="flex flex-col mt-auto">
        <span className={`text-2xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
          {formatValue(value)}
        </span>
        <span className={`text-base font-medium mt-1 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
          {config.unit}
        </span>
      </div>
    </div>
  );
};

// Dosing Module Card - Reference Design (Smaller cards with thin blue line)
const DosingCard = ({
  config,
  value,
  theme,
  status
}: {
  config: SignalConfig;
  value: number;
  theme: 'light' | 'dark';
  status: 'online' | 'offline' | 'warning';
}) => {
  const formatValue = (val: number): string => {
    if (config.unit === '%') {
      return val.toFixed(0);
    }
    return val.toFixed(2);
  };

  return (
    <div className={`relative rounded-lg border p-3 shadow-sm ${theme === 'light'
        ? 'bg-white border-slate-200'
        : 'bg-slate-800/50 border-slate-700'
      }`}>
      {/* Label */}
      <div className={`text-sm font-semibold mb-2 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
        {config.key}
      </div>
      
      {/* Value and Unit */}
      <div className="flex flex-col mb-2">
        <span className={`text-base font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
          {formatValue(value)}
        </span>
        <span className={`text-xs font-medium mt-1 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
          {config.unit}
        </span>
      </div>
      
      {/* Light Blue Horizontal Line */}
      <div className={`h-1.5 rounded-full ${theme === 'light' ? 'bg-blue-200' : 'bg-blue-500/30'}`} />
    </div>
  );
};

// Packing Line Card - Reference Design (Larger cards with package icon on left)
const PackingCard = ({
  config,
  value,
  theme,
  status
}: {
  config: SignalConfig;
  value: number;
  theme: 'light' | 'dark';
  status: 'online' | 'offline' | 'warning';
}) => {
  return (
    <div className={`relative rounded-lg border p-4 shadow-sm h-full flex flex-col ${theme === 'light'
        ? 'bg-white border-slate-200'
        : 'bg-slate-800/50 border-slate-700'
      }`}>
      {/* Package Icon - Top Center */}
      <div className="flex justify-center mb-2 flex-shrink-0">
        <div className={`p-2 rounded-lg ${theme === 'light'
            ? 'bg-cyan-100 text-cyan-600'
            : 'bg-cyan-500/20 text-cyan-400'
          }`}>
          <Package className="w-5 h-5" />
        </div>
      </div>
      
      {/* Module ID - Centered */}
      <div className={`text-base font-bold mb-2 text-center flex-shrink-0 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
        {getDisplayTag(config.key)}
      </div>
      
      {/* Total Output Label - Centered */}
      <div className={`text-sm font-semibold mb-3 uppercase text-center flex-shrink-0 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`}>
        TOTAL OUTPUT
      </div>
      
      {/* Value and Unit - Very Large - Centered */}
      <div className="flex flex-col items-center justify-center flex-1">
        <span className={`text-3xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
          {value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
        <span className={`text-lg font-medium mt-1 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
          {config.unit}
        </span>
      </div>
    </div>
  );
};

// Helper function to get display name for tags (convert SL606_TOT to PL606, SL607_TOT to PL607, remove _TOT from PL601_TOT, PL602_TOT, PL603_TOT)
const getDisplayTag = (tag: string): string => {
  if (tag === 'SL606_TOT') return 'PL606';
  if (tag === 'SL607_TOT') return 'PL607';
  if (tag === 'PL601_TOT') return 'PL601';
  if (tag === 'PL602_TOT') return 'PL602';
  if (tag === 'PL603_TOT') return 'PL603';
  return tag;
};

const LiveMonitor = () => {
  const [latestRecord, setLatestRecord] = useState<ScadaDataRow | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showResetModal, setShowResetModal] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Reset functionality states
  const [availableScales, setAvailableScales] = useState<ScaleStatus[]>([]);
  const [customValues, setCustomValues] = useState<Record<string, number | null>>({});
  const [selectedScales, setSelectedScales] = useState<Set<string>>(new Set());
  const [loadingScales, setLoadingScales] = useState(false);

  const { theme } = useTheme();

  // B9: tag list from scada_tags registry
  const { data: registryTags } = useQuery({
    queryKey: ['/api/scada-config/tags'],
    queryFn: () => scadaConfigApi.getTags(),
    staleTime: 30_000,
  });

  const WEIGHING_CONFIG = useMemo(() => {
    if (!registryTags?.length) return WEIGHING_BOOTSTRAP;
    const input = tagsToConfigs(registryTags, 'INPUT');
    const milling = tagsToConfigs(registryTags, 'MILLING');
    return [...input, ...milling];
  }, [registryTags]);

  const DOSING_CONFIG = useMemo(
    () => (registryTags?.length ? tagsToConfigs(registryTags, 'WATER') : DOSING_BOOTSTRAP),
    [registryTags],
  );

  const PACKING_CONFIG = useMemo(() => {
    if (!registryTags?.length) return PACKING_BOOTSTRAP;
    return tagsToConfigs(registryTags, 'PACKING').filter((c) => !c.key.includes('DAMAGED') && !c.key.includes('COUNTER'));
  }, [registryTags]);

  // Fetch current user info
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  });

  const currentUser = userData as UserInfo | null;

  // Handle scale selection toggle
  const toggleScaleSelection = (tag: string) => {
    setSelectedScales(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tag)) {
        newSet.delete(tag);
      } else {
        newSet.add(tag);
      }
      return newSet;
    });
  };

  // Toggle all scales selection
  const toggleAllScales = () => {
    if (selectedScales.size === availableScales.length) {
      setSelectedScales(new Set());
    } else {
      setSelectedScales(new Set(availableScales.map(s => s.tag)));
    }
  };

  // Fetch latest record
  const fetchLatestRecord = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiFetch(getApiUrl('/api/scada/live-monitoring?limit=1'));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.records && Array.isArray(result.records) && result.records.length > 0) {
        const record = result.records[0];
        setLatestRecord({
          timestamp: record.timestamp
            ? new Date(record.timestamp).toISOString().replace('T', ' ').substring(0, 19)
            : 'N/A',
          rawSignals: record.rawSignals || {}
        });
        setLastUpdate(new Date());
      }

    } catch (err) {
      console.error('Error fetching SCADA record:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch SCADA data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch available scales status
  const fetchAvailableScales = async () => {
    try {
      setLoadingScales(true);
      const response = await apiFetch(getApiUrl('/api/scada/scales/status'));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.success && result.scales) {
        setAvailableScales(result.scales);
        setCustomValues({});
        setSelectedScales(new Set());
      }
    } catch (err) {
      console.error('Error fetching scales status:', err);
    } finally {
      setLoadingScales(false);
    }
  };

  // Reset SCADA baseline
  const handleReset = async () => {
    await fetchAvailableScales();
    setShowResetModal(true);
  };

  // Handle custom value change
  const handleCustomValueChange = (tag: string, value: string) => {
    const numValue = value === '' ? null : parseFloat(value);
    setCustomValues(prev => ({
      ...prev,
      [tag]: (value === '' || isNaN(numValue as number)) ? null : numValue
    }));
  };

  // Confirm reset
  const confirmReset = async () => {
    setShowResetModal(false);

    try {
      setResetting(true);
      setResetMessage(null);
      setError(null);

      const scalesToReset = selectedScales.size > 0
        ? availableScales.filter(s => selectedScales.has(s.tag))
        : availableScales;

      const scale_resets = scalesToReset.map(scale => ({
        tag: scale.tag,
        custom_current_value: customValues[scale.tag] ?? null
      }));

      const response = await apiFetch(getApiUrl('/api/scada/reset'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scale_resets
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to reset SCADA' }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setResetMessage({
          type: 'success',
          text: `SCADA Reset Successful! Baseline updated for ${result.reset_scales?.length || 0} scale(s).`
        });

        setCustomValues({});
        setSelectedScales(new Set());

        setTimeout(() => {
          fetchLatestRecord();
        }, 1000);

        setTimeout(() => {
          setResetMessage(null);
        }, 5000);
      } else {
        throw new Error(result.message || 'Reset failed');
      }
    } catch (err) {
      console.error('Error resetting SCADA:', err);
      setResetMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to reset SCADA baseline'
      });

      setTimeout(() => {
        setResetMessage(null);
      }, 5000);
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    fetchLatestRecord();
    // Auto-refresh every 5 seconds for live feel
    const interval = setInterval(fetchLatestRecord, 5000);
    return () => clearInterval(interval);
  }, []);

  // Determine connection status based on timestamp freshness
  const getConnectionStatus = (timestampStr: string): 'online' | 'offline' | 'warning' => {
    if (!timestampStr || timestampStr === 'N/A') return 'offline';

    // Parse timestamp (assuming UTC or local consistent with server)
    const dataTime = new Date(timestampStr.replace(' ', 'T'));
    const now = new Date();
    const diffSeconds = (now.getTime() - dataTime.getTime()) / 1000;

    if (diffSeconds < 60) return 'online'; // Less than 1 min old
    if (diffSeconds < 300) return 'warning'; // Less than 5 mins old
    return 'offline';
  };

  const globalStatus = latestRecord ? getConnectionStatus(latestRecord.timestamp) : 'offline';

  return (
    <WaterSystemLayout
      title="LIVE MONITOR"
      subtitle="REAL-TIME SENSOR DATA"
    >
      <div className="space-y-6">
        {/* Header Controls */}
        <div className={`p-4 rounded-xl border flex flex-col sm:flex-row justify-between items-center gap-4 ${theme === 'light'
            ? 'bg-white border-slate-200 shadow-sm'
            : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
          }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${globalStatus === 'online' ? 'bg-green-100 text-green-600' :
                globalStatus === 'warning' ? 'bg-amber-100 text-amber-600' :
                  'bg-red-100 text-red-600'
              }`}>
              {globalStatus === 'online' ? <Wifi className="w-5 h-5" /> :
                globalStatus === 'warning' ? <AlertTriangle className="w-5 h-5" /> :
                  <WifiOff className="w-5 h-5" />}
            </div>
            <div>
              <h2 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'
                }`}>
                System Status: {globalStatus.toUpperCase()}
              </h2>
            </div>
          </div>

          <button
            onClick={handleReset}
            disabled={resetting}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${theme === 'light'
                ? 'bg-red-50 text-red-600 hover:bg-red-100 border border-red-200'
                : 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30'
              } ${resetting ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {resetting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Reset Baseline
          </button>
        </div>

        {/* Messages */}
        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}
        {resetMessage && (
          <div className={`p-4 rounded-lg border text-sm ${resetMessage.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-red-50 border-red-200 text-red-700'
            }`}>
            {resetMessage.text}
          </div>
        )}

        {/* Live Data Sections */}
        {loading && !latestRecord ? (
          <div className="flex items-center justify-center h-64">
            <div className={`w-8 h-8 border-4 border-t-transparent rounded-full animate-spin ${theme === 'light' ? 'border-blue-500' : 'border-cyan-500'
              }`} />
          </div>
        ) : latestRecord ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[calc(100vh-300px)]">
            {/* WEIGHING MODULES (WG) Section - Left Column - Takes 4 columns */}
            <div className="lg:col-span-4 flex flex-col">
              <div className={`rounded-xl border p-4 shadow-sm flex flex-col h-full ${theme === 'light'
                  ? 'bg-white border-slate-200'
                  : 'bg-slate-800/50 border-slate-700'
                }`}>
                <div className="flex items-center gap-3 mb-4 flex-shrink-0">
                  <div className={`p-2 rounded-lg ${theme === 'light'
                      ? 'bg-cyan-100 text-cyan-600'
                      : 'bg-cyan-500/20 text-cyan-400'
                    }`}>
                    <Scale className="w-5 h-5" />
                  </div>
                  <h2 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                    WEIGHING MODULES (WG)
                  </h2>
                </div>
                <div className="grid grid-cols-2 gap-3 flex-1 auto-rows-fr">
                  {WEIGHING_CONFIG.map((config) => (
                    <WeighingCard
                      key={config.key}
                      config={config}
                      value={latestRecord.rawSignals[config.key] || 0}
                      theme={theme}
                      status={getConnectionStatus(latestRecord.timestamp)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column - DOSING and PACKING - Takes 8 columns */}
            <div className="lg:col-span-8 flex flex-col gap-6">
              {/* DOSING (DM) Section */}
              <div className={`rounded-xl border p-4 shadow-sm ${theme === 'light'
                  ? 'bg-white border-slate-200'
                  : 'bg-slate-800/50 border-slate-700'
                }`}>
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${theme === 'light'
                      ? 'bg-cyan-100 text-cyan-600'
                      : 'bg-cyan-500/20 text-cyan-400'
                    }`}>
                    <Droplets className="w-5 h-5" />
                  </div>
                  <h2 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                    DOSING (DM)
                  </h2>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                  {DOSING_CONFIG.map((config) => (
                    <DosingCard
                      key={config.key}
                      config={config}
                      value={latestRecord.rawSignals[config.key] || 0}
                      theme={theme}
                      status={getConnectionStatus(latestRecord.timestamp)}
                    />
                  ))}
                </div>
              </div>

              {/* PACKING LINES (PL) Section */}
              <div className={`rounded-xl border p-4 shadow-sm flex-1 flex flex-col ${theme === 'light'
                  ? 'bg-white border-slate-200'
                  : 'bg-slate-800/50 border-slate-700'
                }`}>
                <div className="flex items-center gap-3 mb-4 flex-shrink-0">
                  <div className={`p-2 rounded-lg ${theme === 'light'
                      ? 'bg-cyan-100 text-cyan-600'
                      : 'bg-cyan-500/20 text-cyan-400'
                    }`}>
                    <Package className="w-5 h-5" />
                  </div>
                  <h2 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                    PACKING LINES (PL)
                  </h2>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 flex-1 auto-rows-fr">
                  {PACKING_CONFIG.map((config) => (
                    <PackingCard
                      key={config.key}
                      config={config}
                      value={latestRecord.rawSignals[config.key] || 0}
                      theme={theme}
                      status={getConnectionStatus(latestRecord.timestamp)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className={`text-center py-12 rounded-xl border border-dashed ${theme === 'light' ? 'border-slate-300 text-slate-500' : 'border-slate-700 text-slate-400'
            }`}>
            No live data available
          </div>
        )}

        {/* Reset Modal */}
        {showResetModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowResetModal(false)} />
            <div className={`relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-xl shadow-2xl border ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-900 border-slate-700'
              }`}>
              {/* Modal Header */}
              <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
                <h3 className={`text-xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                  Reset SCADA Baseline
                </h3>
                <button onClick={() => setShowResetModal(false)} className="text-slate-400 hover:text-slate-500">
                  <WifiOff className="w-5 h-5 rotate-45" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto custom-scrollbar">
                {loadingScales ? (
                  <div className="flex justify-center py-8">
                    <div className="w-8 h-8 border-4 border-t-transparent border-blue-500 rounded-full animate-spin" />
                  </div>
                ) : (
                  <table className="w-full text-sm text-left">
                    <thead className={`text-xs uppercase ${theme === 'light' ? 'bg-slate-50 text-slate-500' : 'bg-slate-800 text-slate-400'
                      }`}>
                      <tr>
                        <th className="p-3 w-10">
                          <input
                            type="checkbox"
                            checked={availableScales.length > 0 && selectedScales.size === availableScales.length}
                            onChange={toggleAllScales}
                            className="rounded border-slate-300"
                          />
                        </th>
                        <th className="p-3">Tag</th>
                        <th className="p-3 text-right">Current</th>
                        <th className="p-3 text-right">Total</th>
                        <th className="p-3">Custom Offset</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                      {availableScales.map((scale) => (
                        <tr key={scale.tag} className={theme === 'light' ? 'hover:bg-slate-50' : 'hover:bg-slate-800/50'}>
                          <td className="p-3">
                            <input
                              type="checkbox"
                              checked={selectedScales.has(scale.tag)}
                              onChange={() => toggleScaleSelection(scale.tag)}
                              className="rounded border-slate-300"
                            />
                          </td>
                          <td className={`p-3 font-mono ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
                            {getDisplayTag(scale.tag)}
                          </td>
                          <td className="p-3 text-right font-mono text-blue-500">{scale.current.toFixed(2)}</td>
                          <td className="p-3 text-right font-mono text-slate-500">{scale.total.toFixed(2)}</td>
                          <td className="p-3">
                            <input
                              type="number"
                              placeholder="0.00"
                              className={`w-full px-2 py-1 rounded border text-sm ${theme === 'light'
                                  ? 'bg-white border-slate-300'
                                  : 'bg-slate-800 border-slate-600 text-white'
                                }`}
                              value={customValues[scale.tag] ?? ''}
                              onChange={(e) => handleCustomValueChange(scale.tag, e.target.value)}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-6 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3">
                <button
                  onClick={() => setShowResetModal(false)}
                  className={`px-4 py-2 rounded-lg font-medium text-sm ${theme === 'light'
                      ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                >
                  Cancel
                </button>
                <button
                  onClick={confirmReset}
                  className="px-4 py-2 rounded-lg font-medium text-sm bg-red-500 text-white hover:bg-red-600 shadow-lg shadow-red-500/20"
                >
                  {selectedScales.size > 0 ? `Reset Selected (${selectedScales.size})` : 'Reset All'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </WaterSystemLayout>
  );
};

export default LiveMonitor;
