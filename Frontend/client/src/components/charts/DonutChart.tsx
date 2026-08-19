import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface DonutChartProps {
  kpiData?: KpiData | null;
}

const DonutChart: React.FC<DonutChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();

  // Mock data for demonstration
  const data = [
    { label: 'Active', value: 75, color: '#22c55e' },
    { label: 'Idle', value: 15, color: '#f59e0b' },
    { label: 'Maintenance', value: 7, color: '#ef4444' },
    { label: 'Setup', value: 3, color: '#8b5cf6' },
  ];

  const total = data.reduce((sum, item) => sum + item.value, 0);
  const centerX = 120;
  const centerY = 120;
  const radius = 80;
  const innerRadius = 50;

  let cumulativeAngle = 0;

  const createArcPath = (startAngle: number, endAngle: number, outerR: number, innerR: number) => {
    const startAngleRad = (startAngle * Math.PI) / 180;
    const endAngleRad = (endAngle * Math.PI) / 180;

    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

    const x1 = centerX + outerR * Math.cos(startAngleRad);
    const y1 = centerY + outerR * Math.sin(startAngleRad);
    const x2 = centerX + outerR * Math.cos(endAngleRad);
    const y2 = centerY + outerR * Math.sin(endAngleRad);

    const x3 = centerX + innerR * Math.cos(endAngleRad);
    const y3 = centerY + innerR * Math.sin(endAngleRad);
    const x4 = centerX + innerR * Math.cos(startAngleRad);
    const y4 = centerY + innerR * Math.sin(startAngleRad);

    return [
      "M", x1, y1,
      "A", outerR, outerR, 0, largeArcFlag, 1, x2, y2,
      "L", x3, y3,
      "A", innerR, innerR, 0, largeArcFlag, 0, x4, y4,
      "Z"
    ].join(" ");
  };

  return (
    <div className="relative h-64 w-full flex items-center justify-center">
      <svg viewBox="0 0 240 240" className="w-60 h-60">
        {data.map((segment, i) => {
          const angle = (segment.value / total) * 360;
          const startAngle = cumulativeAngle;
          const endAngle = cumulativeAngle + angle;
          cumulativeAngle += angle;

          return (
            <g key={i}>
              <path
                d={createArcPath(startAngle, endAngle, radius, innerRadius)}
                fill={segment.color}
                className={`drop-shadow-[0_0_8px_${segment.color}] hover:opacity-80 transition-opacity cursor-pointer`}
                opacity="0.8"
              />
              
              {/* Percentage labels */}
              {segment.value > 5 && (
                <text
                  x={centerX + (radius - (radius - innerRadius) / 2) * Math.cos(((startAngle + endAngle) / 2) * Math.PI / 180)}
                  y={centerY + (radius - (radius - innerRadius) / 2) * Math.sin(((startAngle + endAngle) / 2) * Math.PI / 180)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="12"
                  fontWeight="bold"
                  fill={theme === 'light' ? '#1f2937' : '#ffffff'}
                  className="drop-shadow-sm"
                >
                </text>
              )}
            </g>
          );
        })}

        {/* Center text */}
        <text
          x={centerX}
          y={centerY - 8}
          textAnchor="middle"
          fontSize="16"
          fontWeight="bold"
          fill={theme === 'light' ? '#1f2937' : '#f9fafb'}
        >
          Machine
        </text>
        <text
          x={centerX}
          y={centerY + 8}
          textAnchor="middle"
          fontSize="16"
          fontWeight="bold"
          fill={theme === 'light' ? '#1f2937' : '#f9fafb'}
        >
          Utilization
        </text>
      </svg>

      {/* Legend - positioned outside chart area to avoid overlap */}
      <div className={`mt-2 grid grid-cols-2 gap-3 text-xs border-t pt-2 ${
        theme === 'light' ? 'border-slate-200' : 'border-slate-700'
      }`}>
        {data.map((segment, i) => (
          <div key={i} className="flex items-center gap-2">
            <div 
              className="w-4 h-4 rounded-sm" 
              style={{ backgroundColor: segment.color }}
            ></div>
            <span className={theme === 'light' ? 'text-slate-600' : 'text-slate-300'}>
              {segment.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DonutChart;