import { Facility } from "@shared/schema";
import { ProductionCharts } from "./ProductionCharts";

interface NetworkTopologyProps {
  facilities: Facility[];
  onFacilityClick?: (facility: Facility) => void;
}

export function NetworkTopology({ facilities, onFacilityClick }: NetworkTopologyProps) {
  // Expanded coordinate mapping for better space utilization
  const getFacilityPosition = (facility: Facility) => {
    const positions: Record<string, { x: number; y: number }> = {
      "Riyadh": { x: 50, y: 50 }, // Center hub
      "Jeddah": { x: 20, y: 60 }, // West coast 
      "Mecca": { x: 18, y: 70 }, // Southwest of Jeddah
      "Medina": { x: 25, y: 35 }, // Northwest of Riyadh
      "Dammam": { x: 85, y: 52 }, // East coast
      "Al-Khobar": { x: 88, y: 62 }, // Southeast coast
      "Jubail": { x: 82, y: 38 }, // Northeast coast
      "Tabuk": { x: 15, y: 20 }, // Northwest
      "Ha'il": { x: 35, y: 25 }, // North-central
      "Abha": { x: 35, y: 80 }, // South
    };
    return positions[facility.location] || { x: 50, y: 50 };
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "operational": return "#00ff88";
      case "warning": return "#ffaa00";
      case "offline": return "#ff4444";
      default: return "#00ccff";
    }
  };

  const riyadh = facilities.find(f => f.location === "Riyadh");
  const riyadhPos = riyadh ? getFacilityPosition(riyadh) : { x: 50, y: 50 };

  return (
    <div className="relative w-full h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl overflow-hidden">
      {/* Header - Centered */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20 text-center">
        <h3 className="text-cyan-400 text-lg font-semibold tracking-wide">
          Live Network Monitoring
        </h3>
        <p className="text-slate-400 text-sm">Saudi Arabia Water Facilities</p>
      </div>

      {/* Legend - Bottom Center */}
      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 bg-slate-900/95 backdrop-blur-sm rounded-md px-3 py-2 border border-cyan-500/40 shadow-md">
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span className="text-green-300">Operational</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-amber-400 rounded-full"></div>
            <span className="text-amber-300">Warning</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-red-400 rounded-full"></div>
            <span className="text-red-300">Offline</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-yellow-400 rounded-full border border-yellow-500"></div>
            <span className="text-yellow-300">Hub</span>
          </div>
        </div>
      </div>

      {/* SVG Network Visualization */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
        {/* Background Grid */}
        <defs>
          <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(148, 163, 184, 0.1)" strokeWidth="0.5"/>
          </pattern>
          
          {/* Glow Filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Red Glow Filter for Offline Nodes */}
          <filter id="redGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feFlood floodColor="#ff4444" floodOpacity="0.9"/>
            <feComposite in2="coloredBlur" operator="in"/>
            <feMerge> 
              <feMergeNode/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Arrow Marker */}
          <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                  refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#00ccff" opacity="0.8" />
          </marker>
        </defs>

        {/* Grid Background */}
        <rect width="100" height="100" fill="url(#grid)" />

        {/* Connection Lines from Riyadh Hub */}
        {facilities
          .filter(f => f.location !== "Riyadh")
          .map((facility, index) => {
            const pos = getFacilityPosition(facility);
            return (
              <line
                key={facility.id}
                x1={riyadhPos.x}
                y1={riyadhPos.y}
                x2={pos.x}
                y2={pos.y}
                stroke="#00ccff"
                strokeWidth="0.6"
                opacity="0.7"

                className="animate-pulse"
                style={{
                  animationDelay: `${index * 0.2}s`,
                  animationDuration: '3s'
                }}
              />
            );
          })}

        {/* Hub Ring around Riyadh */}
        <circle
          cx={riyadhPos.x}
          cy={riyadhPos.y}
          r="12"
          fill="none"
          stroke="#fbbf24"
          strokeWidth="0.8"
          strokeDasharray="3,1.5"
          opacity="0.8"
        >
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="rotate"
            from={`0 ${riyadhPos.x} ${riyadhPos.y}`}
            to={`360 ${riyadhPos.x} ${riyadhPos.y}`}
            dur="20s"
            repeatCount="indefinite"
          />
        </circle>

        {/* Facility Nodes */}
        {facilities.map((facility, index) => {
          const pos = getFacilityPosition(facility);
          const isHub = facility.location === "Riyadh";
          
          return (
            <g key={facility.id}>
              {/* Node Circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isHub ? "4.5" : "3"}
                fill={getStatusColor(facility.status)}
                stroke="white"
                strokeWidth="0.5"
                opacity="0.9"
                filter={facility.status === "offline" ? "url(#redGlow)" : "url(#glow)"}
                className="cursor-pointer hover:opacity-100 transition-opacity"
                onClick={() => onFacilityClick?.(facility)}
              >
                <animate
                  attributeName="r"
                  values={isHub ? "4.5;5.5;4.5" : "3;3.5;3"}
                  dur="2s"
                  repeatCount="indefinite"
                />
              </circle>

              {/* City Label */}
              <text
                x={pos.x}
                y={pos.y - 6}
                textAnchor="middle"
                fontSize="3.5"
                fontWeight="700"
                fill="white"
                className="cursor-pointer font-mono"
                style={{
                  textShadow: '0 0 6px rgba(0,0,0,0.9)',
                  filter: 'drop-shadow(0 0 3px #00ccff)'
                }}
                onClick={() => onFacilityClick?.(facility)}
              >
                {facility.location}
              </text>


            </g>
          );
        })}

        {/* Data Flow Particles - Smart Routing Based on Facility Status */}
        {facilities
          .filter(f => f.location !== "Riyadh")
          .map((facility, index) => {
            const pos = getFacilityPosition(facility);
            
            // Smart packet routing - only send relevant packets to each facility
            const getPacketsForFacility = (facilityStatus: string) => {
              switch (facilityStatus) {
                case "operational":
                  return [{ color: "#00ff88", delay: 0, type: "routine" }]; // Green nodes get green packets
                case "warning": 
                  return [{ color: "#ffaa00", delay: 0, type: "diagnostic" }]; // Orange nodes get orange packets
                case "offline":
                  return [{ color: "#ff4444", delay: 0, type: "emergency" }]; // Red nodes get red packets
                default:
                  return [{ color: "#00ccff", delay: 0, type: "status" }]; // Default blue
              }
            };

            const packets = getPacketsForFacility(facility.status);
            
            return packets.map((packet, packetIndex) => (
              <circle
                key={`packet-${facility.id}-${packetIndex}`}
                r="0.6"
                fill={packet.color}
                opacity="0.8"
                filter="url(#glow)"
              >
                <animateMotion
                  dur={`${6 + (index * 0.8)}s`} // Slower, more realistic timing
                  repeatCount="indefinite"
                  path={`M${riyadhPos.x},${riyadhPos.y} L${pos.x},${pos.y}`}
                  begin={`${index * 2 + packet.delay}s`} // More spaced out timing
                />
                <animate
                  attributeName="opacity"
                  values="0.2;0.8;0.2"
                  dur="4s"
                  repeatCount="indefinite"
                />
              </circle>
            ));
          }).flat()}

        {/* Reverse Data Flow - Cities to Riyadh (Status Reports) */}
        {facilities
          .filter(f => f.location !== "Riyadh")
          .map((facility, index) => {
            const pos = getFacilityPosition(facility);
            
            // Status report packets - matching facility status color
            const getStatusPacketColor = (facilityStatus: string) => {
              switch (facilityStatus) {
                case "operational": return "#00ff88"; // Same green as outbound
                case "warning": return "#ffaa00";     // Same orange as outbound
                case "offline": return "#ff4444";     // Same red as outbound
                default: return "#00ccff";            // Same blue as outbound
              }
            };

            return (
              <circle
                key={`status-${facility.id}`}
                r="0.4"
                fill={getStatusPacketColor(facility.status)}
                opacity="0.6"
                filter="url(#glow)"
              >
                <animateMotion
                  dur={`${8 + (index * 0.5)}s`} // Much slower return packets
                  repeatCount="indefinite"
                  path={`M${pos.x},${pos.y} L${riyadhPos.x},${riyadhPos.y}`}
                  begin={`${index * 3 + 4}s`} // More spaced out, delayed start
                />
                <animate
                  attributeName="opacity"
                  values="0.1;0.6;0.1"
                  dur="5s"
                  repeatCount="indefinite"
                />
              </circle>
            );
          })}
      </svg>

      {/* Compact Network Status Indicator - Center */}
      <div className="absolute top-20 right-6 z-20 bg-slate-900/90 backdrop-blur-sm rounded-lg p-2 border border-emerald-500/30 w-32">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-emerald-400 text-xs font-semibold">Network</span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-xs">Latency</span>
              <span className="text-emerald-400 text-xs font-mono">12ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-xs">Uptime</span>
              <span className="text-cyan-400 text-xs font-mono">99.9%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-xs">Sync</span>
              <span className="text-blue-400 text-xs font-mono">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Production Charts Integration */}
      <ProductionCharts />
    </div>
  );
}