import { Facility } from "@shared/schema";
import { getStatusColor } from "@/lib/mockData";
import { useState } from "react";

interface WorldMapProps {
  facilities: Facility[];
  onFacilityClick?: (facility: Facility) => void;
}

export function WorldMap({ facilities, onFacilityClick }: WorldMapProps) {
  const [hoveredFacility, setHoveredFacility] = useState<Facility | null>(null);

  const getFacilityPosition = (facility: Facility) => {
    // Convert lat/lng to percentage positions for India map
    // Rough approximation for Indian subcontinent
    const indiaLatRange = [8, 37]; // Min/Max latitude for India
    const indiaLngRange = [68, 97]; // Min/Max longitude for India
    
    const latPercent = ((facility.latitude - indiaLatRange[0]) / (indiaLatRange[1] - indiaLatRange[0])) * 100;
    const lngPercent = ((facility.longitude - indiaLngRange[0]) / (indiaLngRange[1] - indiaLngRange[0])) * 100;
    
    return {
      top: `${100 - latPercent}%`, // Invert because CSS top increases downward
      left: `${lngPercent}%`,
    };
  };

  return (
    <div className="col-span-5 row-span-3 holographic rounded-lg p-4 relative overflow-hidden">
      <div className="text-sm text-[hsl(180,100%,50%)] mb-2 text-glow font-mono">
        GLOBAL FACILITY NETWORK
      </div>
      
      {/* Background Industrial Image */}
      <div className="absolute inset-4 w-full h-5/6 bg-gradient-to-br from-[hsl(240,25%,6%)] to-[hsl(240,36%,12%)] rounded opacity-40" />
      
      {/* India Outline SVG */}
      <div className="absolute inset-4 w-full h-5/6">
        <svg 
          viewBox="0 0 100 100" 
          className="w-full h-full opacity-30"
          style={{ filter: 'drop-shadow(0 0 10px hsl(180, 100%, 50%))' }}
        >
          {/* Simplified India outline */}
          <path 
            d="M20,20 L25,15 L35,18 L45,15 L55,20 L65,25 L70,35 L75,45 L70,55 L65,65 L60,75 L50,80 L40,85 L30,80 L25,70 L20,60 L15,50 L18,40 L20,30 Z" 
            fill="none" 
            stroke="hsl(180, 100%, 50%)" 
            strokeWidth="0.5"
            className="animate-glow-pulse"
          />
        </svg>
      </div>
      
      {/* Facility Markers */}
      <div className="absolute inset-4 w-full h-5/6">
        {facilities.map((facility) => {
          const position = getFacilityPosition(facility);
          const statusColor = getStatusColor(facility.status);
          
          return (
            <div
              key={facility.id}
              className="facility-marker absolute w-5 h-5 rounded-full cursor-pointer transition-all duration-300"
              style={{
                ...position,
                backgroundColor: statusColor,
                boxShadow: `0 0 20px ${statusColor}`,
                transform: hoveredFacility?.id === facility.id ? 'scale(1.5)' : 'scale(1)',
                zIndex: hoveredFacility?.id === facility.id ? 10 : 1,
              }}
              onClick={() => onFacilityClick?.(facility)}
              onMouseEnter={() => setHoveredFacility(facility)}
              onMouseLeave={() => setHoveredFacility(null)}
            >
              {/* Pulsing ring effect */}
              <div 
                className="absolute inset-0 rounded-full animate-ping opacity-75"
                style={{ backgroundColor: statusColor }}
              />
              
              {/* Tooltip */}
              {hoveredFacility?.id === facility.id && (
                <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 bg-[hsl(240,25%,6%)] border border-[hsl(180,100%,50%)] rounded px-2 py-1 text-xs whitespace-nowrap z-20 pointer-events-none">
                  <div className="text-[hsl(180,100%,50%)] font-mono">{facility.location.toUpperCase()}</div>
                  <div className="text-white">{facility.dailyProduction.toLocaleString()} m³/day</div>
                  <div style={{ color: statusColor }}>{facility.efficiency}% efficiency</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Data Flow Lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        {/* Connection lines between facilities */}
        <line 
          x1="20%" y1="20%" x2="80%" y2="80%" 
          stroke="hsl(180, 100%, 50%)" 
          strokeWidth="1" 
          opacity="0.6" 
          filter="url(#glow)"
        >
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/>
        </line>
        <line 
          x1="80%" y1="20%" x2="20%" y2="80%" 
          stroke="hsl(20, 100%, 50%)" 
          strokeWidth="1" 
          opacity="0.4" 
          filter="url(#glow)"
        >
          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite"/>
        </line>
      </svg>
    </div>
  );
}
