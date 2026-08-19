import { useState, useEffect, useCallback } from 'react';
import type { TimeFilterProps } from '@/components/TimeFilter';

export interface HistoricalDataFilters {
  mode: 'single' | 'range';
  date?: string;
  startDate?: string;
  endDate?: string;
  shifts: string[];
  timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
}

export interface HistoricalDataState {
  filters: HistoricalDataFilters | null;
  isHistoricalMode: boolean;
  periodLabel: string;
}

/**
 * Custom hook for managing historical data filtering
 * Supports time period selection and mock data switching
 * 
 * @param defaultMode - Default mode: 'live' or 'historical'
 * @returns Historical data state and control functions
 */
export function useHistoricalData(defaultMode: 'live' | 'historical' = 'live') {
  const [mode, setMode] = useState<'live' | 'historical'>(defaultMode);
  const [filters, setFilters] = useState<HistoricalDataFilters | null>(null);

  // Generate period label for display
  const getPeriodLabel = useCallback((filters: HistoricalDataFilters | null): string => {
    if (!filters) return 'Live Data';

    const timeRangeLabel = filters.timeRange 
      ? filters.timeRange.charAt(0).toUpperCase() + filters.timeRange.slice(1) 
      : '';
    const shifts = filters.shifts.length > 0 ? filters.shifts.join(', ') : 'All';

    if (filters.mode === 'single' && filters.date) {
      const date = new Date(filters.date);
      const dateStr = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      return timeRangeLabel 
        ? `${dateStr} - ${timeRangeLabel} - Shift ${shifts}`
        : `${dateStr} - Shift ${shifts}`;
    }

    if (filters.mode === 'range' && filters.startDate && filters.endDate) {
      const start = new Date(filters.startDate);
      const end = new Date(filters.endDate);
      const rangeStr = `${start.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })} - ${end.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}`;
      return timeRangeLabel
        ? `${rangeStr} - ${timeRangeLabel} - Shift ${shifts}`
        : `${rangeStr} - Shift ${shifts}`;
    }

    return 'Live Data';
  }, []);

  // Handle filter application
  const handleApplyFilters = useCallback((newFilters: {
    mode: 'single' | 'range';
    date?: string;
    startDate?: string;
    endDate?: string;
    shifts?: string[];
    timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
  }) => {
    setFilters({
      ...newFilters,
      shifts: newFilters.shifts || [],
    });
    setMode('historical');
  }, []);

  // Reset to live mode
  const resetToLive = useCallback(() => {
    setFilters(null);
    setMode('live');
  }, []);

  // Check if we're in historical mode
  const isHistoricalMode = mode === 'historical' && filters !== null;

  // Get period label
  const periodLabel = getPeriodLabel(filters);

  return {
    filters,
    isHistoricalMode,
    periodLabel,
    mode,
    handleApplyFilters,
    resetToLive,
    setMode,
  };
}

/**
 * Mock data generator for historical periods
 * This will be replaced with actual API calls later
 */
export function generateMockHistoricalData(
  filters: HistoricalDataFilters | null,
  baseData: any
): any {
  if (!filters) {
    return baseData; // Return live data if no filters
  }

  // Generate mock historical data based on filters
  // This is a placeholder - actual implementation will fetch from API
  const mockMultiplier = 0.85 + Math.random() * 0.3; // Random variation between 85% and 115%

  if (baseData && typeof baseData === 'object') {
    const historicalData = { ...baseData };
    
    // Apply mock variations to numeric values
    Object.keys(historicalData).forEach(key => {
      if (typeof historicalData[key] === 'number') {
        historicalData[key] = historicalData[key] * mockMultiplier;
      } else if (typeof historicalData[key] === 'object' && historicalData[key] !== null) {
        historicalData[key] = generateMockHistoricalData(filters, historicalData[key]);
      }
    });

    return historicalData;
  }

  return baseData;
}

