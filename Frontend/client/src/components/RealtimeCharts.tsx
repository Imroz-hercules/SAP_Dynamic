import { useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { chartColors, chartDefaults, createGradient } from "@/lib/chartUtils";
import { mockFacilityMetrics } from "@/lib/mockData";

Chart.register(...registerables);

interface ChartComponentProps {
  title: string;
  type: 'line' | 'bar' | 'doughnut';
  data: any;
  color: string;
  className?: string;
}

function ChartComponent({ title, type, data, color, className = "" }: ChartComponentProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    // Destroy existing chart
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const chartData = {
      ...data,
      datasets: data.datasets.map((dataset: any) => ({
        ...dataset,
        borderColor: color,
        backgroundColor: type === 'line' ? createGradient(ctx, color, 0.1) : color,
        pointBackgroundColor: color,
        pointBorderColor: '#ffffff',
        pointHoverRadius: 6,
        tension: 0.4,
        fill: type === 'line',
        borderWidth: type === 'bar' ? 1 : 2,
      })),
    };

    chartRef.current = new Chart(ctx, {
      type,
      data: chartData,
      options: {
        ...chartDefaults,
        plugins: {
          ...chartDefaults.plugins,
          legend: {
            display: type === 'doughnut',
            position: 'bottom',
            labels: {
              font: { size: 9 },
              usePointStyle: true,
              color: '#ffffff',
            },
          },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [data, color, type]);

  return (
    <div className={`holographic rounded-lg p-3 relative ${className}`}>
      <div className="text-xs text-[hsl(180,100%,50%)] mb-2 font-mono text-glow">
        {title}
      </div>
      <div className="h-20">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}

function ChemicalUsageWidget() {
  const chemicals = [
    { name: "Chlorine", level: 78, color: "hsl(158, 100%, 50%)" },
    { name: "Alum", level: 65, color: "hsl(180, 100%, 50%)" },
    { name: "pH Adj.", level: 42, color: "hsl(45, 100%, 50%)" },
  ];

  return (
    <div className="holographic rounded-lg p-3 relative">
      <div className="text-xs text-[hsl(180,100%,50%)] mb-2 font-mono text-glow">
        CHEMICAL USAGE
      </div>
      <div className="space-y-2">
        {chemicals.map((chemical) => (
          <div key={chemical.name} className="flex justify-between items-center">
            <span className="text-xs font-mono">{chemical.name}</span>
            <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full animate-glow-pulse transition-all duration-1000" 
                style={{ 
                  width: `${chemical.level}%`,
                  backgroundColor: chemical.color,
                  boxShadow: `0 0 8px ${chemical.color}`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ComplianceWidget() {
  return (
    <div className="holographic rounded-lg p-3 relative">
      <div className="text-xs text-[hsl(180,100%,50%)] mb-2 font-mono text-glow">
        COMPLIANCE
      </div>
      <div className="text-center">
        <div className="text-2xl text-[hsl(158,100%,50%)] text-glow font-bold font-mono">
          97.2%
        </div>
        <div className="text-xs text-gray-400 font-mono">REGULATORY</div>
        <div className="mt-2 flex justify-center space-x-1">
          {[0, 0.5, 1].map((delay) => (
            <div
              key={delay}
              className="w-2 h-2 bg-[hsl(158,100%,50%)] rounded-full animate-glow-pulse"
              style={{ animationDelay: `${delay}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function RealtimeCharts() {
  const flowData = {
    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
    datasets: [{
      data: [2200, 2400, 2800, 3100, 2900, 2600],
    }],
  };

  const pressureData = {
    labels: ['P1', 'P2', 'P3', 'P4', 'P5'],
    datasets: [{
      data: [4.2, 3.8, 4.5, 4.1, 3.9],
    }],
  };

  return (
    <div className="col-span-4 row-span-3 grid grid-cols-2 grid-rows-2 gap-3">
      <ChartComponent
        title="FLOW RATE"
        type="line"
        data={flowData}
        color={chartColors.cyberBlue}
      />
      
      <ChartComponent
        title="PRESSURE"
        type="bar"
        data={pressureData}
        color={chartColors.neonGreen}
      />
      
      <ChemicalUsageWidget />
      
      <ComplianceWidget />
    </div>
  );
}
