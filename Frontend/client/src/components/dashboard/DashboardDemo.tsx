import React, { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import CustomizableDashboard from './CustomizableDashboard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

/**
 * Dashboard Demo Component
 * 
 * A standalone demo component showcasing the customizable dashboard functionality.
 * This can be used for testing, demonstrations, or as a standalone dashboard page.
 */
const DashboardDemo: React.FC = () => {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState('milling');

  // Mock KPI data for demonstration
  const mockKpiData = {
    milling_kpis: {
      "Mill Throughput (%)": 85.5,
      "Mill Time Efficiency (%)": 92.3,
      "Total Utilization (%)": 78.9,
      "Milling Gain": 95.2,
      "Screening Ratios": 88.7,
      "Water Consumption (m³)": 125.4,
      "Extraction Rates (%)": 91.8,
      "Milling Loss (%)": 2.1,
      "Net Hours (hrs)": 18.5,
      "Downtime (hrs)": 1.5
    },
    packing_kpis: {
      "Packing Line Capacity (bags/hr)": 1250,
      "Daily Packing Output (bags)": 950,
      "Net Hours (hrs)": 16.2,
      "Downtime (hrs)": 0.8,
      "Machine Utilization (%)": 89.3
    },
    timestamp: new Date().toISOString(),
    data_source: 'demo'
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className={`text-4xl font-bold ${
            theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
          }`}>
            Hercules SFMS Dashboard Demo
          </h1>
          <p className={`text-lg ${
            theme === 'light' ? 'text-slate-600' : 'text-slate-400'
          }`}>
            Interactive customizable dashboard with drag-and-drop functionality
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className={`${
            theme === 'light' 
              ? 'bg-white/80 border-slate-300' 
              : 'bg-slate-800/50 border-slate-700'
          }`}>
            <CardHeader>
              <CardTitle className={`${
                theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
              }`}>
                🎨 Customizable Layout
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className={`${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                Drag and drop charts to create your perfect dashboard layout. 
                Resize and reposition elements to match your workflow.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className={`${
            theme === 'light' 
              ? 'bg-white/80 border-slate-300' 
              : 'bg-slate-800/50 border-slate-700'
          }`}>
            <CardHeader>
              <CardTitle className={`${
                theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
              }`}>
                💾 Persistent Storage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className={`${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                Your dashboard layout is automatically saved and restored. 
                Switch between operations with separate layouts for each.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className={`${
            theme === 'light' 
              ? 'bg-white/80 border-slate-300' 
              : 'bg-slate-800/50 border-slate-700'
          }`}>
            <CardHeader>
              <CardTitle className={`${
                theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
              }`}>
                🌓 Theme Support
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className={`${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                Full dark and light mode support with smooth transitions. 
                All charts and components adapt to your preferred theme.
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        {/* Dashboard Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className={`grid w-full grid-cols-2 ${
            theme === 'light' 
              ? 'bg-slate-100' 
              : 'bg-slate-800'
          }`}>
            <TabsTrigger 
              value="milling" 
              className={`${
                theme === 'light' 
                  ? 'data-[state=active]:bg-white data-[state=active]:text-slate-900' 
                  : 'data-[state=active]:bg-slate-700 data-[state=active]:text-cyan-400'
              }`}
            >
              Milling Dashboard
            </TabsTrigger>
            <TabsTrigger 
              value="packing"
              className={`${
                theme === 'light' 
                  ? 'data-[state=active]:bg-white data-[state=active]:text-slate-900' 
                  : 'data-[state=active]:bg-slate-700 data-[state=active]:text-cyan-400'
              }`}
            >
              Packing Dashboard
            </TabsTrigger>
          </TabsList>

          <TabsContent value="milling" className="mt-6">
            <CustomizableDashboard 
              operation="milling" 
              kpiData={mockKpiData} 
            />
          </TabsContent>

          <TabsContent value="packing" className="mt-6">
            <CustomizableDashboard 
              operation="packing" 
              kpiData={mockKpiData} 
            />
          </TabsContent>
        </Tabs>

        {/* Instructions */}
        <Card className={`${
          theme === 'light' 
            ? 'bg-blue-50 border-blue-200' 
            : 'bg-blue-900/20 border-blue-700'
        }`}>
          <CardHeader>
            <CardTitle className={`${
              theme === 'light' ? 'text-blue-800' : 'text-blue-400'
            }`}>
              🚀 How to Use
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`space-y-2 text-sm ${
              theme === 'light' ? 'text-blue-700' : 'text-blue-300'
            }`}>
              <p>• <strong>Add Charts:</strong> Click the "Add Chart" button to select from available chart types</p>
              <p>• <strong>Drag & Drop:</strong> Use the grip handle (⋮⋮) to drag charts to new positions</p>
              <p>• <strong>Resize:</strong> Drag the bottom-right corner of any chart to resize it</p>
              <p>• <strong>Remove:</strong> Click the X button in the top-right corner of any chart to remove it</p>
              <p>• <strong>Reset:</strong> Use the "Reset" button to restore the default layout</p>
              <p>• <strong>Persistence:</strong> Your layout is automatically saved and will be restored when you return</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardDemo;
