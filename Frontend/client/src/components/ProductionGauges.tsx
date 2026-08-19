import { aggregateMetrics } from "@/lib/mockData";

interface GaugeProps {
  value: number;
  max: number;
  label: string;
  unit: string;
  color: string;
}

function CircularGauge({ value, max, label, unit, color }: GaugeProps) {
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value, max) / max;
  const offset = circumference - (progress * circumference);

  return (
    <div className="relative">
      <svg className="w-24 h-24 mx-auto transform -rotate-90" viewBox="0 0 120 120">
        {/* Background Circle */}
        <circle 
          cx="60" 
          cy="60" 
          r={radius} 
          fill="none" 
          stroke="rgba(255,255,255,0.1)" 
          strokeWidth="8"
        />
        {/* Progress Circle */}
        <circle 
          cx="60" 
          cy="60" 
          r={radius} 
          fill="none" 
          stroke={color}
          strokeWidth="8" 
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="animate-glow-pulse transition-all duration-2000"
          style={{
            filter: `drop-shadow(0 0 10px ${color})`,
          }}
        />
      </svg>
      
      {/* Center Text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-sm font-mono text-white font-bold">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-xs font-mono" style={{ color }}>
          {unit}
        </div>
      </div>
      
      {/* Label */}
      <div className="text-xs text-center mt-2 text-gray-400 font-mono">
        {label}
      </div>
    </div>
  );
}

export function ProductionGauges() {
  return (
    <div className="col-span-4 row-span-2 glass-morphism rounded-lg p-4">
      <div className="text-sm text-[hsl(180,100%,50%)] mb-3 text-glow font-mono">
        PRODUCTION METRICS
      </div>
      
      <div className="grid grid-cols-3 gap-4 h-full">
        <CircularGauge
          value={aggregateMetrics.totalProduction / 1000}
          max={25}
          label="Daily Production"
          unit="K m³/day"
          color="hsl(180, 100%, 50%)"
        />
        
        <CircularGauge
          value={2.4}
          max={5}
          label="Energy Efficiency"
          unit="kWh/m³"
          color="hsl(158, 100%, 50%)"
        />
        
        <CircularGauge
          value={aggregateMetrics.averageEfficiency}
          max={100}
          label="Quality Score"
          unit="Score"
          color="hsl(45, 100%, 50%)"
        />
      </div>
      
      {/* Floating particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-lg">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-[hsl(180,100%,50%)] rounded-full opacity-30 animate-float"
            style={{
              left: `${20 + i * 15}%`,
              top: `${30 + (i % 2) * 40}%`,
              animationDelay: `${i * 0.5}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
