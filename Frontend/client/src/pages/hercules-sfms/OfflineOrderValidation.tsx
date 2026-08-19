// frontend/src/pages/hercules-sfms/OfflineOrderValidation.tsx

import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Scale, ListOrdered, FileEdit, Clock3, Package, Settings, WifiOff } from 'lucide-react';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { useTheme } from '../../contexts/ThemeContext';
import { getErrorMessage, extractApiErrorMessage, isNetworkError, isVpnError } from '../../utils/errorHandler';
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 OfflineOrderValidation.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

interface Order {
  id: number;
  order_id: string;
  po_number: string;
  material: string;
  material_desc?: string;
  version?: string;
  batch?: string;
  quantity: number;
  unit: string;
  status: string;
  confirmed_qty?: number;
  scrap?: number;
  order_type?: string;
  expected_weight?: number;
  scale1?: string;
  scale1_qty?: number;
  scale2?: string;
  scale2_qty?: number;
  scale3?: string;
  scale3_qty?: number;
  priority?: number;
}

interface KpiCardProps {
  title: string;
  value: number;
  unit: string;
  Icon: React.ComponentType<any>;
  color: string;
  showViewButton?: boolean;
  onViewClick?: () => void;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, unit, Icon, color, showViewButton, onViewClick }) => {
  const { theme } = useTheme();
  
  return (
    <div className="relative group">
      <div className={`p-4 lg:p-6 rounded-lg backdrop-blur-md border transition-all duration-500 shadow-md hover:shadow-lg h-full ${
        theme === 'light'
          ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
          : 'bg-slate-900/20 border-cyan-400/30 hover:border-cyan-400/50 shadow-[0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_30px_rgba(0,255,255,0.2)]'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h3 className={`text-sm lg:text-base font-bold uppercase tracking-widest mb-2 ${
              theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            } group-hover:text-opacity-80 transition-all duration-300`}>
              {title}
            </h3>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl lg:text-3xl font-black ${
                theme === 'light' ? 'text-slate-800' : 'text-white'
              } drop-shadow-sm group-hover:scale-105 transition-all duration-300`} style={{ color }}>
                {value}
              </span>
              <span className={`text-sm font-medium ${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                {unit}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {showViewButton && (
              <span onClick={onViewClick} className={`cursor-pointer text-xs font-medium transition-all duration-300 hover:opacity-80 flex-shrink-0 ${
                theme === 'light' ? 'text-blue-600' : 'text-cyan-400'
              }`}>
                View All
              </span>
            )}
            <div className={`p-2 rounded-md backdrop-blur-sm border transition-all duration-300 ${
              theme === 'light'
                ? 'bg-white/30 border-white/40'
                : 'bg-slate-800/40 border-cyan-400/30'
            }`} style={{ backgroundColor: theme === 'light' ? `${color}20` : `${color}15`, borderColor: `${color}40` }}>
              <Icon className="h-5 w-5 drop-shadow-lg transition-all duration-300 group-hover:scale-110" />
            </div>
          </div>
        </div>
      </div>
      
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none"
           style={{ background: `radial-gradient(circle at center, ${color}30, transparent 70%)` }} />
    </div>
  );
};

export const OfflineOrderValidation: React.FC = () => {
  const { theme } = useTheme();
  // ✅ REMOVED: apiBase variable - now using getApiUrl() from apiConfig.ts
  
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [scrap, setScrap] = useState(0);
  const [confirmedText, setConfirmedText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('All');

  // ✅ FIXED: Helper function to determine order type
  const getOrderType = (order: Order) => {
    // Priority 1: Use order_type if available
    if (order.order_type) {
      return order.order_type.toUpperCase();
    }
    
    // Priority 2: Check unit type
    // TO (Tonnes) or KG = MILLING
    // BAG = PACKING
    if (order.unit === 'TO' || order.unit === 'KG') {
      return 'MILLING';
    }
    
    if (order.unit === 'BAG') {
      return 'PACKING';
    }
    
    // Fallback
    return 'UNKNOWN';
  };

  // ✅ Fetch orders using the SAME API as online validation
  useEffect(() => {
    fetchPendingOrders();
  }, []);

  const fetchPendingOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // ✅ FIXED: Use the EXACT SAME API as online validation
      const statusFilterParam = 'Pending,Open,InProgress';
      const response = await apiFetch(getApiUrl(`/api/sap-sync/orders?statuses=${statusFilterParam}&limit=1000&offset=0`));
      
      if (!response.ok) {
        const errorMessage = await extractApiErrorMessage(response);
        throw new Error(errorMessage);
      }
      
      const responseData = await response.json();
      const apiOrders = responseData.ok ? responseData.orders : [];
      
      console.log('✅ Loaded orders from SAP sync API:', {
        total: apiOrders.length,
        pending: apiOrders.filter((o: Order) => o.status === 'Pending').length,
        inProgress: apiOrders.filter((o: Order) => o.status === 'InProgress').length,
        open: apiOrders.filter((o: Order) => o.status === 'Open').length,
      });
      
      setOrders(apiOrders || []);
    } catch (err: any) {
      console.error('Failed to fetch orders:', err);
      const errorMessage = getErrorMessage(err);
      setError(isNetworkError(err) 
        ? 'Network error: Unable to connect to server. Please check your connection.' 
        : errorMessage
      );
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!selectedOrder) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiFetch(getApiUrl(`/api/process_orders/${selectedOrder.po_number}/offline-confirm`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scrap: scrap,
          confirmed_text: confirmedText
        })
      });

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type');
      let data: any;
      
      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        data = { error: text || `HTTP ${response.status}: ${response.statusText}` };
      }

      if (response.ok && (data.success !== false)) {
        // Check if stored offline vs sent to SAP
        if (data.offline_mode) {
          setSuccess(`⏳ Order ${selectedOrder.po_number} stored for offline confirmation (VPN disconnected). Will sync automatically when VPN reconnects.`);
        } else {
          setSuccess(`✅ Order ${selectedOrder.po_number} validated and sent to SAP!`);
        }
        setSelectedOrder(null);
        setScrap(0);
        setConfirmedText('');
        fetchPendingOrders(); // Refresh order list
      } else {
        // Use error handler for better messages
        const errorMessage = getErrorMessage(data);
        
        // Check for VPN disconnect message
        if (isVpnError(data) || data.message?.includes('VPN')) {
          setError(`⚠️ VPN disconnected: ${errorMessage}`);
        } else {
          setError(errorMessage);
        }
      }
    } catch (err: any) {
      console.error('Validation error:', err);
      
      if (isNetworkError(err)) {
        setError('Network error: Unable to connect to server. Please check your connection and try again.');
      } else {
        setError(getErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const actualProduction = selectedOrder 
    ? (selectedOrder.confirmed_qty || 0) - scrap 
    : 0;

  // Filter orders by status
  const filteredOrders = statusFilter === 'All' 
    ? orders 
    : orders.filter(o => o.status === statusFilter);

  return (
    <WaterSystemLayout 
      title="Offline Order Validation"
      subtitle="Manual Order Validation with Scrap Tracking"
    >
      <div className="w-full space-y-6 px-4 lg:px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className={theme === 'light' ? 'text-xl font-bold text-[#222]' : 'text-xl font-bold text-cyan-400'}>
            📝 Offline Order Validation
          </h1>
        </div>

        {/* Success Message */}
        {success && (
          <div className={`p-3 rounded-lg backdrop-blur-md border transition-all duration-300 ${
            theme === 'light'
              ? 'bg-green-50/80 border-green-200/50 text-green-800'
              : 'bg-green-900/20 border-green-400/30 text-green-300 shadow-[0_20px_rgba(34,197,94,0.1)]'
          }`}>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{success}</span>
              <button onClick={() => setSuccess(null)} className={`ml-auto p-1 rounded-full transition-colors ${
                theme === 'light' ? 'hover:bg-green-100 text-green-600' : 'hover:bg-green-800/30 text-green-400'
              }`}>×</button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className={`p-3 rounded-lg backdrop-blur-md border transition-all duration-300 ${
            theme === 'light'
              ? 'bg-red-50/80 border-red-200/50 text-red-800'
              : 'bg-red-900/20 border-red-400/30 text-red-300 shadow-[0_20px_rgba(239,68,68,0.1)]'
          }`}>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{error}</span>
              <button onClick={() => setError(null)} className={`ml-auto p-1 rounded-full transition-colors ${
                theme === 'light' ? 'hover:bg-red-100 text-red-600' : 'hover:bg-red-800/30 text-red-400'
              }`}>×</button>
            </div>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mb-6">
          <KpiCard
            title="Total Orders"
            value={orders.length}
            unit="Orders"
            Icon={ListOrdered}
            color="#2563eb"
          />
          <KpiCard
            title="Selected"
            value={selectedOrder ? 1 : 0}
            unit=""
            Icon={FileEdit}
            color="#f59e0b"
          />
          <KpiCard
            title="Ready to Validate"
            value={selectedOrder && scrap >= 0 && actualProduction >= 0 ? 1 : 0}
            unit=""
            Icon={CheckCircle}
            color="#10b981"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Order List */}
          <div className={`rounded-lg backdrop-blur-md shadow transition-all duration-300 ${
            theme === 'light'
              ? 'bg-white/20 border border-slate-200/30'
              : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_20px_rgba(0,255,255,0.1)]'
          }`}>
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className={`text-lg font-semibold ${
                  theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                }`}>
                  Orders ({filteredOrders.length})
                </h2>
                
                {/* Status Filter */}
                <select 
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className={`px-3 py-1 border rounded text-sm ${
                    theme === 'light' 
                      ? 'bg-white border-slate-300' 
                      : 'bg-slate-700 border-slate-600'
                  }`}
                >
                  <option value="All">All Status</option>
                  <option value="Pending">Pending</option>
                  <option value="InProgress">In Progress</option>
                  <option value="Open">Open</option>
                </select>
              </div>
              
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {loading && orders.length === 0 ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-current mx-auto" />
                    <p className="mt-2 text-sm">Loading orders...</p>
                  </div>
                ) : filteredOrders.length === 0 ? (
                  <div className="text-center py-8 text-sm opacity-70">
                    <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No orders found</p>
                    <p className="text-xs mt-1">Try changing the filter</p>
                  </div>
                ) : (
                  filteredOrders.map((order) => {
                    const orderType = getOrderType(order);
                    const isMilling = orderType === 'MILLING';
                    
                    return (
                      <div
                        key={order.id}
                        onClick={() => {
                          setSelectedOrder(order);
                          setScrap(0);
                          setConfirmedText('');
                          setError(null);
                          setSuccess(null);
                        }}
                        className={`p-3 border rounded cursor-pointer transition-all duration-200 hover:scale-[1.02] ${
                          selectedOrder?.id === order.id
                            ? theme === 'light'
                              ? 'bg-blue-100 border-blue-500'
                              : 'bg-blue-900/30 border-blue-500'
                            : theme === 'light'
                              ? 'bg-white hover:bg-blue-50 border-slate-200'
                              : 'bg-slate-800/50 hover:bg-slate-700/50 border-slate-600'
                        }`}
                      >
                        <div className="flex justify-between items-start gap-3">
                          <div className="flex-1 min-w-0">
                            {/* Order Number with Type Indicator */}
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <p className="font-medium font-mono">{order.po_number}</p>
                              {/* Inline Type Badge */}
                              <span className={`text-xs px-2 py-0.5 rounded font-bold flex items-center gap-1 ${
                                isMilling
                                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                                  : 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300'
                              }`}>
                                {isMilling ? '⚙️ MILLING' : '📦 PACKING'}
                              </span>
                              {/* Status Badge */}
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                order.status === 'Pending' 
                                  ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                                  : order.status === 'InProgress'
                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                                    : 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300'
                              }`}>
                                {order.status}
                              </span>
                            </div>
                            
                            {/* Material Info */}
                            <p className="text-sm opacity-80 truncate">{order.material}</p>
                            {order.material_desc && (
                              <p className="text-xs opacity-70 truncate">{order.material_desc}</p>
                            )}
                            
                            {/* Target and Priority */}
                            <div className="flex items-center gap-3 mt-1 flex-wrap">
                              <p className="text-sm">
                                Target: <span className="font-bold">{order.quantity}</span> {order.unit}
                              </p>
                              {order.priority && (
                                <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400">
                                  P{order.priority}
                                </span>
                              )}
                            </div>
                            
                            {/* Current Production (if available) */}
                            {order.confirmed_qty && order.confirmed_qty > 0 && (
                              <p className="text-xs text-blue-600 dark:text-blue-400 mt-1 flex items-center gap-1">
                                <Scale size={12} />
                                Current: {order.confirmed_qty.toFixed(2)} {order.unit}
                              </p>
                            )}
                          </div>
                          
                          {/* Large Order Type Badge */}
                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <span className={`px-3 py-1.5 rounded-lg text-sm font-bold whitespace-nowrap shadow-sm flex items-center gap-1 ${
                              isMilling
                                ? theme === 'light'
                                  ? 'bg-purple-500 text-white'
                                  : 'bg-purple-600 text-white'
                                : theme === 'light'
                                  ? 'bg-cyan-500 text-white'
                                  : 'bg-cyan-600 text-white'
                            }`}>
                              {isMilling ? <Settings size={14} /> : <Package size={14} />}
                              {isMilling ? 'MILL' : 'PACK'}
                            </span>
                            <span className="text-xs opacity-60">
                              {order.unit}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right: Validation Form */}
          <div className={`rounded-lg backdrop-blur-md shadow transition-all duration-300 ${
            theme === 'light'
              ? 'bg-white/20 border border-slate-200/30'
              : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_20px_rgba(0,255,255,0.1)]'
          }`}>
            <div className="p-4">
              {selectedOrder ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className={`text-lg font-semibold ${
                      theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                    }`}>Validate Order</h2>
                    
                    {/* Order Type Badge in Header */}
                    <span className={`px-3 py-1 rounded-lg text-sm font-bold flex items-center gap-1 ${
                      getOrderType(selectedOrder) === 'MILLING'
                        ? 'bg-purple-500 text-white'
                        : 'bg-cyan-500 text-white'
                    }`}>
                      {getOrderType(selectedOrder) === 'MILLING' ? <Settings size={16} /> : <Package size={16} />}
                      {getOrderType(selectedOrder) === 'MILLING' ? 'MILLING' : 'PACKING'}
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Order ID</label>
                      <input 
                        type="text" 
                        value={selectedOrder.po_number} 
                        disabled 
                        className={`w-full px-3 py-2 border rounded ${
                          theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-slate-700 text-gray-300'
                        }`}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Material</label>
                      <input 
                        type="text" 
                        value={`${selectedOrder.material}${selectedOrder.material_desc ? ' - ' + selectedOrder.material_desc : ''}`}
                        disabled 
                        className={`w-full px-3 py-2 border rounded ${
                          theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-slate-700 text-gray-300'
                        }`}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Target Quantity</label>
                      <input 
                        type="text" 
                        value={`${selectedOrder.quantity} ${selectedOrder.unit}`}
                        disabled 
                        className={`w-full px-3 py-2 border rounded ${
                          theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-slate-700 text-gray-300'
                        }`}
                      />
                    </div>

                    {/* Scale Data (from SCADA) */}
                    {(selectedOrder.scale1_qty || selectedOrder.scale2_qty || selectedOrder.scale3_qty) ? (
                      <div className={`p-3 rounded ${
                        theme === 'light' ? 'bg-blue-50 border border-blue-200' : 'bg-blue-900/20 border border-blue-700'
                      }`}>
                        <p className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Scale size={16} />
                          Production from Scales (SCADA)
                        </p>
                        {selectedOrder.scale1 && selectedOrder.scale1_qty > 0 && (
                          <p className="text-xs">
                            {selectedOrder.scale1}: {selectedOrder.scale1_qty.toFixed(2)} KG
                          </p>
                        )}
                        {selectedOrder.scale2 && selectedOrder.scale2_qty > 0 && (
                          <p className="text-xs">
                            {selectedOrder.scale2}: {selectedOrder.scale2_qty.toFixed(2)} KG
                          </p>
                        )}
                        {selectedOrder.scale3 && selectedOrder.scale3_qty > 0 && (
                          <p className="text-xs">
                            {selectedOrder.scale3}: {selectedOrder.scale3_qty.toFixed(2)} KG
                          </p>
                        )}
                        <p className="text-sm font-bold mt-2">
                          Total Production: {(selectedOrder.confirmed_qty || 0).toFixed(2)} {selectedOrder.unit}
                        </p>
                      </div>
                    ) : (
                      <div className={`p-3 rounded ${
                        theme === 'light' ? 'bg-yellow-50 border border-yellow-200' : 'bg-yellow-900/20 border border-yellow-700'
                      }`}>
                        <p className="text-sm flex items-center gap-2">
                          <AlertCircle size={16} />
                          No SCADA data available for this order
                        </p>
                      </div>
                    )}

                    {/* Scrap Input */}
                    <div>
                      <label className="block text-sm font-medium mb-1 text-red-600 dark:text-red-400">
                        Scrap (Damaged) *
                      </label>
                      <input 
                        type="number" 
                        value={scrap}
                        onChange={(e) => setScrap(parseFloat(e.target.value) || 0)}
                        className={`w-full px-3 py-2 border rounded focus:ring-2 focus:ring-red-500 ${
                          theme === 'light' 
                            ? 'border-red-300 bg-white' 
                            : 'border-red-700 bg-slate-700'
                        }`}
                        placeholder="Enter damaged quantity"
                        min="0"
                      />
                    </div>

                    {/* Actual Production Calculation */}
                    <div className={`p-3 rounded ${
                      theme === 'light' ? 'bg-purple-50 border border-purple-200' : 'bg-purple-900/20 border border-purple-700'
                    }`}>
                      <p className="text-sm">
                        <strong>Actual Production:</strong> {actualProduction.toFixed(2)} {selectedOrder.unit}
                      </p>
                      <p className="text-xs opacity-70">
                        = Production ({(selectedOrder.confirmed_qty || 0).toFixed(2)}) - Scrap ({scrap.toFixed(2)})
                      </p>
                      {actualProduction < 0 && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                          ⚠️ Warning: Scrap cannot exceed production!
                        </p>
                      )}
                    </div>

                    {/* Notes */}
                    <div>
                      <label className="block text-sm font-medium mb-1">Notes (Optional)</label>
                      <textarea 
                        value={confirmedText}
                        onChange={(e) => setConfirmedText(e.target.value)}
                        className={`w-full px-3 py-2 border rounded ${
                          theme === 'light' ? 'bg-white' : 'bg-slate-700'
                        }`}
                        rows={3}
                        placeholder="Add validation notes..."
                      />
                    </div>

                    <button
                      onClick={handleValidate}
                      disabled={loading || actualProduction < 0}
                      className={`w-full px-4 py-3 rounded font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
                        loading || actualProduction < 0
                          ? 'opacity-50 cursor-not-allowed bg-gray-400'
                          : 'hover:scale-105 bg-purple-600 hover:bg-purple-700'
                      } text-white`}
                    >
                      <CheckCircle size={20} />
                      {loading ? 'Validating & Sending to SAP...' : 'Validate & Send to SAP'}
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center text-gray-500 dark:text-gray-400 py-12">
                  <Clock3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>← Select an order from the list to validate</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </WaterSystemLayout>
  );
};
