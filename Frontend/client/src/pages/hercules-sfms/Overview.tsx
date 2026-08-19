import { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { kpiApi, KpiData } from '../../lib/api';
import {
  Factory,
  Gauge,
  TrendingUp,
  Users,
  Cog,
  AlertTriangle,
  Activity,
  BarChart3,
  CheckCircle,
  Clock,
  Zap,
  Target,
  Settings,
  MonitorSpeaker,
  RefreshCw,
  AlertCircle
} from 'lucide-react';

export default function Overview() {
  const { theme } = useTheme();
  const [selectedFacility, setSelectedFacility] = useState<string | null>(null);
  const [animationPhase, setAnimationPhase] = useState(0);
  const [kpiData, setKpiData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Animation effect for circular progress indicators
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationPhase(prev => (prev + 1) % 100);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  // Fetch KPI data and set up polling
  const fetchKpiData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await kpiApi.getKpis();
      
      // Validate and sanitize the data before setting it
      const validatedData = {
        milling_kpis: {
          "Mill Throughput (%)": data.milling_kpis["Mill Throughput (%)"] || 0,
          "Mill Time Efficiency (%)": data.milling_kpis["Mill Time Efficiency (%)"] || 0,
          "Total Utilization (%)": data.milling_kpis["Total Utilization (%)"] || 0,
          "Milling Gain": data.milling_kpis["Milling Gain"] || 0,
          "Screening Ratios": data.milling_kpis["Screening Ratios"] || 0,
          "Water Consumption (m³)": data.milling_kpis["Water Consumption (m³)"] || 0,
          "Extraction Rates (%)": data.milling_kpis["Extraction Rates (%)"] || 0,
          "Milling Loss (%)": data.milling_kpis["Milling Loss (%)"] || 0,
          "Net Hours (hrs)": data.milling_kpis["Net Hours (hrs)"] || 0,
          "Downtime (hrs)": data.milling_kpis["Downtime (hrs)"] || 0,
        },
        packing_kpis: {
          "Packing Line Capacity (bags/hr)": data.packing_kpis["Packing Line Capacity (bags/hr)"] || 0,
          "Daily Packing Output (bags)": data.packing_kpis["Daily Packing Output (bags)"] || 0,
          "Net Hours (hrs)": data.packing_kpis["Net Hours (hrs)"] || 0,
          "Downtime (hrs)": data.packing_kpis["Downtime (hrs)"] || 0,
          "Machine Utilization (%)": data.packing_kpis["Machine Utilization (%)"] || 0,
        },
        timestamp: data.timestamp,
        data_source: data.data_source,
      };
      
      setKpiData(validatedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch KPI data');
      console.error('Error fetching KPI data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKpiData();
    
    // Set up polling every 60 seconds to get fresh data
    const interval = setInterval(fetchKpiData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Transform API data to match the expected format
  const transformKpiData = (data: KpiData) => {
    // Helper function to safely get values
    const safeValue = (value: any): number => {
      if (value === null || value === undefined || isNaN(value)) {
        return 0;
      }
      return parseFloat(value.toString());
    };

    return {
      systemHealth: {
        overall: 94.5,
        subsystems: [
          { name: 'PLC Network', value: 98.2, status: 'excellent' },
          { name: 'SCADA', value: 96.8, status: 'excellent' },
          { name: 'Database', value: 89.1, status: 'good' },
          { name: 'Network', value: 94.7, status: 'excellent' }
        ]
      },
      millingKPIs: [
        { label: 'Mill Throughput', value: safeValue(data.milling_kpis["Mill Throughput (%)"]), unit: '%', color: '#22c55e', target: 95 },
        { label: 'Mill Time Efficiency', value: safeValue(data.milling_kpis["Mill Time Efficiency (%)"]), unit: '%', color: '#3b82f6', target: 90 },
        { label: 'Total Utilization', value: safeValue(data.milling_kpis["Total Utilization (%)"]), unit: '%', color: '#f59e0b', target: 80 },
        { label: 'Milling Gain', value: safeValue(data.milling_kpis["Milling Gain"]), unit: '%', color: '#8b5cf6', target: 95 },
        { label: 'Screening Ratios', value: safeValue(data.milling_kpis["Screening Ratios"]), unit: '%', color: '#ef4444', target: 85 },
        { label: 'Water Consumption', value: safeValue(data.milling_kpis["Water Consumption (m³)"]), unit: 'm³', color: '#06b6d4', target: 75 },
        { label: 'Extraction Rates', value: safeValue(data.milling_kpis["Extraction Rates (%)"]), unit: '%', color: '#f97316', target: 90 },
        { label: 'Milling Loss', value: safeValue(data.milling_kpis["Milling Loss (%)"]), unit: '%', color: '#10b981', target: 94 },
        { label: 'Net Hours', value: safeValue(data.milling_kpis["Net Hours (hrs)"]), unit: 'hrs', color: '#ec4899', target: 92 },
        { label: 'Downtime', value: safeValue(data.milling_kpis["Downtime (hrs)"]), unit: 'hrs', color: '#84cc16', target: 95 }
      ],
      packingKPIs: [
        { label: 'Packing Line Capacity', value: safeValue(data.packing_kpis["Packing Line Capacity (bags/hr)"]), unit: 'bags/hr', color: '#22c55e', target: 1200 },
        { label: 'Daily Packing Output', value: safeValue(data.packing_kpis["Daily Packing Output (bags)"]), unit: 'bags', color: '#3b82f6', target: 900 },
        { label: 'Net Hours', value: safeValue(data.packing_kpis["Net Hours (hrs)"]), unit: 'hrs', color: '#f59e0b', target: 20 },
        { label: 'Downtime', value: safeValue(data.packing_kpis["Downtime (hrs)"]), unit: 'hrs', color: '#8b5cf6', target: 2 },
        { label: 'Machine Utilization', value: safeValue(data.packing_kpis["Machine Utilization (%)"]), unit: '%', color: '#ef4444', target: 90 }
      ],
      facilities: [
        { name: 'Milling Unit 1', status: 'active', efficiency: 94.2, location: { x: 45, y: 30 }, type: 'production' },
        { name: 'Milling Unit 2', status: 'active', efficiency: 91.8, location: { x: 35, y: 45 }, type: 'production' },
        { name: 'Packing Line A', status: 'active', efficiency: 88.4, location: { x: 60, y: 35 }, type: 'packaging' },
        { name: 'Packing Line B', status: 'maintenance', efficiency: 0, location: { x: 55, y: 55 }, type: 'packaging' },
        { name: 'Quality Control', status: 'active', efficiency: 96.1, location: { x: 70, y: 45 }, type: 'quality' },
        { name: 'Storage', status: 'active', efficiency: 89.3, location: { x: 25, y: 60 }, type: 'storage' }
      ],
      alerts: [
        { type: 'warning', message: 'Packing Line B scheduled maintenance', time: '2h ago' },
        { type: 'info', message: 'Quality check completed successfully', time: '45m ago' },
        { type: 'success', message: 'Daily production target achieved', time: '1h ago' }
      ],
      performance: {
        productivity: 2.4,
        efficiency: 94.2,
        quality: 96.8,
        utilization: 89.4
      }
    };
  };

  // Loading state
  if (loading) {
    return (
      <WaterSystemLayout 
        title="Factory Overview" 
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

  // Error state
  if (error) {
    return (
      <WaterSystemLayout 
        title="Factory Overview" 
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
              className={`px-4 py-2 rounded-md flex items-center gap-2 mx-auto ${
                theme === 'light'
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

  // No data state
  if (!kpiData) {
    return (
      <WaterSystemLayout 
        title="Factory Overview" 
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

  // Transform the data for display
  const factoryData = transformKpiData(kpiData);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return '#22c55e';
      case 'maintenance': return '#f59e0b';
      case 'offline': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const CircularProgress = ({ value, size = 120, strokeWidth = 8, color = '#22c55e', label = 'EFFICIENCY' }: {
    value: number;
    size?: number;
    strokeWidth?: number;
    color?: string;
    label?: string;
  }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const strokeDasharray = `${circumference} ${circumference}`;
    const strokeDashoffset = circumference - (value / 100) * circumference;

    return (
      <div className="relative group" style={{ width: size, height: size }}>
        {/* Pulsing background glow */}
        <div 
          className="absolute inset-0 rounded-full opacity-20 animate-pulse"
          style={{ 
            background: `radial-gradient(circle, ${color}40 0%, transparent 70%)`,
            transform: 'scale(1.2)'
          }}
        />
        
        <svg
          className="transform -rotate-90 transition-all duration-2000 group-hover:scale-105"
          width={size}
          height={size}
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
            strokeWidth={strokeWidth}
            fill="transparent"
            className="transition-all duration-500"
          />
          
          {/* Animated gradient definition */}
          <defs>
            <linearGradient id={`gradient-${color.replace('#', '')}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: color, stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.6 }} />
            </linearGradient>
          </defs>
          
          {/* Progress circle with gradient */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={`url(#gradient-${color.replace('#', '')})`}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-3000 ease-out"
            style={{
              filter: `drop-shadow(0 0 12px ${color}60)`,
              transformOrigin: 'center'
            }}
          />
          
          {/* Animated dots along the circle */}
          {value > 10 && (
            <circle
              cx={size / 2 + radius * Math.cos((value / 100) * 2 * Math.PI - Math.PI / 2)}
              cy={size / 2 + radius * Math.sin((value / 100) * 2 * Math.PI - Math.PI / 2)}
              r="3"
              fill={color}
              className="animate-pulse"
              style={{ filter: `drop-shadow(0 0 8px ${color})` }}
            />
          )}
        </svg>
        
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center transform transition-all duration-500 group-hover:scale-110">
            <div className={`text-2xl font-bold transition-all duration-500 ${theme === 'light' ? 'text-slate-800' : 'text-white'}`}>
              <span className="tabular-nums">{value.toFixed(1)}</span>
            </div>
            <div className={`text-xs font-medium tracking-wider ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              {label}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <WaterSystemLayout 
      title="Factory Overview" 
      subtitle="Real-Time Production Intelligence Dashboard"
    >
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.5);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
        }
        
        @keyframes slideInLeft {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes dataFlow {
          0% { opacity: 0; }
          50% { opacity: 1; }
          100% { opacity: 0; }
        }
      `}</style>
      
      {/* Auto-refresh indicator */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
              Auto-refresh every 60 seconds
            </span>
          </div>
        </div>
        <button
          onClick={fetchKpiData}
          className={`px-3 py-1 rounded-md flex items-center gap-2 text-xs ${
            theme === 'light'
              ? 'bg-blue-500 text-white hover:bg-blue-600'
              : 'bg-cyan-500 text-white hover:bg-cyan-600'
          }`}
        >
          <RefreshCw className="w-3 h-3" />
          Refresh Now
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        
        {/* Milling KPIs */}
        <div className={`p-6 rounded-2xl border backdrop-blur-xl transition-all duration-500 hover:scale-[1.01] group ${
          theme === 'light' 
            ? 'bg-white/80 border-slate-200 hover:bg-white/90 hover:shadow-xl' 
            : 'bg-slate-800/50 border-slate-700 hover:bg-slate-800/70 hover:shadow-[0_20px_50px_rgba(6,182,212,0.1)]'
        }`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="relative">
              <Gauge className="w-6 h-6 text-cyan-500 transition-transform duration-500 group-hover:rotate-12" />
              <div className="absolute inset-0 bg-cyan-500/20 rounded-full animate-pulse" />
            </div>
            <h3 className={`font-bold text-lg ${theme === 'light' ? 'text-slate-800' : 'text-cyan-400'}`}>
              Milling KPIs
            </h3>
          </div>
          
          {/* KPI Grid - 5 columns, 2 rows */}
          <div className="grid grid-cols-5 gap-4">
            {factoryData.millingKPIs.map((metric, index) => (
              <div 
                key={index}
                className={`p-3 rounded-xl border backdrop-blur-md transition-all duration-300 hover:scale-105 cursor-pointer group/kpi ${
                  theme === 'light' 
                    ? 'bg-white/60 border-slate-200/50 hover:bg-white/80' 
                    : 'bg-slate-700/30 border-slate-600/30 hover:bg-slate-700/50'
                }`}
                style={{ 
                  animationDelay: `${index * 0.05}s`,
                  animation: 'fadeInUp 0.6s ease-out forwards'
                }}
              >
                <div className="text-center">
                  {/* KPI Label - Fixed height container */}
                  <div className={`text-xs font-bold mb-2 text-center leading-tight h-8 flex items-center justify-center ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
                    <span className="text-center">
                      {metric.label.toUpperCase()}
                    </span>
                  </div>
                  
                  {/* Circular Progress - Smaller with value inside */}
                  <div className="relative mb-3 flex justify-center">
                    <div className="relative" style={{ width: 50, height: 50 }}>
                      <svg
                        className="transform -rotate-90 transition-all duration-2000"
                        width={50}
                        height={50}
                      >
                        {/* Background circle */}
                        <circle
                          cx={25}
                          cy={25}
                          r={21}
                          stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                          strokeWidth={4}
                          fill="transparent"
                        />
                        
                        {/* Progress circle */}
                        <circle
                          cx={25}
                          cy={25}
                          r={21}
                          stroke={metric.color}
                          strokeWidth={4}
                          fill="transparent"
                          strokeDasharray={`${21 * 2 * Math.PI} ${21 * 2 * Math.PI}`}
                          strokeDashoffset={21 * 2 * Math.PI - (metric.value / 100) * 21 * 2 * Math.PI}
                          strokeLinecap="round"
                          className="transition-all duration-2000 ease-out"
                          style={{
                            filter: `drop-shadow(0 0 6px ${metric.color}60)`
                          }}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className={`text-xs font-bold tabular-nums ${theme === 'light' ? 'text-slate-800' : 'text-white'}`}>
                          {metric.value}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Value below circle - only unit, no percentage */}
                  <div className={`text-sm font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                    {metric.unit}
                  </div>
                  
                  {/* Target bar - simplified */}
                  <div className={`w-full h-0.5 rounded-full mt-2 overflow-hidden ${
                    theme === 'light' ? 'bg-slate-200' : 'bg-slate-600'
                  }`}>
                    <div 
                      className="h-full rounded-full transition-all duration-1000 ease-out"
                      style={{ 
                        width: `${Math.min((metric.value / metric.target) * 100, 100)}%`,
                        background: metric.color,
                        boxShadow: `0 0 4px ${metric.color}60`
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Packing KPIs */}
        <div className={`p-6 rounded-2xl border backdrop-blur-xl transition-all duration-500 hover:scale-[1.01] group ${
          theme === 'light' 
            ? 'bg-white/80 border-slate-200 hover:bg-white/90 hover:shadow-xl' 
            : 'bg-slate-800/50 border-slate-700 hover:bg-slate-800/70 hover:shadow-[0_20px_50px_rgba(6,182,212,0.1)]'
        }`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="relative">
              <Factory className="w-6 h-6 text-orange-500 transition-transform duration-500 group-hover:rotate-12" />
              <div className="absolute inset-0 bg-orange-500/20 rounded-full animate-pulse" />
            </div>
            <h3 className={`font-bold text-lg ${theme === 'light' ? 'text-slate-800' : 'text-orange-400'}`}>
              Packing KPIs
            </h3>
          </div>
          
          {/* KPI Grid - 5 columns, 1 row */}
          <div className="grid grid-cols-5 gap-4">
            {factoryData.packingKPIs.map((metric, index) => (
              <div 
                key={index}
                className={`p-3 rounded-xl border backdrop-blur-md transition-all duration-300 hover:scale-105 cursor-pointer group/kpi ${
                  theme === 'light' 
                    ? 'bg-white/60 border-slate-200/50 hover:bg-white/80' 
                    : 'bg-slate-700/30 border-slate-600/30 hover:bg-slate-700/50'
                }`}
                style={{ 
                  animationDelay: `${index * 0.05}s`,
                  animation: 'fadeInUp 0.6s ease-out forwards'
                }}
              >
                <div className="text-center">
                  {/* KPI Label - Fixed height container */}
                  <div className={`text-xs font-bold mb-2 text-center leading-tight h-8 flex items-center justify-center ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
                    <span className="text-center">
                      {metric.label.toUpperCase()}
                    </span>
                  </div>
                  
                  {/* Circular Progress - with value inside */}
                  <div className="relative mb-3 flex justify-center">
                    <div className="relative" style={{ width: 50, height: 50 }}>
                      <svg
                        className="transform -rotate-90 transition-all duration-2000"
                        width={50}
                        height={50}
                      >
                        {/* Background circle */}
                        <circle
                          cx={25}
                          cy={25}
                          r={20}
                          stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
                          strokeWidth={4}
                          fill="transparent"
                        />
                        
                        {/* Progress circle */}
                        <circle
                          cx={25}
                          cy={25}
                          r={20}
                          stroke={metric.color}
                          strokeWidth={4}
                          fill="transparent"
                          strokeDasharray={`${20 * 2 * Math.PI} ${20 * 2 * Math.PI}`}
                          strokeDashoffset={20 * 2 * Math.PI - (Math.min(metric.value / metric.target, 1)) * 20 * 2 * Math.PI}
                          strokeLinecap="round"
                          className="transition-all duration-2000 ease-out"
                          style={{
                            filter: `drop-shadow(0 0 6px ${metric.color}60)`
                          }}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className={`text-xs font-bold tabular-nums ${theme === 'light' ? 'text-slate-800' : 'text-white'}`}>
                          {metric.value % 1 === 0 ? metric.value.toFixed(0) : metric.value.toFixed(1)}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Value below circle - only unit, no percentage */}
                  <div className={`text-sm font-medium ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                    {metric.unit}
                  </div>
                  
                  {/* Target bar - simplified */}
                  <div className={`w-full h-0.5 rounded-full mt-2 overflow-hidden ${
                    theme === 'light' ? 'bg-slate-200' : 'bg-slate-600'
                  }`}>
                    <div 
                      className="h-full rounded-full transition-all duration-1000 ease-out"
                      style={{ 
                        width: `${Math.min((metric.value / metric.target) * 100, 100)}%`,
                        background: metric.color,
                        boxShadow: `0 0 4px ${metric.color}60`
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </WaterSystemLayout>
  );
}