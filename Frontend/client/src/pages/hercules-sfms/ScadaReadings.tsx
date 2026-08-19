import React from 'react';
import { useScada } from '../../contexts/ScadaContext';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { Package } from 'lucide-react';

const DataDisplay = ({ label, value, theme, isNull = false }: {
  label: string;
  value: number;
  theme: 'light' | 'dark';
  isNull?: boolean;
}) => (
  <div
    className={
      theme === 'light'
        ? 'flex justify-between items-center py-0.5 px-3 mb-2 rounded-md bg-blue-50 text-[#222] border border-blue-200 shadow'
        : 'flex justify-between items-center py-0.5 px-3 mb-2 rounded-md bg-[#111827] text-cyan-300 border border-cyan-500 shadow-[0_0_10px_#00ffff55]'
    }
  >
    <span className="text-sm">{label}</span>
    <span className={`text-base font-bold ${isNull ? 'text-red-500' : ''}`}>
      {isNull ? 'NULL' : parseFloat(value?.toString() || '0').toFixed(2)}
    </span>
  </div>
);


const ScadaReadings = () => {
  const { scadaData, loading, error } = useScada();
  const { theme } = useTheme();

  return (
    <WaterSystemLayout 
      title="SCADA Readings Dashboard" 
      subtitle="Live SCADA Readings Dashboard"
    >
      <div className="space-y-6">
        {/* Loading and Error States */}
        {loading && (
          <div className={`text-center py-4 ${theme === 'light' ? 'text-blue-600' : 'text-cyan-400'}`}>
            Loading SCADA data...
          </div>
        )}
        
        {error && (
          <div className={`text-center py-4 ${theme === 'light' ? 'text-red-600' : 'text-red-400'}`}>
            Error: {error}
          </div>
        )}
        
        {/* Data Source Info */}
        {/* {scadaData.dataSource && (
          <div className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'} mb-4`}>
            Data Source: {scadaData.dataSource}
            {scadaData.lastUpdated && ` | Last Updated: ${new Date(scadaData.lastUpdated).toLocaleString()}`}
          </div>
        )} */}
        
      <h1
        className={
          theme === 'light'
            ? 'text-2xl font-bold mb-6 text-[#222]'
            : 'text-2xl font-bold mb-6 text-cyan-400'
        }
      >
        SCADA Readings Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Milling Panel */}
        <div
          className={
            theme === 'light'
              ? 'p-6 min-h-[620px] rounded-xl bg-white/20 backdrop-blur-md border border-blue-200/30 shadow-lg flex flex-col hover:shadow-xl transition-all duration-300'
              : 'p-6 min-h-[620px] rounded-xl bg-slate-900/20 backdrop-blur-md border border-cyan-400/30 shadow-[0_0_30px_rgba(0,255,255,0.15)] flex flex-col hover:shadow-[0_0_40px_rgba(0,255,255,0.25)] transition-all duration-300'
          }
        >
          <h2
            className={
              theme === 'light'
                ? 'text-lg font-semibold mb-3 text-slate-800 flex items-center gap-2'
                : 'text-lg font-semibold mb-3 text-cyan-300 flex items-center gap-2'
            }
          >
            <Package className="h-5 w-5" />
            Milling Inputs
          </h2>
          <div className="flex-1">
            {[
              ['Cleaning Scale', 'cleaningScale'],
              ['Total Running Time', 'totalRunningTime'],
              ['Dry Wheat Scale', 'dryWheatScale'],
              ['Total Screening', 'totalScreening'],
              ['Total Flour', 'totalFlour'],
            
              ['Total Bran', 'totalBran'],
              ['TOTAL WHEAT (FLOUR+BRAN)', 'totalWheat'],
              ['Total Pre Cleaning Water (litres)', 'totalPreCleaningWater'],
              ['1ST, 2ND AND 3RD Water Clean Wheat', 'waterCleanWheat'],
              ['TOTAL WATER USED IN LITRES PER SHIFT AND DAY', 'totalWaterUsed'],
            ].map(([label, key]) => (
              <DataDisplay 
                key={key} 
                label={label} 
                value={(scadaData as any)[key] || 0} 
                theme={theme} 
              />
            ))}
          </div>
        </div>

        {/* Packing Panel */}
        <div
          className={
            theme === 'light'
              ? 'p-6 min-h-[620px] rounded-xl bg-white/20 backdrop-blur-md border border-blue-200/30 shadow-lg flex flex-col hover:shadow-xl transition-all duration-300'
              : 'p-6 min-h-[620px] rounded-xl bg-slate-900/20 backdrop-blur-md border border-cyan-400/30 shadow-[0_0_30px_rgba(0,255,255,0.15)] flex flex-col hover:shadow-[0_0_40px_rgba(0,255,255,0.25)] transition-all duration-300'
          }
        >
          <h2
            className={
              theme === 'light'
                ? 'text-lg font-semibold mb-3 text-slate-800 flex items-center gap-2'
                : 'text-lg font-semibold mb-3 text-cyan-300 flex items-center gap-2'
            }
          >
            <Package className="h-5 w-5" />
            Packing Inputs
          </h2>
          <div className="flex-1">
            {[
              ['Packing Output', 'actualPackingOutput'],
              ['Packing Capacity', 'packingStdCapacity'],
              ['Packing Good Output', 'packingGoodOutput'],
              ['Total Packing Output', 'packingTotalOutput'],
              ['Planned Packing Output', 'packingPlannedOutput'],
              ['Packing Net Hours', 'packingNetHours'],
              ['Packing Total Hours', 'packingTotalHours'],
            ].map(([label, key]) => (
              <DataDisplay 
                key={key} 
                label={label} 
                value={(scadaData as any)[key] || 0} 
                theme={theme} 
              />
            ))}
          </div>
        </div>
      </div>
      </div>
    </WaterSystemLayout>
  );
};

export default ScadaReadings;