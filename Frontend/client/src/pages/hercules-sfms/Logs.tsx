import React, { useState, useEffect } from "react";
import { useTheme } from "../../contexts/ThemeContext";
import { WaterSystemLayout } from "../../components/hercules-sfms/WaterSystemLayout";
import { Filter, Download, Trash2, RefreshCw, Database, Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../../lib/queryClient';
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 Logs.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

interface LogEntry {
  id: number;
  timestamp: string;
  source: string;
  action: string;
  status: string;
  details?: string;
  operator?: string;
  duration_ms?: number;
  error_code?: string;
  metadata?: any;
  created_at: string;
  shift?: string;
}

interface SyncLogEntry {
  id: number;
  level: string;
  message: string;
  details: any;
  category: string;
  source: string;
  created_at: string;
}

const Logs = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [operator, setOperator] = useState("Operator A");
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shiftDate, setShiftDate] = useState(new Date().toISOString().split('T')[0]);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [showEndShiftModal, setShowEndShiftModal] = useState(false);
  const [showClearModal, setShowClearModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'system' | 'sync'>('system');
  const [syncCurrentPage, setSyncCurrentPage] = useState(1);
  const [syncItemsPerPage] = useState(10);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedLogDetails, setSelectedLogDetails] = useState<any>(null);
  const { theme } = useTheme();

  // Fetch sync logs
  const { data: syncLogsData, isLoading: syncLogsLoading, refetch: refetchSyncLogs } = useQuery({
    queryKey: ['/api/sync-interval/logs'],
    queryFn: () => apiRequest('GET', '/api/sync-interval/logs'),
    select: (data) => data.logs || [],
    enabled: activeTab === 'sync'
  });

  const getCurrentTimestamp = () => new Date().toISOString().replace("T", " ").substring(0, 19);

  // Fetch logs from API
  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch logs with filters and pagination
      const params = new URLSearchParams();
      if (filter !== "All") params.append("status", filter);
      if (search) params.append("search", search);
      params.append("page", currentPage.toString());
      params.append("per_page", itemsPerPage.toString());
      
      const response = await apiFetch(getApiUrl(`/api/system-logs/?${params}`));
      
      console.log("API Response Status:", response.status);
      const data = await response.json();
      console.log("API Response Data:", data);
      
      if (data.ok) {
        setLogs(data.logs || []);
        console.log("Logs set:", data.logs?.length || 0);
      } else {
        setError(data.message || "Failed to fetch logs");
      }
    } catch (err) {
      setError("Failed to connect to server");
      console.error("Error fetching logs:", err);
    } finally {
      setLoading(false);
    }
  };

  // Load logs on component mount and when filters change
  useEffect(() => {
    fetchLogs();
  }, [filter, search, currentPage]);

  const handleManualSync = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(getApiUrl('/api/system-logs/manual-sync'), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ operator }),
      });
      
      const data = await response.json();
      if (data.ok) {
        // Refresh logs after manual sync
        await fetchLogs();
      } else {
        setError(data.message || "Failed to trigger manual sync");
      }
    } catch (err) {
      setError("Failed to trigger manual sync");
      console.error("Error triggering manual sync:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleShiftEnd = () => {
    setShowEndShiftModal(true);
  };

  const confirmEndShift = async () => {
    setShowEndShiftModal(false);
    try {
      setLoading(true);
      const response = await apiFetch(getApiUrl('/api/system-logs/end-shift'), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ operator }),
      });
      
      const data = await response.json();
      if (data.ok) {
        // Refresh logs after shift end
        await fetchLogs();
      } else {
        setError(data.message || "Failed to end shift");
      }
    } catch (err) {
      setError("Failed to end shift");
      console.error("Error ending shift:", err);
    } finally {
      setLoading(false);
    }
  };

  const cancelEndShift = () => {
    setShowEndShiftModal(false);
  };

  const handleUndo = async (logId: number) => {
    try {
      setLoading(true);
      const response = await apiFetch(getApiUrl(`/api/system-logs/undo/${logId}`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ operator }),
      });
      
      const data = await response.json();
      if (data.ok) {
        // Refresh logs after undo
        await fetchLogs();
      } else {
        setError(data.message || "Failed to undo action");
      }
    } catch (err) {
      setError("Failed to undo action");
      console.error("Error undoing action:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'system') {
        await exportSystemLogsPDF();
      } else if (activeTab === 'sync') {
        await exportSyncLogsPDF();
      }
    } catch (err) {
      setError("Failed to export logs");
      console.error("Error exporting logs:", err);
    } finally {
      setLoading(false);
    }
  };

  const exportSystemLogsPDF = async () => {
    if (!logs || logs.length === 0) {
      setError("No system logs data available to export");
      return;
    }

    const doc = new jsPDF('landscape', 'mm', 'a4');
    
    // Header with company info
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('HERCULES SFMS - System Logs Report', 20, 20);
    
    // Report details
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`, 20, 30);
    doc.text(`Report Type: System Logs`, 20, 36);
    doc.text(`Total Records: ${logs.length}`, 20, 42);
    doc.text(`Operator: ${operator}`, 20, 48);
    doc.text(`Filter: ${filter}`, 20, 54);
    if (search) {
      doc.text(`Search: ${search}`, 20, 60);
    }
    
    // Helper: compute shift from timestamp (A: 06-14, B: 14-22, C: 22-06)
    const computeShift = (ts?: string) => {
      if (!ts) return '-';
      try {
        const d = new Date(ts);
        if (isNaN(d.getTime())) return '-';
        const h = d.getHours();
        if (h >= 6 && h < 14) return 'A';
        if (h >= 14 && h < 22) return 'B';
        return 'C';
      } catch {
        return '-';
      }
    };

    // Prepare table data
    const tableData = logs.map(log => {
      const timestamp = log.timestamp || log.created_at;
      let formattedTimestamp = '-';
      if (timestamp) {
        try {
          const date = new Date(timestamp);
          if (!isNaN(date.getTime())) {
            formattedTimestamp = date.toLocaleString('en-US', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: true
            });
          }
        } catch (e) {
          formattedTimestamp = '-';
        }
      }

      const action = log.action || (log.details ? JSON.parse(log.details).sync_type?.replace('_', ' ') || "-" : "-");
      
      let status = log.status;
      if (!status && log.details) {
        try {
          const details = JSON.parse(log.details);
          status = details.status;
        } catch (e) {
          // Ignore JSON parse errors
        }
      }

      return [
        formattedTimestamp,
        log.source || '-',
        action,
        status || '-',
        log.shift || computeShift(timestamp)
      ];
    });

    // Table with improved styling
    autoTable(doc, {
      startY: search ? 70 : 64,
      head: [['Timestamp', 'Source', 'Action', 'Status', 'Shift']],
      body: tableData,
      styles: {
        fontSize: 8,
        cellPadding: 3,
        overflow: 'linebreak',
        halign: 'left'
      },
      headStyles: {
        fillColor: [0, 120, 215],
        textColor: 255,
        fontStyle: 'bold',
        halign: 'center'
      },
      alternateRowStyles: {
        fillColor: [245, 245, 245]
      },
      columnStyles: {
        0: { cellWidth: 35 }, // Timestamp
        1: { cellWidth: 20 }, // Source
        2: { cellWidth: 50 }, // Action
        3: { cellWidth: 25 }, // Status
        4: { cellWidth: 15 }  // Shift
      },
      margin: { left: 20, right: 20 },
      pageBreak: 'auto',
      showHead: 'everyPage'
    });

    // Footer
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setFont('helvetica', 'normal');
      doc.text(`Page ${i} of ${pageCount}`, 20, doc.internal.pageSize.height - 10);
      doc.text('HERCULES SFMS - Smart Factory Management System', doc.internal.pageSize.width - 20, doc.internal.pageSize.height - 10, { align: 'right' });
    }

    // Save the PDF
    doc.save(`system_logs_${new Date().toISOString().split('T')[0]}.pdf`);
  };

  const exportSyncLogsPDF = async () => {
    if (!syncLogsData || syncLogsData.length === 0) {
      setError("No sync logs data available to export");
      return;
    }

    const doc = new jsPDF('landscape', 'mm', 'a4');
    
    // Header with company info
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('HERCULES SFMS - Sync Logs Report', 20, 20);
    
    // Report details
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`, 20, 30);
    doc.text(`Report Type: Sync Activity Logs`, 20, 36);
    doc.text(`Total Records: ${syncLogsData.length}`, 20, 42);
    
    // Prepare table data
    const tableData = syncLogsData.map((log: SyncLogEntry) => {
      const timestamp = new Date(log.created_at).toLocaleString();
      const message = log.message.length > 50 ? log.message.substring(0, 50) + '...' : log.message;
      const details = log.details ? 'Available' : 'None';

      return [
        timestamp,
        message,
        log.category || '-',
        details
      ];
    });

    // Table with improved styling
    autoTable(doc, {
      startY: 50,
      head: [['Timestamp', 'Message', 'Category', 'Details']],
      body: tableData,
      styles: {
        fontSize: 8,
        cellPadding: 3,
        overflow: 'linebreak',
        halign: 'left'
      },
      headStyles: {
        fillColor: [0, 120, 215],
        textColor: 255,
        fontStyle: 'bold',
        halign: 'center'
      },
      alternateRowStyles: {
        fillColor: [245, 245, 245]
      },
      columnStyles: {
        0: { cellWidth: 40 }, // Timestamp
        1: { cellWidth: 80 }, // Message
        2: { cellWidth: 30 }, // Category
        3: { cellWidth: 20 }  // Details
      },
      margin: { left: 20, right: 20 },
      pageBreak: 'auto',
      showHead: 'everyPage'
    });

    // Footer
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setFont('helvetica', 'normal');
      doc.text(`Page ${i} of ${pageCount}`, 20, doc.internal.pageSize.height - 10);
      doc.text('HERCULES SFMS - Smart Factory Management System', doc.internal.pageSize.width - 20, doc.internal.pageSize.height - 10, { align: 'right' });
    }

    // Save the PDF
    doc.save(`sync_logs_${new Date().toISOString().split('T')[0]}.pdf`);
  };

  const handleClear = () => {
    setShowClearModal(true);
  };

  const confirmClear = async () => {
    setShowClearModal(false);
    try {
      setLoading(true);
      const response = await apiFetch(getApiUrl('/api/system-logs/clear'), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ older_than_days: 30 }),
      });
      
      const data = await response.json();
      if (data.ok) {
        // Refresh logs after clear
        await fetchLogs();
      } else {
        setError(data.message || "Failed to clear logs");
      }
    } catch (err) {
      setError("Failed to clear logs");
      console.error("Error clearing logs:", err);
    } finally {
      setLoading(false);
    }
  };

  const cancelClear = () => {
    setShowClearModal(false);
  };

  // Handle Report action
  const handleReport = async (log: LogEntry) => {
    try {
      setLoading(true);
      console.log('Generating report for log:', log);
      
      // Here you can add logic to generate a report for the specific log entry
      // For example: generateLogReport(log.id);
      
      // For now, we'll just show a success message
      setError(null);
      // You could add a success notification here
      
    } catch (err) {
      setError("Failed to generate report");
      console.error("Error generating report:", err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Claim action
  const handleClaim = async (log: LogEntry) => {
    try {
      setLoading(true);
      console.log('Claiming log entry:', log);
      
      // Here you can add logic to claim the log entry
      // For example: claimLogEntry(log.id);
      
      // For now, we'll just show a success message
      setError(null);
      // You could add a success notification here
      
    } catch (err) {
      setError("Failed to claim log entry");
      console.error("Error claiming log entry:", err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate pagination for system logs
  const totalPages = Math.ceil(logs.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentLogs = logs.slice(startIndex, endIndex);

  // Calculate pagination for sync logs
  const syncTotalPages = Math.ceil((syncLogsData?.length || 0) / syncItemsPerPage);
  const syncStartIndex = (syncCurrentPage - 1) * syncItemsPerPage;
  const syncEndIndex = syncStartIndex + syncItemsPerPage;
  const currentSyncLogs = syncLogsData?.slice(syncStartIndex, syncEndIndex) || [];

  // Pagination handlers for system logs
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  // Pagination handlers for sync logs
  const handleSyncPageChange = (page: number) => {
    setSyncCurrentPage(page);
  };

  const handleSyncPreviousPage = () => {
    if (syncCurrentPage > 1) {
      setSyncCurrentPage(syncCurrentPage - 1);
    }
  };

  const handleSyncNextPage = () => {
    if (syncCurrentPage < syncTotalPages) {
      setSyncCurrentPage(syncCurrentPage + 1);
    }
  };

  // Handle showing details modal
  const handleShowDetails = (details: any) => {
    setSelectedLogDetails(details);
    setShowDetailsModal(true);
  };

  const handleCloseDetails = () => {
    setShowDetailsModal(false);
    setSelectedLogDetails(null);
  };

  // Classes
  const inputClass =
    theme === "light"
      ? "px-3 py-2 rounded-lg bg-white border border-blue-300 text-[#222] text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
      : "px-3 py-2 rounded-lg bg-[#0f172a] border border-cyan-500 text-cyan-200 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400";

  const tableHeader =
    theme === "light"
      ? "bg-blue-100 text-[#222] border-b border-blue-300"
      : "bg-[#0f172a] text-cyan-300 border-b border-cyan-500";

  const tableRowEven = theme === "light" ? "bg-blue-50" : "bg-[#22304a]/60";
  const tableRowOdd = theme === "light" ? "bg-white" : "bg-[#1a2532]";
  const borderRow = theme === "light" ? "border-blue-100" : "border-slate-700";

  return (
    <WaterSystemLayout title="System Logs" subtitle="Track system sync & operator activities">
      <style>{`
        /* Force white text for buttons in light mode */
        .logs-manual-sync-light {
          color: white !important;
        }
        
        .logs-manual-sync-light span {
          color: white !important;
        }
        
        .logs-end-shift-light {
          color: white !important;
        }
        
        .logs-end-shift-light span {
          color: white !important;
        }
        
        .logs-export-light {
          color: white !important;
        }
        
        .logs-export-light span {
          color: white !important;
        }
        
        .logs-export-light svg {
          color: white !important;
        }
        
        .logs-clear-light {
          color: white !important;
        }
        
        .logs-clear-light span {
          color: white !important;
        }
        
        .logs-clear-light svg {
          color: white !important;
        }
        
        /* Force white text for modal action buttons in light mode */
        .end-shift-button-light {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .end-shift-button-light span {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .end-shift-button-light svg {
          color: white !important;
        }
        
        .end-shift-button-light * {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .clear-logs-button-light {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .clear-logs-button-light span {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .clear-logs-button-light svg {
          color: white !important;
        }
        
        .clear-logs-button-light * {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        /* Additional specificity for button text */
        button.end-shift-button-light,
        button.clear-logs-button-light {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        button.end-shift-button-light *,
        button.clear-logs-button-light * {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        /* Force white text for action buttons in light mode */
        .action-button-light {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .action-button-light * {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .action-button-light span {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        /* Force white text for active tab buttons */
        .active-tab-text {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .active-tab-text * {
          color: white !important;
          -webkit-text-fill-color: white !important;
          -webkit-text-stroke-color: transparent !important;
        }
      `}</style>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className={theme === "light" ? "text-xl font-bold mb-3 text-[#222]" : "text-xl font-bold mb-3 text-cyan-400"}>
            System Logs
          </h2>
          
          {/* Tab Navigation */}
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('system')}
              className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 ${
                activeTab === 'system'
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50 text-white active-tab-text'
                  : theme === 'light'
                    ? 'bg-gradient-to-r from-slate-200 to-slate-300 shadow-md shadow-slate-200/30 border border-slate-300/50 text-slate-700 hover:from-slate-300 hover:to-slate-400'
                    : 'bg-gradient-to-r from-slate-700 to-slate-600 shadow-md shadow-slate-700/30 border border-slate-600/50 text-slate-300 hover:from-slate-600 hover:to-slate-500'
              }`}
            >
              <span className={`font-semibold tracking-wide ${
                activeTab === 'system' ? 'active-tab-text' : ''
              }`}>System Logs</span>
              <div className={`absolute inset-0 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                activeTab === 'system' 
                  ? 'bg-gradient-to-r from-cyan-400/20 to-blue-500/20' 
                  : 'bg-gradient-to-r from-slate-400/20 to-slate-500/20'
              }`} />
            </button>
            <button
              onClick={() => setActiveTab('sync')}
              className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 ${
                activeTab === 'sync'
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50 text-white active-tab-text'
                  : theme === 'light'
                    ? 'bg-gradient-to-r from-slate-200 to-slate-300 shadow-md shadow-slate-200/30 border border-slate-300/50 text-slate-700 hover:from-slate-300 hover:to-slate-400'
                    : 'bg-gradient-to-r from-slate-700 to-slate-600 shadow-md shadow-slate-700/30 border border-slate-600/50 text-slate-300 hover:from-slate-600 hover:to-slate-500'
              }`}
            >
              <span className={`font-semibold tracking-wide ${
                activeTab === 'sync' ? 'active-tab-text' : ''
              }`}>Sync Logs</span>
              <div className={`absolute inset-0 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                activeTab === 'sync' 
                  ? 'bg-gradient-to-r from-cyan-400/20 to-blue-500/20' 
                  : 'bg-gradient-to-r from-slate-400/20 to-slate-500/20'
              }`} />
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className={`p-3 rounded-lg border ${
            theme === "light" 
              ? "bg-red-50 border-red-200 text-red-800" 
              : "bg-red-900/20 border-red-500/30 text-red-300"
          }`}>
            {error}
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-wrap gap-2 items-center">
          <input type="text" value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="Operator Name" className={inputClass} />
          <button 
            onClick={handleManualSync} 
            disabled={loading}
            className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white logs-manual-sync-light ${
              theme === 'light'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
            } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            style={{
              color: 'white !important'
            }}
            title="Trigger Manual Sync"
          >
            <span className="font-semibold tracking-wide !text-white logs-manual-sync-light" style={{ color: 'white !important' }}>Manual Sync</span>
            <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </button>
          <button 
            onClick={handleShiftEnd} 
            disabled={loading}
            className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white logs-end-shift-light ${
              theme === 'light'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
            } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            style={{
              color: 'white !important'
            }}
            title="End Shift and Sync to SAP"
          >
            <span className="font-semibold tracking-wide !text-white logs-end-shift-light" style={{ color: 'white !important' }}>End Shift</span>
            <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </button>
          <button 
            onClick={() => fetchLogs()} 
            disabled={loading}
            className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white ${
              theme === 'light'
                ? 'bg-gradient-to-r from-green-500 to-green-600 shadow-md shadow-green-500/30 border border-green-400/50'
                : 'bg-gradient-to-r from-green-500 to-green-600 shadow-md shadow-green-500/25'
            } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            style={{
              color: 'white !important'
            }}
            title="Refresh Logs"
          >
            <RefreshCw className={`h-3.5 w-3.5 !text-white ${loading ? 'animate-spin' : ''}`} style={{ color: 'white !important' }} />
            <span className="font-semibold tracking-wide !text-white" style={{ color: 'white !important' }}>Refresh</span>
          </button>
        </div>

        {/* Filters & Export */}
        <div className="flex flex-wrap justify-between items-center gap-2">
          <div className="flex gap-2 items-center">
            <Filter className="h-4 w-4" />
            <select value={filter} onChange={(e) => setFilter(e.target.value)} className={inputClass}>
              <option>All</option>
              <option>Success</option>
              <option>Error</option>
              <option>InProgress</option>
              <option>Reverted</option>
            </select>
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search logs..." className={inputClass} />
            <input 
              type="date" 
              value={shiftDate} 
              onChange={(e) => setShiftDate(e.target.value)} 
              className={inputClass}
              title="Filter by shift date"
            />
          </div>
          <div className="flex gap-2">
            <button 
              onClick={handleExport} 
              disabled={loading || (activeTab === 'system' && (!logs || logs.length === 0)) || (activeTab === 'sync' && (!syncLogsData || syncLogsData.length === 0))}
              className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white logs-export-light ${
                theme === 'light'
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600 shadow-md shadow-blue-500/30 border border-blue-400/50'
                  : 'bg-gradient-to-r from-cyan-500 to-cyan-600 shadow-md shadow-cyan-500/25'
              } ${loading || (activeTab === 'system' && (!logs || logs.length === 0)) || (activeTab === 'sync' && (!syncLogsData || syncLogsData.length === 0)) ? 'opacity-50 cursor-not-allowed' : ''}`}
              style={{
                color: 'white !important'
              }}
              title={activeTab === 'system' ? "Export System Logs to PDF" : "Export Sync Logs to PDF"}
            >
              <Download className="h-3.5 w-3.5 !text-white logs-export-light" style={{ color: 'white !important' }} />
              <span className="font-semibold tracking-wide !text-white logs-export-light" style={{ color: 'white !important' }}>
                {loading ? 'Exporting...' : 'Export PDF'}
              </span>
              <div className="absolute inset-0 rounded-md bg-gradient-to-r from-blue-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
            <button 
              onClick={handleClear} 
              className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white logs-clear-light ${
                theme === 'light'
                  ? 'bg-gradient-to-r from-red-500 to-red-600 shadow-md shadow-red-500/30 border border-red-400/50'
                  : 'bg-gradient-to-r from-red-500 to-red-600 shadow-md shadow-red-500/25'
              }`}
              style={{
                color: 'white !important'
              }}
              title="Clear All Logs"
            >
              <Trash2 className="h-3.5 w-3.5 !text-white logs-clear-light" style={{ color: 'white !important' }} />
              <span className="font-semibold tracking-wide !text-white logs-clear-light" style={{ color: 'white !important' }}>Clear</span>
              <div className="absolute inset-0 rounded-md bg-gradient-to-r from-red-400/20 to-red-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
          </div>
        </div>

        {/* System Logs Table */}
        {activeTab === 'system' && (
          <div
            className={`overflow-auto max-h-[500px] rounded-lg backdrop-blur-md shadow transition-all duration-300 ${
              theme === "light"
                ? "bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30"
                : "bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]"
            }`}
          >
            <table className={`min-w-full text-xs text-left font-mono ${theme === "light" ? "text-[#222]" : "text-cyan-200"}`}>
              <thead className={`${tableHeader} uppercase text-xs tracking-wider`}>
                <tr>
                  <th className="px-3 py-2">Timestamp</th>
                  <th className="px-3 py-2">Source</th>
                  <th className="px-3 py-2">Action</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Shift</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && currentLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Loading logs...</span>
                      </div>
                    </td>
                  </tr>
                ) : currentLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center">
                      <span>No logs found</span>
                    </td>
                  </tr>
                ) : (
                  currentLogs.map((log, idx) => (
                    <tr key={log.id || idx} className={`transition duration-150 border-b ${borderRow} ${idx % 2 === 0 ? tableRowEven : tableRowOdd}`}>
                      <td className="px-3 py-2">
                        {(() => {
                          try {
                            const timestamp = log.timestamp || log.created_at;
                            if (timestamp) {
                              // Parse the ISO timestamp - it should already include timezone info
                              const date = new Date(timestamp);
                              
                              // Check if the date is valid
                              if (isNaN(date.getTime())) {
                                return '-';
                              }
                              
                              // Format in local timezone (browser will automatically convert)
                              return date.toLocaleString('en-US', {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit',
                                hour12: true
                              });
                            }
                            return '-';
                          } catch (e) {
                            console.error('Timestamp parsing error:', e, 'for timestamp:', log.timestamp || log.created_at);
                            return '-';
                          }
                        })()}
                      </td>
                      <td className="px-3 py-2">{log.source}</td>
                      <td className="px-3 py-2">
                        {log.action || (log.details ? JSON.parse(log.details).sync_type?.replace('_', ' ') || "-" : "-")}
                      </td>
                      <td className="px-3 py-2">
                        {(() => {
                          let status = log.status;
                          if (!status && log.details) {
                            try {
                              const details = JSON.parse(log.details);
                              status = details.status;
                            } catch (e) {
                              // Ignore JSON parse errors
                            }
                          }
                          
                          if (status) {
                            return (
                              <span
                                className={`px-2 py-0.5 rounded-full text-xs font-bold shadow-sm ${
                                  status === "Success" || status === "success"
                                    ? theme === "light"
                                      ? "bg-green-400 text-green-900"
                                      : "bg-green-600 text-white"
                                    : status === "Error" || status === "error"
                                    ? theme === "light"
                                      ? "bg-red-300 text-red-900"
                                      : "bg-red-400 text-black"
                                    : status === "InProgress" || status === "in_progress"
                                    ? theme === "light"
                                      ? "bg-blue-300 text-blue-900"
                                      : "bg-blue-400 text-black"
                                    : status === "Reverted" || status === "reverted"
                                    ? theme === "light"
                                      ? "bg-orange-300 text-orange-900"
                                      : "bg-orange-400 text-black"
                                    : theme === "light"
                                    ? "bg-gray-300 text-gray-700"
                                    : "bg-gray-500 text-white"
                                }`}
                              >
                                {status}
                              </span>
                            );
                          } else {
                            return (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                theme === "light" 
                                  ? "bg-gray-100 text-gray-500" 
                                  : "bg-gray-700 text-gray-400"
                              }`}>
                                -
                              </span>
                            );
                          }
                        })()}
                      </td>
                      <td className="px-3 py-2">
                        {(() => {
                          try {
                            const ts = log.timestamp || log.created_at;
                            if (!ts) return log.shift || '-';
                            const d = new Date(ts);
                            if (isNaN(d.getTime())) return log.shift || '-';
                            const h = d.getHours();
                            if (h >= 6 && h < 14) return 'A';
                            if (h >= 14 && h < 22) return 'B';
                            return 'C';
                          } catch {
                            return log.shift || '-';
                          }
                        })()}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleReport(log)}
                            className={`px-2 py-1 text-xs rounded transition-all duration-200 hover:scale-105 action-button-light ${
                              theme === 'light'
                                ? 'bg-blue-500 hover:bg-blue-600'
                                : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                            style={{ color: 'white !important' }}
                            title="Generate Report"
                          >
                            Report
                          </button>
                          <button
                            onClick={() => handleClaim(log)}
                            className={`px-2 py-1 text-xs rounded transition-all duration-200 hover:scale-105 action-button-light ${
                              theme === 'light'
                                ? 'bg-green-500 hover:bg-green-600'
                                : 'bg-green-600 hover:bg-green-700'
                            }`}
                            style={{ color: 'white !important' }}
                            title="Claim Log Entry"
                          >
                            Claim
                          </button>
                          {log.source === "Operator" && log.status !== "Reverted" && log.status !== "Error" && (
                            <button
                              onClick={() => handleUndo(log.id)}
                              disabled={loading}
                              className={`px-2 py-1 text-xs rounded transition-all duration-200 hover:scale-105 action-button-light ${
                                theme === 'light'
                                  ? 'bg-red-500 hover:bg-red-600'
                                  : 'bg-red-600 hover:bg-red-700'
                              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                              style={{ color: 'white !important' }}
                              title="Undo Action"
                            >
                              Undo
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* System Logs Pagination */}
        {activeTab === 'system' && logs.length > 0 && (
          <div className="flex items-center justify-between mt-4">
            <div className={`text-sm ${theme === "light" ? "text-gray-600" : "text-gray-400"}`}>
              Showing {startIndex + 1} to {Math.min(endIndex, logs.length)} of {logs.length} logs
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePreviousPage}
                disabled={currentPage === 1 || loading}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  currentPage === 1 || loading
                    ? theme === "light"
                      ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                      : "bg-gray-700 text-gray-500 cursor-not-allowed"
                    : theme === "light"
                    ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                    : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                }`}
              >
                Previous
              </button>
              
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  
                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      disabled={loading}
                      className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                        currentPage === pageNum
                          ? theme === "light"
                            ? "bg-blue-500 text-white"
                            : "bg-cyan-500 text-white"
                          : theme === "light"
                          ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                          : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              
              <button
                onClick={handleNextPage}
                disabled={currentPage === totalPages || loading}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  currentPage === totalPages || loading
                    ? theme === "light"
                      ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                      : "bg-gray-700 text-gray-500 cursor-not-allowed"
                    : theme === "light"
                    ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                    : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                }`}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modern End Shift Confirmation Modal */}
      {showEndShiftModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center animate-in fade-in duration-300">
          {/* Backdrop */}
          <div 
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${
              theme === 'light' 
                ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30' 
                : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
            }`}
            onClick={cancelEndShift}
          />
          
          {/* Modal */}
          <div className={`relative z-10 w-full max-w-md mx-4 rounded-xl shadow-2xl transform transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${
            theme === "light" 
              ? "bg-white/98 border border-gray-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]" 
              : "bg-slate-800/95 border border-slate-700 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]"
          }`}>
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${
                    theme === "light" 
                      ? "bg-orange-100 text-orange-600" 
                      : "bg-orange-900/30 text-orange-400"
                  }`}>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className={`text-lg font-semibold ${
                      theme === "light" ? "text-gray-900" : "text-white"
                    }`}>
                      End Shift Confirmation
                    </h3>
                    <p className={`text-sm ${
                      theme === "light" ? "text-gray-500" : "text-gray-400"
                    }`}>
                      SFMS Management System
                    </p>
                  </div>
                </div>
                <button
                  onClick={cancelEndShift}
                  className={`p-2 rounded-full transition-all duration-200 hover:scale-110 ${
                    theme === "light" 
                      ? "hover:bg-gray-100 text-gray-500 hover:text-gray-700" 
                      : "hover:bg-slate-700/50 text-gray-400 hover:text-gray-200"
                  }`}
                  title="Close modal"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="px-6 py-4">
              <p className={`text-sm leading-relaxed ${
                theme === "light" ? "text-gray-700" : "text-gray-300"
              }`}>
                Are you sure you want to end the current shift and sync all data to SAP? This action cannot be undone.
              </p>
              
              <div className={`mt-4 p-3 rounded-lg ${
                theme === "light" 
                  ? "bg-blue-50 border border-blue-200" 
                  : "bg-blue-900/20 border border-blue-700/30"
              }`}>
                <div className="flex items-center gap-2">
                  <svg className={`w-4 h-4 ${
                    theme === "light" ? "text-blue-600" : "text-blue-400"
                  }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className={`text-xs font-medium ${
                    theme === "light" ? "text-blue-800" : "text-blue-300"
                  }`}>
                    Operator: {operator}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Footer */}
            <div className={`px-6 py-4 border-t ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex justify-end gap-3">
                <button
                  onClick={cancelEndShift}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    theme === "light"
                      ? "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300"
                      : "bg-slate-700 text-gray-300 hover:bg-slate-600 border border-slate-600"
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  Cancel
                </button>
                <button
                  onClick={confirmEndShift}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 end-shift-button-light ${
                    theme === "light"
                      ? "bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600 shadow-md shadow-orange-500/25"
                      : "bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600 shadow-md shadow-orange-500/25"
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  style={{ 
                    color: 'white !important',
                    WebkitTextFillColor: 'white !important',
                    WebkitTextStrokeColor: 'transparent !important'
                  }}
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Processing...</span>
                    </div>
                  ) : (
                    "End Shift & Sync"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modern Clear Logs Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center animate-in fade-in duration-300">
          {/* Backdrop */}
          <div 
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${
              theme === 'light' 
                ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30' 
                : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
            }`}
            onClick={cancelClear}
          />
          
          {/* Modal */}
          <div className={`relative z-10 w-full max-w-md mx-4 rounded-xl shadow-2xl transform transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${
            theme === "light" 
              ? "bg-white/98 border border-gray-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]" 
              : "bg-slate-800/95 border border-slate-700 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]"
          }`}>
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${
                    theme === "light" 
                      ? "bg-red-100 text-red-600" 
                      : "bg-red-900/30 text-red-400"
                  }`}>
                    <Trash2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className={`text-lg font-semibold ${
                      theme === "light" ? "text-gray-900" : "text-white"
                    }`}>
                      Clear Old Logs
                    </h3>
                    <p className={`text-sm ${
                      theme === "light" ? "text-gray-500" : "text-gray-400"
                    }`}>
                      SFMS Management System
                    </p>
                  </div>
                </div>
                <button
                  onClick={cancelClear}
                  className={`p-2 rounded-full transition-all duration-200 hover:scale-110 ${
                    theme === "light" 
                      ? "hover:bg-gray-100 text-gray-500 hover:text-gray-700" 
                      : "hover:bg-slate-700/50 text-gray-400 hover:text-gray-200"
                  }`}
                  title="Close modal"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="px-6 py-4">
              <p className={`text-sm leading-relaxed ${
                theme === "light" ? "text-gray-700" : "text-gray-300"
              }`}>
                Clear logs older than 30 days? This action cannot be undone.
              </p>
              
              <div className={`mt-4 p-3 rounded-lg ${
                theme === "light" 
                  ? "bg-red-50 border border-red-200" 
                  : "bg-red-900/20 border border-red-700/30"
              }`}>
                <div className="flex items-center gap-2">
                  <svg className={`w-4 h-4 ${
                    theme === "light" ? "text-red-600" : "text-red-400"
                  }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className={`text-xs font-medium ${
                    theme === "light" ? "text-red-800" : "text-red-300"
                  }`}>
                    Warning: Permanent deletion
                  </span>
                </div>
              </div>
            </div>
            
            {/* Footer */}
            <div className={`px-6 py-4 border-t ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex justify-end gap-3">
                <button
                  onClick={cancelClear}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    theme === "light"
                      ? "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300"
                      : "bg-slate-700 text-gray-300 hover:bg-slate-600 border border-slate-600"
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  Cancel
                </button>
                <button
                  onClick={confirmClear}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 clear-logs-button-light ${
                    theme === "light"
                      ? "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-md shadow-red-500/25"
                      : "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-md shadow-red-500/25"
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  style={{ 
                    color: 'white !important',
                    WebkitTextFillColor: 'white !important',
                    WebkitTextStrokeColor: 'transparent !important'
                  }}
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Clearing...</span>
                    </div>
                  ) : (
                    "Clear Logs"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sync Logs Section */}
      {activeTab === 'sync' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className={theme === "light" ? "text-lg font-semibold text-[#222]" : "text-lg font-semibold text-cyan-400"}>
              Sync Activity Logs
            </h3>
          </div>

          {/* Sync Logs Table */}
          <div
            className={`overflow-auto max-h-[500px] rounded-lg backdrop-blur-md shadow transition-all duration-300 ${
              theme === "light"
                ? "bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30"
                : "bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]"
            }`}
          >
            <table className={`min-w-full text-xs text-left font-mono ${theme === "light" ? "text-[#222]" : "text-cyan-200"}`}>
              <thead className={`${tableHeader} uppercase text-xs tracking-wider`}>
                <tr>
                  <th className="px-3 py-2">Timestamp</th>
                  <th className="px-3 py-2">Message</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {syncLogsLoading ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-8 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Loading sync logs...</span>
                      </div>
                    </td>
                  </tr>
                ) : currentSyncLogs && currentSyncLogs.length > 0 ? (
                  currentSyncLogs.map((log: SyncLogEntry, idx: number) => (
                    <tr key={log.id} className={`transition duration-150 border-b ${borderRow} ${idx % 2 === 0 ? tableRowEven : tableRowOdd}`}>
                      <td className="px-3 py-2">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="px-3 py-2 max-w-xs">
                        <div className="truncate" title={log.message}>
                          {log.message}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          theme === "light" 
                            ? "bg-blue-100 text-blue-800" 
                            : "bg-blue-900/30 text-blue-300"
                        }`}>
                          {log.category}
                        </span>
                      </td>
                      <td className="px-3 py-2 max-w-xs">
                        {log.details ? (
                          <button
                            onClick={() => handleShowDetails(log.details)}
                            className={`px-2 py-1 rounded text-xs font-medium transition-all duration-200 hover:scale-105 ${
                              theme === "light" 
                                ? "bg-blue-100 text-blue-700 hover:bg-blue-200" 
                                : "bg-blue-900/30 text-blue-300 hover:bg-blue-800/50"
                            }`}
                            title="Click to view details"
                          >
                            View Details
                          </button>
                        ) : (
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            theme === "light" 
                              ? "bg-gray-100 text-gray-500" 
                              : "bg-gray-700 text-gray-400"
                          }`}>
                            -
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-3 py-8 text-center">
                      <div className="flex flex-col items-center gap-2">
                        <Database className="h-8 w-8 text-slate-400" />
                        <span>No sync logs found</span>
                        <span className="text-xs text-slate-500">
                          Sync activities will appear here when automatic syncs are triggered
                        </span>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Sync Logs Pagination */}
          {syncLogsData && syncLogsData.length > 0 && (
            <div className="flex items-center justify-between mt-4">
              <div className={`text-sm ${theme === "light" ? "text-gray-600" : "text-gray-400"}`}>
                Showing {syncStartIndex + 1} to {Math.min(syncEndIndex, syncLogsData.length)} of {syncLogsData.length} sync logs
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSyncPreviousPage}
                  disabled={syncCurrentPage === 1 || syncLogsLoading}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    syncCurrentPage === 1 || syncLogsLoading
                      ? theme === "light"
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-gray-700 text-gray-500 cursor-not-allowed"
                      : theme === "light"
                      ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                      : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                  }`}
                >
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, syncTotalPages) }, (_, i) => {
                    let pageNum;
                    if (syncTotalPages <= 5) {
                      pageNum = i + 1;
                    } else if (syncCurrentPage <= 3) {
                      pageNum = i + 1;
                    } else if (syncCurrentPage >= syncTotalPages - 2) {
                      pageNum = syncTotalPages - 4 + i;
                    } else {
                      pageNum = syncCurrentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handleSyncPageChange(pageNum)}
                        disabled={syncLogsLoading}
                        className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                          syncCurrentPage === pageNum
                            ? theme === "light"
                              ? "bg-blue-500 text-white"
                              : "bg-cyan-500 text-white"
                            : theme === "light"
                            ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                            : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                        } ${syncLogsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={handleSyncNextPage}
                  disabled={syncCurrentPage === syncTotalPages || syncLogsLoading}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    syncCurrentPage === syncTotalPages || syncLogsLoading
                      ? theme === "light"
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-gray-700 text-gray-500 cursor-not-allowed"
                      : theme === "light"
                      ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                      : "bg-blue-900/30 text-blue-300 hover:bg-blue-900/50"
                  }`}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modern Details Modal */}
      {showDetailsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center animate-in fade-in duration-300">
          {/* Backdrop */}
          <div 
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${
              theme === 'light' 
                ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30' 
                : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
            }`}
            onClick={handleCloseDetails}
          />
          
          {/* Modal */}
          <div className={`relative z-10 w-full max-w-2xl mx-4 rounded-xl shadow-2xl transform transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${
            theme === "light" 
              ? "bg-white/98 border border-gray-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]" 
              : "bg-slate-800/95 border border-slate-700 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]"
          }`}>
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${
                    theme === "light" 
                      ? "bg-blue-100 text-blue-600" 
                      : "bg-blue-900/30 text-blue-400"
                  }`}>
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className={`text-lg font-semibold ${
                      theme === "light" ? "text-gray-900" : "text-white"
                    }`}>
                      Sync Details
                    </h3>
                    <p className={`text-sm ${
                      theme === "light" ? "text-gray-500" : "text-gray-400"
                    }`}>
                      Detailed information about this sync operation
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleCloseDetails}
                  className={`p-2 rounded-full transition-all duration-200 hover:scale-110 ${
                    theme === "light" 
                      ? "hover:bg-gray-100 text-gray-500 hover:text-gray-700" 
                      : "hover:bg-slate-700/50 text-gray-400 hover:text-gray-200"
                  }`}
                  title="Close modal"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="px-6 py-4">
              {selectedLogDetails && (
                <div className="space-y-4">
                  {/* Status and Type */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className={`p-3 rounded-lg ${
                      theme === "light" 
                        ? "bg-green-50 border border-green-200" 
                        : "bg-green-900/20 border border-green-700/30"
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`w-2 h-2 rounded-full ${
                          selectedLogDetails.status === 'success' ? 'bg-green-500' : 'bg-red-500'
                        }`} />
                        <span className={`text-sm font-medium ${
                          theme === "light" ? "text-green-800" : "text-green-300"
                        }`}>
                          Status
                        </span>
                      </div>
                      <span className={`text-lg font-semibold capitalize ${
                        theme === "light" ? "text-green-900" : "text-green-200"
                      }`}>
                        {selectedLogDetails.status || 'Unknown'}
                      </span>
                    </div>
                    
                    <div className={`p-3 rounded-lg ${
                      theme === "light" 
                        ? "bg-blue-50 border border-blue-200" 
                        : "bg-blue-900/20 border border-blue-700/30"
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <Database className={`w-4 h-4 ${
                          theme === "light" ? "text-blue-600" : "text-blue-400"
                        }`} />
                        <span className={`text-sm font-medium ${
                          theme === "light" ? "text-blue-800" : "text-blue-300"
                        }`}>
                          Sync Type
                        </span>
                      </div>
                      <span className={`text-lg font-semibold capitalize ${
                        theme === "light" ? "text-blue-900" : "text-blue-200"
                      }`}>
                        {selectedLogDetails.sync_type?.replace('_', ' ') || 'Unknown'}
                      </span>
                    </div>
                  </div>

                  {/* Duration and Records */}
                  <div className="grid grid-cols-2 gap-4">
                    {selectedLogDetails.duration_seconds && (
                      <div className={`p-3 rounded-lg ${
                        theme === "light" 
                          ? "bg-purple-50 border border-purple-200" 
                          : "bg-purple-900/20 border border-purple-700/30"
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          <Clock className={`w-4 h-4 ${
                            theme === "light" ? "text-purple-600" : "text-purple-400"
                          }`} />
                          <span className={`text-sm font-medium ${
                            theme === "light" ? "text-purple-800" : "text-purple-300"
                          }`}>
                            Duration
                          </span>
                        </div>
                        <span className={`text-lg font-semibold ${
                          theme === "light" ? "text-purple-900" : "text-purple-200"
                        }`}>
                          {selectedLogDetails.duration_seconds.toFixed(2)}s
                        </span>
                      </div>
                    )}
                    
                    {selectedLogDetails.records_processed !== undefined && (
                      <div className={`p-3 rounded-lg ${
                        theme === "light" 
                          ? "bg-orange-50 border border-orange-200" 
                          : "bg-orange-900/20 border border-orange-700/30"
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className={`w-4 h-4 ${
                            theme === "light" ? "text-orange-600" : "text-orange-400"
                          }`} />
                          <span className={`text-sm font-medium ${
                            theme === "light" ? "text-orange-800" : "text-orange-300"
                          }`}>
                            Records Processed
                          </span>
                        </div>
                        <span className={`text-lg font-semibold ${
                          theme === "light" ? "text-orange-900" : "text-orange-200"
                        }`}>
                          {selectedLogDetails.records_processed}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Error Message */}
                  {selectedLogDetails.error_message && (
                    <div className={`p-3 rounded-lg ${
                      theme === "light" 
                        ? "bg-red-50 border border-red-200" 
                        : "bg-red-900/20 border border-red-700/30"
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        <XCircle className={`w-4 h-4 ${
                          theme === "light" ? "text-red-600" : "text-red-400"
                        }`} />
                        <span className={`text-sm font-medium ${
                          theme === "light" ? "text-red-800" : "text-red-300"
                        }`}>
                          Error Message
                        </span>
                      </div>
                      <p className={`text-sm ${
                        theme === "light" ? "text-red-700" : "text-red-200"
                      }`}>
                        {selectedLogDetails.error_message}
                      </p>
                    </div>
                  )}

                  {/* Additional Details */}
                  {selectedLogDetails.setting_id && (
                    <div className={`p-3 rounded-lg ${
                      theme === "light" 
                        ? "bg-gray-50 border border-gray-200" 
                        : "bg-gray-900/20 border border-gray-700/30"
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-sm font-medium ${
                          theme === "light" ? "text-gray-800" : "text-gray-300"
                        }`}>
                          Setting ID
                        </span>
                      </div>
                      <span className={`text-sm ${
                        theme === "light" ? "text-gray-700" : "text-gray-200"
                      }`}>
                        {selectedLogDetails.setting_id}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Footer */}
            <div className={`px-6 py-4 border-t ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className="flex justify-end">
                <button
                  onClick={handleCloseDetails}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    theme === "light"
                      ? "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300"
                      : "bg-slate-700 text-gray-300 hover:bg-slate-600 border border-slate-600"
                  }`}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </WaterSystemLayout>
  );
};

export default Logs;
