import React, { useState, useEffect, useMemo } from 'react';
import OrderTable from '../../components/OrderTable';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { useNotificationHelpers } from '../../components/NotificationSystem';
import { parseSAPError, getSAPErrorIcon } from '../../utils/sapErrorHandler';
import { LoadingOverlay } from '../../components/LoadingOverlay';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { apiFetch, getApiUrl } from '../../lib/apiConfig';

interface ApiOrder {
  id: number | string;       // backend "id"
  po_number?: string;        // backend may also send this
  material: string;
  version?: string;
  batch?: string;
  quantity?: number;
  unit?: string;             // CHANGED: was uom
  status: string;            // Pending | Validated | Rejected | ...
  priority?: number;         // NEW
  created_at?: string;       // ISO
  plant?: string;            // NEW: PLANT column
  confirmed_qty?: number;    // NEW: CONFIRMED_QTY column
  material_desc?: string;    // NEW: MATERIAL_DESC column
  expected_weight?: number;  // NEW: EXPECTED_WEIGHT from SAP sync
  sap_created_on?: string;   // NEW: SAP_CREATED_ON from SAP sync
}

interface Order {
  id: string;                // what your table shows (we'll display po_number if present)
  material: string;
  version: string;
  batch: string;
  quantity: number;
  unit: string;              // NEW (to show KG/TON)
  priority: number;          // NEW (for queueing visibility)
  status: string;
  date: string;              // derived from created_at or today's date
  plant: string;             // NEW: PLANT column
  confirmed_qty: number;     // NEW: CONFIRMED_QTY column
  material_desc: string;     // NEW: MATERIAL_DESC column
  expected_weight: number;   // NEW: EXPECTED_WEIGHT from SAP sync
  sap_created_on: string;    // NEW: SAP_CREATED_ON from SAP sync
}

// Removed QueueStatus type - not needed for historical view

// Pagination Component
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (itemsPerPage: number) => void;
  theme: 'light' | 'dark';
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
  theme
}) => {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5;
    
    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, currentPage - 2);
      const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
      
      if (startPage > 1) {
        pages.push(1);
        if (startPage > 2) {
          pages.push('...');
        }
      }
      
      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }
      
      if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
          pages.push('...');
        }
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  return (
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-lg backdrop-blur-md border transition-all duration-300 ${
      theme === 'light' 
        ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30' 
        : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
    }`}>
      {/* Items per page selector and info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className={`text-sm font-medium ${
            theme === 'light' ? 'text-slate-700' : 'text-slate-300'
          }`}>
            Show:
          </label>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className={`px-2 py-1 rounded border text-sm focus:outline-none focus:ring-1 ${
              theme === 'light'
                ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
            }`}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        
        <div className={`text-sm ${
          theme === 'light' ? 'text-slate-600' : 'text-slate-400'
        }`}>
          Showing {startItem}-{endItem} of {totalItems} orders
        </div>
      </div>

      {/* Pagination controls */}
      <div className="flex items-center gap-2">
        {/* First page */}
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className={`p-2 rounded-md transition-all duration-200 ${
            currentPage === 1
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
          } ${
            theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
          }`}
          title="First page"
        >
          <ChevronsLeft className="h-4 w-4" />
        </button>

        {/* Previous page */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className={`p-2 rounded-md transition-all duration-200 ${
            currentPage === 1
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
          } ${
            theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
          }`}
          title="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {/* Page numbers */}
        <div className="flex items-center gap-1">
          {getPageNumbers().map((page, index) => (
            <button
              key={index}
              onClick={() => typeof page === 'number' ? onPageChange(page) : undefined}
              disabled={page === '...'}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all duration-200 ${
                page === '...'
                  ? 'cursor-default'
                  : 'hover:scale-105'
              } ${
                page === currentPage
                  ? theme === 'light'
                    ? 'bg-blue-500 text-white shadow-md'
                    : 'bg-cyan-500 text-white shadow-md shadow-cyan-500/25'
                  : page === '...'
                  ? theme === 'light'
                    ? 'text-slate-400'
                    : 'text-slate-500'
                  : theme === 'light'
                  ? 'text-slate-700 hover:bg-slate-100'
                  : 'text-slate-300 hover:bg-slate-700'
              }`}
            >
              {page}
            </button>
          ))}
        </div>

        {/* Next page */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className={`p-2 rounded-md transition-all duration-200 ${
            currentPage === totalPages
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
          } ${
            theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
          }`}
          title="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        {/* Last page */}
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className={`p-2 rounded-md transition-all duration-200 ${
            currentPage === totalPages
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
          } ${
            theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
          }`}
          title="Last page"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

const ProcessOrdersPage: React.FC = () => {
  const { theme } = useTheme();
  const { showSuccess, showError, showInfo } = useNotificationHelpers();

  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({ id: '', material: '', status: '', startDate: '', endDate: '' });
  const [activeTab, setActiveTab] = useState<'Daily' | 'Weekly' | 'Monthly'>('Daily');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);

  // Removed queue-related functions - not needed for historical view

  // ---- API helpers (updated to use SAP sync endpoint) ----------------------------------------------------------
  const fetchOrders = async (status?: string): Promise<ApiOrder[]> => {
    const qs = status && status !== 'All' && status !== '' ? `?status=${encodeURIComponent(status)}` : '';
    console.log('Fetching orders from:', `/api/sap-sync/orders${qs}`);
    
    const res = await apiFetch(getApiUrl(`/api/sap-sync/orders${qs}`));
    console.log('Response status:', res.status);
    console.log('Response headers:', res.headers);
    
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errorText}`);
    }
    
    // Check if response is JSON
    const contentType = res.headers.get('content-type');
    console.log('Content-Type:', contentType);
    
    if (!contentType || !contentType.includes('application/json')) {
      throw new Error('Server returned non-JSON response. API endpoint may not exist.');
    }
    
    const responseData = await res.json();
    console.log('API Response data:', responseData);
    
    // Extract orders from the SAP sync response format
    const data = responseData.ok ? responseData.orders : [];
    return data;
  };

  const mapApiToUi = (rows: ApiOrder[]): Order[] =>
    rows.map((r) => ({
      // prefer showing PO number when available, else the numeric id
      id: r.po_number ? String(r.po_number) : String(r.id),
      material: r.material ?? '—',
      version: r.version ?? 'v1.0',
      batch: r.batch ?? '—',
      quantity: Number(r.quantity ?? 0),
      unit: r.unit ?? 'KG',
      priority: Number(r.priority ?? 0),
      status: r.status ?? 'Pending',
      // prefer created_at, else today's date
      date: r.created_at ? new Date(r.created_at).toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10),
      plant: r.plant ?? '—',
      confirmed_qty: Number(r.confirmed_qty ?? 0),
      material_desc: r.material_desc ?? '—',
      // Add new fields from SAP sync endpoint
      expected_weight: Number(r.expected_weight ?? 0),
      sap_created_on: r.sap_created_on ?? '—',
    }));


  // ---- Historical view - show all orders -------------------------------------------------------
  const load = async () => {
    try {
      console.log('ProcessOrdersPage: load() function called - Historical view');
      setLoading(true);
      setError(null);

      // Always fetch all orders for historical view
      const apiRows = await fetchOrders(filters.status);

      console.log('ProcessOrdersPage: API response received:', apiRows);
      const ui = mapApiToUi(apiRows);
      console.log('ProcessOrdersPage: Mapped UI data:', ui);
      
      setOrders(ui);
      setFilteredOrders(ui);
      setError(null); // Clear any previous errors
      console.log('ProcessOrdersPage: Data loaded successfully, orders count:', ui.length);
    } catch (e: any) {
      console.error('ProcessOrdersPage: Error in load():', e);
      const sapError = parseSAPError(e);
      setError(sapError.message);
      
      // Show professional error notification
      showError(
        sapError.title,
        sapError.message,
        0, // Don't auto-dismiss errors
        sapError.actions
      );
      
      setOrders([]);
      setFilteredOrders([]);
    } finally {
      setLoading(false);
    }
  };

  // Removed sync and start next functions - not needed for historical view

  useEffect(() => {
    console.log('ProcessOrdersPage: useEffect triggered, calling load()');
    load();
  }, []);

  // ---- Auto-refresh all orders every 60s for historical view --------------------------------
  useEffect(() => {
    const t = setInterval(() => {
      fetchOrders(filters.status)
        .then((rows) => {
          const ui = mapApiToUi(rows);
          setOrders(ui);
          setFilteredOrders(ui);
        })
        .catch((e) => console.debug('orders refresh skipped:', e?.message));
    }, 60_000); // 60s - less frequent for historical view

    return () => clearInterval(t);
  }, [filters.status]);

  // ---- Filtering & Tabs -----------------------------------------------------
  const applyFilters = useMemo(() => {
    return (tab: typeof activeTab, f = filters) => {
      const today = new Date();
      const filtered = orders.filter((o) => {
        // Text filters (case-insensitive)
        const idMatch = !f.id || o.id.toLowerCase().includes(f.id.toLowerCase());
        const materialMatch = !f.material || o.material.toLowerCase().includes(f.material.toLowerCase());
        const statusMatch = !f.status || f.status === 'All' || f.status === '' || o.status === f.status;

        // Date range filter
        let dateMatch = true;
        if (f.startDate || f.endDate) {
          try {
            const orderDate = new Date(o.date);
            const startDate = f.startDate ? new Date(f.startDate) : null;
            const endDate = f.endDate ? new Date(f.endDate) : null;

            // Set time to start/end of day for accurate comparison
            if (startDate) {
              startDate.setHours(0, 0, 0, 0);
            }
            if (endDate) {
              endDate.setHours(23, 59, 59, 999);
            }
            orderDate.setHours(12, 0, 0, 0); // Set to midday for consistent comparison

            if (startDate && orderDate < startDate) dateMatch = false;
            if (endDate && orderDate > endDate) dateMatch = false;
          } catch (error) {
            console.warn('Date parsing error:', error);
            dateMatch = true; // If date parsing fails, include the record
          }
        }

        // Tab-based filtering (only apply if no date filters are set)
        let tabMatch = true;
        if (!f.startDate && !f.endDate) {
          try {
            const orderDate = new Date(o.date);
            const diffDays = (today.getTime() - orderDate.getTime()) / (1000 * 60 * 60 * 24);

            if (tab === 'Daily' && diffDays > 1) tabMatch = false;
            if (tab === 'Weekly' && diffDays > 7) tabMatch = false;
            if (tab === 'Monthly' && diffDays > 31) tabMatch = false;
          } catch (error) {
            console.warn('Tab filtering error:', error);
            tabMatch = true; // If date parsing fails, include the record
          }
        }

        return idMatch && materialMatch && statusMatch && dateMatch && tabMatch;
      });
      setFilteredOrders(filtered);
    };
  }, [orders, filters, activeTab]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    const next = { ...filters, [name]: value };
    setFilters(next);
  };

  // REPLACED: handleView with server-side status filtering
  const handleView = async () => {
    console.log('ProcessOrdersPage: handleView called - refreshing data');
    await load(); // Use the existing load function
  };

  useEffect(() => { applyFilters(activeTab, filters); }, [orders, activeTab, applyFilters]); // re-run when data, tab, or filters change

  // Auto-reload data when status filter changes
  useEffect(() => {
    console.log('ProcessOrdersPage: Status filter changed, reloading data');
    load();
  }, [filters.status]);

  // Pagination handlers
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1); // Reset to first page when changing items per page
  };

  // Calculate pagination
  const totalPages = Math.ceil(filteredOrders.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentOrders = filteredOrders.slice(startIndex, endIndex);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [filters, activeTab]);

  const handlePrint = () => {
    // Show the print content
    const printContent = document.querySelector('.print-content') as HTMLElement;
    if (printContent) {
      printContent.style.display = 'block';
    }
    
    // Trigger print
    window.print();
    
    // Hide the print content after printing
    setTimeout(() => {
      if (printContent) {
        printContent.style.display = 'none';
      }
    }, 100);
  };

  // ---- Styles ---------------------------------------------------------------
  const filterInput = theme === 'light'
    ? 'p-2 rounded bg-white border border-blue-300 text-blue-900 focus:ring-blue-300'
    : 'p-2 rounded bg-[#0f172a] border border-cyan-500 text-cyan-200 focus:ring-cyan-400';
  const filterSelect = filterInput;

  return (
    <>
      <LoadingOverlay 
        isLoading={loading} 
        message="Processing Request"
        subMessage="Please wait while we connect to SAP..."
      />
      <WaterSystemLayout title="SAP Process Orders" subtitle="SAP Process Orders Management">
      <style>{`
        /* Force white text for buttons and tabs in light mode */
        .process-start-light {
          color: white !important;
        }
        
        .process-start-light span {
          color: white !important;
        }
        
        .process-view-light {
          color: white !important;
        }
        
        .process-view-light span {
          color: white !important;
        }
        
        .process-print-light {
          color: white !important;
        }
        
        .process-print-light span {
          color: white !important;
        }
        
        .process-tab-light {
          color: white !important;
        }
        
        .process-tab-light span {
          color: white !important;
        }

        /* Print-specific styles */
        @media print {
          /* Hide everything except the print content */
          body * {
            visibility: hidden;
          }
          
          .print-content, .print-content * {
            visibility: visible;
          }
          
          .print-content {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            margin-left: 70px;
            padding: 0;
          }
          
          /* Print header */
          .print-header {
            margin-bottom: 15px;
            border-bottom: 2px solid #000;
            padding-bottom: 15px;
            text-align: center;
          }
          
          .print-logo-section {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 15px;
          }
          
          .print-logo {
            margin-right: 20px;
          }
          
          .print-logo-img {
            height: 60px;
            width: auto;
            max-width: 120px;
          }
          
          .print-company-info {
            text-align: center;
            
          }
          
          .print-title {
            font-size: 28px;
            font-weight: bold;
            margin: 0 0 5px 0;
            color: #000 !important;
            letter-spacing: 1px;
          }
          
          .print-report-title {
            font-size: 18px;
            font-weight: 600;
            margin: 0;
            color: #333 !important;
          }
          
          .print-details {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 15px;
            flex-wrap: wrap;
          }
          
          .print-detail-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 5px 0;
          }
          
          .print-label {
            font-weight: bold;
            color: #000 !important;
            font-size: 10px;
          }
          
          .print-value {
            color: #333 !important;
            font-size: 10px;
          }
          
          /* Print table container */
          .print-table-container {
            width: 100%;
            margin: 15px auto 0 auto;
            box-sizing: border-box;
            display: flex;
            justify-content: center;
            padding: 0 10px;
          }
          
          /* Print table styles */
          .print-table {
            width: 100%;
            max-width: 100%;
            border-collapse: collapse;
            font-size: 7px;
            page-break-inside: auto;
            table-layout: fixed;
            margin: 0 auto;
            box-sizing: border-box;
            border: 1px solid #000;
          }
          
          .print-table th,
          .print-table td {
            border: 1px solid #000;
            padding: 2px 3px;
            text-align: center;
            color: #000 !important;
            background: #fff !important;
            vertical-align: middle;
            word-wrap: break-word;
            overflow: hidden;
          }
          
          .print-table th {
            background-color: #f0f0f0 !important;
            font-weight: bold;
            text-align: center;
            font-size: 6px;
            text-transform: uppercase;
            letter-spacing: 0.2px;
            padding: 3px 2px;
            white-space: normal;
            line-height: 1.1;
          }
          
          .print-table tr:nth-child(even) {
            background-color: #f8f8f8 !important;
          }
          
          .print-table tr {
            page-break-inside: avoid;
            page-break-after: auto;
          }
          
          /* Optimized column widths for A4 page - total should be 100% */
          .print-table th:nth-child(1), .print-table td:nth-child(1) { width: 9%; } /* Order ID */
          .print-table th:nth-child(2), .print-table td:nth-child(2) { width: 7%; } /* Material */
          .print-table th:nth-child(3), .print-table td:nth-child(3) { width: 5%; } /* Version */
          .print-table th:nth-child(4), .print-table td:nth-child(4) { width: 7%; } /* Batch */
          .print-table th:nth-child(5), .print-table td:nth-child(5) { width: 5%; } /* Quantity */
          .print-table th:nth-child(6), .print-table td:nth-child(6) { width: 4%; } /* Unit */
          .print-table th:nth-child(7), .print-table td:nth-child(7) { width: 7%; } /* Plant */
          .print-table th:nth-child(8), .print-table td:nth-child(8) { width: 7%; } /* Confirmed Qty */
          .print-table th:nth-child(9), .print-table td:nth-child(9) { width: 20%; } /* Material Description */
          .print-table th:nth-child(10), .print-table td:nth-child(10) { width: 7%; } /* Status */
          .print-table th:nth-child(11), .print-table td:nth-child(11) { width: 5%; } /* Priority */
          .print-table th:nth-child(12), .print-table td:nth-child(12) { width: 8%; } /* Date */
          
          /* Print footer */
          .print-footer {
            margin-top: 25px;
            border-top: 2px solid #000;
            padding-top: 15px;
            page-break-inside: avoid;
            text-align: center;
          }
          
          .print-footer-content {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin-bottom: 15px;
            gap: 40px;
          }
          
          .print-footer-left,
          .print-footer-right {
            font-size: 10px;
            color: #333 !important;
            text-align: center;
          }
          
          .print-footer-left p,
          .print-footer-right p {
            margin: 3px 0;
          }
          
          .print-footer-bottom {
            text-align: center;
            font-size: 9px;
            color: #666 !important;
            font-style: italic;
            border-top: 1px solid #ccc;
            padding-top: 10px;
            margin-top: 15px;
          }
          
          /* Hide non-printable elements */
          .no-print {
            display: none !important;
          }
          
          /* Page setup */
          @page {
            margin: 0.5in;
            size: A4;
          }
          
          /* Ensure proper page breaks */
          .print-content {
            page-break-inside: avoid;
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
            width: 100%;
            box-sizing: border-box;
          }
          
          /* All table cells centered by default */
          .print-table td {
            text-align: center !important;
            font-size: 6px;
            font-weight: normal;
          }
          
          /* Order ID formatting */
          .print-table td:nth-child(1) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Material formatting */
          .print-table td:nth-child(2) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Version formatting */
          .print-table td:nth-child(3) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Batch formatting */
          .print-table td:nth-child(4) {
            font-size: 6px;
          }
          
          /* Quantity formatting */
          .print-table td:nth-child(5) {
            font-family: monospace;
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Unit formatting */
          .print-table td:nth-child(6) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Plant formatting */
          .print-table td:nth-child(7) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Confirmed Qty formatting */
          .print-table td:nth-child(8) {
            font-family: monospace;
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Material description formatting */
          .print-table td:nth-child(9) {
            font-size: 5px;
            line-height: 1.1;
            white-space: normal;
            word-wrap: break-word;
            text-align: left;
            padding: 2px 4px;
          }
          
          /* Status formatting */
          .print-table td:nth-child(10) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Priority formatting */
          .print-table td:nth-child(11) {
            font-weight: bold;
            font-size: 6px;
          }
          
          /* Date formatting */
          .print-table td:nth-child(12) {
            font-size: 5px;
          }
        }
      `}</style>
      {/* Print Content - Hidden by default, visible only when printing */}
      <div className="print-content" style={{ display: 'none' }}>
        <div className="print-header">
          <div className="print-logo-section">
            <div className="print-logo">
              <img 
                src="/src/assets/New_hercules.jfif" 
                alt="Hercules Logo" 
                className="print-logo-img"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
            </div>
            <div className="print-company-info">
              <h1 className="print-title">Hercules SFMS</h1>
              <h2 className="print-report-title">SAP Process Orders Report</h2>
            </div>
          </div>
          <div className="print-details">
            <div className="print-detail-row">
              <span className="print-label">Report Type:</span>
              <span className="print-value">Process Orders Management</span>
            </div>
            <div className="print-detail-row">
              <span className="print-label">Generated:</span>
              <span className="print-value">{new Date().toLocaleDateString()} at {new Date().toLocaleTimeString()}</span>
            </div>
            <div className="print-detail-row">
              <span className="print-label">View Period:</span>
              <span className="print-value">{activeTab} Orders</span>
            </div>
            <div className="print-detail-row">
              <span className="print-label">Total Records:</span>
              <span className="print-value">{filteredOrders.length} orders</span>
            </div>
          </div>
        </div>
        
        <div className="print-table-container">
          <table className="print-table">
          <thead>
            <tr>
              <th>ORDER ID</th>
              <th>MATERIAL</th>
              <th>VERSION</th>
              <th>BATCH</th>
              <th>QUANTITY</th>
              <th>UNIT</th>
              <th>PLANT</th>
              <th>CONFIRMED QTY</th>
              <th>MATERIAL DESCRIPTION</th>
              <th>STATUS</th>
              <th>PRIORITY</th>
              <th>DATE</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order) => (
              <tr key={order.id}>
                <td>{order.id}</td>
                <td>{order.material}</td>
                <td>{order.version}</td>
                <td>{order.batch}</td>
                <td>{order.quantity}</td>
                <td>{order.unit}</td>
                <td>{order.plant}</td>
                <td>{order.confirmed_qty}</td>
                <td>{order.material_desc}</td>
                <td>{order.status}</td>
                <td>{order.priority}</td>
                <td>{order.date}</td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
        
        <div className="print-footer">
          <div className="print-footer-content">
            <div className="print-footer-left">
              <p><strong>Hercules SFMS</strong> - Smart Factory Management System</p>
              <p>Process Orders Management Module</p>
            </div>
            <div className="print-footer-right">
              <p>Total Orders: <strong>{filteredOrders.length}</strong></p>
              <p>View Period: <strong>{activeTab}</strong></p>
              <p>Generated: {new Date().toLocaleDateString()} {new Date().toLocaleTimeString()}</p>
            </div>
          </div>
          <div className="print-footer-bottom">
            <p>This report contains confidential information. Unauthorized distribution is prohibited.</p>
          </div>
        </div>
      </div>

      <div className="space-y-3 no-print">
        {/* Header */}
        <div className="flex justify-between items-center mb-3">
          <h2 className={theme === 'light' ? 'text-xl font-bold text-gray-700 tracking-wide' : 'text-xl font-bold text-cyan-400 tracking-wide'}>
            SAP Process Orders
          </h2>

          {/* Action buttons - Removed sync and start next buttons for historical view */}
        </div>

        {/* Error - Now handled by notification system */}

        {/* Filters Section - Full Width Single Row */}
        <div className={`rounded-lg p-3 mb-4 no-print w-full ${
          theme === 'light'
            ? 'bg-white/30 border border-blue-200/40 shadow-sm'
            : 'bg-slate-800/30 border border-cyan-400/20 shadow-[0_0_15px_rgba(0,255,255,0.1)]'
        }`}>
          <div className="flex items-end gap-4 w-full">
            {/* Order ID */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                Order ID
              </label>
              <input 
                name="id" 
                placeholder="Enter Order ID" 
                value={filters.id} 
                onChange={handleFilterChange} 
                className={`${filterInput} text-sm py-2 px-3 w-full`}
              />
            </div>

            {/* Material */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                Material
              </label>
              <input 
                name="material" 
                placeholder="Enter Material" 
                value={filters.material} 
                onChange={handleFilterChange} 
                className={`${filterInput} text-sm py-2 px-3 w-full`}
              />
            </div>

            {/* Status */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                Status
              </label>
              <select 
                name="status" 
                value={filters.status} 
                onChange={handleFilterChange} 
                className={`${filterSelect} text-sm py-2 px-3 w-full`}
              >
                <option value="">All Statuses</option>
                <option value="Open">Open</option>
                <option value="Pending">Pending</option>
                <option value="InProgress">InProgress</option>
                <option value="Planned">Planned</option>
                <option value="Completed">Completed</option>
                <option value="Validated">Validated</option>
                <option value="Rejected">Rejected</option>
              </select>
            </div>

            {/* Start Date */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                Start Date
              </label>
              <input 
                name="startDate" 
                type="date" 
                value={filters.startDate} 
                onChange={handleFilterChange} 
                className={`${filterInput} text-sm py-2 px-3 w-full`}
                title="Start Date"
              />
            </div>

            {/* End Date */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                End Date
              </label>
              <input 
                name="endDate" 
                type="date" 
                value={filters.endDate} 
                onChange={handleFilterChange} 
                className={`${filterInput} text-sm py-2 px-3 w-full`}
                title="End Date"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col flex-1">
              <label className={`text-xs font-semibold uppercase tracking-wide mb-1 ${theme === 'light' ? 'text-gray-600' : 'text-cyan-300'}`}>
                Actions
              </label>
              <div className="flex space-x-2">
                <button onClick={handleView}
                  className={`relative group flex items-center justify-center gap-1.5 px-3 py-2 rounded-md font-medium text-sm transition-all duration-300 hover:scale-105 !text-white process-view-light flex-1 ${
                    theme === 'light'
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                      : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
                  }`}
                  style={{
                    color: 'white !important'
                  }}
                  title="View Orders"
                >
                  <span className="font-semibold tracking-wide !text-white process-view-light" style={{ color: 'white !important' }}>
                    {loading ? 'Loading…' : 'View'}
                  </span>
                  <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </button>
                <button onClick={handlePrint}
                  className={`relative group flex items-center justify-center gap-1.5 px-3 py-2 rounded-md font-medium text-sm transition-all duration-300 hover:scale-105 !text-white process-print-light flex-1 ${
                    theme === 'light'
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                      : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
                  }`}
                  style={{
                    color: 'white !important'
                  }}
                  title="Print Orders"
                >
                  <span className="font-semibold tracking-wide !text-white process-print-light" style={{ color: 'white !important' }}>Print</span>
                  <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </button>
              </div>
            </div>
          </div>
        </div>



        {/* Time Tabs */}
        <div className="flex space-x-1 mb-3 no-print">
          {(['Daily','Weekly','Monthly'] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`relative group px-4 py-2 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 ${
                activeTab === tab
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 !text-white shadow-lg shadow-cyan-500/30 border border-cyan-400/50'
                  : theme === 'light'
                    ? 'bg-gradient-to-r from-slate-600/80 to-slate-700/80 !text-white border border-slate-500/50 hover:from-slate-500/90 hover:to-slate-600/90 hover:shadow-md process-tab-light'
                    : 'bg-slate-700/60 text-cyan-300/70 border border-slate-600/40 hover:bg-slate-700/80 hover:text-cyan-300'
              }`}
              style={{
                color: theme === 'light' ? 'white !important' : undefined
              }}
              title={`View ${tab} Orders`}
            >
              <span className={`font-semibold tracking-wide ${theme === 'light' ? '!text-white process-tab-light' : ''}`} style={{ color: theme === 'light' ? 'white !important' : undefined }}>{tab}</span>
              {activeTab === tab && (
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-400/20 to-blue-500/20 animate-pulse" />
              )}
            </button>
          ))}
        </div>

        {/* Orders Table */}
        <div className={`no-print ${theme === 'light'
          ? 'rounded-lg border border-blue-200/30 shadow-md bg-white/20 backdrop-blur-md p-3 hover:shadow-lg transition-all duration-300'
          : 'rounded-lg border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.15)] bg-slate-900/20 backdrop-blur-md p-3 hover:shadow-[0_0_25px_rgba(0,255,255,0.25)] transition-all duration-300'}`}>
          <div className="flex justify-between items-center mb-2">
            <h3 className={theme === 'light' ? 'text-base font-semibold text-gray-700' : 'text-base font-semibold text-cyan-300'}>
              {activeTab} Orders
            </h3>
            <span className={`text-xs ${theme === 'light' ? 'text-gray-600' : 'text-cyan-400'}`}>
              {filteredOrders.length} orders
            </span>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <OrderTable orders={currentOrders} theme={theme} />
          </div>
        </div>

        {/* Pagination */}
        {filteredOrders.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filteredOrders.length}
            itemsPerPage={itemsPerPage}
            onPageChange={handlePageChange}
            onItemsPerPageChange={handleItemsPerPageChange}
            theme={theme}
          />
        )}
      </div>
    </WaterSystemLayout>
    </>
  );
};

export default ProcessOrdersPage;
