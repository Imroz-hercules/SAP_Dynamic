import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useScada } from '../../contexts/ScadaContext';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { Package } from 'lucide-react';
import { scadaConfigApi, ScadaTag } from '../../lib/api';

interface ReadingRow {
  key: string;
  label: string;
  unit: string;
}

// B7: the row list for each panel comes from the scada_tags registry
// (scadaConfigApi.getTags) instead of a hardcoded array — disabling a tag in
// the registry now removes its row here too, the same as LiveMonitor.tsx.
function tagsToRows(tags: ScadaTag[], categories: string[]): ReadingRow[] {
  return tags
    .filter((t) => t.is_active && t.is_pollable && categories.includes(t.category))
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((t) => ({ key: t.tag, label: t.display_name || t.tag, unit: t.unit || '' }));
}

// Bootstrap rows used only until /api/scada-config/tags responds (same pattern as LiveMonitor.tsx)
const MILLING_ROWS_BOOTSTRAP: ReadingRow[] = [
  { key: 'WG101', label: 'Wheat input - Silo 1', unit: 'TON' },
  { key: 'WG201', label: 'Wheat input - Silo 2', unit: 'TON' },
  { key: 'WG202', label: 'Clean wheat - active scale', unit: 'TON' },
  { key: 'WG301', label: 'Milling screenings', unit: 'TON' },
  { key: 'WG302', label: 'Pre-clean screenings', unit: 'TON' },
  { key: 'WG501', label: 'Bakery flour stream', unit: 'TON' },
  { key: 'WG502', label: 'Cake / IWW flour stream', unit: 'TON' },
  { key: 'WG503', label: 'Bran stream', unit: 'TON' },
  { key: 'DM101', label: 'Water meter 1', unit: 'm3' },
  { key: 'DM102', label: 'Water meter 2', unit: 'm3' },
  { key: 'DM201', label: 'Water meter 3', unit: 'm3' },
  { key: 'DM202', label: 'Water meter 4', unit: 'm3' },
  { key: 'DM203', label: 'Water meter 5', unit: 'm3' },
];

const PACKING_ROWS_BOOTSTRAP: ReadingRow[] = [
  { key: 'PL601_TOT', label: 'Palletizer 1', unit: 'PALLET' },
  { key: 'PL602_TOT', label: 'Palletizer 2', unit: 'PALLET' },
  { key: 'PL603_TOT', label: 'Palletizer 3 - bran', unit: 'PALLET' },
  { key: 'SL606_TOT', label: 'Line 6 - 1 KG', unit: 'PALLET' },
  { key: 'SL607_TOT', label: 'Line 7 - 10 KG', unit: 'PALLET' },
];

// B7: a screen must never show a plausible-looking number for something that
// was never measured. `null`/`undefined` render as an explicit NO DATA state
// instead of being coerced to 0, which would be indistinguishable from a real
// zero reading.
const DataDisplay = ({ label, value, unit, theme, isNull = false }: {
  label: string;
  value: number | null | undefined;
  unit?: string;
  theme: 'light' | 'dark';
  isNull?: boolean;
}) => {
  const showNoData = isNull || value === null || value === undefined || Number.isNaN(value);
  return (
    <div
      className={
        theme === 'light'
          ? 'flex justify-between items-center py-0.5 px-3 mb-2 rounded-md bg-blue-50 text-[#222] border border-blue-200 shadow'
          : 'flex justify-between items-center py-0.5 px-3 mb-2 rounded-md bg-[#111827] text-cyan-300 border border-cyan-500 shadow-[0_0_10px_#00ffff55]'
      }
    >
      <span className="text-sm">{label}</span>
      <span className={`text-base font-bold ${showNoData ? 'text-red-500' : ''}`}>
        {showNoData ? 'NO DATA' : `${value.toFixed(2)}${unit ? ` ${unit}` : ''}`}
      </span>
    </div>
  );
};


const ScadaReadings = () => {
  const { scadaData, loading, error } = useScada();
  const { theme } = useTheme();

  // B7: tag list from the scada_tags registry
  const { data: registryTags } = useQuery({
    queryKey: ['/api/scada-config/tags'],
    queryFn: () => scadaConfigApi.getTags(),
    staleTime: 30_000,
  });

  const millingRows = useMemo(
    () => (registryTags?.length ? tagsToRows(registryTags, ['INPUT', 'MILLING', 'WATER']) : MILLING_ROWS_BOOTSTRAP),
    [registryTags],
  );
  const packingRows = useMemo(
    () => (registryTags?.length ? tagsToRows(registryTags, ['PACKING']) : PACKING_ROWS_BOOTSTRAP),
    [registryTags],
  );

  // `scadaData` starts out at hardcoded zeros (see ScadaContext.tsx
  // defaultScadaData) before the first successful fetch ever completes, so a
  // bare 0 cannot be trusted to mean "measured zero" — it just as often means
  // "nothing has arrived yet". `lastUpdated` is only set once a fetch has
  // actually succeeded, so gate every reading on that instead of guessing.
  const hasRealData = Boolean(scadaData.lastUpdated) && !error;

  // Rows backed 1:1 by a single registry tag - read straight off the raw
  // signal map the readings endpoint already returns.
  const rawValue = (key: string): number | null =>
    hasRealData && scadaData.rawSignals && key in scadaData.rawSignals
      ? scadaData.rawSignals[key]
      : null;

  // A handful of fields are server-side aggregates across more than one tag
  // (e.g. totalWaterUsed sums all five water meters, totalWheat sums the three
  // milling streams) - there is no single registry tag that can back them, so
  // they stay sourced from the ScadaContext response directly, gated the same
  // honest way as the raw rows above.
  const computedValue = (key: keyof typeof scadaData): number | null => {
    const v = (scadaData as any)[key];
    return hasRealData && typeof v === 'number' && !Number.isNaN(v) ? v : null;
  };

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
            {millingRows.map((row) => (
              <DataDisplay
                key={row.key}
                label={row.label}
                value={rawValue(row.key)}
                unit={row.unit}
                theme={theme}
              />
            ))}
            {/* Server-side aggregates across more than one tag - see computedValue() above */}
            <DataDisplay label="TOTAL WHEAT (FLOUR+BRAN)" value={computedValue('totalWheat')} unit="TON" theme={theme} />
            <DataDisplay label="Total Pre Cleaning Water" value={computedValue('totalPreCleaningWater')} unit="L" theme={theme} />
            <DataDisplay label="1ST, 2ND AND 3RD Water Clean Wheat" value={computedValue('waterCleanWheat')} unit="L" theme={theme} />
            <DataDisplay label="TOTAL WATER USED PER SHIFT AND DAY" value={computedValue('totalWaterUsed')} unit="L" theme={theme} />
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
            {packingRows.map((row) => (
              <DataDisplay
                key={row.key}
                label={row.label}
                value={rawValue(row.key)}
                unit={row.unit}
                theme={theme}
              />
            ))}
            {/* No registry tag reports hours directly - kept as a server-side field, gated the same way */}
            <DataDisplay label="Packing Net Hours" value={computedValue('packingNetHours')} unit="hrs" theme={theme} />
            <DataDisplay label="Packing Total Hours" value={computedValue('packingTotalHours')} unit="hrs" theme={theme} />
          </div>
        </div>
      </div>
      </div>
    </WaterSystemLayout>
  );
};

export default ScadaReadings;