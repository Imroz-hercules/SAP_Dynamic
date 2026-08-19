import React from 'react';

interface LiveDataRow {
  timestamp: string;
  rawSignals: {
    WG201: number;
    WG202: number;
    WG101: number;
    WG301: number;
    WG302: number;
    WG501: number;
    WG502: number;
    WG503: number;
    DM101: number;
    DM102: number;
    DM201: number;
    DM202: number;
    DM203: number;
    PL601_TOT: number;
    PL602_TOT: number;
    PL603_TOT: number;
    // Add HI/LO columns
    WG101_LO?: number;
    WG101_HI?: number;
    WG201_LO?: number;
    WG201_HI?: number;
    WG202_LO?: number;
    WG202_HI?: number;
    WG301_LO?: number;
    WG301_HI?: number;
    WG302_LO?: number;
    WG302_HI?: number;
    WG501_LO?: number;
    WG501_HI?: number;
    WG502_LO?: number;
    WG502_HI?: number;
    WG503_LO?: number;
    WG503_HI?: number;
  };
}

interface LiveDataTableProps {
  data: LiveDataRow[];
  theme: 'light' | 'dark';
}

const LiveDataTable: React.FC<LiveDataTableProps> = ({ data, theme }) => {
  const tableBg = theme === 'light'
    ? 'bg-white border border-blue-200 text-[#222]'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  const tableHeader = theme === 'light'
    ? 'bg-blue-100 text-[#222] border-b border-blue-300'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' ? 'bg-blue-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-blue-100' : 'border-slate-700';

  // Define signal columns - HI/LO columns removed
  const signalColumns = [
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

  return (
    <div 
      className={`rounded-lg ${tableBg} shadow ${theme === 'light' ? '' : 'shadow-[0_0_15px_#00ffff44]'}`} 
      style={{ 
        width: '100%',
        overflowX: 'auto',
        overflowY: 'visible',
        WebkitOverflowScrolling: 'touch',
        position: 'relative',
        display: 'block',
        boxSizing: 'border-box',
        // Force scrollbar to always be visible
        scrollbarWidth: 'thin',
        // Ensure container doesn't exceed parent - critical for preventing overflow
        minWidth: 0,
        // Explicitly set to prevent expansion beyond parent
        flexShrink: 1,
        // Prevent container from expanding beyond parent width
        contain: 'layout',
        // Ensure container is exactly parent width
        margin: 0,
        padding: 0,
        // Ensure container adapts to zoom - use 100% not fixed values
        maxWidth: '100%'
      }}
    >
      <table className={`text-xs text-left font-mono ${theme === 'light' ? 'text-[#222]' : 'text-cyan-200'}`} style={{ minWidth: 'max-content', width: 'auto', tableLayout: 'auto', borderCollapse: 'collapse' }}>
        <thead className={`${tableHeader} uppercase tracking-wider sticky top-0`}>
          <tr>
            <th className="px-3 py-2 whitespace-nowrap">Timestamp</th>
            {signalColumns.map((col) => (
              <th key={col.key} className="px-3 py-2 whitespace-nowrap text-center">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={signalColumns.length + 1} className="px-4 py-8 text-center text-gray-500">
                No data available
              </td>
            </tr>
          ) : (
            data.map((row, idx) => (
              <tr
                key={idx}
                className={`transition duration-150 border-b ${borderRow} ${idx % 2 === 0 ? tableRowEven : tableRowOdd}`}
              >
                <td className="px-3 py-2 whitespace-nowrap">{row.timestamp || 'N/A'}</td>
                {signalColumns.map((col) => (
                  <td key={col.key} className="px-3 py-2 text-center whitespace-nowrap">
                    {(row.rawSignals?.[col.key as keyof typeof row.rawSignals] || 0).toFixed(2)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default LiveDataTable;