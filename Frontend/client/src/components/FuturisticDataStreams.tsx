import { useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { chartColors } from "@/lib/chartUtils";

Chart.register(...registerables);

interface DataStreamProps {
  title: string;
  value: string;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  color: string;
  sparklineData: number[];
}

function DataStreamCard({ title, value, unit, trend, color, sparklineData }: DataStreamProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Array.from({ length: sparklineData.length }, (_, i) => i),
        datasets: [{
          data: sparklineData,
          borderColor: color,
          backgroundColor: `${color}20`,
          tension: 0.4,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
        elements: {
          point: { radius: 0 },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [sparklineData, color]);

  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return '↗';
      case 'down': return '↘';
      default: return '→';
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up': return 'hsl(158, 100%, 50%)';
      case 'down': return 'hsl(0, 100%, 60%)';
      default: return 'hsl(45, 100%, 50%)';
    }
  };

  return (
    <div className="cyberpunk-card rounded-lg p-2 relative group hover:scale-105 transition-all duration-300">
      {/* Background circuit pattern */}
      <div className="absolute inset-0 cyber-grid opacity-20 rounded-lg"></div>
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex justify-between items-start mb-2">
          <div className="text-xs text-[hsl(180,100%,50%)] font-mono text-glow">
            {title}
          </div>
          <div 
            className="text-lg font-bold"
            style={{ color: getTrendColor() }}
          >
            {getTrendIcon()}
          </div>
        </div>

        {/* Main value */}
        <div className="flex items-baseline space-x-1 mb-1">
          <div 
            className="text-lg font-bold text-matrix"
            style={{ color }}
          >
            {value}
          </div>
          <div className="text-xs text-gray-400 font-mono">{unit}</div>
        </div>

        {/* Sparkline */}
        <div className="h-6 mb-1">
          <canvas ref={canvasRef} className="w-full h-full" />
        </div>

        {/* Status indicator */}
        <div className="flex items-center space-x-1">
          <div 
            className="w-1 h-1 rounded-full animate-glow-pulse"
            style={{ backgroundColor: color }}
          />
          <div className="text-xs text-gray-300 font-mono">LIVE</div>
        </div>
      </div>
    </div>
  );
}

export function FuturisticDataStreams() {
  const generateSparkline = () => Array.from({ length: 12 }, () => Math.random() * 100 + 50);

  const dataStreams = [
    {
      title: "FLOW RATE",
      value: "24.8K",
      unit: "L/min",
      trend: 'up' as const,
      color: chartColors.cyberBlue,
      sparklineData: generateSparkline(),
    },
    {
      title: "PRESSURE",
      value: "4.2",
      unit: "Bar",
      trend: 'stable' as const,
      color: chartColors.neonAmber,
      sparklineData: generateSparkline(),
    },
    {
      title: "TEMPERATURE",
      value: "22.5°C",
      unit: "Optimal",
      trend: 'stable' as const,
      color: chartColors.neonGreen,
      sparklineData: generateSparkline(),
    },
    {
      title: "TURBIDITY",
      value: "0.3",
      unit: "NTU",
      trend: 'down' as const,
      color: chartColors.cyberPurple,
      sparklineData: generateSparkline(),
    },
    {
      title: "pH LEVEL",
      value: "7.2",
      unit: "pH",
      trend: 'stable' as const,
      color: chartColors.electricBlue,
      sparklineData: generateSparkline(),
    },
    {
      title: "CHLORINE",
      value: "0.8",
      unit: "mg/L",
      trend: 'stable' as const,
      color: chartColors.neonOrange,
      sparklineData: generateSparkline(),
    },
  ];

  return (
    <div className="cyberpunk-card rounded-lg p-2 h-full">
      <div className="text-xs text-[hsl(180,100%,50%)] mb-2 text-glow font-mono tracking-wider">
        REAL-TIME DATA STREAMS
      </div>
      <div className="grid grid-cols-6 gap-2 h-full">
        {dataStreams.map((stream, index) => (
          <div key={index} className="cyberpunk-card rounded-lg p-2 text-center flex flex-col justify-center relative overflow-hidden group hover:scale-105 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-transparent to-black/20 opacity-50"></div>
            <div className="absolute top-1 right-1 w-3 h-3 border border-current rounded-full flex items-center justify-center animate-rotate-3d" style={{ color: stream.color }}>
              <div className="w-0.5 h-0.5 rounded-full animate-glow-pulse" style={{ backgroundColor: stream.color }}></div>
            </div>
            <div className="relative z-10">
              <div className="text-xs text-[hsl(180,100%,50%)] font-mono mb-1 tracking-wider">{stream.title}</div>
              <div className={`text-lg font-mono text-glow font-bold mb-1`} style={{ color: stream.color }}>
                {stream.value}
              </div>
              <div className="text-xs text-gray-400 font-mono mb-1">{stream.unit}</div>
              <div className="flex items-center justify-center mb-1">
                {stream.trend === 'up' && <span className="text-[hsl(158,100%,50%)] text-xs font-bold">↗</span>}
                {stream.trend === 'down' && <span className="text-[hsl(0,100%,50%)] text-xs font-bold">↘</span>}
                {stream.trend === 'stable' && <span className="text-[hsl(45,100%,50%)] text-xs font-bold">→</span>}
              </div>
              <div className="w-full h-0.5 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full animate-data-flow" style={{
                  background: `linear-gradient(90deg, ${stream.color}, ${stream.color}80)`,
                  width: `${Math.random() * 40 + 40}%`
                }}></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}