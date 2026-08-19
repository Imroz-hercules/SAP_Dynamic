import { BarChart3, Gauge, MapPin, Clock, Database, Wifi } from "lucide-react";
import { useEffect, useRef } from "react";

// Simple circular progress component using SVG
function DonutChart({ percentage, color, size = 60 }: { percentage: number; color: string; size?: number }) {
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
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgb(71, 85, 105)"
          strokeWidth="3"
          fill="none"
          opacity="0.3"
        />
        {/* Progress circle */}
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
    </div>
  );
}

// Bar chart component
function MiniBarChart({ data, color }: { data: number[]; color: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    const max = Math.max(...data);
    const barWidth = width / data.length - 2;

    data.forEach((value, index) => {
      const barHeight = (value / max) * height;
      const x = index * (barWidth + 2);
      const y = height - barHeight;

      ctx.fillStyle = color;
      ctx.fillRect(x, y, barWidth, barHeight);
      
      // Add glow
      ctx.shadowColor = color;
      ctx.shadowBlur = 2;
      ctx.fillRect(x, y, barWidth, barHeight);
    });
  }, [data, color]);

  return <canvas ref={canvasRef} width={100} height={30} className="w-full" />;
}

export function RightDashboardPanel() {
  // Generate sample data for charts
  const dailyProductionData = [85, 92, 78, 95, 88, 91, 87, 83, 96, 89, 94, 90];
  const efficiencyData = [94, 92, 95, 91, 93, 96, 89, 94, 92, 95, 93, 94];

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Live Production Stats with Charts */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-6 border border-slate-700/50">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          <h3 className="text-blue-400 font-semibold">Production Stats</h3>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-slate-300 text-sm">Total Output</span>
            <span className="text-blue-400 font-mono text-lg font-bold">18.4M L</span>
          </div>
          
          {/* Daily Target with Donut Chart */}
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300 text-sm font-medium">Daily Target</span>
              <span className="text-blue-400 text-sm font-bold">87%</span>
            </div>
            <div className="flex items-center gap-3">
              <DonutChart percentage={87} color="#3b82f6" size={60} />
              <div className="flex-1">
                <div className="text-xs text-slate-400 mb-1">12 hours remaining</div>
                <MiniBarChart data={dailyProductionData} color="#06b6d4" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-800/30 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center mb-1">
                <DonutChart percentage={85} color="#22c55e" size={50} />
              </div>
              <div className="text-green-400 font-mono text-sm font-bold">2.1k</div>
              <div className="text-slate-400 text-xs">L/min</div>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center mb-1">
                <DonutChart percentage={94} color="#f59e0b" size={50} />
              </div>
              <div className="text-amber-400 font-mono text-sm font-bold">94.2%</div>
              <div className="text-slate-400 text-xs">Efficiency</div>
            </div>
          </div>
        </div>
      </div>

      {/* Regional Status Matrix with Visual Charts */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-6 border border-slate-700/50 flex-1">
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="w-5 h-5 text-emerald-400" />
          <h3 className="text-emerald-400 font-semibold">Regional Status</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          {[
            { region: "Central", status: "optimal", facilities: 3, efficiency: 95, color: "#10b981" },
            { region: "Western", status: "warning", facilities: 3, efficiency: 78, color: "#f59e0b" },
            { region: "Eastern", status: "optimal", facilities: 3, efficiency: 92, color: "#10b981" },
            { region: "Northern", status: "normal", facilities: 1, efficiency: 87, color: "#3b82f6" }
          ].map((region, index) => (
            <div key={index} className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-200 text-xs font-medium">{region.region}</span>
                <div className="w-2 h-2 rounded-full animate-pulse" 
                     style={{ backgroundColor: region.color }}></div>
              </div>
              
              <div className="flex items-center gap-2 mb-2">
                <DonutChart percentage={region.efficiency} color={region.color} size={36} />
                <div className="flex-1">
                  <div className="text-white text-xs font-bold">{region.efficiency}%</div>
                  <div className="text-slate-400 text-xs">Efficiency</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="text-slate-400 text-xs">{region.facilities} facilities</div>
                <div className="text-xs font-medium capitalize" 
                     style={{ color: region.color }}>{region.status}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Advanced 3D Analytics Charts */}
      <div className="space-y-2 flex-1 flex flex-col">
        {/* Spacer to align Treatment Efficiency with bottom of network */}
        <div className="flex-grow min-h-0"></div>
        
        {/* Treatment Efficiency 3D Radar */}
        <div className="bg-gradient-to-br from-slate-900/95 to-slate-800/95 backdrop-blur-lg border border-slate-700/50 rounded-xl p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-cyan-500/5"></div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Gauge className="w-4 h-4 text-emerald-400" />
              <h4 className="text-emerald-400 font-semibold text-sm">Treatment Efficiency</h4>
            </div>
            
            <div className="relative h-32 flex items-center justify-between">
              {/* 3D Hexagonal Radar Chart */}
              <svg className="w-32 h-32" viewBox="0 0 100 100">
                {/* Hexagon Grid */}
                {[1, 0.75, 0.5, 0.25].map((scale, index) => (
                  <polygon
                    key={index}
                    points="50,10 85,32.5 85,67.5 50,90 15,67.5 15,32.5"
                    fill="none"
                    stroke="rgba(148, 163, 184, 0.1)"
                    strokeWidth="0.5"
                    transform={`scale(${scale}) translate(${50 * (1 - scale)}, ${50 * (1 - scale)})`}
                  />
                ))}
                
                {/* Radar Lines */}
                {Array.from({ length: 6 }, (_, i) => {
                  const angle = (i * 60) - 90;
                  const radian = (angle * Math.PI) / 180;
                  const x = 50 + 35 * Math.cos(radian);
                  const y = 50 + 35 * Math.sin(radian);
                  return (
                    <line
                      key={i}
                      x1="50"
                      y1="50"
                      x2={x}
                      y2={y}
                      stroke="rgba(148, 163, 184, 0.1)"
                      strokeWidth="0.5"
                    />
                  );
                })}
                
                {/* Data Polygon */}
                <polygon
                  points="50,17 72,34 68,63 50,77 32,63 28,34"
                  fill="rgba(16, 185, 129, 0.2)"
                  stroke="rgb(16, 185, 129)"
                  strokeWidth="1.5"
                  className="animate-pulse"
                />
                
                {/* Data Points */}
                {[[50,17], [72,34], [68,63], [50,77], [32,63], [28,34]].map((point, i) => (
                  <circle
                    key={i}
                    cx={point[0]}
                    cy={point[1]}
                    r="1"
                    fill="rgb(16, 185, 129)"
                    className="animate-ping"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </svg>
              
              {/* Stats */}
              <div className="flex-1 space-y-1 ml-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Filtration</span>
                  <span className="text-xs text-emerald-400 font-mono font-bold">96.7%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Purification</span>
                  <span className="text-xs text-cyan-400 font-mono font-bold">94.2%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Disinfection</span>
                  <span className="text-xs text-blue-400 font-mono font-bold">98.1%</span>
                </div>
              </div>
            </div>
          </div>
        </div>





      </div>

    </div>
  );
}