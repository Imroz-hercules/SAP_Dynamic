import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { RefreshCw } from 'lucide-react';

interface SyncButtonProps {
  onClick: () => void;
  isLoading?: boolean;
}

const SyncButton: React.FC<SyncButtonProps> = ({ onClick, isLoading = false }) => {
  const { theme } = useTheme();

  return (
    <>
      <style>{`
        /* Force white text for sync button in light mode */
        .sync-button-light {
          color: white !important;
        }
        
        .sync-button-light span {
          color: white !important;
        }
        
        .sync-button-light svg {
          color: white !important;
        }
      `}</style>
      <button
        onClick={onClick}
        disabled={isLoading}
        className={`relative group flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 !text-white sync-button-light disabled:opacity-50 disabled:hover:scale-100 ${
          theme === 'light'
            ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
            : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
        }`}
        style={{
          color: 'white !important'
        }}
        title="Manual Sync Orders"
      >
        <RefreshCw size={16} className={`transition-all duration-300 group-hover:rotate-180 !text-white sync-button-light ${isLoading ? 'animate-spin' : ''}`} style={{ color: 'white !important' }} />
        <span className="font-semibold tracking-wide !text-white sync-button-light" style={{ color: 'white !important' }}>{isLoading ? 'Syncing...' : 'Sync'}</span>
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </button>
    </>
  );
};

export default SyncButton;