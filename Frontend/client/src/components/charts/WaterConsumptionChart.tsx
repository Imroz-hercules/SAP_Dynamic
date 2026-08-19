import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface WaterConsumptionChartProps {
  kpiData?: KpiData | null;
}

interface HourlyData {
  hour: string;
  consumption: number;
}

const WaterConsumptionChart: React.FC<WaterConsumptionChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();

  // Mock data for demonstration
  const data: HourlyData[] = [
    { hour: '00', consumption: 8.5 },
    { hour: '04', consumption: 7.2 },
    { hour: '08', consumption: 12.8 },
    { hour: '12', consumption: 11.3 },
    { hour: '16', consumption: 9.7 },
    { hour: '20', consumption: 6.4 },
  ];

  const maxValue = Math.max(...data.map(d => d.consumption)) * 1.2;
  const chartHeight = 180;
  const chartWidth = 380;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };

  return (
    <div className="relative h-64 w-full">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight + padding.bottom}`} className="w-full h-full">
        {/* Grid lines */}
        {[0, 5, 10, 15, 20].map((value) => (
          <line
            key={value}
            x1={padding.left}
            y1={chartHeight - (value / maxValue) * chartHeight + padding.top}
            x2={chartWidth - padding.right}
            y2={chartHeight - (value / maxValue) * chartHeight + padding.top}
            stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
            strokeWidth="1"
            opacity="0.3"
          />
        ))}

        {/* Area under curve */}
        <path
          d={`M ${padding.left},${chartHeight + padding.top} ${data.map((d, i) => {
            const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
            const y = chartHeight - (d.consumption / maxValue) * chartHeight + padding.top;
            return `L ${x},${y}`;
          }).join(' ')} L ${chartWidth - padding.right},${chartHeight + padding.top} Z`}
          fill="url(#waterGradient)"
          opacity="0.3"
        />

        {/* Main line */}
        <path
          d={`M ${data.map((d, i) => {
            const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
            const y = chartHeight - (d.consumption / maxValue) * chartHeight + padding.top;
            return `${x},${y}`;
          }).join(' L ')}`}
          fill="none"
          stroke="#0ea5e9"
          strokeWidth="2"
          className="drop-shadow-[0_0_6px_#0ea5e9]"
        />

        {/* Data points */}
        {data.map((d, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
          const y = chartHeight - (d.consumption / maxValue) * chartHeight + padding.top;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3"
              fill="#0ea5e9"
              className="drop-shadow-[0_0_4px_#0ea5e9]"
            />
          );
        })}

        {/* X-axis labels */}
        {data.map((d, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
          return (
            <text
              key={i}
              x={x}
              y={chartHeight + padding.bottom - 5}
              textAnchor="middle"
              fontSize="9"
              fill={theme === 'light' ? '#64748b' : '#94a3b8'}
            >
              {d.hour}
            </text>
          );
        })}

        {/* Y-axis labels */}
        {[0, 5, 10, 15, 20].map((value) => (
          <text
            key={value}
            x={padding.left - 5}
            y={chartHeight - (value / maxValue) * chartHeight + padding.top + 3}
            textAnchor="end"
            fontSize="9"
            fill={theme === 'light' ? '#64748b' : '#94a3b8'}
          >
            {value}
          </text>
        ))}

        {/* Gradient definition */}
        <defs>
          <linearGradient id="waterGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.1"/>
          </linearGradient>
        </defs>
      </svg>

      {/* Current consumption indicator */}
      <div className="absolute top-2 left-2 text-xs mt-2">
        <span className={`font-semibold ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
          Current: 
        </span>
        <span className="text-sky-500 font-bold ml-1">
          {data[data.length - 1].consumption.toFixed(1)} m³/hr
        </span>
      </div>
    </div>
  );
};

export default WaterConsumptionChart;