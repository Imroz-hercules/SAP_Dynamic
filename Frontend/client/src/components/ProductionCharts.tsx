import { useEffect, useRef } from "react";

// Real-time production trend chart
function ProductionTrend({ 
  data, 
  color, 
  width = 280, 
  height = 120 
}: { 
  data: number[]; 
  color: string; 
  width?: number; 
  height?: number; 
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;

    // Draw trend line
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();

    // Add glow effect
    ctx.shadowColor = color;
    ctx.shadowBlur = 6;
    ctx.stroke();

    // Fill area under curve
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, color + '40');
    gradient.addColorStop(1, color + '05');
    
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
  }, [data, color, width, height]);

  return <canvas ref={canvasRef} width={width} height={height} className="w-full h-full" />;
}

// Radial quality indicator
function QualityRadial({ 
  value, 
  max, 
  color, 
  size = 60 
}: { 
  value: number; 
  max: number; 
  color: string; 
  size?: number; 
}) {
  const percentage = (value / max) * 100;
  const radius = size / 2 - 4;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        className="transform -rotate-90"
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgb(71, 85, 105)"
          strokeWidth="3"
          fill="none"
          opacity="0.3"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth="3"
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-1000 ease-out"
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold text-white">{value.toFixed(1)}</span>
      </div>
    </div>
  );
}

export function ProductionCharts() {
  // Generate realistic production data
  const phData = Array.from({ length: 12 }, (_, i) => 
    7.2 + Math.sin(i * 0.5) * 0.3 + (Math.random() - 0.5) * 0.2
  );
  
  const turbidityData = Array.from({ length: 12 }, (_, i) => 
    0.8 + Math.sin(i * 0.4) * 0.2 + (Math.random() - 0.5) * 0.1
  );
  
  const chlorineData = Array.from({ length: 12 }, (_, i) => 
    1.5 + Math.sin(i * 0.6) * 0.3 + (Math.random() - 0.5) * 0.2
  );

  return (
    <>
      {/* Production Monitoring - Top Left */}
      <div className="absolute top-4 left-3 z-20 bg-slate-800/95 backdrop-blur-sm rounded-xl p-3 border border-blue-500/30 w-64">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
          <h3 className="text-blue-400 text-sm font-semibold">Production Trends</h3>
        </div>
        
        <div className="space-y-3">
          <div className="bg-slate-800/50 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-slate-300 text-xs">pH Level</span>
              <span className="text-blue-400 text-xs font-mono">7.3</span>
            </div>
            <ProductionTrend data={phData} color="#3b82f6" width={220} height={35} />
          </div>
          
          <div className="bg-slate-800/50 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-slate-300 text-xs">Turbidity</span>
              <span className="text-emerald-400 text-xs font-mono">0.9 NTU</span>
            </div>
            <ProductionTrend data={turbidityData} color="#10b981" width={220} height={35} />
          </div>
        </div>
      </div>

      {/* Treatment Efficiency - Top Right */}
      <div className="absolute top-4 right-3 z-20 bg-slate-800/95 backdrop-blur-sm rounded-xl p-3 border border-emerald-500/30 w-72">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
          <h3 className="text-emerald-400 text-sm font-semibold">Treatment Efficiency</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center">
            <QualityRadial value={96.8} max={100} color="#10b981" size={48} />
            <div className="text-xs text-slate-300 mt-1">Filtration</div>
          </div>
          <div className="text-center">
            <QualityRadial value={94.2} max={100} color="#06b6d4" size={48} />
            <div className="text-xs text-slate-300 mt-1">Purification</div>
          </div>
          <div className="text-center">
            <QualityRadial value={98.5} max={100} color="#8b5cf6" size={48} />
            <div className="text-xs text-slate-300 mt-1">Disinfection</div>
          </div>
          <div className="text-center">
            <QualityRadial value={97.1} max={100} color="#f59e0b" size={48} />
            <div className="text-xs text-slate-300 mt-1">Conditioning</div>
          </div>
        </div>
      </div>

      {/* Chemical Dosing - Bottom Left */}
      <div className="absolute bottom-3 left-3 z-20 bg-slate-800/95 backdrop-blur-sm rounded-xl p-4 border border-purple-500/30 w-80">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
          <h3 className="text-purple-400 text-sm font-semibold">Chemical Dosing</h3>
        </div>
        
        <div className="space-y-2">
          {[
            { name: "Chlorine", level: 85, color: "#06b6d4", unit: "ppm" },
            { name: "Coagulant", level: 72, color: "#8b5cf6", unit: "mg/L" },
            { name: "pH Adjuster", level: 91, color: "#f59e0b", unit: "mg/L" }
          ].map((chemical, index) => (
            <div key={index} className="bg-slate-800/50 rounded-lg p-2">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-300 text-sm">{chemical.name}</span>
                <span className="text-sm font-mono" style={{ color: chemical.color }}>
                  {chemical.level}% {chemical.unit}
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div 
                  className="h-2 rounded-full transition-all duration-1000"
                  style={{ 
                    width: `${chemical.level}%`,
                    backgroundColor: chemical.color,
                    boxShadow: `0 0 6px ${chemical.color}40`
                  }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Production Analytics - Bottom Right */}
      <div className="absolute bottom-3 right-3 z-20 bg-slate-800/95 backdrop-blur-sm rounded-xl p-4 border border-cyan-500/30 w-80">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
          <h3 className="text-cyan-400 text-sm font-semibold">Production Analytics</h3>
        </div>
        
        <div className="space-y-3">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300 text-sm">Daily Output</span>
              <span className="text-cyan-400 text-sm font-mono">18.4M L</span>
            </div>
            <WaterQualityTrend data={chlorineData} color="#06b6d4" width={280} height={45} />
          </div>
          
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-slate-800/30 rounded-lg p-2">
              <div className="text-green-400 text-lg font-bold font-mono">94.2%</div>
              <div className="text-slate-400 text-sm">Efficiency</div>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-2">
              <div className="text-blue-400 text-lg font-bold font-mono">2.1k</div>
              <div className="text-slate-400 text-sm">L/min</div>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-2">
              <div className="text-purple-400 text-lg font-bold font-mono">99.8%</div>
              <div className="text-slate-400 text-sm">Uptime</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}