import React, { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface StackedAreaChartProps {
  kpiData?: KpiData | null;
}

interface MillingData {
  time: string;
  flour: number;
  bran: number;
  semolina: number;
  other: number;
}

const StackedAreaChart: React.FC<StackedAreaChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();
  const [hoveredPoint, setHoveredPoint] = useState<{index: number, x: number, y: number, data: MillingData} | null>(null);

  // Mock data for demonstration
  const data: MillingData[] = [
    { time: '00:00', flour: 55, bran: 25, semolina: 15, other: 5 },
    { time: '04:00', flour: 58, bran: 23, semolina: 14, other: 5 },
    { time: '08:00', flour: 62, bran: 22, semolina: 13, other: 3 },
    { time: '12:00', flour: 60, bran: 24, semolina: 12, other: 4 },
    { time: '16:00', flour: 57, bran: 26, semolina: 14, other: 3 },
    { time: '20:00', flour: 54, bran: 27, semolina: 15, other: 4 },
  ];

  const chartHeight = 180;
  const chartWidth = 380;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };

  const colors = {
    flour: '#22c55e',
    bran: '#f59e0b',
    semolina: '#3b82f6',
    other: '#64748b'
  };

  // Calculate cumulative values for stacking
  const stackedData = data.map(d => ({
    time: d.time,
    flour: d.flour,
    bran: d.flour + d.bran,
    semolina: d.flour + d.bran + d.semolina,
    other: d.flour + d.bran + d.semolina + d.other
  }));

  const createPath = (values: number[], baseline: number[] = []) => {
    const points = values.map((value, i) => {
      const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (values.length - 1);
      const y = chartHeight - (value / 100) * chartHeight + padding.top;
      return `${x},${y}`;
    });

    const baselinePoints = baseline.length > 0 
      ? baseline.map((value, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (baseline.length - 1);
          const y = chartHeight - (value / 100) * chartHeight + padding.top;
          return `${x},${y}`;
        }).reverse()
      : values.map((_, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (values.length - 1);
          return `${x},${chartHeight + padding.top}`;
        }).reverse();

    return `M ${points.join(' L ')} L ${baselinePoints.join(' L ')} Z`;
  };

  return (
    <div className="relative h-64 w-full">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight + padding.bottom}`} className="w-full h-full">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((value) => (
          <line
            key={value}
            x1={padding.left}
            y1={chartHeight - (value / 100) * chartHeight + padding.top}
            x2={chartWidth - padding.right}
            y2={chartHeight - (value / 100) * chartHeight + padding.top}
            stroke={theme === 'light' ? '#e2e8f0' : '#334155'}
            strokeWidth="1"
            opacity="0.3"
          />
        ))}

        {/* Other area */}
        <path
          d={createPath(
            stackedData.map(d => d.other),
            stackedData.map(d => d.semolina)
          )}
          fill={colors.other}
          opacity="0.7"
          className="drop-shadow-sm"
        />

        {/* Semolina area */}
        <path
          d={createPath(
            stackedData.map(d => d.semolina),
            stackedData.map(d => d.bran)
          )}
          fill={colors.semolina}
          opacity="0.7"
          className="drop-shadow-sm"
        />

        {/* Bran area */}
        <path
          d={createPath(
            stackedData.map(d => d.bran),
            stackedData.map(d => d.flour)
          )}
          fill={colors.bran}
          opacity="0.7"
          className="drop-shadow-sm"
        />

        {/* Flour area */}
        <path
          d={createPath(stackedData.map(d => d.flour))}
          fill={colors.flour}
          opacity="0.7"
          className="drop-shadow-sm"
        />

        {/* Invisible hover areas */}
        {data.map((d, i) => {
          const x = padding.left + (i * (chartWidth - padding.left - padding.right)) / (data.length - 1);
          return (
            <rect
              key={`hover-${i}`}
              x={x - 20}
              y={padding.top}
              width="40"
              height={chartHeight}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredPoint({index: i, x, y: padding.top + chartHeight / 2, data: d})}
              onMouseLeave={() => setHoveredPoint(null)}
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
              {d.time}
            </text>
          );
        })}

        {/* Y-axis labels */}
        {[0, 25, 50, 75, 100].map((value) => (
          <text
            key={value}
            x={padding.left - 5}
            y={chartHeight - (value / 100) * chartHeight + padding.top + 3}
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
          <div className="font-medium">{hoveredPoint.data.time}</div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: colors.flour }}></div>
              <span>Flour: {hoveredPoint.data.flour}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: colors.bran }}></div>
              <span>Bran: {hoveredPoint.data.bran}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: colors.semolina }}></div>
              <span>Semolina: {hoveredPoint.data.semolina}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: colors.other }}></div>
              <span>Other: {hoveredPoint.data.other}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Legend - positioned outside chart area to avoid overlap */}
      <div className={`mt-2 grid grid-cols-2 gap-3 text-xs border-t pt-2 ${
        theme === 'light' ? 'border-slate-200' : 'border-slate-700'
      }`}>
        {Object.entries(colors).map(([key, color]) => (
          <div key={key} className="flex items-center gap-2">
            <div 
              className="w-4 h-4 rounded-sm opacity-70" 
              style={{ backgroundColor: color }}
            ></div>
            <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StackedAreaChart;