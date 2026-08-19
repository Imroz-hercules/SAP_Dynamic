import React, { useState, useEffect } from "react";
import { useTheme } from "../../contexts/ThemeContext";
import { WaterSystemLayout } from "../../components/hercules-sfms/WaterSystemLayout";
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 Reportss.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}
import { FileText, BarChart3, Package, Droplet, Boxes, Gauge, RefreshCw, ListOrdered, Clock3, AlertCircle, X, Search, Filter, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, TrendingUp, Database, Download, Printer } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import herculesLogo from "@/assets/Hercules_New.png";
import asmLogo from "@/assets/Asm_Logo.png";
import modernMillsLogo from "@/assets/modern_millslogo.png";
import { TimeFilter } from "@/components/TimeFilter";
import type { TimeFilterProps } from "@/components/TimeFilter";
import { useHistoricalData, generateMockHistoricalData } from "../../hooks/useHistoricalData";
import { kpiApi, KpiData } from '../../lib/api';
import { useScada } from '../../contexts/ScadaContext';
import { format } from 'date-fns';

// Type definitions
interface Order {
  id: number;
  po_number: string;
  material: string;
  version: string;
  quantity: number;
  unit: string;
  status: string;
  created_at: string;
  updated_at: string;
  confirmed_qty?: number;
  expected_weight?: string;
  order_type?: string; // MILLING or PACKING
}

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
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
      ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
      : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
      }`}>
      {/* Items per page selector and info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className={`text-sm font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            }`}>
            Show:
          </label>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className={`px-2 py-1 rounded border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
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

        <div className={`text-sm ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
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
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === 1
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:scale-105'
            } ${theme === 'light'
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
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === 1
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:scale-105'
            } ${theme === 'light'
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
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all duration-200 ${page === '...'
                ? 'cursor-default'
                : 'hover:scale-105'
                } ${page === currentPage
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
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === totalPages
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:scale-105'
            } ${theme === 'light'
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
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === totalPages
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:scale-105'
            } ${theme === 'light'
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

interface UserInfo { id: number; username: string; roles: string[]; }

const Reports = () => {
  const { theme } = useTheme();
  const { scadaData } = useScada();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  });
  const currentUser = userData as UserInfo | null;
  const isAdmin = currentUser?.roles?.includes('admin') || false;
  const isMillingOnly = !isAdmin && (currentUser?.roles?.includes('milling_operator') ?? false);
  const isPackingOnly = !isAdmin && (currentUser?.roles?.includes('packing_operator') ?? false);
  
  // Main tab state (Orders vs KPIs)
  const [mainTab, setMainTab] = useState<'orders' | 'kpis'>('orders');
  
  // Orders sub-tab state
  const [activeTab, setActiveTab] = useState<'all' | 'milling' | 'packing'>('all');
  
  // KPIs sub-tab state
  const [kpiSubTab, setKpiSubTab] = useState<'milling' | 'packing'>('milling');

  // Default tabs by role: milling operator → Milling only, packing operator → Packing only
  useEffect(() => {
    if (isPackingOnly) {
      setActiveTab('packing');
      setKpiSubTab('packing');
    } else if (isMillingOnly) {
      setActiveTab('milling');
      setKpiSubTab('milling');
    }
  }, [isMillingOnly, isPackingOnly]);
  
  // KPI data state
  const [kpiData, setKpiData] = useState<KpiData | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);
  const [kpiError, setKpiError] = useState<string | null>(null);
  
  // KPI tracking data state (for historical data from kpi_send_tracking table)
  interface KpiTrackingRecord {
    id: number;
    department: string;
    shift_code: string | null;
    last_sent_at: string;
    send_type: string;
    kpi_payload: Record<string, string>;
  }
  const [kpiTrackingData, setKpiTrackingData] = useState<KpiTrackingRecord[]>([]);
  
  // KPI pagination state
  const [kpiCurrentPage, setKpiCurrentPage] = useState(1);
  const [kpiItemsPerPage, setKpiItemsPerPage] = useState(25);
  const [kpiTotalItems, setKpiTotalItems] = useState(1); // For now, 1 row of KPI data
  
  // KPI pagination handlers
  const handleKpiPageChange = (page: number) => {
    setKpiCurrentPage(page);
  };
  
  const handleKpiItemsPerPageChange = (newItemsPerPage: number) => {
    setKpiItemsPerPage(newItemsPerPage);
    setKpiCurrentPage(1);
  };
  
  // Calculate KPI total pages
  const kpiTotalPages = Math.ceil(kpiTotalItems / kpiItemsPerPage);

  // Historical data management for Orders
  const {
    filters: timeFilters,
    isHistoricalMode,
    periodLabel,
    handleApplyFilters,
    resetToLive,
  } = useHistoricalData('live');
  
  // Historical data management for KPIs
  const {
    filters: kpiTimeFilters,
    isHistoricalMode: isKpiHistoricalMode,
    periodLabel: kpiPeriodLabel,
    handleApplyFilters: handleKpiApplyFilters,
    resetToLive: resetKpiToLive,
  } = useHistoricalData('live');

  // Function to determine order_type from material number
  const getOrderTypeFromMaterial = (material: string): string => {
    if (!material) return 'N/A';
    // Remove leading zeros and get the first two significant digits
    const trimmedMaterial = material.replace(/^0+/, '');
    const firstTwoDigits = trimmedMaterial.substring(0, 2);

    if (firstTwoDigits === '14') {
      return 'PACKING';
    } else if (firstTwoDigits === '13') {
      return 'MILLING';
    }
    return 'N/A';
  };

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [totalOrders, setTotalOrders] = useState(0);

  // State to hold all orders for printing
  const [allOrdersForPrint, setAllOrdersForPrint] = useState<Order[]>([]);
  const [isPrintMode, setIsPrintMode] = useState(false);
  const [isLoadingForPrint, setIsLoadingForPrint] = useState(false);

  // Fetch orders data from API using /api/reports/summary
  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      // Calculate offset for pagination
      const offset = (currentPage - 1) * itemsPerPage;

      // Build query parameters from filters
      const queryParams = new URLSearchParams();
      
      // Get date range from timeFilters or use today as default
      let startDate: string;
      let endDate: string;
      
      // Helper function to extract YYYY-MM-DD from various date formats
      const extractDateOnly = (dateString: string): string => {
        if (!dateString) return new Date().toISOString().split('T')[0];
        
        // If it's an ISO string with 'T', split by 'T'
        if (dateString.includes('T')) {
          return dateString.split('T')[0];
        }
        
        // If it's in format "YYYY-MM-DD HH:mm:ss" or "YYYY-MM-DD HH:mm", split by space
        if (dateString.includes(' ')) {
          return dateString.split(' ')[0];
        }
        
        // If it's already in YYYY-MM-DD format, return as is
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
          return dateString;
        }
        
        // Try to parse as Date and format
        try {
          const date = new Date(dateString);
          if (!isNaN(date.getTime())) {
            return date.toISOString().split('T')[0];
          }
        } catch (e) {
          console.warn('Failed to parse date:', dateString, e);
        }
        
        // Fallback to today
        return new Date().toISOString().split('T')[0];
      };
      
      if (isHistoricalMode && timeFilters) {
        if (timeFilters.mode === 'range' && timeFilters.startDate && timeFilters.endDate) {
          // Use provided date range - extract date only (YYYY-MM-DD)
          startDate = extractDateOnly(timeFilters.startDate);
          endDate = extractDateOnly(timeFilters.endDate);
        } else if (timeFilters.mode === 'single' && timeFilters.date) {
          // Single date - use same date for start and end
          startDate = extractDateOnly(timeFilters.date);
          endDate = extractDateOnly(timeFilters.date);
        } else {
          // Default to today
          const today = new Date().toISOString().split('T')[0];
          startDate = today;
          endDate = today;
        }
      } else {
        // Live mode - default to today
        const today = new Date().toISOString().split('T')[0];
        startDate = today;
        endDate = today;
      }

      queryParams.append('start_date', startDate);
      queryParams.append('end_date', endDate);

      // Add shift filter if provided and not all shifts selected
      // Only filter by shifts if a specific subset is selected (not all 3 shifts)
      if (timeFilters?.shifts && timeFilters.shifts.length > 0) {
        const allShifts = ['A', 'B', 'C'];
        const isAllShiftsSelected = allShifts.every(shift => timeFilters.shifts.includes(shift)) && 
                                   timeFilters.shifts.length === allShifts.length;
        
        // Only add shift filter if not all shifts are selected
        if (!isAllShiftsSelected) {
          queryParams.append('shifts', timeFilters.shifts.join(','));
        }
      }

      // Add order type filter based on activeTab
      if (activeTab === 'milling') {
        queryParams.append('order_type', 'MILLING');
      } else if (activeTab === 'packing') {
        queryParams.append('order_type', 'PACKING');
      }
      // If activeTab === 'all', don't add order_type filter

      // Add pagination
      queryParams.append('limit', itemsPerPage.toString());
      queryParams.append('offset', offset.toString());

      const url = getApiUrl(`/api/reports/summary?${queryParams.toString()}`);
      console.log('📊 Fetching orders from reports/summary API:', url);
      console.log('📊 Query params:', {
        startDate,
        endDate,
        shifts: timeFilters?.shifts,
        activeTab,
        isHistoricalMode,
        timeFilters
      });

      const response = await apiFetch(url);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', response.status, errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const responseData = await response.json();
      console.log('📊 API Response:', {
        success: responseData.success,
        total_count: responseData.total_count,
        orders_count: responseData.orders?.length || 0,
        summary: responseData.summary
      });
      
      if (!responseData.success) {
        throw new Error(responseData.error || 'Failed to fetch orders');
      }

      // Map API response to Order interface
      const apiOrders: Order[] = (responseData.orders || []).map((order: any) => ({
        id: order.id,
        po_number: order.po_number || order.order_id || '',
        material: order.material || '',
        version: order.version || '',
        quantity: order.quantity || 0,
        unit: order.unit || '',
        status: order.status || '',
        created_at: order.created_at || '',
        updated_at: order.updated_at || '',
        confirmed_qty: order.confirmed_qty || undefined,
        expected_weight: order.expected_weight?.toString() || undefined,
        order_type: order.order_type || getOrderTypeFromMaterial(order.material || ''),
      }));

      const totalCount = responseData.total_count || apiOrders.length;

      setOrders(apiOrders);
      setTotalOrders(totalCount);

      console.log(`✅ Fetched ${apiOrders.length} orders (total: ${totalCount})`);

    } catch (err) {
      console.error('Error fetching orders:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
      setOrders([]);
      setTotalOrders(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Only fetch when Orders tab is active
    if (mainTab === 'orders') {
      fetchOrders();
    }
  }, [currentPage, itemsPerPage, activeTab, isHistoricalMode, timeFilters, mainTab]);

  // Trigger print after all orders are loaded for printing
  useEffect(() => {
    if (isPrintMode && allOrdersForPrint.length > 0 && !isLoadingForPrint) {
      // Wait for React to re-render with the new data
      // Use requestAnimationFrame to ensure DOM is updated
      let frameId: number;
      let printTimeout: NodeJS.Timeout;
      let resetTimeout: NodeJS.Timeout | undefined;
      
      frameId = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Additional delay to ensure table is fully rendered with all rows
          printTimeout = setTimeout(() => {
            // Force a reflow to ensure all rows are rendered
            const tableWrapper = document.querySelector('.print-table-wrapper') as HTMLElement;
            if (tableWrapper) {
              // Force browser to recalculate layout
              void tableWrapper.offsetHeight;
              // Scroll to ensure all content is in viewport (helps with rendering)
              window.scrollTo(0, 0);
            }
            
            // Verify DOM has all rows before printing
            const tableRows = document.querySelectorAll('.print-table-wrapper tbody tr');
            const expectedRows = allOrdersForPrint.length;
            const actualRows = tableRows.length;
            
            console.log(`Print check: Expected ${expectedRows} rows, found ${actualRows} rows in DOM`);
            
            if (actualRows >= expectedRows) {
              console.log('✅ All rows rendered, triggering print...');
              // Small additional delay to ensure browser has processed all DOM changes
              setTimeout(() => {
                // Add a style tag to force browser to print at actual size (100% scale)
                const style = document.createElement('style');
                style.id = 'print-scale-fix';
                style.textContent = `
                  @media print {
                    @page {
                      size: A4 landscape !important;
                      margin: 0.5in !important;
                      size: 297mm 210mm landscape !important;
                    }
                    html, body {
                      width: 100% !important;
                      height: auto !important;
                      overflow: visible !important;
                      transform: scale(1) !important;
                      -webkit-transform: scale(1) !important;
                      zoom: 1 !important;
                    }
                    * {
                      transform: none !important;
                      -webkit-transform: none !important;
                      zoom: 1 !important;
                      scale: 1 !important;
                    }
                    .print-table-wrapper {
                      width: 100% !important;
                      height: auto !important;
                      max-height: none !important;
                      overflow: visible !important;
                      transform: none !important;
                      zoom: 1 !important;
                    }
                    .print-table-wrapper table {
                      width: 100% !important;
                      height: auto !important;
                      max-height: none !important;
                      page-break-inside: auto !important;
                      transform: none !important;
                      zoom: 1 !important;
                      font-size: 10px !important;
                    }
                    .print-table-wrapper tbody {
                      page-break-inside: auto !important;
                      height: auto !important;
                      max-height: none !important;
                    }
                    .print-table-wrapper tbody tr {
                      page-break-inside: avoid !important;
                      height: auto !important;
                    }
                  }
                `;
                document.head.appendChild(style);
                
                // Try to set print scale via CSS (browsers may ignore this, but worth trying)
                const printStyle = document.createElement('style');
                printStyle.id = 'print-no-scale';
                printStyle.textContent = `
                  @media print {
                    @page {
                      size: A4 landscape !important;
                    }
                  }
                `;
                document.head.appendChild(printStyle);
                
                // Small delay to ensure styles are applied
                setTimeout(() => {
                  window.print();
                }, 100);
                
                // Remove the style tags after printing
                resetTimeout = setTimeout(() => {
                  const styleTag = document.getElementById('print-scale-fix');
                  if (styleTag) {
                    styleTag.remove();
                  }
                  const printStyleTag = document.getElementById('print-no-scale');
                  if (printStyleTag) {
                    printStyleTag.remove();
                  }
                  // Reset after printing dialog closes
                  setIsPrintMode(false);
                  setAllOrdersForPrint([]);
                }, 1000);
              }, 200);
            } else {
              console.warn(`⚠️ Not all rows rendered yet. Retrying in 500ms...`);
              // Retry after a bit more time
              setTimeout(() => {
                const retryRows = document.querySelectorAll('.print-table-wrapper tbody tr').length;
                console.log(`Retry check: Found ${retryRows} rows`);
                if (retryRows >= expectedRows) {
                  setTimeout(() => {
                    // Add a style tag to force browser to print at actual size (100% scale)
                    const style = document.createElement('style');
                    style.id = 'print-scale-fix';
                    style.textContent = `
                      @media print {
                        @page {
                          size: A4 landscape !important;
                          margin: 0.5in !important;
                          size: 297mm 210mm landscape !important;
                        }
                        html, body {
                          width: 100% !important;
                          height: auto !important;
                          overflow: visible !important;
                          transform: scale(1) !important;
                          -webkit-transform: scale(1) !important;
                          zoom: 1 !important;
                        }
                        * {
                          transform: none !important;
                          -webkit-transform: none !important;
                          zoom: 1 !important;
                          scale: 1 !important;
                        }
                        .print-table-wrapper {
                          width: 100% !important;
                          height: auto !important;
                          max-height: none !important;
                          overflow: visible !important;
                          transform: none !important;
                          zoom: 1 !important;
                        }
                        .print-table-wrapper table {
                          width: 100% !important;
                          height: auto !important;
                          max-height: none !important;
                          page-break-inside: auto !important;
                          transform: none !important;
                          zoom: 1 !important;
                          font-size: 10px !important;
                        }
                        .print-table-wrapper tbody {
                          page-break-inside: auto !important;
                          height: auto !important;
                          max-height: none !important;
                        }
                        .print-table-wrapper tbody tr {
                          page-break-inside: avoid !important;
                          height: auto !important;
                        }
                      }
                    `;
                    document.head.appendChild(style);
                    
                    // Try to set print scale via CSS
                    const printStyle = document.createElement('style');
                    printStyle.id = 'print-no-scale';
                    printStyle.textContent = `
                      @media print {
                        @page {
                          size: A4 landscape !important;
                        }
                      }
                    `;
                    document.head.appendChild(printStyle);
                    
                    // Small delay to ensure styles are applied
                    setTimeout(() => {
                      window.print();
                    }, 100);
                    
                    // Remove the style tags after printing
                    resetTimeout = setTimeout(() => {
                      const styleTag = document.getElementById('print-scale-fix');
                      if (styleTag) {
                        styleTag.remove();
                      }
                      const printStyleTag = document.getElementById('print-no-scale');
                      if (printStyleTag) {
                        printStyleTag.remove();
                      }
                      setIsPrintMode(false);
                      setAllOrdersForPrint([]);
                    }, 1000);
                  }, 200);
                } else {
                  console.error('Failed to render all rows for printing');
                  setIsPrintMode(false);
                  setAllOrdersForPrint([]);
                  alert(`Failed to load all orders for printing. Expected ${expectedRows} rows but only found ${retryRows}. Please try again.`);
                }
              }, 500);
            }
          }, 1500); // Increased delay to 1.5 seconds
        });
      });
      
      return () => {
        if (frameId) cancelAnimationFrame(frameId);
        if (printTimeout) clearTimeout(printTimeout);
        if (resetTimeout) clearTimeout(resetTimeout);
      };
    }
  }, [isPrintMode, allOrdersForPrint, isLoadingForPrint]);

  // Refresh orders data
  const refreshData = async () => {
    await fetchOrders();
  };

  // Helper function to format database timestamp without timezone conversion
  // This displays the exact time as stored in the database
  const formatDatabaseTimestamp = (timestamp: string): string => {
    if (!timestamp) return 'N/A';
    
    try {
      // Parse the ISO timestamp string directly without timezone conversion
      // Input format: "2026-01-28T00:00:49.384555-08:00" or "2026-01-28 00:00:49.384555-08"
      
      // Extract date and time parts from the timestamp (ignore timezone offset)
      let dateTimePart = timestamp;
      
      // Remove timezone offset if present (e.g., -08:00, +04:00, -08)
      dateTimePart = dateTimePart.replace(/[+-]\d{2}:?\d{0,2}$/, '');
      
      // Replace 'T' with space if present
      dateTimePart = dateTimePart.replace('T', ' ');
      
      // Split into date and time
      const [datePart, timePart] = dateTimePart.split(' ');
      
      if (!datePart || !timePart) {
        return timestamp; // Return original if can't parse
      }
      
      // Parse date parts (YYYY-MM-DD)
      const [year, month, day] = datePart.split('-').map(Number);
      
      // Parse time parts (HH:MM:SS.microseconds)
      const timeWithoutMicro = timePart.split('.')[0]; // Remove microseconds
      const [hours, minutes, seconds] = timeWithoutMicro.split(':').map(Number);
      
      // Format date as M/D/YYYY
      const formattedDate = `${month}/${day}/${year}`;
      
      // Format time as HH:MM:SS AM/PM
      const hour12 = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
      const ampm = hours < 12 ? 'AM' : 'PM';
      const formattedTime = `${hour12}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')} ${ampm}`;
      
      return `${formattedDate}, ${formattedTime}`;
    } catch (e) {
      console.warn('Failed to parse timestamp:', timestamp, e);
      return timestamp; // Return original if parsing fails
    }
  };
  
  // Function to validate and sanitize KPI data
  const validateKpiData = (data: KpiData): KpiData => {
    const sanitizeValue = (value: any, key?: string): number => {
      if (value === null || value === undefined) {
        if (key) console.warn(`⚠️ KPI value is null/undefined for key: ${key}`);
        return 0;
      }
      const numValue = parseFloat(value.toString());
      if (isNaN(numValue)) {
        if (key) console.warn(`⚠️ KPI value is NaN for key: ${key}, raw value:`, value);
        return 0;
      }
      return numValue;
    };

    // Log raw data structure
    console.log('🔍 Validating KPI data structure:', {
      hasMillingKpis: !!data.milling_kpis,
      hasPackingKpis: !!data.packing_kpis,
      millingKeys: data.milling_kpis ? Object.keys(data.milling_kpis) : [],
      packingKeys: data.packing_kpis ? Object.keys(data.packing_kpis) : [],
    });

    const validatedData = {
      milling_kpis: {
        "Mill Throughput (%)": sanitizeValue(data.milling_kpis?.["Mill Throughput (%)"], "Mill Throughput (%)"),
        "Mill Time Efficiency (%)": sanitizeValue(data.milling_kpis?.["Mill Time Efficiency (%)"], "Mill Time Efficiency (%)"),
        "Total Utilization (%)": sanitizeValue(data.milling_kpis?.["Total Utilization (%)"], "Total Utilization (%)"),
        "Milling Gain": sanitizeValue(data.milling_kpis?.["Milling Gain"], "Milling Gain"),
        "Milling Screening (%)": sanitizeValue(data.milling_kpis?.["Milling Screening (%)"], "Milling Screening (%)"),
        "Flour Extraction (%)": sanitizeValue(data.milling_kpis?.["Flour Extraction (%)"], "Flour Extraction (%)"),
        "Milling Loss (%)": sanitizeValue(data.milling_kpis?.["Milling Loss (%)"], "Milling Loss (%)"),
        "Net Hours (hrs)": sanitizeValue(data.milling_kpis?.["Net Hours (hrs)"], "Net Hours (hrs)"),
        "Downtime (hrs)": sanitizeValue(data.milling_kpis?.["Downtime (hrs)"], "Downtime (hrs)"),
        "Max Utilization of Milling Capacity (%)": sanitizeValue(data.milling_kpis?.["Max Utilization of Milling Capacity (%)"], "Max Utilization of Milling Capacity (%)"),
        "Pre Cleaning Screening (%)": sanitizeValue(data.milling_kpis?.["Pre Cleaning Screening (%)"], "Pre Cleaning Screening (%)"),
        "1st Break Capacity per Hour (t/h)": sanitizeValue(data.milling_kpis?.["1st Break Capacity per Hour (t/h)"], "1st Break Capacity per Hour (t/h)"),
        "Bran Extraction (%)": sanitizeValue(data.milling_kpis?.["Bran Extraction (%)"], "Bran Extraction (%)"),
      },
      packing_kpis: {
        "Packing Line Capacity (bags/hr)": sanitizeValue(data.packing_kpis?.["Packing Line Capacity (bags/hr)"], "Packing Line Capacity (bags/hr)"),
        "Daily Packing Output (bags)": sanitizeValue(data.packing_kpis?.["Daily Packing Output (bags)"], "Daily Packing Output (bags)"),
        "Net Hours (hrs)": sanitizeValue(data.packing_kpis?.["Net Hours (hrs)"], "Net Hours (hrs)"),
        "Downtime (hrs)": sanitizeValue(data.packing_kpis?.["Downtime (hrs)"], "Downtime (hrs)"),
        "Machine Utilization (%)": sanitizeValue(data.packing_kpis?.["Machine Utilization (%)"], "Machine Utilization (%)"),
        "Packing Line Capacity (tons/hr)": sanitizeValue(data.packing_kpis?.["Packing Line Capacity (tons/hr)"], "Packing Line Capacity (tons/hr)"),
      },
      timestamp: data.timestamp,
      data_source: data.data_source,
    };

    // Log validation results
    console.log('✅ Validated KPI values:', {
      milling: validatedData.milling_kpis,
      packing: validatedData.packing_kpis,
    });

    return validatedData;
  };

  // Helper function to map API payload keys to table column names
  const mapPayloadToTableFormat = (payload: Record<string, string>, department: 'MILLING' | 'PACKING'): Record<string, number> => {
    const sanitizeValue = (value: any): number => {
      if (value === null || value === undefined) return 0;
      const numValue = parseFloat(value.toString());
      return isNaN(numValue) ? 0 : numValue;
    };

    if (department === 'MILLING') {
      return {
        "Mill Throughput (%)": sanitizeValue(payload.MILL_THROUGHPUT),
        "Mill Time Efficiency (%)": sanitizeValue(payload.MILL_TIME_EFFICIENCY),
        "Total Utilization (%)": sanitizeValue(payload.TOTAL_UTILIZATION),
        "Milling Gain": sanitizeValue(payload.MILLING_GAIN),
        "Milling Screening (%)": sanitizeValue(payload.MILLING_SCREENING),
        "Flour Extraction (%)": sanitizeValue(payload.FLOUR_EXTRACTION),
        "Milling Loss (%)": sanitizeValue(payload.MILLING_LOSS),
        "Net Hours (hrs)": sanitizeValue(payload.NET_HOURS),
        "Downtime (hrs)": sanitizeValue(payload.MILLING_DOWN_TIME),
        "Max Utilization of Milling Capacity (%)": sanitizeValue(payload.MAX_UTILIZATION),
        "Pre Cleaning Screening (%)": sanitizeValue(payload.PRE_CLEAN_SCREENING),
        "1st Break Capacity per Hour (t/h)": sanitizeValue(payload.BREAK_CAPACITY),
        "Bran Extraction (%)": sanitizeValue(payload.BRAN_EXTRACTION),
        "Pre Cleaning Water (L)": sanitizeValue(payload.PRE_CLEAN_WATER),
        "Water Clean Wheat (L)": sanitizeValue(payload.CLEANING_WATER),
        "Total Water Used (L)": sanitizeValue(payload.TOTAL_WATER),
      };
    } else {
      return {
        "Packing Line Capacity (bags/hr)": sanitizeValue(payload.PACKING_CAPACITY_BAG),
        "Daily Packing Output (bags)": sanitizeValue(payload.PACKING_BAG),
        "Net Hours (hrs)": sanitizeValue(payload.PACKING_HOURS),
        "Downtime (hrs)": sanitizeValue(payload.PACKING_TOTAL_DOWNTIME),
        "Machine Utilization (%)": sanitizeValue(payload.PACKING_MACHINE_UTILIZ),
        "Packing Line Capacity (tons/hr)": sanitizeValue(payload.PACKING_CAPACITY_TON),
      };
    }
  };
  
  // Fetch KPI data
  const fetchKpiData = async () => {
    try {
      setKpiLoading(true);
      setKpiError(null);
      
      // If filters are applied, ALWAYS use historical API (never fall back to live)
      if (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range')) {
        console.log('📊 Fetching historical KPI tracking data with filters:', kpiTimeFilters);
        
        // Determine start and end dates from filters
        let startDate: string;
        let endDate: string;
        
        if (kpiTimeFilters.mode === 'single' && kpiTimeFilters.date) {
          startDate = kpiTimeFilters.date.split(' ')[0];  // Extract YYYY-MM-DD
          endDate = startDate;
        } else if (kpiTimeFilters.mode === 'range' && kpiTimeFilters.startDate && kpiTimeFilters.endDate) {
          startDate = kpiTimeFilters.startDate.split(' ')[0];
          endDate = kpiTimeFilters.endDate.split(' ')[0];
        } else {
          // If filters are applied but dates are missing, show error
          setKpiError('Invalid date filters. Please select a valid date or date range.');
          setKpiTrackingData([]);
          setKpiTotalItems(0);
          setKpiData(null);
          return;
        }
        
        // Call the new KPI tracking API
        const response = await kpiApi.getKpiTracking({
          startDate,
          endDate,
          shifts: kpiTimeFilters.shifts,
          department: kpiSubTab === 'milling' ? 'MILLING' : 'PACKING',
          limit: kpiItemsPerPage,
          offset: (kpiCurrentPage - 1) * kpiItemsPerPage
        });
        
        console.log('📊 KPI tracking response:', response);
        
        if (response.success) {
          setKpiTrackingData(response.data);
          setKpiTotalItems(response.total_count);
          setKpiData(null); // Clear live data when showing historical
          // If no data found, that's okay - we'll show "No data" message
          if (response.data.length === 0) {
            console.log('📊 No historical KPI data found for the selected filters');
          }
        } else {
          throw new Error('Failed to fetch KPI tracking data');
        }
      } else {
        // Live mode - only fetch current KPIs when NO filters are applied
        const data = await kpiApi.getKpis();
        console.log('📊 Raw KPI data from API:', data);
        console.log('📊 Milling KPIs:', data.milling_kpis);
        console.log('📊 Packing KPIs:', data.packing_kpis);
        const validatedData = validateKpiData(data);
        console.log('📊 Validated KPI data:', validatedData);
        console.log('📊 Validated Milling KPIs:', validatedData.milling_kpis);
        setKpiData(validatedData);
        setKpiTrackingData([]); // Clear tracking data when showing live
        setKpiTotalItems(1);
      }
    } catch (err) {
      setKpiError(err instanceof Error ? err.message : 'Failed to fetch KPI data');
      console.error('Error fetching KPI data:', err);
      // When in historical mode and error occurs, clear live data
      if (kpiTimeFilters) {
        setKpiData(null);
        setKpiTrackingData([]);
        setKpiTotalItems(0);
      }
    } finally {
      setKpiLoading(false);
    }
  };
  
  // Auto-apply default filters when KPI tab is first loaded (if no filters are set)
  useEffect(() => {
    if (mainTab === 'kpis' && !kpiTimeFilters) {
      // Apply default filters: today's date, daily period, all shifts
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayStr = format(today, 'yyyy-MM-dd HH:mm:ss');
      
      handleKpiApplyFilters({
        mode: 'single',
        date: todayStr,
        shifts: ['A', 'B', 'C'],
        timeRange: 'daily'
      });
    }
  }, [mainTab]); // Only run when mainTab changes, not on every render

  // Fetch KPI data when KPIs tab is active or filters change
  useEffect(() => {
    if (mainTab === 'kpis') {
      fetchKpiData();
    }
  }, [mainTab, isKpiHistoricalMode, kpiTimeFilters, kpiSubTab, kpiCurrentPage, kpiItemsPerPage]);

  // Handle time filter apply for Orders - now uses the hook
  const handleTimeFilterApply = (filters: {
    mode: 'single' | 'range';
    date?: string;
    startDate?: string;
    endDate?: string;
    shifts?: string[];
    timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
  }) => {
    handleApplyFilters({
      ...filters,
      shifts: filters.shifts || []
    });
    // Reset to first page when filters change
    setCurrentPage(1);
    // fetchOrders will be called automatically by useEffect when timeFilters changes
    console.log('✅ Applied historical filters for Orders:', filters);
  };
  
  // Handle time filter apply for KPIs
  const handleKpiTimeFilterApply = (filters: {
    mode: 'single' | 'range';
    date?: string;
    startDate?: string;
    endDate?: string;
    shifts?: string[];
    timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
  }) => {
    handleKpiApplyFilters({
      ...filters,
      shifts: filters.shifts || []
    });
    // Reset to first page when filters change
    setKpiCurrentPage(1);
    // fetchKpiData will be called automatically by useEffect when kpiTimeFilters changes
    console.log('✅ Applied historical filters for KPIs:', filters);
  };


  // Filter orders based on search term and order type
  const filterOrdersList = (ordersList: Order[]) => {
    return ordersList.filter(order => {
      // Determine order type from material number
      const orderType = getOrderTypeFromMaterial(order.material || '');

      // Filter by order type (MILLING or PACKING)
      if (activeTab !== 'all') {
        if (activeTab === 'milling' && orderType !== 'MILLING') return false;
        if (activeTab === 'packing' && orderType !== 'PACKING') return false;
      }

      // Filter by search term
      if (!searchTerm) return true;
      const searchLower = searchTerm.toLowerCase();
      return (
        order.id.toString().includes(searchLower) ||
        (order.po_number && order.po_number.toLowerCase().includes(searchLower)) ||
        (order.material && order.material.toLowerCase().includes(searchLower)) ||
        (order.version && order.version.toLowerCase().includes(searchLower))
      );
    });
  };

  // Filtered orders for display (paginated) - use all orders when printing
  // When printing, use allOrdersForPrint directly (already filtered), otherwise filter the current page orders
  const filteredOrders = isPrintMode && allOrdersForPrint.length > 0 
    ? allOrdersForPrint 
    : filterOrdersList(orders);

  // Calculate counts by order type (using material-based detection)
  const millingOrders = orders.filter(o => getOrderTypeFromMaterial(o.material || '') === 'MILLING');
  const packingOrders = orders.filter(o => getOrderTypeFromMaterial(o.material || '') === 'PACKING');

  // Pagination handlers
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1);
  };

  // Calculate total pages
  const totalPages = Math.ceil(totalOrders / itemsPerPage);

  // Helper function to convert image to base64
  const getImageBase64 = (imagePath: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0);
          resolve(canvas.toDataURL('image/png'));
        } else {
          reject(new Error('Could not get canvas context'));
        }
      };
      img.onerror = reject;
      img.src = imagePath;
    });
  };

  // Export PDF function
  const handleExportPDF = async () => {
    try {
      const doc = new jsPDF('landscape', 'mm', 'a4'); // Landscape orientation for better table fit

      // Convert logos to base64
      const [herculesLogoBase64, asmLogoBase64, modernMillsLogoBase64] = await Promise.all([
        getImageBase64(herculesLogo),
        getImageBase64(asmLogo),
        getImageBase64(modernMillsLogo)
      ]);

      // Modern header with logos
      const pageWidth = doc.internal.pageSize.getWidth();
      const headerHeight = 25;
      
      // Left side - Hercules Logo
      doc.addImage(herculesLogoBase64, 'PNG', 15, 8, 30, 12);
      
      // Right side - ASM and Modern Mills logos (side by side)
      const logoSpacing = 25;
      const rightStartX = pageWidth - 55;
      const logoY = 10;
      doc.addImage(asmLogoBase64, 'PNG', rightStartX, logoY, 18, 8);
      doc.addImage(modernMillsLogoBase64, 'PNG', rightStartX + logoSpacing, logoY, 18, 8);

      // Title in center
      doc.setFontSize(18);
      doc.setFont('helvetica', 'bold');
      const titleText = 'HERCULES SFMS - Orders Report';
      const titleWidth = doc.getTextWidth(titleText);
      doc.text(titleText, (pageWidth - titleWidth) / 2, 15);

      // Report details below header
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      const reportDetailsY = headerHeight + 5;
      doc.text(`Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`, 15, reportDetailsY);
      doc.text(`Report Type: All Orders`, 15, reportDetailsY + 5);
      doc.text(`Total Records: ${filteredOrders.length}`, 15, reportDetailsY + 10);

      // Table with improved styling
      autoTable(doc, {
        startY: headerHeight + 25,
        head: [["Order ID", "PO Number", "Material", "Version", "Order Type", "Quantity", "Unit", "Status", "Created At"]],
        body: filteredOrders.map((order) => [
          order.id.toString(),
          order.po_number || 'N/A',
          order.material || 'N/A',
          order.version || 'N/A',
          order.order_type || 'N/A',
          order.quantity?.toString() || '0',
          order.unit || 'N/A',
          order.status || 'N/A',
          new Date(order.created_at).toLocaleDateString()
        ]),
        styles: {
          fontSize: 8,
          cellPadding: 3,
          overflow: 'linebreak',
          halign: 'left',
          valign: 'middle'
        },
        headStyles: {
          fillColor: [6, 182, 212], // Cyan color matching theme
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          fontSize: 9,
          halign: 'center'
        },
        alternateRowStyles: {
          fillColor: [248, 250, 252] // Light gray for alternating rows
        },
        columnStyles: {
          0: { halign: 'center', cellWidth: 18 }, // Order ID - centered, narrow
          1: { halign: 'center', cellWidth: 22 }, // PO Number - centered
          2: { halign: 'left', cellWidth: 30 },   // Material - left aligned, wider
          3: { halign: 'center', cellWidth: 18 }, // Version - centered
          4: { halign: 'center', cellWidth: 18 }, // Order Type - centered
          5: { halign: 'center', cellWidth: 18 }, // Quantity - centered
          6: { halign: 'center', cellWidth: 12 }, // Unit - centered, narrow
          7: { halign: 'center', cellWidth: 22 }, // Status - centered
          8: { halign: 'center', cellWidth: 22 }  // Created At - centered
        },
        margin: { top: 50, right: 20, bottom: 20, left: 20 },
        tableWidth: 'auto',
        showHead: 'everyPage',
        pageBreak: 'auto',
        didDrawPage: function (data) {
          // Add header on every page
          const pageWidth = doc.internal.pageSize.getWidth();
          
          // Left side - Hercules Logo
          doc.addImage(herculesLogoBase64, 'PNG', 15, 8, 30, 12);
          
          // Right side - ASM and Modern Mills logos (side by side)
          const logoSpacing = 25;
          const rightStartX = pageWidth - 55;
          const logoY = 10;
          doc.addImage(asmLogoBase64, 'PNG', rightStartX, logoY, 18, 8);
          doc.addImage(modernMillsLogoBase64, 'PNG', rightStartX + logoSpacing, logoY, 18, 8);

          // Title in center
          doc.setFontSize(18);
          doc.setFont('helvetica', 'bold');
          const titleText = 'HERCULES SFMS - Orders Report';
          const titleWidth = doc.getTextWidth(titleText);
          doc.text(titleText, (pageWidth - titleWidth) / 2, 15);

          // Add page numbers
          const pageCount = doc.getNumberOfPages();
          const currentPage = data.pageNumber;

          doc.setFontSize(8);
          doc.setFont('helvetica', 'normal');
          doc.text(`Page ${currentPage} of ${pageCount}`,
            doc.internal.pageSize.width - 30,
            doc.internal.pageSize.height - 10);
        }
      });

      // Footer with summary
      const finalY = (doc as any).lastAutoTable.finalY || 50;
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text('Report Summary:', 20, finalY + 15);

      doc.setFont('helvetica', 'normal');
      doc.text(`• Total Orders: ${filteredOrders.length}`, 20, finalY + 25);
      doc.text(`• Confirmed Orders: ${filteredOrders.filter(o => o.status === 'Confirmed').length}`, 20, finalY + 32);
      doc.text(`• Rejected Orders: ${filteredOrders.filter(o => o.status === 'Rejected').length}`, 20, finalY + 39);
      doc.text(`• Efficiency Rate: ${filteredOrders.length > 0 ? Math.round((filteredOrders.filter(o => o.status === 'Confirmed').length / filteredOrders.length) * 100) : 0}%`, 20, finalY + 46);

      doc.save(`Orders_Report_${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (error) {
      console.error('Error exporting PDF:', error);
      alert('❌ Failed to export PDF');
    }
  };

  // Export CSV function
  const handleExportCSV = () => {
    try {
      // CSV headers
      const headers = ['Order ID', 'PO Number', 'Material', 'Version', 'Order Type', 'Quantity', 'Unit', 'Status', 'Created At'];

      // CSV data rows
      const csvData = filteredOrders.map(order => [
        order.id.toString(),
        order.po_number || 'N/A',
        order.material || 'N/A',
        order.version || 'N/A',
        order.order_type || 'N/A',
        order.quantity?.toString() || '0',
        order.unit || 'N/A',
        order.status || 'N/A',
        new Date(order.created_at).toLocaleDateString()
      ]);

      // Combine headers and data
      const csvContent = [headers, ...csvData]
        .map(row => row.map(field => `"${field}"`).join(','))
        .join('\n');

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `Orders_Report_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('❌ Failed to export CSV');
    }
  };

  // Print function - fetches all orders before printing using reports/summary API
  const handlePrint = async () => {
    setIsPrintMode(true);
    setIsLoadingForPrint(true);
    
    try {
      // Build query parameters (same as fetchOrders but without pagination)
      const queryParams = new URLSearchParams();
      
      // Helper function to extract YYYY-MM-DD from various date formats
      const extractDateOnly = (dateString: string): string => {
        if (!dateString) return new Date().toISOString().split('T')[0];
        
        // If it's an ISO string with 'T', split by 'T'
        if (dateString.includes('T')) {
          return dateString.split('T')[0];
        }
        
        // If it's in format "YYYY-MM-DD HH:mm:ss" or "YYYY-MM-DD HH:mm", split by space
        if (dateString.includes(' ')) {
          return dateString.split(' ')[0];
        }
        
        // If it's already in YYYY-MM-DD format, return as is
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
          return dateString;
        }
        
        // Try to parse as Date and format
        try {
          const date = new Date(dateString);
          if (!isNaN(date.getTime())) {
            return date.toISOString().split('T')[0];
          }
        } catch (e) {
          console.warn('Failed to parse date:', dateString, e);
        }
        
        // Fallback to today
        return new Date().toISOString().split('T')[0];
      };
      
      // Get date range from timeFilters or use today as default
      let startDate: string;
      let endDate: string;
      
      if (isHistoricalMode && timeFilters) {
        if (timeFilters.mode === 'range' && timeFilters.startDate && timeFilters.endDate) {
          startDate = extractDateOnly(timeFilters.startDate);
          endDate = extractDateOnly(timeFilters.endDate);
        } else if (timeFilters.mode === 'single' && timeFilters.date) {
          startDate = extractDateOnly(timeFilters.date);
          endDate = extractDateOnly(timeFilters.date);
        } else {
          const today = new Date().toISOString().split('T')[0];
          startDate = today;
          endDate = today;
        }
      } else {
        const today = new Date().toISOString().split('T')[0];
        startDate = today;
        endDate = today;
      }

      queryParams.append('start_date', startDate);
      queryParams.append('end_date', endDate);

      // Add shift filter if provided and not all shifts selected
      if (timeFilters?.shifts && timeFilters.shifts.length > 0) {
        const allShifts = ['A', 'B', 'C'];
        const isAllShiftsSelected = allShifts.every(shift => timeFilters.shifts.includes(shift)) && 
                                   timeFilters.shifts.length === allShifts.length;
        
        // Only add shift filter if not all shifts are selected
        if (!isAllShiftsSelected) {
          queryParams.append('shifts', timeFilters.shifts.join(','));
        }
      }

      if (activeTab === 'milling') {
        queryParams.append('order_type', 'MILLING');
      } else if (activeTab === 'packing') {
        queryParams.append('order_type', 'PACKING');
      }

      // Fetch all orders (use large limit)
      queryParams.append('limit', '10000');
      queryParams.append('offset', '0');

      const url = getApiUrl(`/api/reports/summary?${queryParams.toString()}`);
      console.log('📄 Fetching all orders for print from reports/summary API:', url);

      const response = await apiFetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const responseData = await response.json();
      
      if (!responseData.success) {
        throw new Error(responseData.error || 'Failed to fetch orders for print');
      }

      // Map API response to Order interface
      const allOrders: Order[] = (responseData.orders || []).map((order: any) => ({
        id: order.id,
        po_number: order.po_number || order.order_id || '',
        material: order.material || '',
        version: order.version || '',
        quantity: order.quantity || 0,
        unit: order.unit || '',
        status: order.status || '',
        created_at: order.created_at || '',
        updated_at: order.updated_at || '',
        confirmed_qty: order.confirmed_qty || undefined,
        expected_weight: order.expected_weight?.toString() || undefined,
        order_type: order.order_type || getOrderTypeFromMaterial(order.material || ''),
      }));

      // Apply search filter if any
      const allFilteredOrders = filterOrdersList(allOrders);
      
      console.log(`✅ Fetched ${allFilteredOrders.length} orders for print`);
      setAllOrdersForPrint(allFilteredOrders);
      
    } catch (error) {
      console.error('Error fetching all orders for print:', error);
      alert('Failed to load orders for printing. Please try again.');
      setIsPrintMode(false);
      setAllOrdersForPrint([]);
    } finally {
      setIsLoadingForPrint(false);
    }
  };

  return (
    <WaterSystemLayout title="Orders Reports" subtitle="Orders Management & Analytics">
      <style>{`
        @media print {
          /* Reset page margins - CRITICAL: Use explicit size to prevent scaling */
          @page {
            margin: 0.5in !important;
            size: A4 landscape !important;
            /* Allow content to flow across pages */
            orphans: 3 !important;
            widows: 3 !important;
            /* Explicitly set page size to prevent scaling */
            size: 297mm 210mm landscape !important;
          }
          
          /* CRITICAL: Prevent browser from scaling to fit on one page */
          @page {
            size: A4 landscape !important;
            margin: 0.5in !important;
            size: 297mm 210mm landscape !important;
          }
          
          /* Force browser to print at actual size without scaling */
          html, body {
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            /* Prevent any scaling */
            transform: scale(1) !important;
            -webkit-transform: scale(1) !important;
            zoom: 1 !important;
            /* Force actual size */
            font-size: 12pt !important;
          }
          
          /* CRITICAL: Prevent any element from being scaled */
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            transform: none !important;
            -webkit-transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
          }
          
          /* Prevent browser from scaling to fit on one page - CRITICAL */
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
            -webkit-transform: none !important;
            -moz-transform: none !important;
            -ms-transform: none !important;
            -o-transform: none !important;
          }
          
          /* Force browser to use actual size, not scale to fit */
          html {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            transform: scale(1) !important;
            zoom: 1 !important;
            -webkit-transform: scale(1) !important;
          }
          
          /* Explicitly prevent any container from forcing single page */
          body > * {
            page-break-inside: auto !important;
            break-inside: auto !important;
            height: auto !important;
            max-height: none !important;
          }
          
          /* Ensure body and html are visible and can span multiple pages */
          body, html {
            background: white !important;
            margin: 0 !important;
            padding: 0 !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            overflow: visible !important;
            page-break-inside: auto !important;
            /* Prevent scaling */
            transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
          }
          
          /* Hide sidebar, navigation, buttons, filters, etc. */
          nav, aside, button, header, footer {
            display: none !important;
          }
          
          /* Hide Sidebar component - target by its specific structure and classes */
          div[class*="bg-slate-900"][class*="border-r"][class*="backdrop-blur"],
          div[class*="w-16"][class*="h-screen"][class*="border-r"],
          div[class*="w-64"][class*="h-screen"][class*="border-r"],
          /* Hide any element that looks like a sidebar (has border-r and specific width) */
          div[class*="border-r"]:not([class*="flex-1"]):not([class*="print"]):not([class*="table"]):not([class*="wrapper"]),
          /* Hide any sibling element before flex-1 (the main content) */
          div[class*="flex"] > div:not([class*="flex-1"]):not([class*="fixed"]):not([class*="absolute"]):not([class*="video"]):not([class*="inset"]),
          /* Hide elements with sidebar-like width that aren't the main content */
          div[class*="w-16"]:not([class*="flex-1"]),
          div[class*="w-64"]:not([class*="flex-1"]) {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
          }
          
          /* Hide all sidebar-related elements */
          [class*="sidebar"],
          [class*="Sidebar"],
          [id*="sidebar"],
          [id*="Sidebar"],
          aside,
          .sidebar,
          .Sidebar,
          #sidebar,
          #Sidebar,
          [data-sidebar],
          [role="complementary"],
          [role="navigation"]:not(.print-table-wrapper),
          /* Hide any fixed or sticky sidebars */
          [class*="fixed"][class*="left"],
          [class*="fixed"][class*="right"],
          [class*="sticky"][class*="left"],
          [class*="sticky"][class*="right"],
          /* Hide Sidebar component specifically - target by common classes */
          [class*="w-16"][class*="border-r"],
          [class*="w-64"][class*="border-r"],
          [class*="bg-slate-900"][class*="border-r"],
          [class*="backdrop-blur"][class*="border-r"],
          /* Hide first child if it's likely the sidebar */
          body > div > div:first-child:not([class*="flex-1"]):not([class*="main"]):not([class*="content"]),
          /* Hide any element with sidebar-like width classes */
          [class*="w-16"]:not([class*="flex-1"]):not(.print-table-wrapper),
          [class*="w-64"]:not([class*="flex-1"]):not(.print-table-wrapper) {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
          }
          
          /* Specifically target the Sidebar component structure */
          div[class*="h-screen"][class*="flex"] > div:first-child:not([class*="flex-1"]),
          div[class*="h-screen"][class*="flex"] > div:nth-child(2):not([class*="flex-1"]),
          /* Target any direct child of flex container that has sidebar-like classes */
          div[class*="flex"] > div:not([class*="flex-1"]):not([class*="fixed"]):not([class*="absolute"])[class*="border-r"],
          /* Hide video background and overlays */
          div[class*="fixed"][class*="inset-0"][class*="pointer-events-none"],
          video {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -9999px !important;
          }
          
          /* Hide all sections except orders section */
          .w-full.space-y-6 > div:not(.orders-section) {
            display: none !important;
          }
          
          /* Ensure main content takes full width when sidebar is hidden */
          [class*="main"],
          [class*="content"],
          [class*="container"]:not(.print-table-wrapper),
          main,
          .main-content,
          .content-area,
          /* Target the flex-1 main content area */
          div[class*="flex-1"],
          div[class*="flex"][class*="flex-col"] {
            width: 100% !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            flex: 1 1 100% !important;
          }
          
          /* Ensure parent flex container doesn't reserve space for sidebar */
          div[class*="flex"][class*="h-screen"] {
            flex-direction: column !important;
          }
          
          div[class*="flex"][class*="h-screen"] > div[class*="flex-1"] {
            width: 100% !important;
            margin-left: 0 !important;
            flex: 1 1 100% !important;
          }
          
          /* Adjust flex/grid layouts to remove sidebar space */
          [class*="flex"],
          [class*="grid"] {
            gap: 0 !important;
          }
          
          /* Remove any left margin/padding that was for sidebar */
          body > *,
          [class*="layout"],
          [class*="Layout"] {
            margin-left: 0 !important;
            padding-left: 0 !important;
          }
          
          /* Hide UI elements within orders section */
          .orders-section > div:first-child,
          .orders-section .flex.flex-wrap,
          .orders-section .flex.items-center.justify-between,
          .orders-section .relative,
          .orders-section .mt-4 {
            display: none !important;
          }
          
          /* Ensure all parent containers are visible and can span multiple pages */
          [class*="WaterSystemLayout"],
          [class*="WaterSystemLayout"] > *,
          [class*="WaterSystemLayout"] > * > *,
          .w-full,
          .w-full.space-y-6,
          .orders-section,
          .orders-section > div,
          .orders-section > div > div,
          .orders-section > div > div > div {
            display: block !important;
            visibility: visible !important;
            background: white !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            overflow: visible !important;
            page-break-inside: auto !important;
          }
          
          /* Ensure tab content is visible and can span multiple pages */
          .p-6 {
            display: block !important;
            visibility: visible !important;
            padding: 0 !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            overflow: visible !important;
            page-break-inside: auto !important;
          }
          
          /* Show only the orders table container */
          .print-table-wrapper {
            display: block !important;
            position: relative !important;
            width: 100% !important;
            margin: 0 auto !important;
            padding: 20px !important;
            page-break-inside: auto !important;
            background: white !important;
            visibility: visible !important;
            overflow: visible !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            /* Prevent scaling */
            transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
            /* Force multi-page printing */
            break-inside: auto !important;
            page-break-after: auto !important;
          }
          
          /* Ensure all table elements are visible */
          .print-table-wrapper * {
            visibility: visible !important;
          }
          
          /* Print header with logos */
          .print-header {
            display: none !important;
          }
          
          .print-table-wrapper .print-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            margin-bottom: 20px !important;
            padding-bottom: 15px !important;
            border-bottom: 2px solid #000 !important;
            page-break-after: avoid !important;
            width: 100% !important;
          }
          
          .print-header-left {
            display: flex !important;
            align-items: center !important;
          }
          
          .print-header-left img {
            display: block !important;
            height: auto !important;
            max-height: 50px !important;
            width: auto !important;
            max-width: 150px !important;
          }
          
          .print-header-right {
            display: flex !important;
            align-items: center !important;
            gap: 20px !important;
          }
          
          .print-header-right img {
            display: block !important;
            height: auto !important;
            max-height: 45px !important;
            width: auto !important;
            max-width: 120px !important;
          }
          
          /* Print title and date */
          .print-table-wrapper::before {
            content: "HERCULES SFMS - ORDERS REPORT";
            display: block;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-top: 10px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 2px solid #000;
          }
          
          .print-table-wrapper::after {
            content: attr(data-print-date);
            display: block;
            font-size: 12px;
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
          }
          
          /* Remove overflow restrictions in print */
          .print-table-wrapper {
            overflow: visible !important;
            overflow-x: visible !important;
            overflow-y: visible !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            width: 100% !important;
            /* Prevent scaling - CRITICAL for multi-page printing */
            transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
            -webkit-transform: none !important;
            -moz-transform: none !important;
            -ms-transform: none !important;
            -o-transform: none !important;
            /* Explicitly allow content to span multiple pages */
            page-break-inside: auto !important;
            break-inside: auto !important;
          }
          
          /* Ensure table is properly styled for print */
          .print-table-wrapper table {
            display: table !important;
            border-collapse: collapse !important;
            width: 100% !important;
            font-size: 10px !important;
            font-family: Arial, Helvetica, sans-serif !important;
            page-break-inside: auto !important;
            visibility: visible !important;
            background: white !important;
            table-layout: auto !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            overflow: visible !important;
            /* Prevent scaling */
            transform: none !important;
            zoom: 1 !important;
            scale: 1 !important;
            /* Force multi-page printing - CRITICAL */
            break-inside: auto !important;
            page-break-inside: auto !important;
            page-break-after: auto !important;
            page-break-before: auto !important;
            /* Explicitly allow table to span multiple pages */
            -webkit-region-break-inside: auto !important;
            region-break-inside: auto !important;
          }
          
          /* Ensure tbody can span multiple pages */
          .print-table-wrapper tbody {
            display: table-row-group !important;
            height: auto !important;
            max-height: none !important;
            min-height: auto !important;
            overflow: visible !important;
            page-break-inside: auto !important;
          }
          
          /* Table header styling - repeat on every page */
          .print-table-wrapper thead {
            display: table-header-group !important;
            background-color: #e0e0e0 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            /* Ensure header repeats on each page */
            position: relative !important;
          }
          
          .print-table-wrapper thead tr {
            page-break-inside: avoid !important;
            page-break-after: avoid !important;
            break-inside: avoid !important;
            display: table-row !important;
          }
          
          .print-table-wrapper th {
            background-color: #e0e0e0 !important;
            color: #000 !important;
            font-weight: bold !important;
            border: 1px solid #000 !important;
            padding: 8px 4px !important;
            text-align: center !important;
            font-size: 10px !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          /* Table body styling - allow rows to flow across pages */
          .print-table-wrapper tbody {
            display: table-row-group !important;
            visibility: visible !important;
            page-break-inside: auto !important;
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
          }
          
          /* Ensure table can span multiple pages */
          .print-table-wrapper table {
            page-break-after: auto !important;
            page-break-before: auto !important;
            page-break-inside: auto !important;
            break-inside: auto !important;
            /* Allow table to flow across pages */
            display: table !important;
            table-layout: auto !important;
          }
          
          /* Hide pagination in print */
          .mt-4:has(.pagination),
          .pagination {
            display: none !important;
          }
          
          .print-table-wrapper tbody tr {
            display: table-row !important;
            visibility: visible !important;
            /* Allow rows to break across pages if needed (though we prefer to keep rows intact) */
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            /* But allow the table body to flow across pages */
            page-break-after: auto !important;
            break-after: auto !important;
            /* Keep row together, but allow page break after */
            page-break-inside: avoid !important;
            page-break-after: auto !important;
            break-inside: avoid !important;
            break-after: auto !important;
            border-bottom: 1px solid #000 !important;
            /* Ensure rows can flow across pages */
            orphans: 2 !important;
            widows: 2 !important;
          }
          
          /* Ensure all rows are visible, even if hidden in screen view */
          .print-table-wrapper tbody tr[style*="display: none"],
          .print-table-wrapper tbody tr[hidden],
          .print-table-wrapper tbody tr[style*="display:none"] {
            display: table-row !important;
            visibility: visible !important;
          }
          
          /* Prevent individual cells from breaking, but allow rows to flow */
          .print-table-wrapper tbody tr td {
            display: table-cell !important;
            visibility: visible !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            page-break-after: auto !important;
          }
          
          .print-table-wrapper td {
            display: table-cell !important;
            visibility: visible !important;
            border: 1px solid #000 !important;
            padding: 6px 4px !important;
            text-align: center !important;
            color: #000 !important;
            background: white !important;
            font-size: 9px !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
          }
          
          .print-table-wrapper th {
            display: table-cell !important;
            visibility: visible !important;
          }
          
          /* Alternating row colors for better readability */
          .print-table-wrapper tbody tr:nth-child(even) {
            background-color: #f5f5f5 !important;
          }
          
          .print-table-wrapper tbody tr:nth-child(odd) {
            background-color: white !important;
          }
          
          /* Remove background colors from status badges for print */
          .print-table-wrapper .bg-purple-100,
          .print-table-wrapper .bg-purple-900,
          .print-table-wrapper .bg-orange-100,
          .print-table-wrapper .bg-orange-900,
          .print-table-wrapper .bg-green-100,
          .print-table-wrapper .bg-green-900,
          .print-table-wrapper .bg-red-100,
          .print-table-wrapper .bg-red-900,
          .print-table-wrapper .bg-gray-100,
          .print-table-wrapper .bg-gray-900,
          .print-table-wrapper .bg-blue-50,
          .print-table-wrapper .bg-slate-800,
          .print-table-wrapper .bg-slate-700 {
            background: transparent !important;
            color: #000 !important;
            border: none !important;
            padding: 0 !important;
            font-weight: bold !important;
          }
          
          /* Ensure Order Type and Status columns are clearly visible in print */
          .print-table-wrapper td:nth-child(5),
          .print-table-wrapper td:nth-child(8) {
            color: #000 !important;
            font-weight: bold !important;
            font-size: 10px !important;
            background: white !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
          }
          
          /* Make sure spans inside Order Type and Status columns are visible */
          .print-table-wrapper td:nth-child(5) span,
          .print-table-wrapper td:nth-child(8) span {
            color: #000 !important;
            font-weight: bold !important;
            background: transparent !important;
            border: 1px solid #000 !important;
            padding: 3px 6px !important;
            display: inline-block !important;
            white-space: nowrap !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          /* Ensure headers for Order Type and Status are also clearly visible */
          .print-table-wrapper th:nth-child(5),
          .print-table-wrapper th:nth-child(8) {
            color: #000 !important;
            font-weight: bold !important;
            font-size: 10px !important;
            background: #e5e7eb !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          /* Ensure monospace font is visible */
          .print-table-wrapper .font-mono {
            font-family: 'Courier New', monospace !important;
            color: #000 !important;
          }
          
          /* Hide loading and empty state messages in print */
          .print-table-wrapper tbody tr:has(.animate-spin) {
            display: none !important;
          }
          
          /* Ensure table is visible and properly formatted */
          .print-table-wrapper table,
          .print-table-wrapper table * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          /* Ensure proper column widths */
          .print-table-wrapper th:nth-child(1),
          .print-table-wrapper td:nth-child(1) {
            width: 8% !important;
          }
          
          .print-table-wrapper th:nth-child(2),
          .print-table-wrapper td:nth-child(2) {
            width: 12% !important;
          }
          
          .print-table-wrapper th:nth-child(3),
          .print-table-wrapper td:nth-child(3) {
            width: 18% !important;
          }
          
          .print-table-wrapper th:nth-child(4),
          .print-table-wrapper td:nth-child(4) {
            width: 8% !important;
          }
          
          .print-table-wrapper th:nth-child(5),
          .print-table-wrapper td:nth-child(5) {
            width: 12% !important;
            min-width: 80px !important;
          }
          
          .print-table-wrapper th:nth-child(6),
          .print-table-wrapper td:nth-child(6) {
            width: 8% !important;
          }
          
          .print-table-wrapper th:nth-child(7),
          .print-table-wrapper td:nth-child(7) {
            width: 6% !important;
          }
          
          .print-table-wrapper th:nth-child(8),
          .print-table-wrapper td:nth-child(8) {
            width: 12% !important;
            min-width: 80px !important;
          }
          
          .print-table-wrapper th:nth-child(9),
          .print-table-wrapper td:nth-child(9) {
            width: 20% !important;
          }
        }
      `}</style>
      <div className="w-full space-y-6 px-4 lg:px-6">
        {/* Error Message */}
        {error && (
          <div className={`p-2 rounded-lg backdrop-blur-md border transition-all duration-300 text-sm ${theme === 'light'
            ? 'bg-red-50/80 border-red-200/50 text-red-800'
            : 'bg-red-900/20 border-red-400/30 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
            }`}>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span className="text-xs font-medium">{error}</span>
              <button
                onClick={() => setError(null)}
                className={`ml-auto p-1 rounded-full transition-colors ${theme === 'light'
                  ? 'hover:bg-red-100 text-red-600'
                  : 'hover:bg-red-800/30 text-red-400'
                  }`}
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Header Section - Orders Reports Summary / KPI Reports Summary */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {mainTab === 'orders' ? (
              <>
                <ListOrdered className={`h-5 w-5 ${theme === 'light' ? 'text-slate-600' : 'text-cyan-400'}`} />
                <h2 className={`text-lg font-semibold ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'}`}>
                  Orders Reports Summary
                </h2>
              </>
            ) : (
              <>
                <BarChart3 className={`h-5 w-5 ${theme === 'light' ? 'text-slate-600' : 'text-cyan-400'}`} />
                <h2 className={`text-lg font-semibold ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'}`}>
                  KPI Reports Summary
                </h2>
              </>
            )}
          </div>
          <button
            onClick={mainTab === 'orders' ? refreshData : fetchKpiData}
            disabled={mainTab === 'orders' ? loading : kpiLoading}
            className={`relative group flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 hover:scale-105 bg-gradient-to-r from-cyan-500 to-cyan-600 !text-white shadow-md shadow-cyan-500/25 ${(mainTab === 'orders' ? loading : kpiLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <RefreshCw className={`h-4 w-4 ${(mainTab === 'orders' ? loading : kpiLoading) ? 'animate-spin' : ''}`} />
            {(mainTab === 'orders' ? loading : kpiLoading) ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        {/* Main Tabs: Orders and KPIs */}
        <div className="space-y-4">
          {/* Main Tab Headers */}
          <div className={`w-full rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
            ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
            : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
            }`}>
            <div className="flex flex-wrap gap-2 p-2">
              <button
                onClick={() => setMainTab('orders')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 border ${mainTab === 'orders'
                  ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 border-cyan-500 shadow-lg shadow-cyan-500/40 !text-white font-semibold'
                  : theme === 'light'
                    ? 'text-slate-600 border-slate-300 bg-slate-100 hover:bg-slate-200 hover:border-slate-400'
                    : 'text-slate-400 border-slate-600 bg-slate-800/30 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-500'
                  }`}
              >
                <ListOrdered className={`h-4 w-4 ${mainTab === 'orders' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`} />
                <span className={mainTab === 'orders' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>Orders</span>
              </button>
              <button
                onClick={() => setMainTab('kpis')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 border ${mainTab === 'kpis'
                  ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 border-cyan-500 shadow-lg shadow-cyan-500/40 !text-white font-semibold'
                  : theme === 'light'
                    ? 'text-slate-600 border-slate-300 bg-slate-100 hover:bg-slate-200 hover:border-slate-400'
                    : 'text-slate-400 border-slate-600 bg-slate-800/30 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-500'
                  }`}
              >
                <BarChart3 className={`h-4 w-4 ${mainTab === 'kpis' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`} />
                <span className={mainTab === 'kpis' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>KPIs</span>
              </button>
            </div>
          </div>

          {/* Main Tab Content */}
          {mainTab === 'orders' ? (
            /* Orders Tab Content */
            <div className="space-y-4 orders-section">

              {/* Orders Sub-Tabs */}
              <div className={`w-full rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
                ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
                : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
                }`}>
                {/* Orders Sub-Tab Headers - filter by role: milling operator sees Milling only, packing sees Packing only */}
                <div className="flex flex-wrap gap-2 p-2">
                  {[
                    ...(isAdmin ? [{ key: 'all' as const, label: 'All Types', count: orders.length }] : []),
                    ...(isAdmin || isMillingOnly ? [{ key: 'milling' as const, label: 'Milling', count: millingOrders.length }] : []),
                    ...(isAdmin || isPackingOnly ? [{ key: 'packing' as const, label: 'Packing', count: packingOrders.length }] : [])
                  ].map((type) => (
                    <button
                      key={type.key}
                      onClick={() => setActiveTab(type.key as 'all' | 'milling' | 'packing')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 border ${activeTab === type.key
                        ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 border-cyan-500 shadow-lg shadow-cyan-500/40 !text-white font-semibold'
                        : theme === 'light'
                          ? 'text-slate-600 border-slate-300 bg-slate-100 hover:bg-slate-200 hover:border-slate-400'
                          : 'text-slate-400 border-slate-600 bg-slate-800/30 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-500'
                        }`}
                    >
                      <span className={activeTab === type.key ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>{type.label}</span>
                      {type.count !== null && (
                        <span className={`px-2 py-0.5 rounded text-xs ${activeTab === type.key
                          ? 'bg-white/20 text-white'
                          : theme === 'light'
                            ? 'bg-slate-200 text-slate-600'
                            : 'bg-slate-700 text-slate-300'
                          }`}>
                          {type.count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

          {/* Tab Content */}
          <div className="p-6">
            <>
                {/* Filter Panel - Only for All Types, Milling, and Packing */}
                <div className="space-y-2 mb-4">
                  <TimeFilter
                    onApply={handleTimeFilterApply}
                    initialValues={timeFilters || undefined}
                  />
                  
                  {/* Historical Mode Indicator - No Reset to Live button since data is always from database */}
                  {isHistoricalMode && (
                    <div className={`flex items-center px-3 py-2 rounded-md border ${theme === 'light'
                      ? 'bg-amber-50 border-amber-200 text-amber-800'
                      : 'bg-amber-900/20 border-amber-700/30 text-amber-300'
                      }`}>
                      <div className="flex items-center gap-2">
                        <Clock3 className={`w-4 h-4 ${theme === 'light' ? 'text-amber-600' : 'text-amber-400'}`} />
                        <span className="text-xs font-medium">Historical Mode: {periodLabel}</span>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Search and Export */}
                <div className="flex items-center justify-between mb-4">
                  <div className="relative">
                    <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'}`} />
                    <input
                      type="text"
                      placeholder="Search orders..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className={`pl-10 pr-4 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
                        ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                        : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
                        }`}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleExportPDF}
                      className={`relative group flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 hover:scale-105 bg-gradient-to-r from-cyan-500 to-cyan-600 !text-white shadow-md shadow-cyan-500/25`}
                      title="Export to PDF with professional formatting"
                    >
                      <FileText className="h-4 w-4" />
                      Export PDF
                    </button>

                    <button
                      onClick={handleExportCSV}
                      className={`relative group flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 hover:scale-105 bg-gradient-to-r from-green-500 to-green-600 !text-white shadow-md shadow-green-500/25`}
                      title="Export to CSV for Excel/Google Sheets"
                    >
                      <BarChart3 className="h-4 w-4" />
                      Export CSV
                    </button>

                    <button
                      onClick={handlePrint}
                      className={`relative group flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 hover:scale-105 bg-gradient-to-r from-cyan-500 to-cyan-600 !text-white shadow-md shadow-cyan-500/25`}
                      title="Print orders table"
                    >
                      <Printer className="h-4 w-4" />
                      Print
                    </button>
                  </div>
                </div>

                {/* Orders Table */}
            <div 
              className={`print-table-wrapper overflow-x-auto rounded-lg border transition-all duration-300 ${theme === 'light'
                ? 'bg-white border-slate-200'
                : 'bg-slate-800 border-slate-600'
                }`}
              data-print-date={new Date().toLocaleDateString() + ' at ' + new Date().toLocaleTimeString()}
            >
              {/* Print Header - Only visible in print */}
              <div className="print-header hidden">
                <div className="print-header-left">
                  <img 
                    src={herculesLogo} 
                    alt="Hercules Logo" 
                  />
                </div>
                <div className="print-header-right">
                  <img 
                    src={modernMillsLogo} 
                    alt="Modern Mills Logo" 
                  />
                  <img 
                    src={asmLogo} 
                    alt="ASM Logo" 
                  />
                </div>
              </div>
              <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'
                }`}>
                <thead className={`${theme === 'light'
                  ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                  : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                  }`}>
                  <tr>
                    <th className="px-3 py-2 text-center font-medium">Order ID</th>
                    <th className="px-3 py-2 text-center font-medium">PO Number</th>
                    <th className="px-3 py-2 text-center font-medium">Material</th>
                    <th className="px-3 py-2 text-center font-medium">Version</th>
                    <th className="px-3 py-2 text-center font-medium">Order Type</th>
                    <th className="px-3 py-2 text-center font-medium">Quantity</th>
                    <th className="px-3 py-2 text-center font-medium">Unit</th>
                    <th className="px-3 py-2 text-center font-medium">Status</th>
                    <th className="px-3 py-2 text-center font-medium">Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {!isPrintMode && loading ? (
                    <tr>
                      <td colSpan={9} className="px-3 py-4 text-center text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                          Loading orders...
                        </div>
                      </td>
                    </tr>
                  ) : isPrintMode && isLoadingForPrint ? (
                    <tr>
                      <td colSpan={9} className="px-3 py-4 text-center text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                          Loading all orders for printing...
                        </div>
                      </td>
                    </tr>
                  ) : filteredOrders.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-3 py-4 text-center opacity-70 text-sm">
                        No orders found
                      </td>
                    </tr>
                  ) : (
                    filteredOrders.map((order, index) => (
                      <tr
                        key={order.id}
                        className={`border-b ${theme === 'light' ? 'border-slate-100' : 'border-slate-600'
                          } ${index % 2 === 0
                            ? theme === 'light' ? 'bg-white' : 'bg-slate-800'
                            : theme === 'light' ? 'bg-blue-50' : 'bg-slate-700'
                          }`}
                      >
                        <td className="px-3 py-2 font-mono text-xs font-semibold text-center">{order.id}</td>
                        <td className="px-3 py-2 font-mono text-xs text-center">{order.po_number}</td>
                        <td className="px-3 py-2 font-mono text-xs text-center">{order.material}</td>
                        <td className="px-3 py-2 font-mono text-xs text-center">{order.version}</td>
                        <td className="px-3 py-2 text-center">
                          {(() => {
                            const orderType = getOrderTypeFromMaterial(order.material || '');
                            return (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${orderType === 'MILLING'
                                ? theme === 'light' ? 'bg-purple-100 text-purple-700' : 'bg-purple-900/30 text-purple-300'
                                : orderType === 'PACKING'
                                  ? theme === 'light' ? 'bg-orange-100 text-orange-700' : 'bg-orange-900/30 text-orange-300'
                                  : theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-gray-900/30 text-gray-300'
                                }`}>
                                {orderType}
                              </span>
                            );
                          })()}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs font-bold text-center">{order.quantity}</td>
                        <td className="px-3 py-2 font-mono text-xs text-center">{order.unit}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${order.status === 'Confirmed'
                            ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                            : order.status === 'Rejected'
                              ? theme === 'light' ? 'bg-red-100 text-red-700' : 'bg-red-900/30 text-red-300'
                              : theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-gray-900/30 text-gray-300'
                            }`}>
                            {order.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs text-center">
                          {new Date(order.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

                {/* Pagination */}
                {totalOrders > 0 && (
                  <div className="mt-4">
                    <Pagination
                      currentPage={currentPage}
                      totalPages={totalPages}
                      totalItems={totalOrders}
                      itemsPerPage={itemsPerPage}
                      onPageChange={handlePageChange}
                      onItemsPerPageChange={handleItemsPerPageChange}
                      theme={theme}
                    />
                  </div>
                )}
              </>
              </div>
            </div>
          </div>
          ) : (
            /* KPIs Tab Content */
            <div className="space-y-4">
              {/* KPI Error Message */}
              {kpiError && (
                <div className={`p-2 rounded-lg backdrop-blur-md border transition-all duration-300 text-sm ${theme === 'light'
                  ? 'bg-red-50/80 border-red-200/50 text-red-800'
                  : 'bg-red-900/20 border-red-400/30 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
                  }`}>
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    <span className="text-xs font-medium">{kpiError}</span>
                    <button
                      onClick={() => setKpiError(null)}
                      className={`ml-auto p-1 rounded-full transition-colors ${theme === 'light'
                        ? 'hover:bg-red-100 text-red-600'
                        : 'hover:bg-red-800/30 text-red-400'
                        }`}
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}

              {/* Time Filter for KPIs */}
              <div className="space-y-2">
                <TimeFilter
                  onApply={handleKpiTimeFilterApply}
                  initialValues={kpiTimeFilters || undefined}
                />
                
                {/* Historical Mode Indicator - No Reset to Live button since data is always from database */}
                {(isKpiHistoricalMode || (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range'))) && (
                  <div className={`flex items-center px-3 py-2 rounded-md border ${theme === 'light'
                    ? 'bg-amber-50 border-amber-200 text-amber-800'
                    : 'bg-amber-900/20 border-amber-700/30 text-amber-300'
                    }`}>
                    <div className="flex items-center gap-2">
                      <Clock3 className={`w-4 h-4 ${theme === 'light' ? 'text-amber-600' : 'text-amber-400'}`} />
                      <span className="text-xs font-medium">Historical Mode: {kpiPeriodLabel || 'Filters Applied'}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* KPIs Sub-Tabs */}
              <div className={`w-full rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
                ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
                : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
                }`}>
                {/* KPI Sub-Tab Headers - show only relevant tab for operators */}
                <div className="flex flex-wrap gap-2 p-2">
                  {(isAdmin || isMillingOnly) && (
                  <button
                    onClick={() => setKpiSubTab('milling')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 border ${kpiSubTab === 'milling'
                      ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 border-cyan-500 shadow-lg shadow-cyan-500/40 !text-white font-semibold'
                      : theme === 'light'
                        ? 'text-slate-600 border-slate-300 bg-slate-100 hover:bg-slate-200 hover:border-slate-400'
                        : 'text-slate-400 border-slate-600 bg-slate-800/30 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-500'
                      }`}
                  >
                    <span className={kpiSubTab === 'milling' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>Milling KPIs</span>
                  </button>
                  )}
                  {(isAdmin || isPackingOnly) && (
                  <button
                    onClick={() => setKpiSubTab('packing')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300 border ${kpiSubTab === 'packing'
                      ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 border-cyan-500 shadow-lg shadow-cyan-500/40 !text-white font-semibold'
                      : theme === 'light'
                        ? 'text-slate-600 border-slate-300 bg-slate-100 hover:bg-slate-200 hover:border-slate-400'
                        : 'text-slate-400 border-slate-600 bg-slate-800/30 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-500'
                      }`}
                  >
                    <span className={kpiSubTab === 'packing' ? '!text-white' : theme === 'light' ? 'text-slate-600' : 'text-slate-400'}>Packing KPIs</span>
                  </button>
                  )}
                </div>

                {/* KPI Sub-Tab Content */}
                <div className="p-6">
                  {kpiSubTab === 'milling' ? (
                    <>
                      {/* Milling KPIs Table */}
                      <div className={`overflow-x-auto rounded-lg border transition-all duration-300 ${theme === 'light'
                        ? 'bg-white border-slate-200'
                        : 'bg-slate-800 border-slate-600'
                        }`}>
                        {kpiLoading ? (
                          <div className="p-8 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <RefreshCw className="h-5 w-5 animate-spin text-cyan-400" />
                              <span className={theme === 'light' ? 'text-slate-700' : 'text-cyan-300'}>
                                Loading Milling KPIs...
                              </span>
                            </div>
                          </div>
                        ) : kpiError ? (
                          <div className="p-8 text-center">
                            <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                            <p className={theme === 'light' ? 'text-slate-700' : 'text-red-300'}>
                              {kpiError}
                            </p>
                          </div>
                        ) : (isKpiHistoricalMode || (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range'))) ? (
                          // Historical mode: Show multiple rows from tracking data
                          kpiTrackingData.length > 0 ? (
                            <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'}`}>
                              <thead className={`${theme === 'light'
                                ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                                : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                                }`}>
                                <tr>
                                  <th className="px-3 py-2 text-center font-medium">Shift</th>
                                  <th className="px-3 py-2 text-center font-medium">Date/Time</th>
                                  <th className="px-3 py-2 text-center font-medium">Mill Throughput (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Mill Time Efficiency (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Total Utilization (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Milling Gain</th>
                                  <th className="px-3 py-2 text-center font-medium">Milling Screening (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Flour Extraction (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Milling Loss (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Net Hours (hrs)</th>
                                  <th className="px-3 py-2 text-center font-medium">Downtime (hrs)</th>
                                  <th className="px-3 py-2 text-center font-medium">Max Utilization of Milling Capacity (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Pre Cleaning Screening (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">1st Break Capacity per Hour (t/h)</th>
                                  <th className="px-3 py-2 text-center font-medium">Bran Extraction (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Pre Cleaning Water (L)</th>
                                  <th className="px-3 py-2 text-center font-medium">Water Clean Wheat (L)</th>
                                  <th className="px-3 py-2 text-center font-medium">Total Water Used (L)</th>
                                </tr>
                              </thead>
                              <tbody>
                                {kpiTrackingData
                                  .filter(record => record.department === 'MILLING')
                                  .map((record) => {
                                    const mappedData = mapPayloadToTableFormat(record.kpi_payload, 'MILLING');
                                    return (
                                      <tr key={record.id} className={`border-b ${theme === 'light' ? 'border-slate-100 bg-white' : 'border-slate-600 bg-slate-800'}`}>
                                        <td className="px-3 py-2 text-center font-semibold">
                                          {record.shift_code || 'N/A'}
                                        </td>
                                        <td className="px-3 py-2 text-center text-xs">
                                          {formatDatabaseTimestamp(record.last_sent_at)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Mill Throughput (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Mill Time Efficiency (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Total Utilization (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Milling Gain"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Milling Screening (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Flour Extraction (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Milling Loss (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Net Hours (hrs)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Downtime (hrs)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Max Utilization of Milling Capacity (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Pre Cleaning Screening (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["1st Break Capacity per Hour (t/h)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Bran Extraction (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Pre Cleaning Water (L)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Water Clean Wheat (L)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Total Water Used (L)"].toFixed(2)}
                                        </td>
                                      </tr>
                                    );
                                  })}
                              </tbody>
                            </table>
                          ) : (
                            <div className="p-8 text-center">
                              <p className={theme === 'light' ? 'text-slate-700' : 'text-slate-300'}>
                                No historical KPI data found for the selected filters
                              </p>
                            </div>
                          )
                        ) : !kpiData ? (
                          <div className="p-8 text-center">
                            <p className={theme === 'light' ? 'text-slate-700' : 'text-slate-300'}>
                              No KPI data available
                            </p>
                          </div>
                        ) : (
                          // Live mode: Show single row from current KPI data
                          <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'}`}>
                            <thead className={`${theme === 'light'
                              ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                              : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                              }`}>
                              <tr>
                                <th className="px-3 py-2 text-center font-medium">Date/Time</th>
                                <th className="px-3 py-2 text-center font-medium">Mill Throughput (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Mill Time Efficiency (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Total Utilization (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Milling Gain</th>
                                <th className="px-3 py-2 text-center font-medium">Milling Screening (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Flour Extraction (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Milling Loss (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Net Hours (hrs)</th>
                                <th className="px-3 py-2 text-center font-medium">Downtime (hrs)</th>
                                <th className="px-3 py-2 text-center font-medium">Max Utilization of Milling Capacity (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Pre Cleaning Screening (%)</th>
                                <th className="px-3 py-2 text-center font-medium">1st Break Capacity per Hour (t/h)</th>
                                <th className="px-3 py-2 text-center font-medium">Bran Extraction (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Pre Cleaning Water (L)</th>
                                <th className="px-3 py-2 text-center font-medium">Water Clean Wheat (L)</th>
                                <th className="px-3 py-2 text-center font-medium">Total Water Used (L)</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className={`border-b ${theme === 'light' ? 'border-slate-100 bg-white' : 'border-slate-600 bg-slate-800'}`}>
                                <td className="px-3 py-2 text-center text-xs">
                                  {kpiData?.timestamp ? new Date(kpiData.timestamp).toLocaleString() : new Date().toLocaleString()}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Mill Throughput (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Mill Time Efficiency (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Total Utilization (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Milling Gain"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Milling Screening (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Flour Extraction (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Milling Loss (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Net Hours (hrs)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Downtime (hrs)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Max Utilization of Milling Capacity (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Pre Cleaning Screening (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["1st Break Capacity per Hour (t/h)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData.milling_kpis["Bran Extraction (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {scadaData?.totalPreCleaningWater ? (typeof scadaData.totalPreCleaningWater === 'string' ? parseFloat(scadaData.totalPreCleaningWater) : scadaData.totalPreCleaningWater).toFixed(2) : '0.00'}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {scadaData?.waterCleanWheat ? (typeof scadaData.waterCleanWheat === 'string' ? parseFloat(scadaData.waterCleanWheat) : scadaData.waterCleanWheat).toFixed(2) : '0.00'}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {scadaData?.totalWaterUsed ? (typeof scadaData.totalWaterUsed === 'string' ? parseFloat(scadaData.totalWaterUsed) : scadaData.totalWaterUsed).toFixed(2) : '0.00'}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        )}
                      </div>
                      
                      {/* Milling KPIs Pagination */}
                      {(isKpiHistoricalMode || (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range'))) && kpiTotalItems > 0 && (
                        <div className="mt-4">
                          <Pagination
                            currentPage={kpiCurrentPage}
                            totalPages={kpiTotalPages}
                            totalItems={kpiTotalItems}
                            itemsPerPage={kpiItemsPerPage}
                            onPageChange={handleKpiPageChange}
                            onItemsPerPageChange={handleKpiItemsPerPageChange}
                            theme={theme}
                          />
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {/* Packing KPIs Table */}
                      <div className={`overflow-x-auto rounded-lg border transition-all duration-300 ${theme === 'light'
                        ? 'bg-white border-slate-200'
                        : 'bg-slate-800 border-slate-600'
                        }`}>
                        {kpiLoading ? (
                          <div className="p-8 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <RefreshCw className="h-5 w-5 animate-spin text-cyan-400" />
                              <span className={theme === 'light' ? 'text-slate-700' : 'text-cyan-300'}>
                                Loading Packing KPIs...
                              </span>
                            </div>
                          </div>
                        ) : kpiError ? (
                          <div className="p-8 text-center">
                            <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                            <p className={theme === 'light' ? 'text-slate-700' : 'text-red-300'}>
                              {kpiError}
                            </p>
                          </div>
                        ) : (isKpiHistoricalMode || (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range'))) ? (
                          // Historical mode: Show multiple rows from tracking data
                          kpiTrackingData.length > 0 ? (
                            <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'}`}>
                              <thead className={`${theme === 'light'
                                ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                                : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                                }`}>
                                <tr>
                                  <th className="px-3 py-2 text-center font-medium">Shift</th>
                                  <th className="px-3 py-2 text-center font-medium">Date/Time</th>
                                  <th className="px-3 py-2 text-center font-medium">Packing Line Capacity (bags/hr)</th>
                                  <th className="px-3 py-2 text-center font-medium">Daily Packing Output (bags)</th>
                                  <th className="px-3 py-2 text-center font-medium">Net Hours (hrs)</th>
                                  <th className="px-3 py-2 text-center font-medium">Downtime (hrs)</th>
                                  <th className="px-3 py-2 text-center font-medium">Machine Utilization (%)</th>
                                  <th className="px-3 py-2 text-center font-medium">Packing Line Capacity (tons/hr)</th>
                                </tr>
                              </thead>
                              <tbody>
                                {kpiTrackingData
                                  .filter(record => record.department === 'PACKING')
                                  .map((record) => {
                                    const mappedData = mapPayloadToTableFormat(record.kpi_payload, 'PACKING');
                                    return (
                                      <tr key={record.id} className={`border-b ${theme === 'light' ? 'border-slate-100 bg-white' : 'border-slate-600 bg-slate-800'}`}>
                                        <td className="px-3 py-2 text-center font-semibold">
                                          {record.shift_code || 'N/A'}
                                        </td>
                                        <td className="px-3 py-2 text-center text-xs">
                                          {formatDatabaseTimestamp(record.last_sent_at)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Packing Line Capacity (bags/hr)"].toLocaleString()}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Daily Packing Output (bags)"].toLocaleString()}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Net Hours (hrs)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Downtime (hrs)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Machine Utilization (%)"].toFixed(2)}
                                        </td>
                                        <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                          {mappedData["Packing Line Capacity (tons/hr)"].toFixed(2)}
                                        </td>
                                      </tr>
                                    );
                                  })}
                              </tbody>
                            </table>
                          ) : (
                            <div className="p-8 text-center">
                              <p className={theme === 'light' ? 'text-slate-700' : 'text-slate-300'}>
                                No historical KPI data found for the selected filters
                              </p>
                            </div>
                          )
                        ) : !kpiData ? (
                          <div className="p-8 text-center">
                            <p className={theme === 'light' ? 'text-slate-700' : 'text-slate-300'}>
                              No KPI data available
                            </p>
                          </div>
                        ) : (
                          // Live mode: Show single row from current KPI data
                          <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'}`}>
                            <thead className={`${theme === 'light'
                              ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                              : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                              }`}>
                              <tr>
                                <th className="px-3 py-2 text-center font-medium">Date/Time</th>
                                <th className="px-3 py-2 text-center font-medium">Packing Line Capacity (bags/hr)</th>
                                <th className="px-3 py-2 text-center font-medium">Daily Packing Output (bags)</th>
                                <th className="px-3 py-2 text-center font-medium">Net Hours (hrs)</th>
                                <th className="px-3 py-2 text-center font-medium">Downtime (hrs)</th>
                                <th className="px-3 py-2 text-center font-medium">Machine Utilization (%)</th>
                                <th className="px-3 py-2 text-center font-medium">Packing Line Capacity (tons/hr)</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className={`border-b ${theme === 'light' ? 'border-slate-100 bg-white' : 'border-slate-600 bg-slate-800'}`}>
                                <td className="px-3 py-2 text-center text-xs">
                                  {kpiData?.timestamp ? new Date(kpiData.timestamp).toLocaleString() : new Date().toLocaleString()}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Packing Line Capacity (bags/hr)"].toLocaleString()}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Daily Packing Output (bags)"].toLocaleString()}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Net Hours (hrs)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Downtime (hrs)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Machine Utilization (%)"].toFixed(2)}
                                </td>
                                <td className="px-3 py-2 font-mono text-xs text-center font-semibold">
                                  {kpiData?.packing_kpis["Packing Line Capacity (tons/hr)"].toFixed(2)}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        )}
                      </div>
                      
                      {/* Packing KPIs Pagination */}
                      {(isKpiHistoricalMode || (kpiTimeFilters && (kpiTimeFilters.mode === 'single' || kpiTimeFilters.mode === 'range'))) && kpiTotalItems > 0 && (
                        <div className="mt-4">
                          <Pagination
                            currentPage={kpiCurrentPage}
                            totalPages={kpiTotalPages}
                            totalItems={kpiTotalItems}
                            itemsPerPage={kpiItemsPerPage}
                            onPageChange={handleKpiPageChange}
                            onItemsPerPageChange={handleKpiItemsPerPageChange}
                            theme={theme}
                          />
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </WaterSystemLayout>
  );
};

export default Reports;

