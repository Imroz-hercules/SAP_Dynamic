import React from 'react';

interface Order {
  id: string;
  material: string;
  version: string;
  batch: string;
  quantity: number;
  unit: string;              // NEW (to show KG/TON)
  priority: number;          // NEW (for queueing visibility)
  status: string;
  date: string;
  plant: string;             // NEW: PLANT column
  confirmed_qty: number;     // NEW: CONFIRMED_QTY column
  material_desc: string;     // NEW: MATERIAL_DESC column
  expected_weight: number;   // NEW: EXPECTED_WEIGHT from SAP sync
  sap_created_on: string;    // NEW: SAP_CREATED_ON from SAP sync
}

interface OrderTableProps {
  orders: Order[];
  theme: 'light' | 'dark';
}

// Simple Table Row Component
interface TableRowProps {
  order: Order;
  index: number;
  theme: 'light' | 'dark';
}

const TableRow: React.FC<TableRowProps> = ({ order, index, theme }) => {
  const tableRowEven = theme === 'light' ? 'bg-blue-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-blue-100' : 'border-slate-700';

  return (
    <tr
      className={`transition-all duration-200 border-b ${borderRow} ${
        index % 2 === 0 ? tableRowEven : tableRowOdd
      }`}
    >
      <td className="px-2 py-1.5 font-mono text-xs truncate" title={order.id}>
        {order.id}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs truncate" title={order.material}>
        {order.material}
      </td>
      <td className="px-2 py-1.5 text-xs truncate max-w-20" title={order.material_desc}>
        {order.material_desc}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.version}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs truncate" title={order.batch}>
        {order.batch}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.plant}
      </td>
      <td className="px-2 py-1.5">
        <span className={`px-1.5 py-0.5 rounded text-xs font-bold transition-all duration-200 ${
          order.priority === 1 
            ? theme === 'light' ? 'bg-red-200 text-red-800 shadow-sm' : 'bg-red-600 text-white shadow-red-500/30'
            : order.priority === 2
            ? theme === 'light' ? 'bg-orange-200 text-orange-800 shadow-sm' : 'bg-orange-600 text-white shadow-orange-500/30'
            : order.priority === 3
            ? theme === 'light' ? 'bg-yellow-200 text-yellow-800 shadow-sm' : 'bg-yellow-600 text-white shadow-yellow-500/30'
            : theme === 'light' ? 'bg-gray-200 text-gray-800 shadow-sm' : 'bg-gray-600 text-white shadow-gray-500/30'
        }`}>
          {order.priority}
        </span>
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.quantity}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.confirmed_qty}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.unit}
      </td>
      <td className="px-2 py-1.5">
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-bold ${
            order.status === 'Completed'
              ? theme === 'light'
                ? 'bg-green-400 text-green-900'
                : 'bg-green-600 text-white'
              : order.status === 'InProgress'
                ? theme === 'light'
                  ? 'bg-blue-300 text-blue-900'
                  : 'bg-blue-500 text-white'
                : order.status === 'Planned'
                  ? theme === 'light'
                    ? 'bg-yellow-300 text-yellow-900'
                    : 'bg-yellow-400 text-black'
                  : order.status === 'Pending'
                    ? theme === 'light'
                      ? 'bg-orange-300 text-orange-900'
                      : 'bg-orange-500 text-white'
                    : theme === 'light'
                      ? 'bg-gray-300 text-gray-700'
                      : 'bg-gray-500 text-white'
          }`}
        >
          {order.status}
        </span>
      </td>
      <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
        {order.date}
      </td>
    </tr>
  );
};

const OrderTable: React.FC<OrderTableProps> = ({ orders, theme }) => {

  const tableBg = theme === 'light'
    ? 'bg-white border border-blue-200 text-[#222]'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  const tableHeader = theme === 'light'
    ? 'bg-blue-100 text-[#222] border-b border-blue-300'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' ? 'bg-blue-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-blue-100' : 'border-slate-700';

  const tableContent = (
    <table className={`w-full text-xs text-left ${theme === 'light' ? 'text-[#222]' : 'text-cyan-200'}`}>
      <thead className={`${tableHeader} uppercase text-xs tracking-wider`}>
        <tr>
          <th className="px-2 py-1.5 w-20">Order ID</th>
          <th className="px-2 py-1.5 w-16">Material</th>
          <th className="px-2 py-1.5 w-20">Description</th>
          <th className="px-2 py-1.5 w-12">Ver</th>
          <th className="px-2 py-1.5 w-16">Batch</th>
          <th className="px-2 py-1.5 w-12">Plant</th>
          <th className="px-2 py-1.5 w-12">Prio</th>
          <th className="px-2 py-1.5 w-16">Qty</th>
          <th className="px-2 py-1.5 w-16">Conf Qty</th>
          <th className="px-2 py-1.5 w-12">Unit</th>
          <th className="px-2 py-1.5 w-20">Status</th>
          <th className="px-2 py-1.5 w-20">Date</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order, idx) => (
          <TableRow
            key={order.id}
            order={order}
            index={idx}
            theme={theme}
          />
        ))}
      </tbody>
    </table>
  );

  return (
    <div className={`overflow-x-auto rounded-lg ${tableBg} shadow ${theme === 'light' ? '' : 'shadow-[0_0_15px_#00ffff44]'}`}>
      {tableContent}
    </div>
  );
};

export default OrderTable;