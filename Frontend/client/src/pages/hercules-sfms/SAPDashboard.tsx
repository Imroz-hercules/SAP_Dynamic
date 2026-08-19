import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { TimeFilter } from '../../components/TimeFilter';
import { useHistoricalData } from '../../hooks/useHistoricalData';
import {
  RotateCcw,
  Package,
  Factory as FactoryIcon,
  Activity,
  Droplets,
  BarChart3,
  Timer,
  Zap,
  Clock,
  TrendingUp,
  TrendingDown,
  Filter,
  Gauge,
  Boxes,
  Scale
} from 'lucide-react';
import { kpiApi, KpiData, shiftApi, ShiftMaster, systemApi } from '../../lib/api';
import { useScada } from '../../contexts/ScadaContext';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart
} from 'recharts';

// ============================================================================
// INTERFACES
// ============================================================================

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  color?: string;
  theme: 'light' | 'dark';
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: React.ReactNode;
}

interface GaugeCardProps {
  label: string;
  value: number;
  color: string;
  theme: 'light' | 'dark';
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, color, theme, trend, trendValue, icon }) => {
  return (
    <div className={`p-2 rounded-lg border transition-all duration-300 ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      <div className={`text-xs font-semibold tracking-wider mb-1 flex items-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
        }`}>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        {title}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className={`text-lg font-bold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-white'
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
      {trend && (
        <div className={`text-xs mt-1 flex items-center gap-1 ${trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-slate-500'
          }`}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '•'} {trendValue}
        </div>
      )}
    </div>
  );
};

const GaugeCard: React.FC<GaugeCardProps> = ({ label, value, color, theme }) => {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(Math.max(value, 0), 100);
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  const svgSize = 70;
  const center = svgSize / 2;

  return (
    <div className={`p-2 rounded-lg border flex flex-col items-center justify-center transition-all duration-300 min-h-0 ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      <div className={`text-xs font-semibold tracking-wider mb-1.5 flex-shrink-0 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
        }`}>
        {label}
      </div>
      <div className="relative inline-block flex-shrink-0" style={{ width: svgSize, height: svgSize }}>
        <svg width={svgSize} height={svgSize} className="transform -rotate-90" style={{ overflow: 'visible' }}>
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
            strokeWidth="5"
            className="opacity-30"
          />
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="4"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={`text-sm font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'
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

// Milling Section Component
const MillingSection: React.FC<{ 
  theme: 'light' | 'dark'; 
  kpiData: KpiData | null; 
  scadaData?: any; 
  shifts?: ShiftMaster[]; 
  isHistoricalMode?: boolean;
  dateRange?: { startDate?: string; endDate?: string };
}> = ({ theme, kpiData, scadaData, shifts, isHistoricalMode, dateRange }) => {
  const safeValue = (value: any): number => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return parseFloat(value.toString());
  };

  // Show "No Data" message if no data is available
  if (!kpiData) {
    return (
      <div className={`p-6 rounded-2xl border shadow-sm ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-900 border-slate-800'}`}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">📊</span>
          <h2 className={`text-sm font-semibold tracking-widest ${theme === 'light' ? 'text-slate-700' : 'text-slate-200'}`}>
            MILLING LINE
          </h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <span className="text-4xl mb-4 block">📭</span>
            <p className={`text-lg font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              No data available
            </p>
            <p className={`text-sm mt-2 ${theme === 'light' ? 'text-slate-500' : 'text-slate-500'}`}>
              No KPI records found for the selected date and shift filters
            </p>
          </div>
        </div>
      </div>
    );
  }

  // All 16 Milling KPIs - no fallback values, show 0 if no data
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

  // Check if date range spans multiple days
  const isMultiDayRange = (): boolean => {
    if (!dateRange?.startDate || !dateRange?.endDate) return false;
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    return start.getTime() !== end.getTime();
  };

  // Generate daily date labels for multi-day range
  const generateDailyLabels = (): string[] => {
    if (!dateRange?.startDate || !dateRange?.endDate) return [];
    const labels: string[] = [];
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    const current = new Date(start);
    
    while (current <= end) {
      const day = current.getDate();
      const month = current.toLocaleString('en-US', { month: 'short' });
      labels.push(`${month} ${day}`);
      current.setDate(current.getDate() + 1);
    }
    return labels;
  };

  // Generate hourly time labels for milling: 07:00 to 23:00
  const generateMillingTimeLabels = (): string[] => {
    const labels: string[] = [];
    for (let hour = 7; hour <= 23; hour++) {
      labels.push(`${hour.toString().padStart(2, '0')}:00`);
    }
    return labels;
  };

  // Get current hour for filtering (only show times up to current hour) in live mode
  const currentHour = new Date().getHours();
  
  // Choose labels based on whether it's multi-day range or single day
  const timeLabels = isMultiDayRange() 
    ? generateDailyLabels()
    : isHistoricalMode 
      ? generateMillingTimeLabels() 
      : generateMillingTimeLabels().filter(time => {
          const hour = parseInt(time.split(':')[0], 10);
          return hour <= currentHour;
        });

  // Chart data for downtime - use appropriate time labels
  const downtimeData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
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
          <div className={`text-2xl font-bold ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`}>
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

      {/* Efficiency & Utilization Gauges */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        <GaugeCard label="Mill Time Efficiency" value={timeEff} color="#f59e0b" theme={theme} />
        <GaugeCard label="Total Utilization" value={totalUtil} color="#f59e0b" theme={theme} />
        <GaugeCard label="Max Utilization" value={maxUtil} color="#22c55e" theme={theme} />
      </div>

      {/* Capacity, Time & Milling Metrics */}
      <div className="grid grid-cols-3 gap-2 flex-shrink-0">
        <MetricCard
          title="1st Break Capacity"
          value={firstBreakCap.toFixed(2)}
          unit="t/h"
          theme={theme}
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Net Hours"
          value={netHours.toFixed(2)}
          unit="hrs"
          theme={theme}
          icon={<Clock className="w-3.5 h-3.5" />}
        />
        <MetricCard 
          title="Milling Gain" 
          value={millingGain.toFixed(2)} 
          theme={theme}
          icon={<TrendingUp className="w-3.5 h-3.5" />}
        />
        <MetricCard 
          title="Milling Loss" 
          value={`${millingLoss.toFixed(2)}%`} 
          theme={theme}
          icon={<TrendingDown className="w-3.5 h-3.5" />}
        />
        <MetricCard 
          title="Flour Extraction" 
          value={`${flourExt.toFixed(2)}%`} 
          theme={theme}
          icon={<Package className="w-3.5 h-3.5" />}
        />
        <MetricCard 
          title="Bran Extraction" 
          value={`${branExt.toFixed(2)}%`} 
          theme={theme}
          icon={<Boxes className="w-3.5 h-3.5" />}
        />
      </div>

      {/* Downtime with Chart */}
      <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 flex items-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Timer className="w-3.5 h-3.5" />
          Downtime
        </div>
        <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`} style={{ color: downtime > 0 ? '#ef4444' : '#22c55e' }}>
          {downtime.toFixed(2)} hrs
        </div>
        <div className="h-[50px] -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={downtimeData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="downtime" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Screening Metrics */}
      <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-slate-50 border-slate-200' : 'bg-slate-800/30 border-slate-700'
        }`}>
        <div className={`text-sm font-bold tracking-wider mb-2 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
          }`}>
          SCREENING METRICS
        </div>
        <div className="grid grid-cols-2 gap-2">
          <MetricCard
            title="Milling Screening"
            value={`${millingScreening.toFixed(2)}%`}
            color="#22c55e"
            theme={theme}
            icon={<Filter className="w-3.5 h-3.5" />}
          />
          <MetricCard
            title="Pre Cleaning Screening"
            value={`${preCleanScreening.toFixed(2)}%`}
            color="#22c55e"
            theme={theme}
            icon={<Filter className="w-3.5 h-3.5" />}
          />
        </div>
      </div>

      {/* Water Consumption */}
      <div className={`p-4 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-blue-50/50 border-blue-100' : 'bg-cyan-900/10 border-cyan-900/30'
        }`}>
        <div className="flex items-center gap-2 mb-3">
          <Droplets className={`w-4 h-4 ${theme === 'light' ? 'text-blue-500' : 'text-cyan-400'}`} />
          <div className={`text-sm font-bold tracking-wider ${theme === 'light' ? 'text-blue-700' : 'text-cyan-400'
            }`}>
            WATER CONSUMPTION
          </div>
        </div>
        <div className="space-y-2.5">
          <div className="flex justify-between items-center">
            <span className={`text-sm ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>Pre Cleaning Water</span>
            <span className={`text-sm font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
              {preCleaningWater.toFixed(2)} L
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className={`text-sm ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>Water Clean Wheat</span>
            <span className={`text-sm font-bold ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
              {waterCleanWheat.toFixed(2)} L
            </span>
          </div>
          <div className="h-px bg-slate-200 dark:bg-slate-700" />
          <div className="flex justify-between items-center">
            <span className={`text-sm font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>Total Water Used</span>
            <span className={`text-sm font-bold ${theme === 'light' ? 'text-blue-600' : 'text-cyan-400'}`}>
              {totalWaterUsed.toFixed(2)} L
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Charts Section Component
const ChartsSection: React.FC<{ 
  theme: 'light' | 'dark'; 
  kpiData: KpiData | null; 
  shifts?: ShiftMaster[]; 
  isHistoricalMode?: boolean;
  dateRange?: { startDate?: string; endDate?: string };
}> = ({ theme, kpiData, shifts, isHistoricalMode, dateRange }) => {
  
  // Check if date range spans multiple days
  const isMultiDayRange = (): boolean => {
    if (!dateRange?.startDate || !dateRange?.endDate) return false;
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    return start.getTime() !== end.getTime();
  };

  // Generate daily date labels for multi-day range
  const generateDailyLabels = (): string[] => {
    if (!dateRange?.startDate || !dateRange?.endDate) return [];
    const labels: string[] = [];
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    const current = new Date(start);
    
    while (current <= end) {
      const day = current.getDate();
      const month = current.toLocaleString('en-US', { month: 'short' });
      labels.push(`${month} ${day}`);
      current.setDate(current.getDate() + 1);
    }
    return labels;
  };

  // Generate hourly time labels for milling: 07:00 to 23:00
  const generateMillingTimeLabels = (): string[] => {
    const labels: string[] = [];
    for (let hour = 7; hour <= 23; hour++) {
      labels.push(`${hour.toString().padStart(2, '0')}:00`);
    }
    return labels;
  };

  // Get current hour for filtering (only show times up to current hour) in live mode
  const currentHour = new Date().getHours();
  
  // Choose labels based on whether it's multi-day range or single day
  const timeLabels = isMultiDayRange() 
    ? generateDailyLabels()
    : isHistoricalMode 
      ? generateMillingTimeLabels() 
      : generateMillingTimeLabels().filter(time => {
          const hour = parseInt(time.split(':')[0], 10);
          return hour <= currentHour;
        });

  // Get KPI values for charts
  const safeValue = (value: any): number => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return parseFloat(value.toString());
  };

  // Show "No Data" message if no data is available
  if (!kpiData) {
    return (
      <div className={`p-6 rounded-2xl border shadow-sm h-full ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-900 border-slate-800'}`}>
        <div className="flex items-center justify-center h-full py-12">
          <div className="text-center">
            <span className="text-4xl mb-4 block">📊</span>
            <p className={`text-lg font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              No chart data available
            </p>
            <p className={`text-sm mt-2 ${theme === 'light' ? 'text-slate-500' : 'text-slate-500'}`}>
              Select a date with available KPI data to view charts
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No fallback values, show 0 if no data
  const throughput = kpiData ? safeValue(kpiData.milling_kpis['Mill Throughput (%)']) : 0;
  const timeEff = kpiData ? safeValue(kpiData.milling_kpis['Mill Time Efficiency (%)']) : 0;
  const flourExt = kpiData ? safeValue(kpiData.milling_kpis['Flour Extraction (%)']) : 0;
  const branExt = kpiData ? safeValue(kpiData.milling_kpis['Bran Extraction (%)']) : 0;
  const totalWater = kpiData && (kpiData.milling_kpis as any)['Total Water Used (L)'] 
    ? safeValue((kpiData.milling_kpis as any)['Total Water Used (L)']) : 0;

  // Chart data using appropriate time labels (daily for multi-day, hourly for single day)
  const throughputData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      throughput: Math.round(throughput * (0.9 + (progress * 0.1)) * 100) / 100,
      efficiency: Math.round(timeEff * (0.95 + (progress * 0.05)) * 100) / 100,
    };
  });

  const extractionData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      flour: Math.round(flourExt * (0.95 + (progress * 0.05)) * 100) / 100,
      bran: Math.round(branExt * (0.98 + (progress * 0.02)) * 100) / 100,
    };
  });

  const waterData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      usage: Math.round(totalWater * progress * 100) / 100,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={`p-3 rounded-lg shadow-lg border ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-800 border-slate-700'
          }`}>
          <p className={`text-xs font-bold mb-2 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-xs">
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

  const ChartContainer = ({ title, subtitle, children }: { title: string, subtitle: string, children: React.ReactNode }) => (
    <div className={`p-1.5 rounded-lg border h-full flex flex-col ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      <div className="mb-0.5 flex-shrink-0">
        <h3 className={`text-sm font-bold tracking-wider ${theme === 'light' ? 'text-slate-900' : 'text-cyan-400'
          }`}>
          {title}
        </h3>
        <p className={`text-xs ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          {subtitle}
        </p>
      </div>
      <div className="flex-1 min-h-0 -ml-4 pr-2 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          {children as React.ReactElement}
        </ResponsiveContainer>
      </div>
    </div>
  );

  return (
    <div className="grid grid-cols-1 gap-2 h-full overflow-y-auto">
      <ChartContainer title="THROUGHPUT VS. EFFICIENCY" subtitle="Real-time Correlation">
        <LineChart data={throughputData} margin={{ top: 10, left: -10, right: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
          <XAxis
            dataKey="time"
            stroke={theme === 'light' ? '#94a3b8' : '#64748b'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke={theme === 'light' ? '#94a3b8' : '#ffffff'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ paddingTop: '5px', fontSize: '14px' }} />
          <Line
            type="monotone"
            dataKey="throughput"
            name="Throughput"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={{ r: 3, fill: '#0ea5e9', strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="efficiency"
            name="Efficiency"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ r: 3, fill: '#22c55e', strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ChartContainer>

      <ChartContainer title="EXTRACTION BALANCE" subtitle="Yield Distribution">
        <AreaChart data={extractionData} margin={{ left: -10, right: 10 }}>
          <defs>
            <linearGradient id="colorFlour" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorBran" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
          <XAxis
            dataKey="time"
            stroke={theme === 'light' ? '#94a3b8' : '#64748b'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke={theme === 'light' ? '#94a3b8' : '#ffffff'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ paddingTop: '5px', fontSize: '14px' }} />
          <Area
            type="monotone"
            dataKey="flour"
            name="Flour"
            stackId="1"
            stroke="#6366f1"
            fill="url(#colorFlour)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="bran"
            name="Bran"
            stackId="1"
            stroke="#14b8a6"
            fill="url(#colorBran)"
            strokeWidth={2}
          />
        </AreaChart>
      </ChartContainer>

      <ChartContainer title="WATER USAGE" subtitle="Tempering (L)">
        <LineChart data={waterData} margin={{ left: -10, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
          <XAxis
            dataKey="time"
            stroke={theme === 'light' ? '#94a3b8' : '#64748b'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke={theme === 'light' ? '#94a3b8' : '#ffffff'}
            fontSize={16}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="step"
            dataKey="usage"
            name="Usage"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={{ r: 3, fill: '#0ea5e9', strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ChartContainer>
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

// Packing Section Component
const PackingSection: React.FC<{ 
  theme: 'light' | 'dark'; 
  kpiData: KpiData | null;
  historicalChartData?: HistoricalChartData;
  shifts?: ShiftMaster[];
  isHistoricalMode?: boolean;
  dateRange?: { startDate?: string; endDate?: string };
}> = ({ theme, kpiData, historicalChartData, shifts, isHistoricalMode, dateRange }) => {
  const safeValue = (value: any): number => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return parseFloat(value.toString());
  };

  // Show "No Data" message if no data is available
  if (!kpiData) {
    return (
      <div className={`p-6 rounded-2xl border shadow-sm ${theme === 'light' ? 'bg-white border-slate-200' : 'bg-slate-900 border-slate-800'}`}>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">📦</span>
          <h2 className={`text-sm font-semibold tracking-widest ${theme === 'light' ? 'text-slate-700' : 'text-slate-200'}`}>
            PACKING LINE
          </h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <span className="text-4xl mb-4 block">📭</span>
            <p className={`text-lg font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              No data available
            </p>
            <p className={`text-sm mt-2 ${theme === 'light' ? 'text-slate-500' : 'text-slate-500'}`}>
              No KPI records found for the selected date and shift filters
            </p>
          </div>
        </div>
      </div>
    );
  }

  // All 6 Packing KPIs - no fallback values, show 0 if no data
  const dailyOutput = kpiData ? safeValue(kpiData.packing_kpis['Daily Packing Output (bags)']) : 0;
  const lineCapacityBags = kpiData ? safeValue(kpiData.packing_kpis['Packing Line Capacity (bags/hr)']) : 0;
  const lineCapacityTons = kpiData ? safeValue(kpiData.packing_kpis['Packing Line Capacity (tons/hr)']) : 0;
  const machineUtil = kpiData ? safeValue(kpiData.packing_kpis['Machine Utilization (%)']) : 0;
  const netHours = kpiData ? safeValue(kpiData.packing_kpis['Net Hours (hrs)']) : 0;
  const downtime = kpiData ? safeValue(kpiData.packing_kpis['Downtime (hrs)']) : 0;

  // Check if date range spans multiple days
  const isMultiDayRange = (): boolean => {
    if (!dateRange?.startDate || !dateRange?.endDate) return false;
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    return start.getTime() !== end.getTime();
  };

  // Generate daily date labels for multi-day range
  const generateDailyLabels = (): string[] => {
    if (!dateRange?.startDate || !dateRange?.endDate) return [];
    const labels: string[] = [];
    const start = new Date(dateRange.startDate.split(' ')[0]);
    const end = new Date(dateRange.endDate.split(' ')[0]);
    const current = new Date(start);
    
    while (current <= end) {
      const day = current.getDate();
      const month = current.toLocaleString('en-US', { month: 'short' });
      labels.push(`${month} ${day}`);
      current.setDate(current.getDate() + 1);
    }
    return labels;
  };

  // Generate hourly time labels for packing: 07:30 to 23:30
  const generatePackingTimeLabels = (): string[] => {
    const labels: string[] = [];
    for (let hour = 7; hour <= 23; hour++) {
      labels.push(`${hour.toString().padStart(2, '0')}:30`);
    }
    return labels;
  };

  // Get current hour for filtering (only show times up to current hour) in live mode
  const currentHour = new Date().getHours();
  const currentMinute = new Date().getMinutes();
  
  // Choose labels based on whether it's multi-day range or single day
  const timeLabels = isMultiDayRange() 
    ? generateDailyLabels()
    : isHistoricalMode 
      ? generatePackingTimeLabels() 
      : generatePackingTimeLabels().filter(time => {
          const [hourStr, minStr] = time.split(':');
          const hour = parseInt(hourStr, 10);
          const minute = parseInt(minStr, 10);
          if (hour < currentHour) return true;
          if (hour === currentHour && minute <= currentMinute) return true;
          return false;
        });

  // Chart data for each KPI - use appropriate time labels
  const packingLineCapacityData = timeLabels.map((time) => ({
    time,
    capacity: lineCapacityBags,
  }));

  const dailyOutputData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      output: Math.round(dailyOutput * progress) || 0,
    };
  });

  const packingCapacityTonsData = timeLabels.map((time) => ({
    time,
    capacity: lineCapacityTons,
  }));

  const netHoursData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      hours: Math.round(netHours * progress * 10) / 10 || 0,
    };
  });

  const downtimeData = timeLabels.map((time, idx) => {
    const progress = (idx + 1) / timeLabels.length;
    return {
      time,
      downtime: Math.round(downtime * progress * 100) / 100 || 0,
    };
  });

  const machineUtilData = timeLabels.map((time) => ({
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
    <div className={`h-full p-2 rounded-lg border flex flex-col gap-1.5 overflow-y-auto ${theme === 'light'
      ? 'bg-white border-slate-200 shadow-sm'
      : 'bg-slate-800/50 border-slate-700 backdrop-blur-sm'
      }`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg ${theme === 'light' ? 'bg-orange-100 text-orange-700' : 'bg-orange-500/20 text-orange-400'}`}>
            <Package className="w-4 h-4" />
          </div>
          <h2 className={`text-sm font-bold tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-orange-400'
            }`}>
            PACKING LINE
          </h2>
        </div>
      </div>

      {/* Daily Packing Output */}
      <div className={`p-1.5 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 pt-1 flex-shrink-0 flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Package className="w-4 h-4" />
          Daily Packing Output
        </div>
        <div className={`text-base font-bold tracking-tight mb-1 flex-shrink-0 text-center ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`}>
          {dailyOutput.toLocaleString()} <span className="text-xs font-medium text-slate-500">BAGS</span>
        </div>
        <div className="flex-1 min-h-0 -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyOutputData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="output" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Net Hours */}
      <div className={`p-1.5 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 pt-1 flex-shrink-0 flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Clock className="w-4 h-4" />
          Net Hours
        </div>
        <div className={`text-base font-bold tracking-tight mb-1 flex-shrink-0 text-center ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`}>
          {netHours}h
        </div>
        <div className="flex-1 min-h-0 -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={netHoursData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis 
                dataKey="time" 
                stroke={theme === 'light' ? '#94a3b8' : '#ffffff'} 
                fontSize={16} 
                tickLine={false} 
                axisLine={false}
                angle={0}
                textAnchor="middle"
                height={30}
              />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#ffffff'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="hours" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Packing Line Capacity */}
      <div className={`p-1.5 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 pt-1 flex-shrink-0 flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <BarChart3 className="w-4 h-4" />
          Packing Line Capacity
        </div>
        <div className={`text-base font-bold tracking-tight mb-1 flex-shrink-0 text-center ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`}>
          {lineCapacityBags.toLocaleString()} /hr
        </div>
        <div className="flex-1 min-h-0 -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={packingLineCapacityData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="capacity" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Packing Capacity (tons) */}
      <div className={`p-1.5 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 pt-1 flex-shrink-0 flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Scale className="w-4 h-4" />
          Packing Capacity (tons)
        </div>
        <div className={`text-base font-bold tracking-tight mb-1 flex-shrink-0 text-center ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`}>
          {lineCapacityTons.toFixed(2)} /hr
        </div>
        <div className="flex-1 min-h-0 -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={packingCapacityTonsData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="capacity" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Machine Utilization with Circular Progress */}
      <div className={`p-2 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-2 flex-shrink-0 text-center flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Gauge className="w-4 h-4" />
          Machine Utilization
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="relative inline-block">
            <svg width="80" height="80" className="transform -rotate-90">
              <circle
                cx="40"
                cy="40"
                r="32"
                fill="none"
                stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                strokeWidth="6"
                className="opacity-30"
              />
              <circle
                cx="40"
                cy="40"
                r="32"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="5"
                strokeDasharray={2 * Math.PI * 32}
                strokeDashoffset={2 * Math.PI * 32 - (machineUtil / 100) * 2 * Math.PI * 32}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-base font-bold ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'}`}>
                {machineUtil.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Net Hours with Chart */}
      <div className={`p-2 rounded-lg border flex-shrink-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-xs font-semibold tracking-wider mb-1 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          Net Hours
        </div>
        <div className={`text-lg font-bold tracking-tight mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`}>
          {netHours}h
        </div>
        <div className="h-[60px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={netHoursData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="hours" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Downtime with Chart */}
      <div className={`p-1.5 rounded-lg border flex-1 flex flex-col min-h-0 ${theme === 'light' ? 'bg-white border-slate-200 shadow-sm' : 'bg-slate-800/50 border-slate-700'
        }`}>
        <div className={`text-sm font-semibold tracking-wider mb-1 pt-1 flex-shrink-0 text-center flex items-center justify-center gap-1.5 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
          }`}>
          <Timer className="w-4 h-4" />
          Downtime
        </div>
        <div className={`text-base font-bold tracking-tight mb-1 flex-shrink-0 text-center ${theme === 'light' ? 'text-slate-900' : 'text-white'
          }`} style={{ color: downtime > 0 ? '#ef4444' : '#22c55e' }}>
          {downtime}h
        </div>
        <div className="flex-1 min-h-0 -ml-4 pr-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={downtimeData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e2e8f0' : '#334155'} vertical={false} />
              <XAxis dataKey="time" stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <YAxis stroke={theme === 'light' ? '#94a3b8' : '#64748b'} fontSize={16} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="downtime" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};


// ============================================================================
// MAIN COMPONENT
// ============================================================================

const SAPDashboard = () => {
  const [kpiData, setKpiData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historicalChartData, setHistoricalChartData] = useState<HistoricalChartData | null>(null);
  const [packingShifts, setPackingShifts] = useState<ShiftMaster[]>([]);
  const [millingShifts, setMillingShifts] = useState<ShiftMaster[]>([]);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true); // Default to demo mode
  const { theme } = useTheme();
  const { scadaData } = useScada();
  
  // Auto-scale state to fit content to viewport
  const [scale, setScale] = useState(1);
  
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
  
  // Historical data management
  const {
    filters,
    isHistoricalMode,
    periodLabel,
    handleApplyFilters,
    resetToLive,
  } = useHistoricalData('live');

  // Helper function to map API payload keys to KPI format
  const mapPayloadToKpiFormat = (payload: Record<string, string>, department: 'MILLING' | 'PACKING'): Record<string, number> => {
    const sanitizeValue = (value: any): number => {
      if (value === null || value === undefined) return 0;
      const numValue = parseFloat(value.toString());
      return isNaN(numValue) ? 0 : numValue;
    };

    if (department === 'MILLING') {
      return {
        "Mill Throughput (%)": sanitizeValue(payload.MILL_THROUGHPUT),
        "Mill Time Efficiency (%)": sanitizeValue(payload.MILL_TIME_EFFICIENCY),
        "Total Utilization (%)": sanitizeValue(payload.TOTAL_UTILIZATION),
        "Milling Gain": sanitizeValue(payload.MILLING_GAIN),
        "Milling Screening (%)": sanitizeValue(payload.MILLING_SCREENING),
        "Flour Extraction (%)": sanitizeValue(payload.FLOUR_EXTRACTION),
        "Milling Loss (%)": sanitizeValue(payload.MILLING_LOSS),
        "Net Hours (hrs)": sanitizeValue(payload.NET_HOURS),
        "Downtime (hrs)": sanitizeValue(payload.MILLING_DOWN_TIME),
        "Max Utilization of Milling Capacity (%)": sanitizeValue(payload.MAX_UTILIZATION),
        "Pre Cleaning Screening (%)": sanitizeValue(payload.PRE_CLEAN_SCREENING),
        "1st Break Capacity per Hour (t/h)": sanitizeValue(payload.BREAK_CAPACITY),
        "Bran Extraction (%)": sanitizeValue(payload.BRAN_EXTRACTION),
        "Pre Cleaning Water (L)": sanitizeValue(payload.PRE_CLEAN_WATER),
        "Water Clean Wheat (L)": sanitizeValue(payload.CLEANING_WATER),
        "Total Water Used (L)": sanitizeValue(payload.TOTAL_WATER),
      };
    } else {
      return {
        "Packing Line Capacity (bags/hr)": sanitizeValue(payload.PACKING_CAPACITY_BAG),
        "Daily Packing Output (bags)": sanitizeValue(payload.PACKING_BAG),
        "Net Hours (hrs)": sanitizeValue(payload.PACKING_HOURS),
        "Downtime (hrs)": sanitizeValue(payload.PACKING_TOTAL_DOWNTIME),
        "Machine Utilization (%)": sanitizeValue(payload.PACKING_MACHINE_UTILIZ),
        "Packing Line Capacity (tons/hr)": sanitizeValue(payload.PACKING_CAPACITY_TON),
      };
    }
  };

  // Helper function to aggregate historical KPI data
  const aggregateHistoricalKpis = (records: Array<{ kpi_payload: Record<string, string>; department: string }>): KpiData | null => {
    if (records.length === 0) return null;

    const millingRecords = records.filter(r => r.department === 'MILLING');
    const packingRecords = records.filter(r => r.department === 'PACKING');

    // Aggregate milling KPIs (average)
    const aggregateMilling = (key: string): number => {
      const values = millingRecords
        .map(r => {
          const mapped = mapPayloadToKpiFormat(r.kpi_payload, 'MILLING');
          return mapped[key];
        })
        .filter(v => !isNaN(v) && v !== 0);
      if (values.length === 0) return 0;
      return values.reduce((sum, v) => sum + v, 0) / values.length;
    };

    // Aggregate packing KPIs (average)
    const aggregatePacking = (key: string): number => {
      const values = packingRecords
        .map(r => {
          const mapped = mapPayloadToKpiFormat(r.kpi_payload, 'PACKING');
          return mapped[key];
        })
        .filter(v => !isNaN(v) && v !== 0);
      if (values.length === 0) return 0;
      return values.reduce((sum, v) => sum + v, 0) / values.length;
    };

    return {
      milling_kpis: {
        "Mill Throughput (%)": aggregateMilling("Mill Throughput (%)"),
        "Mill Time Efficiency (%)": aggregateMilling("Mill Time Efficiency (%)"),
        "Total Utilization (%)": aggregateMilling("Total Utilization (%)"),
        "Milling Gain": aggregateMilling("Milling Gain"),
        "Milling Screening (%)": aggregateMilling("Milling Screening (%)"),
        "Flour Extraction (%)": aggregateMilling("Flour Extraction (%)"),
        "Bran Extraction (%)": aggregateMilling("Bran Extraction (%)"),
        "Milling Loss (%)": aggregateMilling("Milling Loss (%)"),
        "Net Hours (hrs)": aggregateMilling("Net Hours (hrs)"),
        "Downtime (hrs)": aggregateMilling("Downtime (hrs)"),
        "Max Utilization of Milling Capacity (%)": aggregateMilling("Max Utilization of Milling Capacity (%)"),
        "Pre Cleaning Screening (%)": aggregateMilling("Pre Cleaning Screening (%)"),
        "1st Break Capacity per Hour (t/h)": aggregateMilling("1st Break Capacity per Hour (t/h)"),
      },
      packing_kpis: {
        "Packing Line Capacity (bags/hr)": aggregatePacking("Packing Line Capacity (bags/hr)"),
        "Daily Packing Output (bags)": aggregatePacking("Daily Packing Output (bags)"),
        "Net Hours (hrs)": aggregatePacking("Net Hours (hrs)"),
        "Downtime (hrs)": aggregatePacking("Downtime (hrs)"),
        "Machine Utilization (%)": aggregatePacking("Machine Utilization (%)"),
        "Packing Line Capacity (tons/hr)": aggregatePacking("Packing Line Capacity (tons/hr)"),
      },
      timestamp: new Date().toISOString(),
      data_source: 'historical',
    };
  };

  const fetchKpiData = async () => {
    try {
      setLoading(true);
      setError(null);

      // ===============================================================
      // DUAL MODE LOGIC:
      // - Demo Mode (Emulator): Use getKpis() for live emulator data
      // - Production Mode (SQL Server): Use getKpiTracking() for historical data
      // ===============================================================
      
      if (isDemoMode) {
        // ✅ DEMO MODE: Fetch live KPI data from emulator
        console.log('📊 [DEMO MODE] Fetching live KPI data from emulator...');
        
        try {
          const liveData = await kpiApi.getKpis();
          console.log('📊 [DEMO MODE] Live KPI data received:', liveData);
          setKpiData(liveData);
        } catch (err) {
          console.error('📊 [DEMO MODE] Error fetching live data:', err);
          // If live fetch fails, try to show a meaningful message
          setKpiData(null);
          throw new Error('Emulator data not available. Ensure the emulator is running.');
        }
      } else {
        // ✅ PRODUCTION MODE: Fetch historical data from SQL Server via kpi_send_tracking
        console.log('📊 [PRODUCTION MODE] Fetching historical KPI data from SQL Server...');
        
        let startDate: string;
        let endDate: string;
        let shiftsToUse: string[] = [];
        
        if (filters && (filters.mode === 'single' || filters.mode === 'range')) {
          // Use filter dates
          if (filters.mode === 'single' && filters.date) {
            startDate = filters.date.split(' ')[0];  // Extract YYYY-MM-DD
            endDate = startDate;
          } else if (filters.mode === 'range' && filters.startDate && filters.endDate) {
            startDate = filters.startDate.split(' ')[0];
            endDate = filters.endDate.split(' ')[0];
          } else {
            // Default to today
            const today = new Date().toISOString().split('T')[0];
            startDate = today;
            endDate = today;
          }
          shiftsToUse = filters.shifts || [];
        } else {
          // No filters - default to today's date
          const today = new Date().toISOString().split('T')[0];
          startDate = today;
          endDate = today;
        }
        
        console.log('📊 [PRODUCTION MODE] Fetching KPI tracking data:', { startDate, endDate, shifts: shiftsToUse });
        
        // Fetch KPI tracking data for both departments
        const [millingResponse, packingResponse] = await Promise.all([
          kpiApi.getKpiTracking({
            startDate,
            endDate,
            shifts: shiftsToUse,
            department: 'MILLING',
            limit: 1000,
            offset: 0
          }),
          kpiApi.getKpiTracking({
            startDate,
            endDate,
            shifts: shiftsToUse,
            department: 'PACKING',
            limit: 1000,
            offset: 0
          })
        ]);
        
        console.log('📊 [PRODUCTION MODE] KPI tracking responses:', { milling: millingResponse, packing: packingResponse });
        
        if (millingResponse.success && packingResponse.success) {
          // Combine records and aggregate
          const allRecords = [
            ...millingResponse.data.map(r => ({ ...r, department: 'MILLING' })),
            ...packingResponse.data.map(r => ({ ...r, department: 'PACKING' }))
          ];
          
          if (allRecords.length === 0) {
            console.log('📊 [PRODUCTION MODE] No KPI data found for the selected date/filters');
            setKpiData(null);
          } else {
            const aggregatedData = aggregateHistoricalKpis(allRecords);
            console.log('📊 [PRODUCTION MODE] Aggregated KPI data:', aggregatedData);
            setKpiData(aggregatedData);
          }
        } else {
          throw new Error('Failed to fetch KPI data from SQL Server');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch KPI data');
      setKpiData(null);
    } finally {
      setLoading(false);
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

      // Always fetch chart data from historical API
      try {
        let startDate: string;
        let endDate: string;
        let shiftsToUse: string[] = [];
        
        if (filters && (filters.mode === 'single' || filters.mode === 'range')) {
          if (filters.mode === 'single' && filters.date) {
            startDate = filters.date.split(' ')[0];
            endDate = startDate;
          } else if (filters.mode === 'range' && filters.startDate && filters.endDate) {
            startDate = filters.startDate.split(' ')[0];
            endDate = filters.endDate.split(' ')[0];
          } else {
            const today = new Date().toISOString().split('T')[0];
            startDate = today;
            endDate = today;
          }
          shiftsToUse = filters.shifts || [];
        } else {
          // No filters - default to today
          const today = new Date().toISOString().split('T')[0];
          startDate = today;
          endDate = today;
        }

        // Fetch packing data for charts using kpi-tracking API
        const packingResponse = await kpiApi.getKpiTracking({
          startDate,
          endDate,
          shifts: shiftsToUse,
          department: 'PACKING',
          limit: 1000,
          offset: 0
        });

        console.log('📊 Chart data response:', packingResponse);

        if (packingResponse.success && packingResponse.data.length > 0) {
          // Create a map of shift codes to end times
          const shiftTimeMap: Record<string, string> = {};
          packingShiftsData.forEach(shift => {
            shiftTimeMap[shift.shift_code] = shift.end_time.substring(0, 5);
          });

          // Map data to chart format
          const chartData: HistoricalChartData = {
            dailyOutputData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              output: parseFloat(record.kpi_payload.PACKING_BAG || '0'),
            })),
            packingLineCapacityData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              capacity: parseFloat(record.kpi_payload.PACKING_CAPACITY_BAG || '0'),
            })),
            packingCapacityTonsData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              capacity: parseFloat(record.kpi_payload.PACKING_CAPACITY_TON || '0'),
            })),
            netHoursData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              hours: parseFloat(record.kpi_payload.PACKING_HOURS || '0'),
            })),
            downtimeData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              downtime: parseFloat(record.kpi_payload.PACKING_TOTAL_DOWNTIME || '0'),
            })),
            machineUtilData: packingResponse.data.map(record => ({
              time: record.shift_code ? shiftTimeMap[record.shift_code] || record.shift_code : 'N/A',
              util: parseFloat(record.kpi_payload.PACKING_MACHINE_UTILIZ || '0'),
            })),
          };
          console.log('📊 Chart data:', chartData);
          setHistoricalChartData(chartData);
        } else {
          setHistoricalChartData(null);
        }
      } catch (apiErr) {
        console.log('Chart data API error:', apiErr);
        setHistoricalChartData(null);
      }

    } catch (err) {
      console.error('Failed to fetch shifts:', err);
      setHistoricalChartData(null);
    }
  };

  // Fetch system mode on mount
  useEffect(() => {
    const checkSystemMode = async () => {
      try {
        const modeInfo = await systemApi.getSystemMode();
        setIsDemoMode(modeInfo.demo_mode);
        console.log('📊 System mode:', modeInfo.demo_mode ? 'DEMO (Emulator)' : 'PRODUCTION (SQL Server)');
      } catch (error) {
        console.warn('Could not fetch system mode, defaulting to demo mode:', error);
        setIsDemoMode(true);
      }
    };
    checkSystemMode();
    
    // Poll system mode every 30 seconds to detect mode changes
    const interval = setInterval(checkSystemMode, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch KPI data on mount and when filters or mode changes
  useEffect(() => {
    fetchKpiData();
  }, [filters, isDemoMode]);

  // Fetch shifts and chart data on mount and when filters change
  useEffect(() => {
    fetchShiftsAndChartData();
  }, [filters]);

  if (loading) {
    return (
      <WaterSystemLayout title="SAP Production Intelligence" subtitle="Loading KPI data...">
        <div className="flex items-center justify-center h-screen">
          <div className="flex flex-col items-center gap-4">
            <div className={`w-12 h-12 border-4 border-t-transparent rounded-full animate-spin ${theme === 'light' ? 'border-blue-500' : 'border-cyan-500'
              }`} />
            <span className={theme === 'light' ? 'text-slate-700' : 'text-cyan-300'}>Loading Dashboard...</span>
          </div>
        </div>
      </WaterSystemLayout>
    );
  }

  if (error) {
    return (
      <WaterSystemLayout title="SAP Production Intelligence" subtitle="Error loading data">
        <div className="flex items-center justify-center h-screen">
          <div className={`p-8 rounded-xl border text-center max-w-md ${theme === 'light' ? 'bg-white border-red-200' : 'bg-slate-800 border-red-900/50'
            }`}>
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Zap className="w-8 h-8 text-red-500" />
            </div>
            <h3 className={`text-lg font-bold mb-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
              Connection Error
            </h3>
            <p className={`mb-6 ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              {error}
            </p>
            <button
              onClick={fetchKpiData}
              className={`px-6 py-2.5 rounded-lg font-medium transition-all ${theme === 'light'
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-200'
                : 'bg-cyan-500 text-white hover:bg-cyan-600 shadow-lg shadow-cyan-500/20'
                }`}
            >
              <RotateCcw className="w-4 h-4 inline-block mr-2" />
              Retry Connection
            </button>
          </div>
        </div>
      </WaterSystemLayout>
    );
  }

  return (
    <WaterSystemLayout
      title="PRODUCTION INSIGHTS"
      subtitle="REAL-TIME ANALYTICS DASHBOARD"
    >
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
          <div className="flex flex-col h-full p-2 gap-2">
            {/* Header Section */}
            <div className={`p-2 rounded-lg border backdrop-blur-md flex-shrink-0 ${theme === 'light'
              ? 'bg-white/80 border-slate-200 shadow-sm'
              : 'bg-slate-900/60 border-slate-700/50'
              }`}>
              <div className="flex flex-row items-center justify-between gap-2">
                {/* Title */}
                <div>
                  <h1 className={`text-xl font-black tracking-tight ${theme === 'light' ? 'text-slate-900' : 'text-white'
                    }`}>
                    PRODUCTION INSIGHTS
                  </h1>
                  <p className={`text-xs font-medium ${theme === 'light' ? 'text-slate-500' : 'text-cyan-400'
                    }`}>
                    REAL-TIME ANALYTICS DASHBOARD
                  </p>
                </div>

                {/* Time Controls */}
                <div className="flex items-center gap-2">
                  <TimeFilter
                    onApply={handleApplyFilters}
                    initialValues={filters || undefined}
                  />
                  
                  {/* Historical Mode Indicator */}
                  {isHistoricalMode && (
                    <div className={`flex items-center gap-2 px-2 py-1 rounded-md border ${theme === 'light'
                      ? 'bg-amber-50 border-amber-200 text-amber-800'
                      : 'bg-amber-900/20 border-amber-700/30 text-amber-300'
                      }`}>
                      <div className="flex items-center gap-1.5">
                        <Clock className={`w-3 h-3 ${theme === 'light' ? 'text-amber-600' : 'text-amber-400'}`} />
                        <span className="text-xs font-medium">Historical: {periodLabel}</span>
                      </div>
                      <button
                        onClick={resetToLive}
                        className={`text-xs px-2 py-0.5 rounded transition-colors ${theme === 'light'
                          ? 'hover:bg-amber-100 text-amber-700'
                          : 'hover:bg-amber-800/30 text-amber-400'
                          }`}
                      >
                        Reset
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Main 3-Column Layout - Fixed height */}
            <div className="grid grid-cols-12 gap-3 flex-1">
              {/* LEFT COLUMN - Milling Section */}
              <div className="col-span-3">
                <MillingSection 
                  theme={theme} 
                  kpiData={kpiData} 
                  scadaData={scadaData} 
                  shifts={millingShifts} 
                  isHistoricalMode={isHistoricalMode}
                  dateRange={filters ? { startDate: filters.startDate || filters.date, endDate: filters.endDate || filters.date } : undefined}
                />
              </div>

              {/* CENTER COLUMN - Charts Section */}
              <div className="col-span-6">
                <ChartsSection 
                  theme={theme} 
                  kpiData={kpiData} 
                  shifts={millingShifts} 
                  isHistoricalMode={isHistoricalMode}
                  dateRange={filters ? { startDate: filters.startDate || filters.date, endDate: filters.endDate || filters.date } : undefined}
                />
              </div>

              {/* RIGHT COLUMN - Packing Section */}
              <div className="col-span-3">
                <PackingSection 
                  theme={theme} 
                  kpiData={kpiData} 
                  historicalChartData={historicalChartData || undefined} 
                  shifts={packingShifts} 
                  isHistoricalMode={isHistoricalMode}
                  dateRange={filters ? { startDate: filters.startDate || filters.date, endDate: filters.endDate || filters.date } : undefined}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </WaterSystemLayout>
  );
};

export default SAPDashboard;
