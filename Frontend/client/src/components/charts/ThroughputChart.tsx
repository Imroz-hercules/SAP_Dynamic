import React, { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface ThroughputChartProps {
  kpiData?: KpiData | null;
}

interface ChartData {
  time: string;
  throughput: number;
  efficiency: number;
}

const ThroughputChart: React.FC<ThroughputChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();
  const [hoveredPoint, setHoveredPoint] = useState<{index: number, type: 'throughput' | 'efficiency', x: number, y: number, value: number} | null>(null);

  // Mock data for demonstration
  const data: ChartData[] = [
    { time: '00:00', throughput: 75, efficiency: 82 },
    { time: '04:00', throughput: 68, efficiency: 78 },
    { time: '08:00', throughput: 92, efficiency: 88 },
    { time: '12:00', throughput: 85, efficiency: 91 },
    { time: '16:00', throughput: 79, efficiency: 84 },
    { time: '20:00', throughput: 71, efficiency: 76 },
  ];

  const maxValue = 100;
  const chartHeight = 180;
  const chartWidth = 380;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };

  return (
    <div className="relative h-64 w-full">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight + padding.bottom}`} className="w-full h-full">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((value) => (
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

        {/* Throughput line */}
        <path
          d={`M ${data.map((d, i) => {
            const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
            const y = chartHeight - (d.throughput / maxValue) * chartHeight + padding.top;
            return `${x},${y}`;
          }).join(' L ')}`}
          fill="none"
          stroke="#00d9ff"
          strokeWidth="2"
          className="drop-shadow-[0_0_6px_#00d9ff]"
        />

        {/* Efficiency line */}
        <path
          d={`M ${data.map((d, i) => {
            const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
            const y = chartHeight - (d.efficiency / maxValue) * chartHeight + padding.top;
            return `${x},${y}`;
          }).join(' L ')}`}
          fill="none"
          stroke="#a855f7"
          strokeWidth="2"
          className="drop-shadow-[0_0_6px_#a855f7]"
        />

        {/* Data points */}
        {data.map((d, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
          const throughputY = chartHeight - (d.throughput / maxValue) * chartHeight + padding.top;
          const efficiencyY = chartHeight - (d.efficiency / maxValue) * chartHeight + padding.top;
          return (
            <g key={i}>
              <circle
                cx={x}
                cy={throughputY}
                r="4"
                fill="#00d9ff"
                className="drop-shadow-[0_0_3px_#00d9ff] cursor-pointer"
                onMouseEnter={() => setHoveredPoint({index: i, type: 'throughput', x, y: throughputY, value: d.throughput})}
                onMouseLeave={() => setHoveredPoint(null)}
              />
              <circle
                cx={x}
                cy={efficiencyY}
                r="4"
                fill="#a855f7"
                className="drop-shadow-[0_0_3px_#a855f7] cursor-pointer"
                onMouseEnter={() => setHoveredPoint({index: i, type: 'efficiency', x, y: efficiencyY, value: d.efficiency})}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            </g>
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
              {d.time}
            </text>
          );
        })}

        {/* Y-axis labels */}
        {[0, 25, 50, 75, 100].map((value) => (
          <text
            key={value}
            x={padding.left - 5}
            y={chartHeight - (value / maxValue) * chartHeight + padding.top + 3}
            textAnchor="end"
            fontSize="9"
            fill={theme === 'light' ? '#64748b' : '#94a3b8'}
          >
            {value}%
          </text>
        ))}
      </svg>

      {/* Tooltip */}
      {hoveredPoint && (
        <div 
          className={`absolute z-10 px-2 py-1 text-xs rounded shadow-lg pointer-events-none ${
            theme === 'light' 
              ? 'bg-white border border-slate-200 text-slate-800' 
              : 'bg-slate-800 border border-slate-600 text-slate-200'
          }`}
          style={{
            left: `${(hoveredPoint.x / chartWidth) * 100}%`,
            top: `${(hoveredPoint.y / (chartHeight + padding.bottom)) * 100}%`,
            transform: 'translate(-50%, -100%) translateY(-8px)'
          }}
        >
          <div className="font-medium">{data[hoveredPoint.index].time}</div>
          <div className={`${hoveredPoint.type === 'throughput' ? 'text-cyan-400' : 'text-purple-400'}`}>
            {hoveredPoint.type === 'throughput' ? 'Throughput' : 'Efficiency'}: {hoveredPoint.value}%
          </div>
        </div>
      )}

      {/* Legend - positioned outside chart area to avoid overlap */}
      <div className={`mt-2 flex justify-center gap-6 text-xs border-t pt-2 ${
        theme === 'light' ? 'border-slate-200' : 'border-slate-700'
      }`}>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-cyan-400 shadow-[0_0_4px_#00d9ff]"></div>
          <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
            Throughput
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-purple-500 shadow-[0_0_4px_#a855f7]"></div>
          <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
            Efficiency
          </span>
        </div>
      </div>
    </div>
  );
};

export default ThroughputChart;