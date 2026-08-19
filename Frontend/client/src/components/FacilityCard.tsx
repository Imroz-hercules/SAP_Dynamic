import { Facility } from "@shared/schema";
import { getStatusColor } from "@/lib/mockData";
import { calculateCircularProgress } from "@/lib/chartUtils";

interface FacilityCardProps {
  facility: Facility;
  onClick?: () => void;
}

export function FacilityCard({ facility, onClick }: FacilityCardProps) {
  const statusColor = getStatusColor(facility.status);
  const { circumference, offset } = calculateCircularProgress(facility.efficiency);

  return (
    <div 
      className="cyberpunk-card rounded-md p-2 relative group hover:scale-102 transition-all duration-200 cursor-pointer h-16 flex items-center"
      onClick={onClick}
    >
      {/* Status Indicator */}
      <div 
        className="w-3 h-3 rounded-full status-indicator mr-2 flex-shrink-0"
        style={{ backgroundColor: statusColor }}
      />
      
      <div className="flex-1 min-w-0">
        {/* Location Label */}
        <div className="text-xs text-[hsl(180,100%,50%)] text-glow font-mono truncate">
          {facility.location.replace(' Water Treatment Plant', '').toUpperCase()}
        </div>
        
        {/* Metrics Row */}
        <div className="flex items-center justify-between mt-1">
          <div className="text-xs font-mono text-white">
            {(facility.dailyProduction / 1000).toFixed(1)}K m³
          </div>
          <div 
            className="text-xs font-bold text-glow"
            style={{ color: statusColor }}
          >
            {facility.efficiency}%
          </div>
        </div>
      </div>
      
      {/* Mini Progress Bar */}
      <div className="w-1 h-12 bg-gray-700 rounded-full overflow-hidden ml-2 flex-shrink-0">
        <div 
          className="w-full rounded-full animate-glow-pulse transition-all duration-1000"
          style={{ 
            height: `${facility.efficiency}%`,
            backgroundColor: statusColor,
            boxShadow: `0 0 6px ${statusColor}`,
          }}
        />
      </div>
      
      {/* Compact Data Flow Animation */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-md">
        <div className="w-px h-full bg-gradient-to-b from-transparent via-[hsl(180,100%,50%)] to-transparent opacity-30 absolute left-1 animate-data-flow" />
      </div>
    </div>
  );
}
