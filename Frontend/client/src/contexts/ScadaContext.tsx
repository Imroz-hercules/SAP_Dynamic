import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch, getApiUrl } from '../lib/apiConfig';

interface ScadaData {
  // Milling inputs - Real SCADA data from ASMReporting_5
  cleaningScale: number;
  totalRunningTime: number;
  dryWheatScale: number;
  totalScreening: number;
  totalFlour: number;
  flour: number;
  totalBran: number;
  totalWheat: number;
  totalPreCleaningWater: number;
  waterCleanWheat: number;
  totalWaterUsed: number;
  
  // Packing inputs
  actualPackingOutput: number;
  packingStdCapacity: number;
  packingGoodOutput: number;
  packingTotalOutput: number;
  packingPlannedOutput: number;
  packingNetHours: number;
  packingTotalHours: number;
  
  // Live monitoring data
  scale: number;
  waterDosing: number;
  equipmentStatus: string;
  
  // Metadata
  lastUpdated?: string;
  dataSource?: string;
  rawSignals?: Record<string, number>;
}

interface ScadaContextType {
  scadaData: ScadaData;
  updateScadaData: (data: Partial<ScadaData>) => void;
  loading: boolean;
  error: string | null;
}

const defaultScadaData: ScadaData = {
  // Milling inputs - Real SCADA data from ASMReporting_5
  cleaningScale: 0,
  totalRunningTime: 0,
  dryWheatScale: 0,
  totalScreening: 0,
  totalFlour: 0,
  flour: 0,
  totalBran: 0,
  totalWheat: 0,
  totalPreCleaningWater: 0,
  waterCleanWheat: 0,
  totalWaterUsed: 0,
  
  // Packing inputs - Real SCADA data from ASMReporting_5
  actualPackingOutput: 0,
  packingStdCapacity: 0,
  packingGoodOutput: 0,
  packingTotalOutput: 0,
  packingPlannedOutput: 0,
  packingNetHours: 0,
  packingTotalHours: 0,
  
  // Live monitoring data
  scale: 0,
  waterDosing: 0,
  equipmentStatus: 'Running',
};

const ScadaContext = createContext<ScadaContextType | undefined>(undefined);

export function ScadaProvider({ children }: { children: React.ReactNode }) {
  const [scadaData, setScadaData] = useState<ScadaData>(defaultScadaData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch real SCADA data from API
  const fetchScadaData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiFetch(getApiUrl('/api/scada/readings'));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update SCADA data with real values from database
      setScadaData(prev => ({
        ...prev,
        // Milling inputs from real SCADA data
        cleaningScale: data.cleaningScale || 0,
        totalRunningTime: data.totalRunningTime || 0,
        dryWheatScale: data.dryWheatScale || 0,
        totalScreening: data.totalScreening || 0,
        totalFlour: data.totalFlour || 0,
        flour: data.flour || 0,
        totalBran: data.totalBran || 0,
        totalWheat: data.totalWheat || 0,
        totalPreCleaningWater: data.totalPreCleaningWater || 0,
        waterCleanWheat: data.waterCleanWheat || 0,
        totalWaterUsed: data.totalWaterUsed || 0,
        
        // Packing inputs from real SCADA data
        actualPackingOutput: data.actualPackingOutput || 0,
        packingStdCapacity: data.packingStdCapacity || 0,
        packingGoodOutput: data.packingGoodOutput || 0,
        packingTotalOutput: data.packingTotalOutput || 0,
        packingPlannedOutput: data.packingPlannedOutput || 0,
        packingNetHours: data.packingNetHours || 0,
        packingTotalHours: data.packingTotalHours || 0,
        
        // Metadata
        lastUpdated: data.lastUpdated,
        dataSource: data.dataSource,
        rawSignals: data.rawSignals,
        
        // Update live monitoring data
        scale: data.rawSignals?.WG101 || 0, // Use WG101 (Dry Wheat Scale) for scale reading
        waterDosing: (data.rawSignals?.DM101 || 0) + (data.rawSignals?.DM102 || 0), // Use DM101 + DM102 for waterDosing
        equipmentStatus: 'Running',
      }));
      
    } catch (err) {
      console.error('Error fetching SCADA data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch SCADA data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch data on component mount and set up polling
  useEffect(() => {
    fetchScadaData(); // Initial fetch
    
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchScadaData, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const updateScadaData = (data: Partial<ScadaData>) => {
    setScadaData(prev => ({ ...prev, ...data }));
  };

  return (
    <ScadaContext.Provider value={{ scadaData, updateScadaData, loading, error }}>
      {children}
    </ScadaContext.Provider>
  );
}

export function useScada() {
  const context = useContext(ScadaContext);
  if (context === undefined) {
    throw new Error('useScada must be used within a ScadaProvider');
  }
  return context;
}