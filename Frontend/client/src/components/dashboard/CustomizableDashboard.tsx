import React, { useState, useEffect, useCallback } from 'react';
import { Responsive, WidthProvider, Layout } from 'react-grid-layout';
import { Plus, Settings, RotateCcw } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import ChartCard from './ChartCard';
import ChartConfigurationModal from './ChartConfigurationModal';

/**
 * CustomizableDashboard Component
 * 
 * Features:
 * - Popup form for adding charts with configuration options
 * - Chart configuration includes: title, type, data source, time range, refresh interval, color scheme
 * - All configuration data is stored in localStorage for persistence
 * - Drag and drop grid layout for chart positioning
 * - Chart configuration data is available for future enhancements
 */
import {
  PieChartExample,
  BarChartExample,
  LineChartExample,
  TrendChartExample,
  GaugeChartExample,
  DoughnutChartExample,
  ComposedChartExample
} from './charts/ExampleCharts';
import TestChart from './TestChart';

// Import react-grid-layout CSS
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

// Create the responsive grid layout component
const ResponsiveGridLayout = WidthProvider(Responsive);


// Chart type definitions
interface ChartConfig {
  id: string;
  type: string;
  title: string;
  component: React.ComponentType;
  dataSource?: string;
  timeRange?: string;
  refreshInterval?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  colorScheme?: string;
}

// Chart type for localStorage (without component reference)
interface SavedChartConfig {
  id: string;
  type: string;
  title: string;
  dataSource?: string;
  timeRange?: string;
  refreshInterval?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  colorScheme?: string;
}

// Available chart types
const chartTypes: ChartConfig[] = [
  { id: 'test', type: 'test', title: 'Test Chart', component: TestChart },
  { id: 'pie', type: 'pie', title: 'Production Distribution', component: PieChartExample },
  { id: 'bar', type: 'bar', title: 'Line Performance', component: BarChartExample },
  { id: 'line', type: 'line', title: 'Throughput vs Efficiency', component: LineChartExample },
  { id: 'trend', type: 'trend', title: 'Production Trend', component: TrendChartExample },
  { id: 'gauge', type: 'gauge', title: 'System Metrics', component: GaugeChartExample },
  { id: 'doughnut', type: 'doughnut', title: 'Machine Status', component: DoughnutChartExample },
  { id: 'composed', type: 'composed', title: 'Production & Efficiency', component: ComposedChartExample }
];

// Helper function to reconstruct chart config from saved data
const reconstructChartConfig = (savedChart: SavedChartConfig): ChartConfig | null => {
  const chartType = chartTypes.find(ct => ct.type === savedChart.type);
  if (!chartType) {
    console.error(`Chart type not found: ${savedChart.type}`);
    return null;
  }
  
  return {
    id: savedChart.id,
    type: savedChart.type,
    title: savedChart.title,
    component: chartType.component,
    dataSource: savedChart.dataSource,
    timeRange: savedChart.timeRange,
    refreshInterval: savedChart.refreshInterval,
    showLegend: savedChart.showLegend,
    showGrid: savedChart.showGrid,
    showTooltip: savedChart.showTooltip,
    colorScheme: savedChart.colorScheme
  };
};


interface CustomizableDashboardProps {
  operation: 'milling' | 'packing';
  kpiData?: any;
  isFullScreen?: boolean;
}

const CustomizableDashboard: React.FC<CustomizableDashboardProps> = ({ 
  operation, 
  kpiData,
  isFullScreen = false
}) => {
  const { theme } = useTheme();
  const [layouts, setLayouts] = useState<{ [key: string]: Layout[] }>({});
  const [charts, setCharts] = useState<ChartConfig[]>([]);
  const [showAddChartModal, setShowAddChartModal] = useState(false);

  // Load saved layout and charts from localStorage
  useEffect(() => {
    const savedLayouts = localStorage.getItem(`dashboard-layout-${operation}`);
    const savedCharts = localStorage.getItem(`dashboard-charts-${operation}`);
    
    console.log(`Loading dashboard for ${operation}:`, { savedLayouts, savedCharts });
    
    if (savedLayouts) {
      try {
        setLayouts(JSON.parse(savedLayouts));
      } catch (error) {
        console.error('Error loading saved layout:', error);
      }
    }
    
    if (savedCharts) {
      try {
        const parsedCharts: SavedChartConfig[] = JSON.parse(savedCharts);
        console.log('Parsed charts from localStorage:', parsedCharts);
        const reconstructedCharts = parsedCharts
          .map(reconstructChartConfig)
          .filter((chart): chart is ChartConfig => chart !== null);
        console.log('Reconstructed charts:', reconstructedCharts);
        setCharts(reconstructedCharts);
      } catch (error) {
        console.error('Error loading saved charts:', error);
        // Fallback to default charts if loading fails
        const defaultCharts = operation === 'milling' 
          ? [chartTypes[0], chartTypes[2], chartTypes[4]] // Pie, Line, Gauge
          : [chartTypes[1], chartTypes[5], chartTypes[6]]; // Bar, Doughnut, Composed
        setCharts(defaultCharts);
      }
    } else {
      // Default charts for first time
      const defaultCharts = operation === 'milling' 
        ? [chartTypes[0], chartTypes[2], chartTypes[4]] // Pie, Line, Gauge
        : [chartTypes[1], chartTypes[5], chartTypes[6]]; // Bar, Doughnut, Composed
      setCharts(defaultCharts);
    }
  }, [operation]);

  // Save layout to localStorage
  const saveLayout = useCallback((newLayouts: { [key: string]: Layout[] }) => {
    setLayouts(newLayouts);
    localStorage.setItem(`dashboard-layout-${operation}`, JSON.stringify(newLayouts));
  }, [operation]);

  // Save charts to localStorage
  const saveCharts = useCallback((newCharts: ChartConfig[]) => {
    setCharts(newCharts);
    // Save only serializable data (without component references)
    const serializableCharts: SavedChartConfig[] = newCharts.map(chart => ({
      id: chart.id,
      type: chart.type,
      title: chart.title,
      dataSource: chart.dataSource,
      timeRange: chart.timeRange,
      refreshInterval: chart.refreshInterval,
      showLegend: chart.showLegend,
      showGrid: chart.showGrid,
      showTooltip: chart.showTooltip,
      colorScheme: chart.colorScheme
    }));
    console.log(`Saving charts for ${operation}:`, serializableCharts);
    localStorage.setItem(`dashboard-charts-${operation}`, JSON.stringify(serializableCharts));
  }, [operation]);

  // Handle layout change
  const handleLayoutChange = useCallback((layout: Layout[], allLayouts: { [key: string]: Layout[] }) => {
    saveLayout(allLayouts);
  }, [saveLayout]);

  // Add new chart from modal configuration
  const addChartFromConfig = (config: any) => {
    const chartType = chartTypes.find(ct => ct.type === config.type);
    if (!chartType) {
      console.error(`Chart type not found: ${config.type}`);
      return;
    }

    const newChart: ChartConfig = {
      id: `${config.type}-${Date.now()}`,
      type: config.type,
      title: config.title,
      component: chartType.component,
      dataSource: config.dataSource,
      timeRange: config.timeRange,
      refreshInterval: config.refreshInterval,
      showLegend: config.showLegend,
      showGrid: config.showGrid,
      showTooltip: config.showTooltip,
      colorScheme: config.colorScheme
    };

    const newCharts = [...charts, newChart];
    saveCharts(newCharts);
    setShowAddChartModal(false);
    
    // Auto-position the new chart
    const newLayouts = { ...layouts };
    const newLayout = getDefaultLayout(newChart.id, charts.length);
    
    // Add layout for all breakpoints
    Object.keys(newLayouts).forEach(breakpoint => {
      if (!newLayouts[breakpoint]) {
        newLayouts[breakpoint] = [];
      }
      newLayouts[breakpoint].push(newLayout);
    });
    
    // If no layouts exist, create default ones
    if (Object.keys(newLayouts).length === 0) {
      newLayouts.lg = [newLayout];
      newLayouts.md = [newLayout];
      newLayouts.sm = [newLayout];
      newLayouts.xs = [newLayout];
      newLayouts.xxs = [newLayout];
    }
    
    saveLayout(newLayouts);
  };

  // Remove chart
  const removeChart = (chartId: string) => {
    const newCharts = charts.filter(chart => chart.id !== chartId);
    saveCharts(newCharts);
    
    // Remove from layout as well
    const newLayouts = { ...layouts };
    Object.keys(newLayouts).forEach(breakpoint => {
      newLayouts[breakpoint] = newLayouts[breakpoint].filter(item => item.i !== chartId);
    });
    saveLayout(newLayouts);
  };

  // Reset dashboard
  const resetDashboard = () => {
    const defaultCharts = operation === 'milling' 
      ? [chartTypes[0], chartTypes[2], chartTypes[4]]
      : [chartTypes[1], chartTypes[5], chartTypes[6]];
    
    setCharts(defaultCharts);
    saveCharts(defaultCharts);
    
    // Clear layout
    setLayouts({});
    localStorage.removeItem(`dashboard-layout-${operation}`);
  };

  // Generate default layout for new charts
  const getDefaultLayout = (chartId: string, index: number): Layout => {
    const cols = 12;
    // Adjust chart dimensions based on full-screen mode
    const chartWidth = isFullScreen ? 6 : 8; // Smaller width in full-screen for more charts per row
    const chartHeight = isFullScreen ? 6 : 5; // Taller charts in full-screen
    const chartsPerRow = isFullScreen ? 2 : 1.5; // More charts per row in full-screen
    const x = (index % chartsPerRow) * chartWidth;
    const y = Math.floor(index / chartsPerRow) * chartHeight;
    
    return {
      i: chartId,
      x: x,
      y: y,
      w: chartWidth,
      h: chartHeight,
      minW: 2, // Allow smaller minimum width for flexibility
      minH: 2, // Allow smaller minimum height for flexibility
      maxW: 12, // Allow full width
      maxH: isFullScreen ? 12 : 10   // Allow taller charts in full-screen
    };
  };

  // Get current layout for all breakpoints
  const getCurrentLayouts = (): { [key: string]: Layout[] } => {
    const currentLayouts = { ...layouts };
    
    // Ensure all charts have layouts
    charts.forEach((chart, index) => {
      Object.keys(currentLayouts).forEach(breakpoint => {
        if (!currentLayouts[breakpoint].find(item => item.i === chart.id)) {
          currentLayouts[breakpoint].push(getDefaultLayout(chart.id, index));
        }
      });
    });
    
    return currentLayouts;
  };

  return (
    <div className="space-y-4">
      {/* Dashboard Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className={`text-lg font-semibold ${
            theme === 'light' ? 'text-slate-700' : 'text-cyan-400'
          }`}>
            Customizable {operation.charAt(0).toUpperCase() + operation.slice(1)} Dashboard
          </h2>
          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
            theme === 'light' 
              ? 'bg-green-100 text-green-800' 
              : 'bg-green-900/30 text-green-400'
          }`}>
            {charts.length} charts
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddChartModal(true)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105 !text-white ${
              theme === 'light'
                ? 'bg-blue-500 hover:bg-blue-600'
                : 'bg-cyan-500 hover:bg-cyan-600'
            }`}
            style={{ color: 'white !important' }}
          >
            <Plus className="w-4 h-4 !text-white" style={{ color: 'white !important' }} />
            Add Chart
          </button>
          
          <button
            onClick={resetDashboard}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105 !text-white ${
              theme === 'light'
                ? 'bg-slate-500 hover:bg-slate-600'
                : 'bg-slate-600 hover:bg-slate-700'
            }`}
            style={{ color: 'white !important' }}
            title="Reset to default layout"
          >
            <RotateCcw className="w-4 h-4 !text-white" style={{ color: 'white !important' }} />
            Reset
          </button>
        </div>
      </div>

      {/* Chart Configuration Modal */}
      <ChartConfigurationModal
        isOpen={showAddChartModal}
        onClose={() => setShowAddChartModal(false)}
        onSave={addChartFromConfig}
        operation={operation}
      />

      {/* Dashboard Grid */}
      {charts.length > 0 ? (
        <div className={`${isFullScreen ? 'min-h-[calc(100vh-200px)]' : 'min-h-[400px]'}`}>
          {ResponsiveGridLayout ? (
            <ResponsiveGridLayout
              className="layout"
              layouts={getCurrentLayouts()}
              onLayoutChange={handleLayoutChange}
              breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
              cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
              rowHeight={isFullScreen ? 80 : 100}
              isDraggable={true}
              isResizable={true}
              margin={isFullScreen ? [15, 15] : [20, 20]}
              containerPadding={isFullScreen ? [5, 5] : [10, 10]}
              useCSSTransforms={true}
              draggableHandle=".drag-handle"
              compactType="vertical"
              preventCollision={false}
            >
              {charts.map((chart) => {
                const ChartComponent = chart.component;
                console.log(`Rendering chart ${chart.id}:`, { 
                  chart, 
                  ChartComponent, 
                  isUndefined: !ChartComponent 
                });
                
                // Fallback component if ChartComponent is undefined
                if (!ChartComponent) {
                  console.error(`Chart component is undefined for chart: ${chart.id}`);
                  return (
                    <div key={chart.id} className="h-full">
                      <ChartCard
                        id={chart.id}
                        title={chart.title}
                        onRemove={removeChart}
                        className="h-full"
                      >
                        <div className="flex items-center justify-center h-full text-red-500">
                          Chart component not found: {chart.type}
                        </div>
                      </ChartCard>
                    </div>
                  );
                }
                
                return (
                  <div key={chart.id} className="h-full">
                    <ChartCard
                      id={chart.id}
                      title={chart.title}
                      onRemove={removeChart}
                      className="h-full"
                    >
                      <ChartComponent />
                    </ChartCard>
                  </div>
                );
              })}
            </ResponsiveGridLayout>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {charts.map((chart) => {
                const ChartComponent = chart.component;
                console.log(`Rendering chart (fallback) ${chart.id}:`, { 
                  chart, 
                  ChartComponent, 
                  isUndefined: !ChartComponent 
                });
                
                // Fallback component if ChartComponent is undefined
                if (!ChartComponent) {
                  console.error(`Chart component is undefined for chart: ${chart.id}`);
                  return (
                    <div key={chart.id} className="h-64">
                      <ChartCard
                        id={chart.id}
                        title={chart.title}
                        onRemove={removeChart}
                        className="h-full"
                      >
                        <div className="flex items-center justify-center h-full text-red-500">
                          Chart component not found: {chart.type}
                        </div>
                      </ChartCard>
                    </div>
                  );
                }
                
                return (
                  <div key={chart.id} className="h-64">
                    <ChartCard
                      id={chart.id}
                      title={chart.title}
                      onRemove={removeChart}
                      className="h-full"
                    >
                      <ChartComponent />
                    </ChartCard>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className={`flex items-center justify-center h-64 rounded-xl border-2 border-dashed ${
          theme === 'light' 
            ? 'border-slate-300 bg-slate-50/50' 
            : 'border-slate-600 bg-slate-800/20'
        }`}>
          <div className="text-center">
            <Settings className={`w-12 h-12 mx-auto mb-4 ${
              theme === 'light' ? 'text-slate-400' : 'text-slate-500'
            }`} />
            <p className={`text-lg font-medium ${
              theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            }`}>
              No charts added yet
            </p>
            <p className={`text-sm mt-2 ${
              theme === 'light' ? 'text-slate-500' : 'text-slate-500'
            }`}>
              Click "Add Chart" to start building your dashboard
            </p>
          </div>
        </div>
      )}

      {/* CSS for react-grid-layout */}
      <style>{`
        .react-grid-layout {
          position: relative;
        }
        .react-grid-item {
          transition: all 200ms ease;
          transition-property: left, top;
        }
        .react-grid-item.cssTransforms {
          transition-property: transform;
        }
        .react-grid-item.react-draggable-dragging {
          transition: none;
          z-index: 3;
          transform: rotate(5deg);
        }
        .react-grid-item > .react-resizable-handle {
          position: absolute;
          width: 20px;
          height: 20px;
          bottom: 0;
          right: 0;
          background: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNiIgaGVpZ2h0PSI2IiB2aWV3Qm94PSIwIDAgNiA2IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8ZG90cyBmaWxsPSIjOTk5IiBkPSJtNiAwaC02djZoNnoiLz4KPC9zdmc+');
          background-position: bottom right;
          padding: 0 3px 3px 0;
          background-repeat: no-repeat;
          background-origin: content-box;
          box-sizing: border-box;
          cursor: se-resize;
        }
        .react-grid-item.react-grid-placeholder {
          background: ${theme === 'light' ? '#3b82f6' : '#00ffff'};
          opacity: 0.3;
          transition-duration: 100ms;
          z-index: 2;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          -o-user-select: none;
          user-select: none;
          border: 2px dashed ${theme === 'light' ? '#1d4ed8' : '#00ffff'};
          border-radius: 12px;
        }
        .react-grid-item > .react-resizable-handle::after {
          content: '';
          position: absolute;
          right: 3px;
          bottom: 3px;
          width: 5px;
          height: 5px;
          border-right: 2px solid ${theme === 'light' ? '#64748b' : '#94a3b8'};
          border-bottom: 2px solid ${theme === 'light' ? '#64748b' : '#94a3b8'};
        }
        .drag-handle {
          cursor: grab !important;
        }
        .drag-handle:active {
          cursor: grabbing !important;
        }
        .react-grid-item:hover .drag-handle {
          opacity: 1;
        }
        .react-grid-item .drag-handle {
          opacity: 0.7;
          transition: opacity 0.2s ease;
        }
      `}</style>
    </div>
  );
};

export default CustomizableDashboard;
