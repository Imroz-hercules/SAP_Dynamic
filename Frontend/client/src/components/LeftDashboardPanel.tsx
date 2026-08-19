import { TrendingUp, Zap, Droplets, Activity, Shield } from "lucide-react";
import { useEffect, useRef } from "react";

// Mini chart component for sparklines
function MiniChart({ data, color, height = 40 }: { data: number[]; color: string; height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height: canvasHeight } = canvas;
    ctx.clearRect(0, 0, width, canvasHeight);

    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    data.forEach((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = canvasHeight - ((value - min) / range) * canvasHeight;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();

    // Add glow effect
    ctx.shadowColor = color;
    ctx.shadowBlur = 3;
    ctx.stroke();
  }, [data, color]);

  return <canvas ref={canvasRef} width={120} height={height} className="w-full" />;
}

export function LeftDashboardPanel() {
  // Generate sample time series data
  const generateSparklineData = (base: number, variance: number) => {
    return Array.from({ length: 20 }, (_, i) => 
      base + Math.sin(i * 0.5) * variance + (Math.random() - 0.5) * variance * 0.3
    );
  };

  const systemMetrics = [
    { 
      label: "Network Latency", 
      value: "12ms", 
      color: "#10b981", 
      data: generateSparklineData(12, 3),
      trend: "down"
    },
    { 
      label: "Data Throughput", 
      value: "89.2 MB/s", 
      color: "#06b6d4", 
      data: generateSparklineData(89, 15),
      trend: "up"
    },
    { 
      label: "System Load", 
      value: "34%", 
      color: "#3b82f6", 
      data: generateSparklineData(34, 8),
      trend: "stable"
    },
    { 
      label: "Error Rate", 
      value: "0.02%", 
      color: "#22c55e", 
      data: generateSparklineData(0.02, 0.01),
      trend: "down"
    }
  ];

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Advanced System Health Monitor */}
      <div className="bg-gradient-to-br from-slate-900/90 via-slate-800/80 to-slate-900/90 rounded-xl p-6 border border-emerald-500/20 relative">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-transparent to-cyan-500/5"></div>
        <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-pulse"></div>
        
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" />
              <h3 className="text-emerald-400 font-semibold tracking-wide">System Health</h3>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-ping"></div>
              <span className="text-emerald-400 text-xs font-mono">LIVE</span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {[
              { 
                label: "Network", 
                value: "12ms", 
                percentage: 95, 
                color: "#10b981",
                icon: "🌐",
                status: "OPTIMAL"
              },
              { 
                label: "Throughput", 
                value: "89.2 MB/s", 
                percentage: 89, 
                color: "#06b6d4",
                icon: "⚡",
                status: "HIGH"
              },
              { 
                label: "Load", 
                value: "34%", 
                percentage: 66, 
                color: "#3b82f6",
                icon: "⚙️",
                status: "NORMAL"
              },
              { 
                label: "Errors", 
                value: "0.02%", 
                percentage: 98, 
                color: "#22c55e",
                icon: "🛡️",
                status: "MINIMAL"
              }
            ].map((metric, index) => {
              const circumference = 2 * Math.PI * 16;
              const strokeDasharray = circumference;
              const strokeDashoffset = circumference - (metric.percentage / 100) * circumference;
              
              return (
                <div key={index} className="relative group">
                  <div className="bg-slate-800/40 backdrop-blur-sm rounded-lg p-4 border border-slate-700/30 hover:border-emerald-500/40 transition-all duration-300">
                    {/* Metric Icon and Value */}
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xl">{metric.icon}</span>
                      <div className="text-right">
                        <div className="text-white font-mono text-sm font-bold">{metric.value}</div>
                        <div className="text-xs font-medium" style={{ color: metric.color }}>
                          {metric.status}
                        </div>
                      </div>
                    </div>
                    
                    {/* Circular Progress */}
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300 text-xs font-medium">{metric.label}</span>
                      <div className="relative w-8 h-8">
                        <svg className="w-8 h-8 transform -rotate-90" viewBox="0 0 36 36">
                          <circle
                            cx="18"
                            cy="18"
                            r="16"
                            stroke="rgb(71, 85, 105)"
                            strokeWidth="2"
                            fill="none"
                            opacity="0.3"
                          />
                          <circle
                            cx="18"
                            cy="18"
                            r="16"
                            stroke={metric.color}
                            strokeWidth="2"
                            fill="none"
                            strokeDasharray={strokeDasharray}
                            strokeDashoffset={strokeDashoffset}
                            className="transition-all duration-1000 ease-out"
                            style={{ 
                              filter: `drop-shadow(0 0 4px ${metric.color})`,
                              strokeLinecap: 'round'
                            }}
                          />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-xs font-bold text-white">
                            {metric.percentage}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Hover Effect */}
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Overall Health Score */}
          <div className="mt-4 bg-slate-800/20 rounded-lg p-3 border border-emerald-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
                <span className="text-emerald-400 font-semibold text-sm">Overall Health Score</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-2xl font-bold text-emerald-400 font-mono">94.5%</div>
                <div className="text-emerald-400 text-xs">EXCELLENT</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Metrics with Circular Progress */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-6 border border-slate-700/50 flex-1">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-5 h-5 text-cyan-400" />
          <h3 className="text-cyan-400 font-semibold">Performance</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          {[
            { icon: Droplets, label: "Flow Rate", value: 85, max: 100, display: "2.4k L/s", color: "#3b82f6" },
            { icon: Zap, label: "Power", value: 68, max: 100, display: "847 kW", color: "#eab308" },
            { icon: Shield, label: "Quality", value: 99, max: 100, display: "98.7%", color: "#22c55e" },
            { icon: Activity, label: "Uptime", value: 100, max: 100, display: "99.9%", color: "#10b981" }
          ].map((metric, index) => {
            const circumference = 2 * Math.PI * 18;
            const strokeDasharray = circumference;
            const strokeDashoffset = circumference - (metric.value / metric.max) * circumference;
            
            return (
              <div key={index} className="bg-slate-800/30 rounded-lg p-4 text-center relative">
                <div className="relative mx-auto w-12 h-12 mb-2">
                  <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 40 40">
                    <circle
                      cx="20"
                      cy="20"
                      r="18"
                      stroke="rgb(71, 85, 105)"
                      strokeWidth="2"
                      fill="none"
                    />
                    <circle
                      cx="20"
                      cy="20"
                      r="18"
                      stroke={metric.color}
                      strokeWidth="2"
                      fill="none"
                      strokeDasharray={strokeDasharray}
                      strokeDashoffset={strokeDashoffset}
                      className="transition-all duration-1000 ease-out"
                      style={{ filter: `drop-shadow(0 0 4px ${metric.color})` }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <metric.icon className="w-4 h-4" style={{ color: metric.color }} />
                  </div>
                </div>
                <div className="text-white text-sm font-bold font-mono">
                  {metric.display}
                </div>
                <div className="text-slate-300 text-xs mt-1">{metric.label}</div>
              </div>
            );
          })}
        </div>

        {/* System Performance Matrix */}
        <div className="bg-slate-800/20 rounded-lg p-2 border border-cyan-500/20">
          <div className="text-cyan-400 font-semibold text-sm mb-3 flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse"></div>
            System Performance
          </div>
          
          <div className="grid grid-cols-2 gap-2">
            {[
              { metric: 'MTBF', value: '2.4k', unit: 'h', color: '#10b981' },
              { metric: 'Uptime', value: '99.8', unit: '%', color: '#3b82f6' },
              { metric: 'Alerts', value: '3', unit: 'active', color: '#f59e0b' },
              { metric: 'Energy', value: '847', unit: 'kWh', color: '#a855f7' }
            ].map((item, index) => (
              <div key={index} className="bg-slate-800/40 rounded-lg p-1.5 border border-slate-600/20">
                <div className="text-center">
                  <div 
                    className="text-sm font-mono font-bold"
                    style={{ color: item.color }}
                  >
                    {item.value}
                  </div>
                  <div className="text-xs text-slate-400">{item.unit}</div>
                  <div className="text-xs text-slate-500 font-mono">{item.metric}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}