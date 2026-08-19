import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface PackingBarChartProps {
  kpiData?: KpiData | null;
}

const PackingBarChart: React.FC<PackingBarChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();

  // Mock data for demonstration
  const data = [
    { line: 'Line 1', output: 850, target: 900 },
    { line: 'Line 2', output: 920, target: 950 },
    { line: 'Line 3', output: 780, target: 850 },
    { line: 'Line 4', output: 890, target: 900 },
    { line: 'Line 5', output: 950, target: 1000 },
  ];

  const maxValue = Math.max(...data.map(d => Math.max(d.output, d.target))) * 1.1;
  const chartHeight = 180;
  const chartWidth = 380;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };
  const barWidth = (chartWidth - padding.left - padding.right) / data.length / 2 - 4;

  return (
    <div className="relative h-64 w-full">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight + padding.bottom}`} className="w-full h-full">
        {/* Grid lines */}
        {[0, 200, 400, 600, 800, 1000].map((value) => (
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

        {/* Bars */}
        {data.map((d, i) => {
          const groupX = padding.left + (i * (chartWidth - padding.left - padding.right)) / data.length;
          const actualHeight = (d.output / maxValue) * chartHeight;
          const targetHeight = (d.target / maxValue) * chartHeight;

          return (
            <g key={i}>
              {/* Target bar (background) */}
              <rect
                x={groupX}
                y={chartHeight - targetHeight + padding.top}
                width={barWidth}
                height={targetHeight}
                fill={theme === 'light' ? '#e2e8f0' : '#374151'}
                opacity="0.5"
                rx="2"
              />
              
              {/* Actual output bar */}
              <rect
                x={groupX}
                y={chartHeight - actualHeight + padding.top}
                width={barWidth}
                height={actualHeight}
                fill={d.output >= d.target ? '#22c55e' : '#f59e0b'}
                className={`drop-shadow-[0_0_6px_${d.output >= d.target ? '#22c55e' : '#f59e0b'}]`}
                rx="2"
              />
            </g>
          );
        })}

        {/* X-axis labels */}
        {data.map((d, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / data.length + barWidth / 2;
          return (
            <text
              key={i}
              x={x}
              y={chartHeight + padding.bottom - 5}
              textAnchor="middle"
              fontSize="9"
              fill={theme === 'light' ? '#64748b' : '#94a3b8'}
            >
              {d.line}
            </text>
          );
        })}

        {/* Y-axis labels */}
        {[0, 200, 400, 600, 800, 1000].map((value) => (
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
      </svg>

      {/* Legend - positioned outside chart area to avoid overlap */}
      <div className={`mt-2 flex justify-center gap-6 text-xs border-t pt-2 ${
        theme === 'light' ? 'border-slate-200' : 'border-slate-700'
      }`}>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded-sm"></div>
          <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
            At/Above Target
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-amber-500 rounded-sm"></div>
          <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
            Below Target
          </span>
        </div>
      </div>
    </div>
  );
};

export default PackingBarChart;