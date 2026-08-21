import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { kpiApi, KpiData, shiftApi, ShiftMaster } from '../../lib/api';
import { useScada } from '../../contexts/ScadaContext';
import ShiftIndicator from '../../components/ShiftIndicator';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import {
  Clock3,
  CheckCircle,
  XCircle,
  Droplet,
  BarChartBig,
  Gauge,
  ListOrdered,
  LayoutGrid,
  PercentCircle,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  RefreshCw,
  X,
  Factory as FactoryIcon,
  Package,
  Droplets,
  Zap,
  Timer,
  Activity,
  Boxes,
  Scale,
  Wheat,
  Percent,
  PackageX,
  PackageCheck,
  PackagePlus,
  Clock,
  Settings,
  LucideIcon,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// MetricCard Component (from SAPDashboard)
interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  color?: string;
  theme: 'light' | 'dark';
  icon?: LucideIcon;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, color, theme, icon: Icon }) => {
  return (
    <div className={`p-2 rounded-lg border transition-all duration-300 ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      <div className="flex items-center gap-1.5 mb-1">
        {Icon && (
          <Icon className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} style={color ? { color } : undefined} />
        )}
        <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          {title}
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className={`text-xl font-bold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`}
          style={color ? { color } : undefined}
        >
          {value}
        </span>
        {unit && (
          <span className={`text-xs font-medium ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
            }`}>
            {unit}
          </span>
        )}
      </div>
    </div>
  );
};

// GaugeCard Component (from SAPDashboard)
interface GaugeCardProps {
  label: string;
  value: number;
  color: string;
  theme: 'light' | 'dark';
}

const GaugeCard: React.FC<GaugeCardProps> = ({ label, value, color, theme }) => {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(Math.max(value, 0), 100);
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`p-2 rounded-lg border flex flex-col items-center justify-center transition-all duration-300 ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      <div className={`text-xs font-semibold tracking-wider mb-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
        }`}>
        {label}
      </div>
      <div className="relative inline-block">
        <svg width="72" height="72" className="transform -rotate-90">
          <circle
            cx="36"
            cy="36"
            r={radius}
            fill="none"
            stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
            strokeWidth="6"
            className="opacity-30"
          />
          <circle
            cx="36"
            cy="36"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={`text-base font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'
              }`}
            style={{ color }}
          >
            {Math.round(value)}%
          </span>
        </div>
      </div>
    </div>
  );
};

// Helper function to check if a shift has ended based on shift end time (HH:MM or HH:MM:SS format)
const hasShiftEnded = (shiftEndTime: string): boolean => {
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();

  // Parse shift end time (handles both "HH:MM" and "HH:MM:SS" formats)
  const timeParts = shiftEndTime.split(':');
  const shiftEndHour = parseInt(timeParts[0], 10);
  const shiftEndMinute = parseInt(timeParts[1] || '0', 10);

  // Convert to minutes for easier comparison
  const currentTotalMinutes = currentHour * 60 + currentMinute;
  const shiftEndTotalMinutes = shiftEndHour * 60 + shiftEndMinute;

  // Shift has ended if current time is past the shift end time
  return currentTotalMinutes >= shiftEndTotalMinutes;
};

// Helper function to filter shift data to only include completed shifts
const filterCompletedShifts = <T extends { time: string }>(
  data: T[],
  shifts: ShiftMaster[]
): T[] => {
  if (!shifts || shifts.length === 0) return data;

  return data.filter(item => {
    // Find the shift that matches this time label
    const matchingShift = shifts.find(s => {
      const shiftEndTime = s.end_time.substring(0, 5); // Get "HH:MM" format
      return item.time === shiftEndTime;
    });

    // If we found a matching shift, check if it has ended
    // If no matching shift found, include the data (might be historical)
    if (matchingShift) {
      return hasShiftEnded(matchingShift.end_time);
    }

    // For time labels that don't match any shift, check directly
    return hasShiftEnded(item.time);
  });
};

interface UserInfo { id: number; username: string; roles: string[]; }

const KpiCalculations = () => {
  const [kpiData, setKpiData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historicalChartData, setHistoricalChartData] = useState<HistoricalChartData | null>(null);
  const [packingShifts, setPackingShifts] = useState<ShiftMaster[]>([]);
  const [millingShifts, setMillingShifts] = useState<ShiftMaster[]>([]);
  const [activeTab, setActiveTab] = useState<'milling' | 'packing'>('milling');
  const { theme } = useTheme();
  const { scadaData } = useScada();

  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  });
  const currentUser = userData as UserInfo | null;
  const isAdmin = currentUser?.roles?.includes('admin') || false;
  const isMillingOnly = !isAdmin && (currentUser?.roles?.includes('milling_operator') ?? false);
  const isPackingOnly = !isAdmin && (currentUser?.roles?.includes('packing_operator') ?? false);

  // Auto-scale state to fit content to viewport
  const [scale, setScale] = useState(1);

  // Default tab by role: milling operator → milling only, packing operator → packing only
  useEffect(() => {
    if (isPackingOnly) setActiveTab('packing');
    else if (isMillingOnly) setActiveTab('milling');
  }, [isMillingOnly, isPackingOnly]);

  // Calculate scale to fit fixed-size dashboard in any viewport
  useEffect(() => {
    const calculateScale = () => {
      // Design size - must fit all content including bottom and right edges
      // Reduced height to ensure everything fits without scrolling
      const designWidth = 2000;
      const designHeight = 1100; // Reduced from 1200 to ensure fit

      // Available space - subtract sidebar and header
      const sidebarWidth = 240;
      const headerHeight = 80; // Account for top header
      const availableWidth = window.innerWidth - sidebarWidth;
      const availableHeight = window.innerHeight - headerHeight;

      // Calculate scale factors
      const scaleX = availableWidth / designWidth;
      const scaleY = availableHeight / designHeight;

      // Use the smaller scale to fit both dimensions
      // Min 0.5 for smaller screens, max 1.0 to ensure fit
      const newScale = Math.max(Math.min(scaleX, scaleY, 1.0), 0.5);
      setScale(newScale);
    };

    calculateScale();
    window.addEventListener('resize', calculateScale);
    return () => window.removeEventListener('resize', calculateScale);
  }, []);

  // Loading states for manual sync buttons
  const [syncingMilling, setSyncingMilling] = useState(false);
  const [syncingPacking, setSyncingPacking] = useState(false);

  // Custom popup state
  const [showCustomPopup, setShowCustomPopup] = useState(false);
  const [popupData, setPopupData] = useState<{
    title: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    onConfirm?: () => void;
  } | null>(null);

  // Function to validate and sanitize KPI data
  const validateKpiData = (data: KpiData): KpiData => {
    const sanitizeValue = (value: any): number => {
      if (value === null || value === undefined || isNaN(value)) {
        return 0;
      }
      return parseFloat(value.toString());
    };

    const validatedData = {
      milling_kpis: {
        "Mill Throughput (%)": sanitizeValue(data.milling_kpis["Mill Throughput (%)"]),
        "Mill Time Efficiency (%)": sanitizeValue(data.milling_kpis["Mill Time Efficiency (%)"]),
        "Total Utilization (%)": sanitizeValue(data.milling_kpis["Total Utilization (%)"]),
        "Milling Gain": sanitizeValue(data.milling_kpis["Milling Gain"]),
        "Milling Screening (%)": sanitizeValue(data.milling_kpis["Milling Screening (%)"]),
        "Flour Extraction (%)": sanitizeValue(data.milling_kpis["Flour Extraction (%)"]),
        "Milling Loss (%)": sanitizeValue(data.milling_kpis["Milling Loss (%)"]),
        "Net Hours (hrs)": sanitizeValue(data.milling_kpis["Net Hours (hrs)"]),
        "Downtime (hrs)": sanitizeValue(data.milling_kpis["Downtime (hrs)"]),
        // New KPIs
        "Max Utilization of Milling Capacity (%)": sanitizeValue(data.milling_kpis["Max Utilization of Milling Capacity (%)"]),
        "Pre Cleaning Screening (%)": sanitizeValue(data.milling_kpis["Pre Cleaning Screening (%)"]),
        "1st Break Capacity per Hour (t/h)": sanitizeValue(data.milling_kpis["1st Break Capacity per Hour (t/h)"]),
        "Bran Extraction (%)": sanitizeValue(data.milling_kpis["Bran Extraction (%)"]),
      },
      packing_kpis: {
        "Packing Line Capacity (bags/hr)": sanitizeValue(data.packing_kpis["Packing Line Capacity (bags/hr)"]),
        "Daily Packing Output (bags)": sanitizeValue(data.packing_kpis["Daily Packing Output (bags)"]),
        "Net Hours (hrs)": sanitizeValue(data.packing_kpis["Net Hours (hrs)"]),
        "Downtime (hrs)": sanitizeValue(data.packing_kpis["Downtime (hrs)"]),
        "Machine Utilization (%)": sanitizeValue(data.packing_kpis["Machine Utilization (%)"]),
        // New KPI
        "Packing Line Capacity (tons/hr)": sanitizeValue(data.packing_kpis["Packing Line Capacity (tons/hr)"]),
      },
      timestamp: data.timestamp,
      data_source: data.data_source,
    };

    // Check if all values are zero (no meaningful data)
    const allMillingZero = Object.values(validatedData.milling_kpis).every(v => v === 0);
    const allPackingZero = Object.values(validatedData.packing_kpis).every(v => v === 0);

    if (allMillingZero && allPackingZero) {
      validatedData.data_source = 'no_scada_data';
    }

    return validatedData;
  };

  const fetchKpiData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await kpiApi.getKpis();
      // Validate and sanitize the data before setting it
      const validatedData = validateKpiData(data);
      setKpiData(validatedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch KPI data');
      console.error('Error fetching KPI data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to show custom popup
  const showCustomAlert = (title: string, message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', onConfirm?: () => void) => {
    setPopupData({ title, message, type, onConfirm });
    setShowCustomPopup(true);
  };

  // Close custom popup
  const closeCustomPopup = () => {
    setShowCustomPopup(false);
    setPopupData(null);
  };

  // Manual sync handlers
  const handleSyncMilling = async () => {
    try {
      setSyncingMilling(true);
      const result = await kpiApi.sendMillingToSap();
      if (result.success) {
        setError(null);
        showCustomAlert(
          'Success',
          result.message || 'Milling KPIs sent to SAP successfully',
          'success'
        );
      } else {
        // Don't set error state - just show popup notification
        showCustomAlert(
          'Warning',
          result.message || 'Failed to send milling KPIs to SAP',
          'warning'
        );
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync milling KPIs to SAP';
      // Don't set error state - just show popup notification
      showCustomAlert(
        'Error',
        errorMessage,
        'error'
      );
      console.error('Error syncing milling KPIs:', err);
    } finally {
      setSyncingMilling(false);
    }
  };

  const handleSyncPacking = async () => {
    try {
      setSyncingPacking(true);
      const result = await kpiApi.sendPackingToSap();
      if (result.success) {
        setError(null);
        showCustomAlert(
          'Success',
          result.message || 'Packing KPIs sent to SAP successfully',
          'success'
        );
      } else {
        // Don't set error state - just show popup notification
        showCustomAlert(
          'Warning',
          result.message || 'Failed to send packing KPIs to SAP',
          'warning'
        );
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync packing KPIs to SAP';
      // Don't set error state - just show popup notification
      showCustomAlert(
        'Error',
        errorMessage,
        'error'
      );
      console.error('Error syncing packing KPIs:', err);
    } finally {
      setSyncingPacking(false);
    }
  };

  const fetchShiftsAndChartData = async () => {
    try {
      // First, fetch shifts to get the correct time labels
      const shiftsData = await shiftApi.getShifts();

      // Get packing shifts
      const packingShiftsData = shiftsData
        .filter((s: ShiftMaster) => s.department === 'PACKING')
        .sort((a: ShiftMaster, b: ShiftMaster) => a.sort_order - b.sort_order);
      setPackingShifts(packingShiftsData);

      // Get milling shifts
      const millingShiftsData = shiftsData
        .filter((s: ShiftMaster) => s.department === 'MILLING')
        .sort((a: ShiftMaster, b: ShiftMaster) => a.sort_order - b.sort_order);
      setMillingShifts(millingShiftsData);

      // Try to fetch shift-based KPI history (if backend has the new endpoint)
      try {
        const shiftHistoryResponse = await kpiApi.getShiftKpiHistory({
          department: 'PACKING',
        });

        const packingData = shiftHistoryResponse.packing_data || [];

        if (packingData.length > 0) {
          // Use actual shift data from API
          const chartData: HistoricalChartData = {
            dailyOutputData: packingData.map(p => ({
              time: p.time_label,
              output: parseFloat(p.kpis?.PACKING_BAG || '0'),
            })),
            packingLineCapacityData: packingData.map(p => ({
              time: p.time_label,
              capacity: parseFloat(p.kpis?.PACKING_CAPACITY_BAG || '0'),
            })),
            packingCapacityTonsData: packingData.map(p => ({
              time: p.time_label,
              capacity: parseFloat(p.kpis?.PACKING_CAPACITY_TON || '0'),
            })),
            netHoursData: packingData.map(p => ({
              time: p.time_label,
              hours: parseFloat(p.kpis?.PACKING_HOURS || '0'),
            })),
            downtimeData: packingData.map(p => ({
              time: p.time_label,
              downtime: parseFloat(p.kpis?.PACKING_TOTAL_DOWNTIME || '0'),
            })),
            machineUtilData: packingData.map(p => ({
              time: p.time_label,
              util: parseFloat(p.kpis?.PACKING_MACHINE_UTILIZ || '0'),
            })),
          };
          setHistoricalChartData(chartData);
          return;
        }
      } catch (apiErr) {
        console.log('Shift history API not available, using fallback with shift times');
      }

      // Fallback: Use shift end times for chart labels (no actual historical data)
      // This creates placeholder data points at correct shift times
      setHistoricalChartData(null); // Will use fallback in PackingSection with shift times

    } catch (err) {
      console.error('Failed to fetch shifts:', err);
      setHistoricalChartData(null);
    }
  };

  // Fetch KPI data with polling
  useEffect(() => {
    fetchKpiData();

    // Set up polling every 60 seconds to get fresh data
    const interval = setInterval(fetchKpiData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Fetch shifts and chart data on mount and refresh every minute
  useEffect(() => {
    fetchShiftsAndChartData();
    // Auto-refresh chart data every minute
    const interval = setInterval(fetchShiftsAndChartData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <WaterSystemLayout
        title="KPI Calculations"
        subtitle="Loading KPI data from database..."
      >
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3">
            <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
            <span className={theme === 'light' ? 'text-slate-700' : 'text-cyan-300'}>
              Loading KPI data...
            </span>
          </div>
        </div>
      </WaterSystemLayout>
    );
  }

  if (error) {
    return (
      <WaterSystemLayout
        title="KPI Calculations"
        subtitle="Error loading KPI data"
      >
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className={theme === 'light' ? 'text-slate-800 text-lg font-semibold mb-2' : 'text-red-400 text-lg font-semibold mb-2'}>
              Error Loading KPI Data
            </h3>
            <p className={theme === 'light' ? 'text-slate-600 mb-4' : 'text-slate-300 mb-4'}>
              {error}
            </p>
            <button
              onClick={fetchKpiData}
              className={`px-4 py-2 rounded-md flex items-center gap-2 mx-auto ${theme === 'light'
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-cyan-500 text-white hover:bg-cyan-600'
                }`}
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        </div>
      </WaterSystemLayout>
    );
  }

  if (!kpiData) {
    return (
      <WaterSystemLayout
        title="KPI Calculations"
        subtitle="No KPI data available"
      >
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h3 className={theme === 'light' ? 'text-slate-800 text-lg font-semibold' : 'text-yellow-400 text-lg font-semibold'}>
              No KPI Data Available
            </h3>
            <p className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
              No KPI data found in the database.
            </p>
          </div>
        </div>
      </WaterSystemLayout>
    );
  }

  return (
    <WaterSystemLayout
      title="PRODUCTION INSIGHTS"
      subtitle="REAL-TIME KPI ANALYTICS"
    >
      <style>{`
        /* Force white text for tabs and buttons in light mode */
        .kpi-tab-light {
          color: white !important;
        }
        
        .kpi-tab-light span {
          color: white !important;
        }
        
        .kpi-refresh-light {
          color: white !important;
        }
        
        .kpi-refresh-light span {
          color: white !important;
        }
        
        .kpi-refresh-light svg {
          color: white !important;
        }
      `}</style>
      <style>{`
        /* Ensure custom popup is always on top */
        .custom-popup-overlay {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          z-index: 9999 !important;
          display: flex !important;
          align-items: flex-start !important;
          justify-content: center !important;
          padding-top: 5vh !important;
        }
        
        .custom-popup-content {
          position: relative !important;
          z-index: 10000 !important;
          margin-top: 0 !important;
          transform: translateY(0) !important;
        }
      `}</style>
      {/* Scaling container */}
      <div style={{
        width: '100%',
        height: '100vh',
        overflow: 'hidden'
      }}>
        {/* Fixed-size dashboard that scales to fit viewport */}
        <div style={{
          width: '2000px',
          height: '1100px',
          transform: `scale(${scale})`,
          transformOrigin: 'top left'
        }}>
          <div className="flex flex-col h-full p-2 gap-4">
            {/* Header Section - Simplified */}
            <div className={`p-4 rounded-lg border backdrop-blur-md ${theme === 'light'
              ? 'bg-white/80 border-slate-200 shadow-sm'
              : 'bg-slate-900/60 border-slate-700/50'
              }`}>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                {/* Title and Status */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className={`text-xl font-black tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                      PRODUCTION INSIGHTS
                    </h1>
                    {/* Shift Indicators - show only relevant one for operators */}
                    <div className="flex items-center gap-2">
                      {(isAdmin || isMillingOnly) && <ShiftIndicator operation="milling" />}
                      {(isAdmin || isPackingOnly) && <ShiftIndicator operation="packing" />}
                    </div>
                  </div>
                  {kpiData && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className={`w-2 h-2 rounded-full ${kpiData.data_source === 'no_scada_data' || kpiData.data_source === 'error_fallback'
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                        }`} />
                      <span className={`text-xs font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-300'
                        }`}>
                        {kpiData.data_source === 'no_scada_data'
                          ? 'No SCADA data available - showing default values'
                          : kpiData.data_source === 'error_fallback'
                            ? 'Error in calculation - showing default values'
                            : kpiData.data_source === 'real_time_calculation'
                              ? 'Live data from SCADA system'
                              : 'Data source: ' + (kpiData.data_source || 'unknown')
                        }
                      </span>
                      {kpiData.timestamp && (
                        <span className={`text-xs ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                          }`}>
                          | Last updated: {new Date(kpiData.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={fetchKpiData}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 !text-white ${theme === 'light'
                      ? 'bg-blue-500 hover:bg-blue-600 shadow-md'
                      : 'bg-cyan-500 hover:bg-cyan-600 shadow-md'
                      }`}
                    style={{ color: 'white !important' }}
                    title="Refresh KPI Data"
                  >
                    <RefreshCw size={16} className="transition-all duration-300 group-hover:rotate-180" style={{ color: 'white !important' }} />
                    <span style={{ color: 'white !important' }}>UPDATE</span>
                  </button>

                  {(isAdmin || isMillingOnly) && (
                  <button
                    onClick={handleSyncMilling}
                    disabled={syncingMilling}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 !text-white ${syncingMilling ? 'opacity-50 cursor-not-allowed' : ''
                      } ${theme === 'light'
                        ? 'bg-blue-500 hover:bg-blue-600 shadow-md'
                        : 'bg-cyan-500 hover:bg-cyan-600 shadow-md'
                      }`}
                    style={{ color: 'white !important' }}
                    title="Manual Sync Milling"
                  >
                    <RefreshCw
                      size={16}
                      className={`transition-all duration-300 ${syncingMilling ? 'animate-spin' : 'group-hover:rotate-180'}`}
                      style={{ color: 'white !important' }}
                    />
                    <span style={{ color: 'white !important' }}>
                      {syncingMilling ? 'Syncing...' : 'Sync Milling'}
                    </span>
                  </button>
                  )}

                  {(isAdmin || isPackingOnly) && (
                  <button
                    onClick={handleSyncPacking}
                    disabled={syncingPacking}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 !text-white ${syncingPacking ? 'opacity-50 cursor-not-allowed' : ''
                      } ${theme === 'light'
                        ? 'bg-blue-500 hover:bg-blue-600 shadow-md'
                        : 'bg-cyan-500 hover:bg-cyan-600 shadow-md'
                      }`}
                    style={{ color: 'white !important' }}
                    title="Manual Sync Packing"
                  >
                    <RefreshCw
                      size={16}
                      className={`transition-all duration-300 ${syncingPacking ? 'animate-spin' : 'group-hover:rotate-180'}`}
                      style={{ color: 'white !important' }}
                    />
                    <span style={{ color: 'white !important' }}>
                      {syncingPacking ? 'Syncing...' : 'Sync Packing'}
                    </span>
                  </button>
                  )}
                </div>
              </div>
            </div>

            {/* Tab Selection - show both tabs only for admin; operators see only their tab */}
            <div className="flex gap-2 justify-center">
              {(isAdmin || isMillingOnly) && (
              <button
                onClick={() => setActiveTab('milling')}
                className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-bold text-xs transition-all duration-200 ${activeTab === 'milling'
                  ? theme === 'light'
                    ? 'bg-cyan-500 text-white shadow-md'
                    : 'bg-cyan-500 text-white shadow-md shadow-cyan-500/30'
                  : theme === 'light'
                    ? 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
                  }`}
              >
                <FactoryIcon className="w-4 h-4" />
                <span>MILLING KPIs</span>
              </button>
              )}
              {(isAdmin || isPackingOnly) && (
              <button
                onClick={() => setActiveTab('packing')}
                className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-bold text-xs transition-all duration-200 ${activeTab === 'packing'
                  ? theme === 'light'
                    ? 'bg-cyan-500 text-white shadow-md'
                    : 'bg-cyan-500 text-white shadow-md shadow-cyan-500/30'
                  : theme === 'light'
                    ? 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
                  }`}
              >
                <Package className="w-4 h-4" />
                <span>PACKING KPIs</span>
              </button>
              )}
            </div>

            {/* KPI Sections - Show only active tab */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'milling' ? (
                <MillingSection theme={theme} kpiData={kpiData} scadaData={scadaData} shifts={millingShifts} />
              ) : (
                <PackingSection theme={theme} kpiData={kpiData} historicalChartData={historicalChartData || undefined} shifts={packingShifts} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Custom Modern Popup */}
      {showCustomPopup && popupData && (
        <div className="custom-popup-overlay animate-in fade-in duration-300">
          {/* Backdrop */}
          <div
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${theme === 'light'
              ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30'
              : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
              }`}
            onClick={closeCustomPopup}
            style={{ top: 0, left: 0, right: 0, bottom: 0 }}
          />

          {/* Popup Content */}
          <div className={`custom-popup-content w-full max-w-2xl rounded-xl border shadow-2xl transition-all duration-300 transform backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${theme === 'light'
            ? 'bg-white/98 border-slate-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]'
            : 'bg-slate-900/95 border-cyan-400/40 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]'
            }`}>
            {/* Header */}
            <div className={`flex items-center gap-3 p-4 border-b ${theme === 'light' ? 'border-slate-200' : 'border-cyan-400/30'
              }`}>
              <div className={`p-2 rounded-lg ${popupData.type === 'success'
                ? theme === 'light' ? 'bg-green-100' : 'bg-green-900/30'
                : popupData.type === 'error'
                  ? theme === 'light' ? 'bg-red-100' : 'bg-red-900/30'
                  : popupData.type === 'warning'
                    ? theme === 'light' ? 'bg-orange-100' : 'bg-orange-900/30'
                    : theme === 'light' ? 'bg-blue-100' : 'bg-blue-900/30'
                }`}>
                {popupData.type === 'success' && (
                  <CheckCircle className={`h-6 w-6 ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`} />
                )}
                {popupData.type === 'error' && (
                  <XCircle className={`h-6 w-6 ${theme === 'light' ? 'text-red-600' : 'text-red-400'}`} />
                )}
                {popupData.type === 'warning' && (
                  <AlertCircle className={`h-6 w-6 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'}`} />
                )}
                {popupData.type === 'info' && (
                  <AlertCircle className={`h-6 w-6 ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`} />
                )}
              </div>
              <div className="flex-1">
                <h3 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                  }`}>
                  {popupData.title}
                </h3>
              </div>
              <button
                onClick={closeCustomPopup}
                className={`p-2 rounded-lg transition-all duration-200 hover:scale-110 ${theme === 'light'
                  ? 'hover:bg-slate-100 text-slate-600'
                  : 'hover:bg-slate-700/50 text-cyan-300'
                  }`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              <div className={`text-sm leading-relaxed whitespace-pre-wrap ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                {popupData.message}
              </div>
            </div>

            {/* Footer */}
            <div className={`flex justify-end gap-3 p-4 border-t ${theme === 'light' ? 'border-slate-200 bg-slate-50' : 'border-cyan-400/30 bg-slate-800/50'
              }`}>
              <button
                onClick={() => {
                  if (popupData.onConfirm) {
                    popupData.onConfirm();
                  }
                  closeCustomPopup();
                }}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 hover:scale-105 ${popupData.type === 'success'
                  ? theme === 'light'
                    ? 'bg-green-600 text-white hover:bg-green-700 shadow-md'
                    : 'bg-green-500 text-white hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                  : popupData.type === 'error'
                    ? theme === 'light'
                      ? 'bg-red-600 text-white hover:bg-red-700 shadow-md'
                      : 'bg-red-500 text-white hover:bg-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                    : popupData.type === 'warning'
                      ? theme === 'light'
                        ? 'bg-orange-600 text-white hover:bg-orange-700 shadow-md'
                        : 'bg-orange-500 text-white hover:bg-orange-400 shadow-[0_0_15px_rgba(249,115,22,0.3)]'
                      : theme === 'light'
                        ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md'
                        : 'bg-blue-500 text-white hover:bg-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]'
                  }`}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </WaterSystemLayout>
  );
};

// Milling Section Component (from SAPDashboard style)
const MillingSection: React.FC<{ theme: 'light' | 'dark'; kpiData: KpiData | null; scadaData?: any; shifts?: ShiftMaster[] }> = ({ theme, kpiData, scadaData, shifts }) => {
  const safeValue = (value: any): number => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return parseFloat(value.toString());
  };

  // All 16 Milling KPIs
  const throughput = kpiData ? safeValue(kpiData.milling_kpis['Mill Throughput (%)']) : 0;
  const timeEff = kpiData ? safeValue(kpiData.milling_kpis['Mill Time Efficiency (%)']) : 0;
  const totalUtil = kpiData ? safeValue(kpiData.milling_kpis['Total Utilization (%)']) : 0;
  const maxUtil = kpiData ? safeValue(kpiData.milling_kpis['Max Utilization of Milling Capacity (%)']) : 0;
  const firstBreakCap = kpiData ? safeValue(kpiData.milling_kpis['1st Break Capacity per Hour (t/h)']) : 0;
  const netHours = kpiData ? safeValue(kpiData.milling_kpis['Net Hours (hrs)']) : 0;
  const downtime = kpiData ? safeValue(kpiData.milling_kpis['Downtime (hrs)']) : 0;
  const millingGain = kpiData ? safeValue(kpiData.milling_kpis['Milling Gain']) : 0;
  const millingLoss = kpiData ? safeValue(kpiData.milling_kpis['Milling Loss (%)']) : 0;
  const flourExt = kpiData ? safeValue(kpiData.milling_kpis['Flour Extraction (%)']) : 0;
  const branExt = kpiData ? safeValue(kpiData.milling_kpis['Bran Extraction (%)']) : 0;
  const millingScreening = kpiData ? safeValue(kpiData.milling_kpis['Milling Screening (%)']) : 0;
  const preCleanScreening = kpiData ? safeValue(kpiData.milling_kpis['Pre Cleaning Screening (%)']) : 0;
  const preCleaningWater = scadaData?.totalPreCleaningWater ? parseFloat(scadaData.totalPreCleaningWater) : (kpiData && (kpiData.milling_kpis as any)['Pre Cleaning Water (L)'] ? safeValue((kpiData.milling_kpis as any)['Pre Cleaning Water (L)']) : 0);
  const waterCleanWheat = scadaData?.waterCleanWheat ? parseFloat(scadaData.waterCleanWheat) : (kpiData && (kpiData.milling_kpis as any)['Water Clean Wheat (L)'] ? safeValue((kpiData.milling_kpis as any)['Water Clean Wheat (L)']) : 0);
  const totalWaterUsed = scadaData?.totalWaterUsed ? parseFloat(scadaData.totalWaterUsed) : (kpiData && (kpiData.milling_kpis as any)['Total Water Used (L)'] ? safeValue((kpiData.milling_kpis as any)['Total Water Used (L)']) : 0);

  if (!kpiData) {
    return (
      <div className={`rounded-lg p-8 text-center ${theme === 'light' ? 'bg-white text-slate-600' : 'bg-slate-800 text-slate-300'}`}>
        No milling KPI data available.
      </div>
    );
  }

  // Generate hourly time labels for milling: 07:00 to 23:00
  const generateMillingTimeLabels = (): string[] => {
    const labels: string[] = [];
    for (let hour = 7; hour <= 23; hour++) {
      labels.push(`${hour.toString().padStart(2, '0')}:00`);
    }
    return labels;
  };

  // Get current hour for filtering (only show times up to current hour)
  const currentHour = new Date().getHours();

  // Milling time labels from 07:00 to 23:00, filtered to current time
  const millingTimeLabels = generateMillingTimeLabels().filter(time => {
    const hour = parseInt(time.split(':')[0], 10);
    return hour <= currentHour;
  });

  // Chart data for downtime - distribute values across time labels
  const downtimeData = millingTimeLabels.map((time, idx) => {
    const hour = parseInt(time.split(':')[0], 10);
    // Calculate progressive downtime based on time of day
    const progress = (idx + 1) / millingTimeLabels.length;
    return {
      time,
      downtime: Math.round(downtime * progress * 100) / 100 || 0,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={`p-2 rounded-lg shadow-lg border text-xs ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-800 border-slate-700'
          }`}>
          <p className={`font-bold mb-1 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>
                {entry.name}:
              </span>
              <span className={`font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                {entry.value}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`h-full p-2 rounded-lg border flex flex-col gap-2 overflow-y-auto ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg ${theme === 'light' ? 'bg-cyan-100 text-cyan-700' : 'bg-cyan-500/20 text-cyan-400'}`}>
            <FactoryIcon className="w-4 h-4" />
          </div>
          <h2 className={`text-sm font-bold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-cyan-400'
            }`}>
            MILLING LINE
          </h2>
        </div>
      </div>

      {/* Mill Throughput */}
      <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-slate-50 border-slate-200' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className="flex justify-between items-end mb-2">
          <div className={`text-sm font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
            Mill Throughput
          </div>
          <div className={`text-3xl font-bold ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`}>
            {throughput.toFixed(2)}%
          </div>
        </div>
        <div className={`h-3 rounded-full overflow-hidden ${theme === 'light' ? 'bg-slate-200' : 'bg-slate-700'
          }`}>
          <div
            className="h-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-1000 ease-out"
            style={{ width: `${Math.min(throughput, 100)}%` }}
          />
        </div>
      </div>

      {/* Efficiency & Utilization Gauges - Increased Height */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        <div className={`p-4 rounded-lg border flex flex-col items-center justify-center transition-all duration-300 min-h-[280px] ${theme === 'light'
          ? 'bg-white border-slate-200 shadow-sm'
          : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
          }`}>
          <div className={`text-xs font-semibold tracking-wider mb-3 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
            }`}>
            Mill Time Efficiency
          </div>
          <div className="relative inline-block">
            <svg width="160" height="160" className="transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                strokeWidth="12"
                className="opacity-30"
              />
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="12"
                strokeDasharray={2 * Math.PI * 70}
                strokeDashoffset={2 * Math.PI * 70 - (timeEff / 100) * 2 * Math.PI * 70}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-3xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`} style={{ color: '#f59e0b' }}>
                {Math.round(timeEff)}%
              </span>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border flex flex-col items-center justify-center transition-all duration-300 min-h-[280px] ${theme === 'light'
          ? 'bg-white border-slate-200 shadow-sm'
          : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
          }`}>
          <div className={`text-xs font-semibold tracking-wider mb-3 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
            }`}>
            Total Utilization
          </div>
          <div className="relative inline-block">
            <svg width="160" height="160" className="transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                strokeWidth="12"
                className="opacity-30"
              />
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="12"
                strokeDasharray={2 * Math.PI * 70}
                strokeDashoffset={2 * Math.PI * 70 - (totalUtil / 100) * 2 * Math.PI * 70}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-3xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`} style={{ color: '#f59e0b' }}>
                {Math.round(totalUtil)}%
              </span>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border flex flex-col items-center justify-center transition-all duration-300 min-h-[280px] ${theme === 'light'
          ? 'bg-white border-slate-200 shadow-sm'
          : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
          }`}>
          <div className={`text-xs font-semibold tracking-wider mb-3 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
            }`}>
            Max Utilization
          </div>
          <div className="relative inline-block">
            <svg width="160" height="160" className="transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                strokeWidth="12"
                className="opacity-30"
              />
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="#22c55e"
                strokeWidth="12"
                strokeDasharray={2 * Math.PI * 70}
                strokeDashoffset={2 * Math.PI * 70 - (maxUtil / 100) * 2 * Math.PI * 70}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-3xl font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`} style={{ color: '#22c55e' }}>
                {Math.round(maxUtil)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Capacity, Time & Milling Metrics - All 6 cards in one row */}
      <div className="grid grid-cols-6 gap-2 flex-shrink-0">
        <MetricCard
          title="1st Break Capacity"
          value={firstBreakCap.toFixed(2)}
          unit="t/h"
          theme={theme}
          icon={Zap}
        />
        <MetricCard
          title="Net Hours"
          value={netHours.toFixed(2)}
          unit="hrs"
          theme={theme}
          icon={Clock}
        />
        <MetricCard
          title="Milling Gain"
          value={millingGain.toFixed(2)}
          theme={theme}
          icon={TrendingUp}
        />
        <MetricCard
          title="Milling Loss"
          value={`${millingLoss.toFixed(2)}%`}
          theme={theme}
          icon={TrendingDown}
        />
        <MetricCard
          title="Flour Extraction"
          value={`${flourExt.toFixed(2)}%`}
          theme={theme}
          icon={Wheat}
        />
        <MetricCard
          title="Bran Extraction"
          value={`${branExt.toFixed(2)}%`}
          theme={theme}
          icon={Scale}
        />
      </div>

      {/* Downtime with Chart */}
      <div className={`p-3 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-xs font-semibold tracking-wider mb-2 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          Downtime
        </div>
        <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`} style={{ color: downtime > 0 ? '#ef4444' : '#22c55e' }}>
          {downtime.toFixed(2)} hrs
        </div>
        <div className="h-[180px]">
          {downtimeData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={downtimeData} margin={{ bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="downtime" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
              No completed shifts yet
            </div>
          )}
        </div>
      </div>

      {/* Screening Metrics and Water Consumption - Side by Side */}
      <div className="grid grid-cols-2 gap-2">
        {/* Screening Metrics */}
        <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-slate-50 border-slate-200' : 'bg-slate-800/30 border-slate-700'
          }`}>
          <div className={`text-xs font-bold tracking-wider mb-2 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            }`}>
            SCREENING METRICS
          </div>
          <div className="grid grid-cols-2 gap-2">
            <MetricCard
              title="Milling Screening"
              value={`${millingScreening.toFixed(2)}%`}
              color="#22c55e"
              theme={theme}
              icon={Activity}
            />
            <MetricCard
              title="Pre Cleaning Screening"
              value={`${preCleanScreening.toFixed(2)}%`}
              color="#22c55e"
              theme={theme}
              icon={Settings}
            />
          </div>
        </div>

        {/* Water Consumption */}
        <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-blue-50/50 border-blue-100' : 'bg-cyan-900/10 border-cyan-900/30'
          }`}>
          <div className="flex items-center gap-2 mb-2">
            <Droplets className={`w-4 h-4 ${theme === 'light' ? 'text-blue-500' : 'text-cyan-400'}`} />
            <div className={`text-xs font-bold tracking-wider ${theme === 'light' ? 'text-blue-700' : 'text-cyan-400'
              }`}>
              WATER CONSUMPTION
            </div>
          </div>
          <div className="space-y-2.5">
            <div className="flex justify-between items-center">
              <span className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>Pre Cleaning Water</span>
              <span className={`text-sm font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                {preCleaningWater.toFixed(2)} L
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>Water Clean Wheat</span>
              <span className={`text-sm font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                {waterCleanWheat.toFixed(2)} L
              </span>
            </div>
            <div className="h-px bg-slate-200 dark:bg-slate-700" />
            <div className="flex justify-between items-center">
              <span className={`text-xs font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>Total Water Used</span>
              <span className={`text-sm font-bold ${theme === 'light' ? 'text-blue-600' : 'text-cyan-400'}`}>
                {totalWaterUsed.toFixed(2)} L
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Chart data type for shift-based historical data
interface HistoricalChartData {
  dailyOutputData: Array<{ time: string; output: number }>;
  packingLineCapacityData: Array<{ time: string; capacity: number }>;
  packingCapacityTonsData: Array<{ time: string; capacity: number }>;
  netHoursData: Array<{ time: string; hours: number }>;
  downtimeData: Array<{ time: string; downtime: number }>;
  machineUtilData: Array<{ time: string; util: number }>;
}

// Packing Section Component (from SAPDashboard style)
const PackingSection: React.FC<{
  theme: 'light' | 'dark';
  kpiData: KpiData | null;
  historicalChartData?: HistoricalChartData;
  shifts?: ShiftMaster[];
}> = ({ theme, kpiData, historicalChartData, shifts }) => {
  const safeValue = (value: any): number => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return parseFloat(value.toString());
  };

  // All 6 Packing KPIs
  const dailyOutput = kpiData ? safeValue(kpiData.packing_kpis['Daily Packing Output (bags)']) : 0;
  const lineCapacityBags = kpiData ? safeValue(kpiData.packing_kpis['Packing Line Capacity (bags/hr)']) : 0;
  const lineCapacityTons = kpiData ? safeValue(kpiData.packing_kpis['Packing Line Capacity (tons/hr)']) : 0;
  const machineUtil = kpiData ? safeValue(kpiData.packing_kpis['Machine Utilization (%)']) : 0;
  const netHours = kpiData ? safeValue(kpiData.packing_kpis['Net Hours (hrs)']) : 0;
  const downtime = kpiData ? safeValue(kpiData.packing_kpis['Downtime (hrs)']) : 0;

  if (!kpiData) {
    return (
      <div className={`rounded-lg p-8 text-center ${theme === 'light' ? 'bg-white text-slate-600' : 'bg-slate-800 text-slate-300'}`}>
        No packing KPI data available.
      </div>
    );
  }

  // Generate hourly time labels for packing: 07:30 to 23:30
  const generatePackingTimeLabels = (): string[] => {
    const labels: string[] = [];
    for (let hour = 7; hour <= 23; hour++) {
      labels.push(`${hour.toString().padStart(2, '0')}:30`);
    }
    return labels;
  };

  // Get current hour for filtering (only show times up to current hour)
  const currentHour = new Date().getHours();
  const currentMinute = new Date().getMinutes();

  // Packing time labels from 07:30 to 23:30, filtered to current time
  const packingTimeLabels = generatePackingTimeLabels().filter(time => {
    const [hourStr, minStr] = time.split(':');
    const hour = parseInt(hourStr, 10);
    const minute = parseInt(minStr, 10);
    // Include if we've passed this time
    if (hour < currentHour) return true;
    if (hour === currentHour && minute <= currentMinute) return true;
    return false;
  });

  // Chart data for each KPI - distribute values across hourly time labels
  const packingLineCapacityData = packingTimeLabels.map((time) => ({
    time,
    capacity: lineCapacityBags,
  }));

  const dailyOutputData = packingTimeLabels.map((time, idx) => {
    const progress = (idx + 1) / packingTimeLabels.length;
    return {
      time,
      output: Math.round(dailyOutput * progress) || 0,
    };
  });

  const packingCapacityTonsData = packingTimeLabels.map((time) => ({
    time,
    capacity: lineCapacityTons,
  }));

  const netHoursData = packingTimeLabels.map((time, idx) => {
    const progress = (idx + 1) / packingTimeLabels.length;
    return {
      time,
      hours: Math.round(netHours * progress * 10) / 10 || 0,
    };
  });

  const downtimeData = packingTimeLabels.map((time, idx) => {
    const progress = (idx + 1) / packingTimeLabels.length;
    return {
      time,
      downtime: Math.round(downtime * progress * 100) / 100 || 0,
    };
  });

  const machineUtilData = packingTimeLabels.map((time) => ({
    time,
    util: machineUtil,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={`p-2 rounded-lg shadow-lg border text-xs ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-800 border-slate-700'
          }`}>
          <p className={`font-bold mb-1 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>
                {entry.name}:
              </span>
              <span className={`font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                {entry.value}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`h-full p-2 rounded-lg border flex flex-col gap-1.5 ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`p-1 rounded-lg ${theme === 'light' ? 'bg-orange-100 text-orange-700' : 'bg-orange-500/20 text-orange-400'}`}>
            <Package className="w-3.5 h-3.5" />
          </div>
          <h2 className={`text-xs font-bold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-orange-400'
            }`}>
            PACKING LINE
          </h2>
        </div>
      </div>

      {/* Top row with Output and Capacity Charts */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        {/* Daily Packing Output with Chart */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-1">
            <Boxes className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Daily Packing Output
            </div>
          </div>
          <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`}>
            {dailyOutput.toLocaleString()} <span className="text-xs font-medium text-slate-500">BAGS</span>
          </div>
          <div className="h-[350px]">
            {dailyOutputData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyOutputData} margin={{ bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                  <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="output" stroke="#0ea5e9" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
                No completed shifts yet
              </div>
            )}
          </div>
        </div>

        {/* Packing Line Capacity with Chart */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-1">
            <PackageCheck className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Packing Line Capacity
            </div>
          </div>
          <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`}>
            {lineCapacityBags.toLocaleString()} /hr
          </div>
          <div className="h-[350px]">
            {packingLineCapacityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={packingLineCapacityData} margin={{ bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                  <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="capacity" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
                No completed shifts yet
              </div>
            )}
          </div>
        </div>

        {/* Packing Capacity (tons) with Chart */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-1">
            <Scale className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Packing Capacity (tons)
            </div>
          </div>
          <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`}>
            {lineCapacityTons.toFixed(2)} /hr
          </div>
          <div className="h-[350px]">
            {packingCapacityTonsData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={packingCapacityTonsData} margin={{ bottom: 5 }}>
                  <defs>
                    <linearGradient id="colorTonsCapacity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                  <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="capacity" stroke="#6366f1" fill="url(#colorTonsCapacity)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
                No completed shifts yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Machine Utilization, Net Hours, Downtime - Single Row */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        {/* Machine Utilization with Circular Progress */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-2">
            <Gauge className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Machine Utilization
            </div>
          </div>
          <div className="h-[350px] flex items-center justify-center">
            <div className="relative inline-block">
              <svg width="220" height="220" className="transform -rotate-90">
                <circle
                  cx="110"
                  cy="110"
                  r="100"
                  fill="none"
                  stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                  strokeWidth="14"
                  className="opacity-30"
                />
                <circle
                  cx="110"
                  cy="110"
                  r="100"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="14"
                  strokeDasharray={2 * Math.PI * 100}
                  strokeDashoffset={2 * Math.PI * 100 - (machineUtil / 100) * 2 * Math.PI * 100}
                  strokeLinecap="round"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-4xl font-bold ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'}`}>
                  {machineUtil.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Net Hours with Chart */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-1">
            <Clock className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Net Hours
            </div>
          </div>
          <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`}>
            {netHours}h
          </div>
          <div className="h-[350px]">
            {netHoursData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={netHoursData} margin={{ bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                  <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="hours" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
                No completed shifts yet
              </div>
            )}
          </div>
        </div>

        {/* Downtime with Chart */}
        <div className={`p-3 rounded-lg border ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
          }`}>
          <div className="flex items-center gap-1.5 mb-1">
            <AlertCircle className={`w-3.5 h-3.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`} />
            <div className={`text-xs font-semibold tracking-wider ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
              }`}>
              Downtime
            </div>
          </div>
          <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
            }`} style={{ color: downtime > 0 ? '#ef4444' : '#22c55e' }}>
            {downtime}h
          </div>
          <div className="h-[350px]">
            {downtimeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={downtimeData} margin={{ bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
                  <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="downtime" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className={`flex items-center justify-center h-full text-xs ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`}>
                No completed shifts yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KpiCalculations;