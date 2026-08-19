import React from 'react';
import { X, GripVertical } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

interface ChartCardProps {
  id: string;
  title: string;
  children: React.ReactNode;
  onRemove: (id: string) => void;
  className?: string;
  isDragging?: boolean;
}

const ChartCard: React.FC<ChartCardProps> = ({
  id,
  title,
  children,
  onRemove,
  className = '',
  isDragging = false
}) => {
  const { theme } = useTheme();

  return (
    <div
      className={`relative group h-full w-full transition-all duration-300 ${
        isDragging ? 'z-50 scale-105 rotate-2' : 'hover:scale-[1.02]'
      } ${className}`}
    >
      {/* Main Card Container */}
      <div
        className={`h-full rounded-xl backdrop-blur-md border transition-all duration-500 shadow-lg hover:shadow-xl ${
          theme === 'light' 
            ? 'bg-white/20 border-slate-400/80 hover:border-slate-500/90 hover:bg-white/30' 
            : 'bg-slate-900/20 border-cyan-400/30 hover:border-cyan-400/50 shadow-[0_0_30px_rgba(0,255,255,0.1)] hover:shadow-[0_0_40px_rgba(0,255,255,0.2)]'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-2 pb-1">
          <div className="flex items-center gap-1">
            {/* Drag Handle */}
            <div className={`drag-handle p-0.5 rounded-md cursor-grab active:cursor-grabbing transition-colors ${
              theme === 'light' 
                ? 'hover:bg-slate-200/50' 
                : 'hover:bg-slate-700/50'
            }`}>
              <GripVertical 
                className={`w-3 h-3 ${
                  theme === 'light' ? 'text-slate-600' : 'text-slate-400'
                }`} 
              />
            </div>
            
            <h3 className={`text-sm font-bold tracking-wide truncate ${
              theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
            }`}>
              {title}
            </h3>
          </div>
          
          {/* Remove Button */}
          <button
            onClick={() => onRemove(id)}
            className={`p-1 rounded-md transition-all duration-200 hover:scale-110 ${
              theme === 'light' 
                ? 'hover:bg-red-100 text-slate-500 hover:text-red-600' 
                : 'hover:bg-red-900/30 text-slate-400 hover:text-red-400'
            }`}
            title="Remove chart"
          >
            <X className="w-3 h-3" />
          </button>
        </div>

        {/* Chart Content */}
        <div className="p-2 pt-1 h-[calc(100%-50px)] overflow-hidden min-h-[100px]">
          <div className="h-full w-full">
            {children}
          </div>
        </div>

        {/* Animated glow effect */}
        <div 
          className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none"
          style={{
            background: theme === 'light' 
              ? 'radial-gradient(circle at center, rgba(59, 130, 246, 0.3), transparent 70%)'
              : 'radial-gradient(circle at center, rgba(0, 255, 255, 0.3), transparent 70%)'
          }}
        />
        
        {/* Pulse animation ring */}
        <div 
          className="absolute -inset-1 rounded-xl opacity-0 group-hover:opacity-50 transition-opacity duration-500 pointer-events-none animate-pulse"
          style={{
            background: theme === 'light' 
              ? 'linear-gradient(45deg, rgba(59, 130, 246, 0.2), transparent, rgba(59, 130, 246, 0.2))'
              : 'linear-gradient(45deg, rgba(0, 255, 255, 0.2), transparent, rgba(0, 255, 255, 0.2))'
          }}
        />
      </div>
      
      {/* Floating particles effect for dark mode */}
      {theme === 'dark' && (
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 rounded-full animate-ping"
              style={{
                backgroundColor: '#00ffff',
                left: `${20 + i * 30}%`,
                top: `${25 + (i % 2) * 30}%`,
                animationDelay: `${i * 0.4}s`,
                animationDuration: '2s'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ChartCard;
