import { Facility } from "@shared/schema";
import { getStatusColor } from "@/lib/mockData";
import { useState, useEffect } from "react";

interface HolographicMapProps {
  facilities: Facility[];
  onFacilityClick?: (facility: Facility) => void;
}

export function HolographicMap({ facilities, onFacilityClick }: HolographicMapProps) {
  const [hoveredFacility, setHoveredFacility] = useState<Facility | null>(null);
  const [animationFrame, setAnimationFrame] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationFrame(prev => (prev + 1) % 360);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const getFacilityPosition = (facility: Facility) => {
    // Accurate Saudi Arabia geographic bounds
    const saudiLatRange = [16.0, 32.5];  // South to North
    const saudiLngRange = [34.0, 56.0];  // West to East (Red Sea to Persian Gulf)
    
    // Calculate normalized position (0-1 range)
    const latNorm = (facility.latitude - saudiLatRange[0]) / (saudiLatRange[1] - saudiLatRange[0]);
    const lngNorm = (facility.longitude - saudiLngRange[0]) / (saudiLngRange[1] - saudiLngRange[0]);
    
    // Map to SVG coordinate system with proper bounds
    const x = Math.max(10, Math.min(110, lngNorm * 100 + 10)); // 10-110 range in 120 width
    const y = Math.max(10, Math.min(70, (1 - latNorm) * 60 + 10)); // 10-70 range in 80 height (inverted for SVG)
    
    return { x, y };
  };

  return (
    <div className="relative w-full h-full">
      {/* Network Status Display */}
      <div className="absolute top-4 left-4 z-10">
        <div className="text-cyan-400 text-sm font-mono">SAUDI ARABIA NETWORK MAP</div>
      </div>
      
      <div className="absolute top-4 right-4 z-10">
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
          <span className="text-cyan-300">NETWORK STATUS</span>
        </div>
        <div className="text-green-400 text-xs font-mono">● ONLINE</div>
      </div>
      
      {/* Live Network Monitoring Background */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Matrix-style data streams */}
        <div className="absolute inset-0">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="absolute w-px opacity-30"
              style={{
                left: `${10 + i * 12}%`,
                height: '100%',
                background: 'linear-gradient(180deg, transparent 0%, hsl(120, 100%, 50%) 20%, hsl(180, 100%, 50%) 50%, hsl(195, 100%, 50%) 80%, transparent 100%)',
                animation: `matrix-rain ${3 + i * 0.5}s linear infinite`,
                animationDelay: `${i * 0.3}s`,
              }}
            />
          ))}
        </div>
        
        {/* Network monitoring overlay patterns */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              radial-gradient(circle at 25% 25%, hsl(180, 100%, 50%) 0%, transparent 50%),
              radial-gradient(circle at 75% 75%, hsl(195, 100%, 50%) 0%, transparent 50%),
              linear-gradient(45deg, transparent 45%, hsl(180, 100%, 30%) 50%, transparent 55%)
            `,
            backgroundSize: '40px 40px, 60px 60px, 20px 20px',
            animation: 'network-pulse 4s ease-in-out infinite',
          }} />
        </div>
        
        {/* Live system metrics overlay */}
        <div className="absolute top-2 left-2 text-xs font-mono text-green-400 opacity-60">
          <div className="flex gap-4">
            <span>CPU: {(75 + Math.sin(animationFrame * 0.1) * 15).toFixed(1)}%</span>
            <span>MEM: {(68 + Math.cos(animationFrame * 0.08) * 10).toFixed(1)}%</span>
            <span>NET: {(1.2 + Math.sin(animationFrame * 0.05) * 0.8).toFixed(1)}Gb/s</span>
          </div>
        </div>
        
        {/* Scanning sweep line */}
        <div 
          className="absolute w-full h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-50"
          style={{
            top: `${50 + Math.sin(animationFrame * 0.03) * 40}%`,
            boxShadow: '0 0 10px hsl(180, 100%, 50%)',
          }}
        />
      </div>
      
      {/* Network Topology Visualization */}
      <div className="absolute inset-4 w-full h-5/6">
        <svg 
          viewBox="0 0 120 80" 
          className="w-full h-full"
          style={{ 
            filter: 'drop-shadow(0 0 15px hsl(180, 100%, 50%)) drop-shadow(0 0 25px hsl(180, 100%, 30%))',
            transform: `perspective(1000px) rotateX(${Math.sin(animationFrame * 0.02) * 5}deg)`
          }}
        >
          <defs>
            <linearGradient id="networkBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="hsl(180, 100%, 15%)" stopOpacity="0.3"/>
              <stop offset="50%" stopColor="hsl(195, 100%, 20%)" stopOpacity="0.2"/>
              <stop offset="100%" stopColor="hsl(210, 100%, 10%)" stopOpacity="0.1"/>
            </linearGradient>
            
            <pattern id="monitoringGrid" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
              <circle cx="4" cy="4" r="0.5" fill="hsl(180, 100%, 40%)" opacity="0.3"/>
              <path d="M 8 0 L 0 0 0 8" fill="none" stroke="hsl(180, 100%, 30%)" strokeWidth="0.2" opacity="0.4"/>
            </pattern>
            
            <filter id="nodeGlow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <filter id="dataPathGlow">
              <feGaussianBlur stdDeviation="1" result="softGlow"/>
              <feColorMatrix values="0 0 0 0 0  0 1 1 0 0.8  0 1 1 0 1  0 0 0 1 0"/>
              <feMerge>
                <feMergeNode in="softGlow"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                    refX="0" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="hsl(180, 100%, 70%)" opacity="0.9"/>
            </marker>
          </defs>
          
          {/* Network Monitoring Background */}
          <rect width="100%" height="100%" fill="url(#networkBg)"/>
          <rect width="100%" height="100%" fill="url(#monitoringGrid)" opacity="0.6"/>
          
          {/* Network Topology Grid */}
          <g stroke="hsl(180, 100%, 30%)" strokeWidth="0.2" opacity="0.3">
            {[10,20,30,40,50,60,70,80,90,100,110].map(x => (
              <line key={x} x1={x} y1="0" x2={x} y2="80"/>
            ))}
            {[10,20,30,40,50,60,70].map(y => (
              <line key={y} x1="0" y1={y} x2="120" y2={y}/>
            ))}
          </g>
          
          {/* Facility Network Nodes positioned at accurate geographic coordinates */}
          {facilities.map((facility, index) => {
            const { x, y } = getFacilityPosition(facility);
            
            return (
              <g key={facility.id}>
                {/* Network Node */}
                <circle 
                  cx={x} cy={y} r="4" 
                  fill={getStatusColor(facility.status)} 
                  stroke="hsl(180, 100%, 70%)" 
                  strokeWidth="1.5"
                  filter="url(#nodeGlow)"
                  opacity="0.9"
                  style={{ cursor: 'pointer' }}
                  onClick={() => onFacilityClick?.(facility)}
                  onMouseEnter={() => setHoveredFacility(facility)}
                  onMouseLeave={() => setHoveredFacility(null)}
                >
                  <animate attributeName="r" values="3;5;3" dur={`${2 + index * 0.3}s`} repeatCount="indefinite"/>
                </circle>
                
                {/* Facility Label directly above dot */}
                <text 
                  x={x} y={y - 8} 
                  textAnchor="middle" 
                  fill="hsl(180, 100%, 100%)" 
                  fontSize="5"
                  fontWeight="bold"
                  opacity="1"
                  style={{ 
                    cursor: 'pointer',
                    filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.8)) drop-shadow(0 0 8px hsl(180, 100%, 70%))',
                    fontFamily: 'monospace'
                  }}
                  onClick={() => onFacilityClick?.(facility)}
                >
                  {facility.location}
                </text>
                
                {/* Data Transfer Indicator */}
                <circle 
                  cx={x} cy={y} r="6" 
                  fill="none" 
                  stroke="hsl(195, 100%, 60%)" 
                  strokeWidth="0.5"
                  opacity="0.6"
                >
                  <animate attributeName="r" values="6;12;6" dur="4s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.6;0;0.6" dur="4s" repeatCount="indefinite"/>
                </circle>
              </g>
            );
          })}
          
          {/* Network Connections - Riyadh as Central Hub */}
          <g stroke="hsl(180, 100%, 60%)" strokeWidth="1.5" opacity="0.8">
            {(() => {
              const riyadh = facilities.find(f => f.location === "Riyadh");
              if (!riyadh) return null;
              
              const riyadhPos = getFacilityPosition(riyadh);
              
              return (
                <>
                  {/* Central Hub Ring around Riyadh */}
                  <circle cx={riyadhPos.x} cy={riyadhPos.y} r="18" fill="none" strokeDasharray="4,2" stroke="hsl(180, 100%, 70%)" strokeWidth="2">
                    <animate attributeName="stroke-dashoffset" values="0;6" dur="2s" repeatCount="indefinite"/>
                  </circle>
                  
                  {/* Hub Label with clean shadow */}
                  <text 
                    x={riyadhPos.x} y={riyadhPos.y + 30} 
                    textAnchor="middle" 
                    fill="hsl(45, 100%, 100%)" 
                    fontSize="4.5"
                    fontWeight="bold"
                    opacity="1"
                    style={{ 
                      filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.8)) drop-shadow(0 0 8px hsl(45, 100%, 70%))',
                      fontFamily: 'monospace'
                    }}
                  >
                    CENTRAL HUB
                  </text>
                  
                  {/* Connections from Riyadh to ALL other cities */}
                  {facilities
                    .filter(f => f.location !== "Riyadh")
                    .map((facility, index) => {
                      const facilityPos = getFacilityPosition(facility);
                      return (
                        <line 
                          key={facility.id}
                          x1={riyadhPos.x} y1={riyadhPos.y} 
                          x2={facilityPos.x} y2={facilityPos.y} 
                          markerEnd="url(#arrowhead)"
                          stroke="hsl(180, 100%, 55%)"
                          strokeWidth="1.2"
                        >
                          <animate 
                            attributeName="stroke-dasharray" 
                            values="0,60;30,30;60,0" 
                            dur={`${2.5 + index * 0.3}s`} 
                            repeatCount="indefinite"
                          />
                        </line>
                      );
                    })}
                </>
              );
            })()}
          </g>
          
          {/* Secondary Network Mesh between coastal cities */}
          <g stroke="hsl(195, 100%, 40%)" strokeWidth="0.8" opacity="0.5">
            {(() => {
              const jeddah = facilities.find(f => f.location === "Jeddah");
              const dammam = facilities.find(f => f.location === "Dammam");
              const khobar = facilities.find(f => f.location === "Al-Khobar");
              
              return (
                <>
                  {jeddah && dammam && (
                    <line 
                      x1={getFacilityPosition(jeddah).x} y1={getFacilityPosition(jeddah).y}
                      x2={getFacilityPosition(dammam).x} y2={getFacilityPosition(dammam).y}
                    >
                      <animate attributeName="stroke-dasharray" values="0,40;20,20;40,0" dur="4s" repeatCount="indefinite"/>
                    </line>
                  )}
                  {dammam && khobar && (
                    <line 
                      x1={getFacilityPosition(dammam).x} y1={getFacilityPosition(dammam).y}
                      x2={getFacilityPosition(khobar).x} y2={getFacilityPosition(khobar).y}
                    >
                      <animate attributeName="stroke-dasharray" values="0,40;20,20;40,0" dur="3s" repeatCount="indefinite"/>
                    </line>
                  )}
                </>
              );
            })()}
          </g>
          
          {/* Data Flow Streams from Riyadh Hub to all cities */}
          <g fill="hsl(195, 100%, 90%)" opacity="1">
            {(() => {
              const riyadh = facilities.find(f => f.location === "Riyadh");
              if (!riyadh) return null;
              
              const riyadhPos = getFacilityPosition(riyadh);
              
              return facilities
                .filter(f => f.location !== "Riyadh")
                .map((facility, index) => {
                  const facilityPos = getFacilityPosition(facility);
                  return (
                    <g key={facility.id}>
                      {/* Data packet flowing from Riyadh to facility */}
                      <circle r="1.5" fill="hsl(120, 100%, 70%)">
                        <animateMotion dur={`${3 + index * 0.4}s`} repeatCount="indefinite">
                          <path d={`M${riyadhPos.x},${riyadhPos.y} L${facilityPos.x},${facilityPos.y}`}/>
                        </animateMotion>
                      </circle>
                      
                      {/* Return data packet flowing from facility to Riyadh */}
                      <circle r="1" fill="hsl(180, 100%, 80%)">
                        <animateMotion dur={`${3.5 + index * 0.4}s`} repeatCount="indefinite" begin={`${index * 0.5}s`}>
                          <path d={`M${facilityPos.x},${facilityPos.y} L${riyadhPos.x},${riyadhPos.y}`}/>
                        </animateMotion>
                      </circle>
                    </g>
                  );
                });
            })()}
          </g>
          
          {/* Network Performance Indicators */}
          <g opacity="0.8">
            {/* Bandwidth Usage */}
            <rect x="5" y="65" width="20" height="3" fill="hsl(180, 100%, 20%)" stroke="hsl(180, 100%, 60%)"/>
            <rect x="5" y="65" width={15 + Math.sin(animationFrame * 0.1) * 3} height="3" fill="hsl(120, 100%, 50%)"/>
            <text x="5" y="62" fill="hsl(180, 100%, 80%)" fontSize="2">BW</text>
            
            {/* Latency Indicator */}
            <rect x="95" y="65" width="20" height="3" fill="hsl(180, 100%, 20%)" stroke="hsl(180, 100%, 60%)"/>
            <rect x="95" y="65" width={8 + Math.cos(animationFrame * 0.08) * 2} height="3" fill="hsl(60, 100%, 50%)"/>
            <text x="95" y="62" fill="hsl(180, 100%, 80%)" fontSize="2">LAT</text>
          </g>
        </svg>
      </div>
      
      {/* Facility Tooltip */}
      {hoveredFacility && (
        <div className="absolute z-50 pointer-events-none">
          <div 
            className="bg-slate-900 border border-cyan-400 rounded-lg px-3 py-2 text-xs text-cyan-100 whitespace-nowrap cyber-glow"
            style={{
              left: `${((getFacilityPosition(hoveredFacility).x / 120) * 100) + 5}%`,
              top: `${((getFacilityPosition(hoveredFacility).y / 80) * 100) - 15}%`,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div className="font-semibold">{hoveredFacility.name}</div>
            <div className="text-cyan-400">{hoveredFacility.location}</div>
            <div className="flex justify-between gap-4 mt-1">
              <span>Status: <span className="text-green-400">{hoveredFacility.status}</span></span>
              <span>Efficiency: <span className="text-blue-400">{hoveredFacility.efficiency}%</span></span>
            </div>
            <div className="text-gray-400">Production: {hoveredFacility.dailyProduction.toLocaleString()} m³/day</div>
          </div>
        </div>
      )}
    </div>
  );
}