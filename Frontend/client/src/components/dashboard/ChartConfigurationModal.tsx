import React, { useState } from 'react';
import { X, Save, BarChart3, PieChart, LineChart, TrendingUp, Gauge, Donut, Activity } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

// Chart type definitions with icons
const chartTypes = [
  { id: 'test', type: 'test', title: 'Test Chart', icon: Activity, description: 'Basic test chart for development' },
  { id: 'pie', type: 'pie', title: 'Production Distribution', icon: PieChart, description: 'Shows production data distribution' },
  { id: 'bar', type: 'bar', title: 'Line Performance', icon: BarChart3, description: 'Displays performance metrics in bars' },
  { id: 'line', type: 'line', title: 'Throughput vs Efficiency', icon: LineChart, description: 'Shows trends over time' },
  { id: 'trend', type: 'trend', title: 'Production Trend', icon: TrendingUp, description: 'Production trend analysis' },
  { id: 'gauge', type: 'gauge', title: 'System Metrics', icon: Gauge, description: 'Gauge-style metrics display' },
  { id: 'doughnut', type: 'doughnut', title: 'Machine Status', icon: Donut, description: 'Machine status overview' },
  { id: 'composed', type: 'composed', title: 'Production & Efficiency', icon: BarChart3, description: 'Combined chart types' }
];

// Data source options
const dataSources = [
  { id: 'milling_kpis', label: 'Milling KPIs', description: 'Milling operation key performance indicators' },
  { id: 'packing_kpis', label: 'Packing KPIs', description: 'Packing operation key performance indicators' },
  { id: 'real_time', label: 'Real-time Data', description: 'Live production data' },
  { id: 'historical', label: 'Historical Data', description: 'Past production records' },
  { id: 'custom', label: 'Custom Data', description: 'User-defined data source' }
];

// Time range options
const timeRanges = [
  { id: '1h', label: 'Last Hour', description: 'Data from the past hour' },
  { id: '6h', label: 'Last 6 Hours', description: 'Data from the past 6 hours' },
  { id: '24h', label: 'Last 24 Hours', description: 'Data from the past day' },
  { id: '7d', label: 'Last 7 Days', description: 'Data from the past week' },
  { id: '30d', label: 'Last 30 Days', description: 'Data from the past month' },
  { id: 'custom', label: 'Custom Range', description: 'User-defined time range' }
];

// Refresh interval options
const refreshIntervals = [
  { id: '30s', label: '30 Seconds', description: 'Update every 30 seconds' },
  { id: '1m', label: '1 Minute', description: 'Update every minute' },
  { id: '5m', label: '5 Minutes', description: 'Update every 5 minutes' },
  { id: '15m', label: '15 Minutes', description: 'Update every 15 minutes' },
  { id: '30m', label: '30 Minutes', description: 'Update every 30 minutes' },
  { id: 'manual', label: 'Manual', description: 'Update only when manually refreshed' }
];

interface ChartConfiguration {
  title: string;
  type: string;
  dataSource: string;
  timeRange: string;
  refreshInterval: string;
  showLegend: boolean;
  showGrid: boolean;
  showTooltip: boolean;
  colorScheme: string;
}

interface ChartConfigurationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ChartConfiguration) => void;
  operation: 'milling' | 'packing';
}

const ChartConfigurationModal: React.FC<ChartConfigurationModalProps> = ({
  isOpen,
  onClose,
  onSave,
  operation
}) => {
  const { theme } = useTheme();
  const [config, setConfig] = useState<ChartConfiguration>({
    title: '',
    type: 'pie',
    dataSource: operation === 'milling' ? 'milling_kpis' : 'packing_kpis',
    timeRange: '24h',
    refreshInterval: '5m',
    showLegend: true,
    showGrid: true,
    showTooltip: true,
    colorScheme: 'default'
  });

  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  const colorSchemes = [
    { id: 'default', label: 'Default', description: 'System default colors' },
    { id: 'blue', label: 'Blue Theme', description: 'Blue color scheme' },
    { id: 'green', label: 'Green Theme', description: 'Green color scheme' },
    { id: 'purple', label: 'Purple Theme', description: 'Purple color scheme' },
    { id: 'orange', label: 'Orange Theme', description: 'Orange color scheme' },
    { id: 'red', label: 'Red Theme', description: 'Red color scheme' }
  ];

  const handleInputChange = (field: keyof ChartConfiguration, value: string | boolean) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {};

    if (!config.title.trim()) {
      newErrors.title = 'Chart title is required';
    }

    if (!config.type) {
      newErrors.type = 'Chart type is required';
    }

    if (!config.dataSource) {
      newErrors.dataSource = 'Data source is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateForm()) {
      onSave(config);
      onClose();
    }
  };

  const handleClose = () => {
    setConfig({
      title: '',
      type: 'pie',
      dataSource: operation === 'milling' ? 'milling_kpis' : 'packing_kpis',
      timeRange: '24h',
      refreshInterval: '5m',
      showLegend: true,
      showGrid: true,
      showTooltip: true,
      colorScheme: 'default'
    });
    setErrors({});
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className={`relative w-full max-w-3xl mx-4 max-h-[80vh] overflow-y-auto rounded-xl border backdrop-blur-xl shadow-2xl ${
        theme === 'light' 
          ? 'bg-white/95 border-slate-300/50' 
          : 'bg-slate-900/95 border-slate-700/50'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between p-4 border-b ${
          theme === 'light' ? 'border-slate-200' : 'border-slate-700'
        }`}>
          <div>
            <h2 className={`text-xl font-bold ${
              theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
            }`}>
              Configure New Chart
            </h2>
            <p className={`text-sm mt-1 ${
              theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            }`}>
              Customize your chart settings and data source
            </p>
          </div>
          <button
            onClick={handleClose}
            className={`p-2 rounded-lg transition-colors ${
              theme === 'light' 
                ? 'hover:bg-slate-100 text-slate-500' 
                : 'hover:bg-slate-800 text-slate-400'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Chart Title - Full Width */}
          <div className="mb-4">
            <label className={`block text-sm font-medium mb-2 ${
              theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            }`}>
              Chart Title *
            </label>
            <input
              type="text"
              value={config.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
              placeholder="Enter chart title..."
              className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                theme === 'light'
                  ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                  : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
              } ${errors.title ? 'border-red-500' : ''} ${
                theme === 'light' ? 'text-slate-900' : 'text-white'
              }`}
            />
            {errors.title && (
              <p className="text-red-500 text-sm mt-1">{errors.title}</p>
            )}
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* Left Column */}
            <div className="space-y-4">
              {/* Chart Type */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Chart Type *
                </label>
                <select
                  value={config.type}
                  onChange={(e) => handleInputChange('type', e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                      : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
                  } ${errors.type ? 'border-red-500' : ''} ${
                    theme === 'light' ? 'text-slate-900' : 'text-white'
                  }`}
                >
                  {chartTypes.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.title} ({type.type})
                    </option>
                  ))}
                </select>
                {errors.type && (
                  <p className="text-red-500 text-sm mt-1">{errors.type}</p>
                )}
                {config.type && (
                  <p className={`text-xs mt-2 ${
                    theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {chartTypes.find(t => t.id === config.type)?.description}
                  </p>
                )}
              </div>

              {/* Data Source */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Data Source *
                </label>
                <select
                  value={config.dataSource}
                  onChange={(e) => handleInputChange('dataSource', e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                      : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
                  } ${errors.dataSource ? 'border-red-500' : ''} ${
                    theme === 'light' ? 'text-slate-900' : 'text-white'
                  }`}
                >
                  {dataSources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.label}
                    </option>
                  ))}
                </select>
                {errors.dataSource && (
                  <p className="text-red-500 text-sm mt-1">{errors.dataSource}</p>
                )}
                {config.dataSource && (
                  <p className={`text-xs mt-2 ${
                    theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {dataSources.find(s => s.id === config.dataSource)?.description}
                  </p>
                )}
              </div>

              {/* Time Range */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Time Range
                </label>
                <select
                  value={config.timeRange}
                  onChange={(e) => handleInputChange('timeRange', e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                      : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
                  } ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}
                >
                  {timeRanges.map((range) => (
                    <option key={range.id} value={range.id}>
                      {range.label}
                    </option>
                  ))}
                </select>
                <p className={`text-xs mt-2 ${
                  theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {timeRanges.find(r => r.id === config.timeRange)?.description}
                </p>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
              {/* Refresh Interval */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Refresh Interval
                </label>
                <select
                  value={config.refreshInterval}
                  onChange={(e) => handleInputChange('refreshInterval', e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                      : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
                  } ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}
                >
                  {refreshIntervals.map((interval) => (
                    <option key={interval.id} value={interval.id}>
                      {interval.label}
                    </option>
                  ))}
                </select>
                <p className={`text-xs mt-2 ${
                  theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {refreshIntervals.find(i => i.id === config.refreshInterval)?.description}
                </p>
              </div>

              {/* Color Scheme */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Color Scheme
                </label>
                <select
                  value={config.colorScheme}
                  onChange={(e) => handleInputChange('colorScheme', e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border transition-colors ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                      : 'bg-slate-800 border-slate-600 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200/20'
                  } ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}
                >
                  {colorSchemes.map((scheme) => (
                    <option key={scheme.id} value={scheme.id}>
                      {scheme.label}
                    </option>
                  ))}
                </select>
                <p className={`text-xs mt-2 ${
                  theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {colorSchemes.find(s => s.id === config.colorScheme)?.description}
                </p>
              </div>

              {/* Chart Options */}
              <div>
                <label className={`block text-sm font-medium mb-3 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Chart Options
                </label>
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.showLegend}
                      onChange={(e) => handleInputChange('showLegend', e.target.checked)}
                      className={`w-4 h-4 rounded border-2 transition-colors ${
                        theme === 'light'
                          ? 'border-slate-300 text-blue-600 focus:ring-blue-200'
                          : 'border-slate-600 text-cyan-600 focus:ring-cyan-200/20'
                      }`}
                    />
                    <span className={`ml-3 text-sm ${
                      theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                    }`}>
                      Show Legend
                    </span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.showGrid}
                      onChange={(e) => handleInputChange('showGrid', e.target.checked)}
                      className={`w-4 h-4 rounded border-2 transition-colors ${
                        theme === 'light'
                          ? 'border-slate-300 text-blue-600 focus:ring-blue-200'
                          : 'border-slate-600 text-cyan-600 focus:ring-cyan-200/20'
                      }`}
                    />
                    <span className={`ml-3 text-sm ${
                      theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                    }`}>
                      Show Grid
                    </span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.showTooltip}
                      onChange={(e) => handleInputChange('showTooltip', e.target.checked)}
                      className={`w-4 h-4 rounded border-2 transition-colors ${
                        theme === 'light'
                          ? 'border-slate-300 text-blue-600 focus:ring-blue-200'
                          : 'border-slate-600 text-cyan-600 focus:ring-cyan-200/20'
                      }`}
                    />
                    <span className={`ml-3 text-sm ${
                      theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                    }`}>
                      Show Tooltip
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className={`flex items-center justify-end gap-3 p-4 border-t ${
          theme === 'light' ? 'border-slate-200' : 'border-slate-700'
        }`}>
          <button
            onClick={handleClose}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              theme === 'light'
                ? 'text-slate-600 hover:bg-slate-100'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-medium !text-white transition-all duration-200 hover:scale-105 ${
              theme === 'light'
                ? 'bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/30'
                : 'bg-cyan-600 hover:bg-cyan-700 shadow-lg shadow-cyan-500/30'
            }`}
            style={{ color: 'white !important' }}
          >
            <Save className="w-4 h-4 !text-white" style={{ color: 'white !important' }} />
            Create Chart
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChartConfigurationModal;
