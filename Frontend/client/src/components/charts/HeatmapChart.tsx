import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { KpiData } from '../../lib/api';

interface HeatmapChartProps {
  kpiData?: KpiData | null;
}

const HeatmapChart: React.FC<HeatmapChartProps> = ({ kpiData }) => {
  const { theme } = useTheme();

  // Mock data for demonstration
  const shifts = ['Morning', 'Afternoon', 'Night'];
  const materials = ['Flour A', 'Flour B', 'Bran', 'Semolina'];
  const data = [
    // Morning shift
    [92, 88, 85, 90],
    // Afternoon shift  
    [89, 91, 87, 88],
    // Night shift
    [87, 85, 89, 92]
  ];

  const minValue = 80;
  const maxValue = 95;
  const cellWidth = 80;
  const cellHeight = 40;

  const getColor = (value: number) => {
    const normalized = (value - minValue) / (maxValue - minValue);
    if (theme === 'light') {
      // Lighter colors for light mode
      if (normalized < 0.3) return '#fecaca'; // Light red for low values
      if (normalized < 0.6) return '#fed7aa'; // Light amber for medium values
      if (normalized < 0.8) return '#bbf7d0'; // Light green for good values
      return '#a7f3d0'; // Light emerald for excellent values
    } else {
      // Original darker colors for dark mode
      if (normalized < 0.3) return '#ef4444'; // Red for low values
      if (normalized < 0.6) return '#f59e0b'; // Amber for medium values
      if (normalized < 0.8) return '#22c55e'; // Green for good values
      return '#10b981'; // Emerald for excellent values
    }
  };

  const getIntensity = (value: number) => {
    if (theme === 'light') {
      // Higher opacity for light mode to ensure visibility
      return ((value - minValue) / (maxValue - minValue)) * 0.6 + 0.4;
    } else {
      // Original opacity for dark mode
      return ((value - minValue) / (maxValue - minValue)) * 0.8 + 0.2;
    }
  };

  const getTextColor = (value: number) => {
    const normalized = (value - minValue) / (maxValue - minValue);
    // For light mode, use dark text on light backgrounds and light text on dark backgrounds
    if (theme === 'light') {
      // Use dark text for better contrast in light mode
      return '#1f2937'; // Dark gray
    } else {
      // Use white text for dark mode
      return '#ffffff';
    }
  };

  return (
    <div className="relative h-64 w-full">
      <svg viewBox="0 0 400 200" className="w-full h-full">
        {/* Material labels (top) */}
        {materials.map((material, i) => (
          <text
            key={i}
            x={80 + i * cellWidth + cellWidth / 2}
            y={15}
            textAnchor="middle"
            fontSize="11"
            fontWeight="bold"
            fill={theme === 'light' ? '#374151' : '#d1d5db'}
          >
            {material}
          </text>
        ))}

        {/* Shift labels (left) */}
        {shifts.map((shift, i) => (
          <text
            key={i}
            x={70}
            y={40 + i * cellHeight + cellHeight / 2}
            textAnchor="end"
            fontSize="11"
            fontWeight="bold"
            fill={theme === 'light' ? '#374151' : '#d1d5db'}
            dominantBaseline="middle"
          >
            {shift}
          </text>
        ))}

        {/* Heatmap cells */}
        {data.map((shiftData, shiftIndex) => 
          shiftData.map((value, materialIndex) => (
            <g key={`${shiftIndex}-${materialIndex}`}>
              <rect
                x={80 + materialIndex * cellWidth}
                y={25 + shiftIndex * cellHeight}
                width={cellWidth - 2}
                height={cellHeight - 2}
                fill={getColor(value)}
                opacity={getIntensity(value)}
                stroke={theme === 'light' ? '#e5e7eb' : '#1f2937'}
                strokeWidth="1"
                className="drop-shadow-sm"
                rx="4"
              />
            </g>
          ))
        )}

        {/* Legend */}
        <g transform="translate(80, 155)">
          <text
            x="0"
            y="0"
            fontSize="10"
            fill={theme === 'light' ? '#64748b' : '#94a3b8'}
          >
            Extraction Rate:
          </text>
          
          {/* Legend gradient bar */}
          <rect x="80" y="-8" width="160" height="12" fill="url(#heatmapGradient)" rx="2"/>
          
          {/* Legend labels */}
          <text x="80" y="20" fontSize="9" fill={theme === 'light' ? '#64748b' : '#94a3b8'}>
            {minValue}%
          </text>
          <text x="240" y="20" fontSize="9" fill={theme === 'light' ? '#64748b' : '#94a3b8'} textAnchor="end">
            {maxValue}%
          </text>
        </g>

        {/* Gradient definition */}
        <defs>
          <linearGradient id="heatmapGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            {theme === 'light' ? (
              <>
                <stop offset="0%" stopColor="#fecaca"/>
                <stop offset="33%" stopColor="#fed7aa"/>
                <stop offset="66%" stopColor="#bbf7d0"/>
                <stop offset="100%" stopColor="#a7f3d0"/>
              </>
            ) : (
              <>
                <stop offset="0%" stopColor="#ef4444"/>
                <stop offset="33%" stopColor="#f59e0b"/>
                <stop offset="66%" stopColor="#22c55e"/>
                <stop offset="100%" stopColor="#10b981"/>
              </>
            )}
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};

export default HeatmapChart;