import { useState } from "react";
import { useLocation } from "wouter";

interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  facilityId?: number;
}

const mainNavItems: NavItem[] = [
  { id: "dashboard", label: "Main Dashboard", icon: "🏢", path: "/" },
];

const facilityNavItems: NavItem[] = [
  { id: "overview", label: "Facility Overview", icon: "📊", path: "/facility/%id/overview" },
  { id: "process", label: "Process Flow", icon: "🔄", path: "/facility/%id/process" },
  { id: "quality", label: "Water Quality", icon: "💧", path: "/facility/%id/quality" },
  { id: "energy", label: "Energy Monitoring", icon: "⚡", path: "/facility/%id/energy" },
  { id: "maintenance", label: "Maintenance", icon: "🔧", path: "/facility/%id/maintenance" },
  { id: "chemical", label: "Chemical Dosing", icon: "⚗️", path: "/facility/%id/chemical" },
];

interface NavigationSidebarProps {
  selectedFacilityId?: number;
  onClose?: () => void;
}

export function NavigationSidebar({ selectedFacilityId, onClose }: NavigationSidebarProps) {
  const [location, setLocation] = useLocation();
  const [isExpanded, setIsExpanded] = useState(true);

  const handleNavigation = (path: string) => {
    const finalPath = selectedFacilityId ? path.replace('%id', selectedFacilityId.toString()) : path;
    setLocation(finalPath);
    if (onClose) onClose();
  };

  return (
    <div className={`fixed left-0 top-0 h-full z-50 transition-all duration-300 ${isExpanded ? 'w-64' : 'w-16'}`}>
      <div className="h-full cyberpunk-card rounded-r-lg p-4 relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 cyber-grid opacity-10" />
        
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          {isExpanded && (
            <div className="text-sm text-[hsl(180,100%,50%)] font-mono text-glow">
              NAVIGATION
            </div>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-[hsl(180,100%,50%)] hover:text-[hsl(180,100%,70%)] transition-colors"
          >
            {isExpanded ? '←' : '→'}
          </button>
        </div>

        {/* Main Navigation */}
        <div className="space-y-2 mb-6">
          {mainNavItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavigation(item.path)}
              className={`w-full p-3 rounded-md text-left transition-all duration-200 group ${
                location === item.path
                  ? 'cyberpunk-card text-[hsl(180,100%,50%)]'
                  : 'hover:bg-black hover:bg-opacity-30 text-gray-300'
              }`}
            >
              <div className="flex items-center space-x-3">
                <span className="text-lg">{item.icon}</span>
                {isExpanded && (
                  <span className="text-sm font-mono group-hover:text-glow">
                    {item.label}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Facility Navigation */}
        {selectedFacilityId && (
          <div className="space-y-2">
            {isExpanded && (
              <div className="text-xs text-[hsl(158,100%,50%)] font-mono text-glow mb-2">
                FACILITY {selectedFacilityId}
              </div>
            )}
            {facilityNavItems.map((item) => {
              const itemPath = item.path.replace('%id', selectedFacilityId.toString());
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigation(item.path)}
                  className={`w-full p-2 rounded-md text-left transition-all duration-200 group ${
                    location === itemPath
                      ? 'cyberpunk-card text-[hsl(180,100%,50%)]'
                      : 'hover:bg-black hover:bg-opacity-30 text-gray-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-sm">{item.icon}</span>
                    {isExpanded && (
                      <span className="text-xs font-mono group-hover:text-glow">
                        {item.label}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Close Button */}
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-[hsl(180,100%,50%)] hover:text-red-500 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}