import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { apiFetch, getApiUrl } from '../../lib/apiConfig';
import { 
  ArrowUpRight, 
  ArrowDownLeft, 
  Search, 
  Filter, 
  Clock, 
  AlertCircle, 
  CheckCircle, 
  X,
  Code,
  Copy,
  Download
} from 'lucide-react';

interface SapLogEntry {
  id: number;
  direction: 'sent' | 'received';
  endpoint: string;
  method: string;
  status_code: number;
  po_number: string | null;
  log_type: string | null;
  created_at: string;
  duration_ms: number | null;
  error_message: string | null;
}

interface SapLogDetail extends SapLogEntry {
  request_payload: any;
  response_payload: any;
}

const SapLog = () => {
  const { theme } = useTheme();
  const [logs, setLogs] = useState<SapLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [limit, setLimit] = useState(50);
  
  // Filters
  const [directionFilter, setDirectionFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [poSearch, setPoSearch] = useState('');
  
  // Detail Modal
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const [logDetail, setLogDetail] = useState<SapLogDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });
      
      if (directionFilter) params.append('direction', directionFilter);
      if (typeFilter) params.append('log_type', typeFilter);
      if (poSearch) params.append('po_number', poSearch);
      
      const response = await apiFetch(getApiUrl(`/api/sap-logs?${params.toString()}`));
      if (!response.ok) throw new Error('Failed to fetch logs');
      
      const data = await response.json();
      setLogs(data.logs);
      setTotalPages(data.pages);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchLogDetail = async (id: number) => {
    try {
      setDetailLoading(true);
      const response = await apiFetch(getApiUrl(`/api/sap-logs/${id}`));
      if (!response.ok) throw new Error('Failed to fetch detail');
      
      const data = await response.json();
      setLogDetail(data.log);
    } catch (err: any) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, limit, directionFilter, typeFilter]); // Trigger on filter change

  // Debounced search for PO
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      fetchLogs();
    }, 500);
    return () => clearTimeout(timer);
  }, [poSearch]);

  const handleRowClick = (id: number) => {
    setSelectedLogId(id);
    fetchLogDetail(id);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Could add toast here
  };

  return (
    <WaterSystemLayout
      title="SAP Interface Logs"
      subtitle="View all API requests and responses to SAP"
    >
      <div className="space-y-4">
        {/* Filters */}
        <div className={`p-4 rounded-lg border flex flex-wrap gap-4 items-center ${
          theme === 'light' ? 'bg-white border-gray-200' : 'bg-slate-800 border-slate-700'
        }`}>
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by PO Number..."
              value={poSearch}
              onChange={(e) => setPoSearch(e.target.value)}
              className={`w-full bg-transparent outline-none text-sm ${
                theme === 'light' ? 'text-gray-800' : 'text-gray-200'
              }`}
            />
          </div>
          
          <select
            value={directionFilter}
            onChange={(e) => { setDirectionFilter(e.target.value); setPage(1); }}
            className={`px-3 py-1.5 rounded text-sm border outline-none ${
              theme === 'light' ? 'bg-gray-50 border-gray-300' : 'bg-slate-700 border-slate-600 text-gray-200'
            }`}
          >
            <option value="">All Directions</option>
            <option value="sent">Sent</option>
            <option value="received">Received</option>
          </select>
          
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className={`px-3 py-1.5 rounded text-sm border outline-none ${
              theme === 'light' ? 'bg-gray-50 border-gray-300' : 'bg-slate-700 border-slate-600 text-gray-200'
            }`}
          >
            <option value="">All Types</option>
            <option value="online_confirmation">Online Confirmation</option>
            <option value="offline_confirmation">Offline Confirmation</option>
            <option value="order_sync">Order Sync</option>
            <option value="raw_data">Raw Data</option>
          </select>
          
          <button
            onClick={fetchLogs}
            className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Table */}
        <div className={`rounded-lg border overflow-hidden ${
          theme === 'light' ? 'bg-white border-gray-200' : 'bg-slate-800 border-slate-700'
        }`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className={`text-xs uppercase ${
                theme === 'light' ? 'bg-gray-50 text-gray-700' : 'bg-slate-700 text-gray-300'
              }`}>
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Direction</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Endpoint</th>
                  <th className="px-4 py-3">PO Number</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Duration</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${theme === 'light' ? 'divide-gray-100' : 'divide-slate-700'}`}>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center">
                      <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-blue-500 border-t-transparent"></div>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                      No logs found
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr
                      key={log.id}
                      onClick={() => handleRowClick(log.id)}
                      className={`cursor-pointer transition-colors ${
                        theme === 'light' ? 'hover:bg-gray-50' : 'hover:bg-slate-700/50'
                      }`}
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-mono">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                          log.direction === 'sent'
                            ? theme === 'light' ? 'bg-blue-100 text-blue-700' : 'bg-blue-900/30 text-blue-300'
                            : theme === 'light' ? 'bg-purple-100 text-purple-700' : 'bg-purple-900/30 text-purple-300'
                        }`}>
                          {log.direction === 'sent' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownLeft className="w-3 h-3" />}
                          {log.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {log.log_type?.replace(/_/g, ' ') || '-'}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs truncate max-w-[200px]" title={log.endpoint}>
                        {log.endpoint}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">
                        {log.po_number || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          log.status_code && log.status_code >= 200 && log.status_code < 300
                            ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                            : theme === 'light' ? 'bg-red-100 text-red-700' : 'bg-red-900/30 text-red-300'
                        }`}>
                          {log.status_code || 'ERR'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs font-mono">
                        {log.duration_ms ? `${log.duration_ms}ms` : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          {/* Pagination */}
          <div className={`px-4 py-3 border-t flex justify-between items-center ${
            theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-slate-700 bg-slate-800'
          }`}>
            <span className={`text-xs ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-xs rounded border disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 text-xs rounded border disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedLogId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className={`w-full max-w-4xl max-h-[90vh] rounded-lg shadow-2xl flex flex-col ${
            theme === 'light' ? 'bg-white' : 'bg-slate-900 border border-slate-700'
          }`}>
            <div className={`flex items-center justify-between p-4 border-b ${
              theme === 'light' ? 'border-gray-200' : 'border-slate-700'
            }`}>
              <h3 className={`text-lg font-bold ${theme === 'light' ? 'text-gray-800' : 'text-white'}`}>
                Log Details #{selectedLogId}
              </h3>
              <button
                onClick={() => setSelectedLogId(null)}
                className={`p-2 rounded-full hover:bg-opacity-20 ${
                  theme === 'light' ? 'hover:bg-gray-200 text-gray-500' : 'hover:bg-gray-700 text-gray-400'
                }`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {detailLoading || !logDetail ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div className={`p-3 rounded ${theme === 'light' ? 'bg-gray-50' : 'bg-slate-800'}`}>
                      <div className="text-gray-500 text-xs mb-1">Status</div>
                      <div className={`font-mono font-bold ${
                        logDetail.status_code && logDetail.status_code >= 200 && logDetail.status_code < 300
                          ? 'text-green-600' : 'text-red-600'
                      }`}>{logDetail.status_code}</div>
                    </div>
                    <div className={`p-3 rounded ${theme === 'light' ? 'bg-gray-50' : 'bg-slate-800'}`}>
                      <div className="text-gray-500 text-xs mb-1">Method</div>
                      <div className={`font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-white'}`}>
                        {logDetail.method}
                      </div>
                    </div>
                    <div className={`p-3 rounded ${theme === 'light' ? 'bg-gray-50' : 'bg-slate-800'}`}>
                      <div className="text-gray-500 text-xs mb-1">Duration</div>
                      <div className={`font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-white'}`}>
                        {logDetail.duration_ms}ms
                      </div>
                    </div>
                    <div className={`p-3 rounded ${theme === 'light' ? 'bg-gray-50' : 'bg-slate-800'}`}>
                      <div className="text-gray-500 text-xs mb-1">Time</div>
                      <div className={`font-mono font-bold text-xs ${theme === 'light' ? 'text-gray-800' : 'text-white'}`}>
                        {new Date(logDetail.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>

                  <div className={`p-3 rounded text-sm font-mono break-all ${
                    theme === 'light' ? 'bg-gray-50 text-gray-600' : 'bg-slate-800 text-gray-300'
                  }`}>
                    {logDetail.endpoint}
                  </div>

                  {logDetail.error_message && (
                    <div className={`p-4 rounded border-l-4 ${
                      theme === 'light' 
                        ? 'bg-red-50 border-red-500 text-red-700' 
                        : 'bg-red-900/20 border-red-500 text-red-300'
                    }`}>
                      <h4 className="font-bold text-sm mb-1">Error Message</h4>
                      <p className="text-sm">{logDetail.error_message}</p>
                    </div>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className={`text-sm font-bold flex items-center gap-2 ${
                        theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                      }`}>
                        <Code className="w-4 h-4" /> Request Payload
                      </h4>
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(logDetail.request_payload, null, 2))}
                        className="text-xs text-blue-500 hover:underline flex items-center gap-1"
                      >
                        <Copy className="w-3 h-3" /> Copy
                      </button>
                    </div>
                    <pre className={`p-4 rounded-lg overflow-x-auto text-xs font-mono border ${
                      theme === 'light' 
                        ? 'bg-gray-50 border-gray-200 text-gray-800' 
                        : 'bg-slate-950 border-slate-700 text-green-400'
                    }`}>
                      {JSON.stringify(logDetail.request_payload, null, 2)}
                    </pre>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className={`text-sm font-bold flex items-center gap-2 ${
                        theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                      }`}>
                        <Code className="w-4 h-4" /> Response Payload
                      </h4>
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(logDetail.response_payload, null, 2))}
                        className="text-xs text-blue-500 hover:underline flex items-center gap-1"
                      >
                        <Copy className="w-3 h-3" /> Copy
                      </button>
                    </div>
                    <pre className={`p-4 rounded-lg overflow-x-auto text-xs font-mono border ${
                      theme === 'light' 
                        ? 'bg-gray-50 border-gray-200 text-gray-800' 
                        : 'bg-slate-950 border-slate-700 text-blue-300'
                    }`}>
                      {JSON.stringify(logDetail.response_payload, null, 2)}
                    </pre>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </WaterSystemLayout>
  );
};

export default SapLog;

