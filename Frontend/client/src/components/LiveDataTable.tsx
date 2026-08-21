import React, { useEffect, useMemo, useState } from 'react';
import { scadaConfigApi } from '@/lib/api';

interface LiveDataRow {
  timestamp: string;
  rawSignals: {
    [key: string]: number | undefined;
  };
}

interface LiveDataTableProps {
  data: LiveDataRow[];
  theme: 'light' | 'dark';
}

const BOOTSTRAP_COLUMNS = [
  { key: 'WG201', label: 'WG201' },
  { key: 'WG202', label: 'WG202' },
  { key: 'WG101', label: 'WG101' },
  { key: 'WG301', label: 'WG301' },
  { key: 'WG302', label: 'WG302' },
  { key: 'WG501', label: 'WG501' },
  { key: 'WG502', label: 'WG502' },
  { key: 'WG503', label: 'WG503' },
  { key: 'DM101', label: 'DM101' },
  { key: 'DM102', label: 'DM102' },
  { key: 'DM201', label: 'DM201' },
  { key: 'DM202', label: 'DM202' },
  { key: 'DM203', label: 'DM203' },
  { key: 'PL601_TOT', label: 'PL601_TOT' },
  { key: 'PL602_TOT', label: 'PL602_TOT' },
  { key: 'PL603_TOT', label: 'PL603_TOT' },
];

const LiveDataTable: React.FC<LiveDataTableProps> = ({ data, theme }) => {
  const [registryColumns, setRegistryColumns] = useState<{ key: string; label: string }[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    scadaConfigApi
      .getTags()
      .then((tags) => {
        if (cancelled) return;
        const cols = tags
          .filter(
            (t) =>
              t.is_active &&
              !t.tag.includes('DAMAGED') &&
              !t.tag.includes('COUNTER'),
          )
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((t) => ({
            key: t.tag,
            label: t.display_name || t.tag,
          }));
        setRegistryColumns(cols);
      })
      .catch(() => {
        if (!cancelled) setRegistryColumns(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signalColumns = useMemo(
    () => (registryColumns && registryColumns.length > 0 ? registryColumns : BOOTSTRAP_COLUMNS),
    [registryColumns],
  );

  const tableBg = theme === 'light'
    ? 'bg-white border border-blue-200 text-[#222]'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  const tableHeader = theme === 'light'
    ? 'bg-blue-100 text-[#222] border-b border-blue-300'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' ? 'bg-blue-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-blue-100' : 'border-slate-700';

  return (
    <div 
      className={`rounded-lg ${tableBg} shadow ${theme === 'light' ? '' : 'shadow-[0_0_15px_#00ffff44]'}`} 
      style={{ overflowX: 'auto' }}
    >
      <table className="min-w-full text-sm">
        <thead className={tableHeader}>
          <tr>
            <th className="px-3 py-2 text-left whitespace-nowrap">Timestamp</th>
            {signalColumns.map((col) => (
              <th key={col.key} className="px-3 py-2 text-left whitespace-nowrap">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr
              key={`${row.timestamp}-${idx}`}
              className={`${idx % 2 === 0 ? tableRowEven : tableRowOdd} border-b ${borderRow}`}
            >
              <td className="px-3 py-2 whitespace-nowrap">{row.timestamp}</td>
              {signalColumns.map((col) => {
                const value = row.rawSignals?.[col.key];
                return (
                  <td key={col.key} className="px-3 py-2 whitespace-nowrap font-mono">
                    {value === undefined || value === null ? '—' : Number(value).toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LiveDataTable;
