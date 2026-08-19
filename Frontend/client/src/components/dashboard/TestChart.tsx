import React from 'react';
import { PieChartExample } from './charts/ExampleCharts';
import { useTheme } from '../../contexts/ThemeContext';

const TestChart: React.FC = () => {
  const { theme } = useTheme();
  console.log('TestChart rendering, PieChartExample:', PieChartExample);
  
  return (
    <div className={`h-full w-full p-4 rounded-lg border-2 ${
      theme === 'light' 
        ? 'bg-gradient-to-br from-blue-50 to-cyan-50 border-blue-300' 
        : 'bg-gradient-to-br from-slate-800 to-slate-900 border-slate-600'
    }`}>
      <h3 className={`text-lg font-bold mb-4 ${
        theme === 'light' ? 'text-blue-800' : 'text-cyan-300'
      }`}>
        Test Chart - Milling Gain
      </h3>
      <div className="h-[calc(100%-3rem)]">
        {PieChartExample ? (
          <PieChartExample />
        ) : (
          <div className={`flex items-center justify-center h-full ${
            theme === 'light' ? 'text-red-600' : 'text-red-400'
          }`}>
            PieChartExample is undefined
          </div>
        )}
      </div>
    </div>
  );
};

export default TestChart;
