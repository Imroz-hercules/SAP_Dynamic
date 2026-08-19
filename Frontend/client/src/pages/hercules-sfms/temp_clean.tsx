import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { ListOrdered, CheckCircle, XCircle, Clock3, AlertCircle, X, Search, Filter, Play, BarChart3 } from 'lucide-react';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { orderApi, Order, ValidationRequest, ValidationResult } from '../../lib/api';
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';
import OrderValidationModal from '../../components/OrderValidationModal';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 temp_clean.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}
import OrderRejectionModal, { RejectionData } from '../../components/OrderRejectionModal';
import OrderTable from '../../components/OrderTable';

interface KpiCardProps {
  title: string;
  value: number;
  unit: string;
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
  showViewButton?: boolean;
  onViewClick?: () => void;
  showUnderlineText?: boolean;
  underlineText?: string;
  onUnderlineClick?: () => void;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, unit, Icon, color, showViewButton, onViewClick, showUnderlineText, underlineText, onUnderlineClick }) => {
  const { theme } = useTheme();
  
  return (
    <div className="relative group">
      {/* Glassmorphism card with transparent background */}
      <div className={`p-4 lg:p-6 rounded-lg backdrop-blur-md border transition-all duration-500 shadow-md hover:shadow-lg h-full ${
        theme === 'light' 
          ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
          : 'bg-slate-900/20 border-cyan-400/30 hover:border-cyan-400/50 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_30px_rgba(0,255,255,0.2)]'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h3 className={`text-sm lg:text-base font-bold uppercase tracking-widest mb-2 ${
              theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            } group-hover:text-opacity-80 transition-all duration-300`}>
              {title}
            </h3>
            <div className="flex items-baseline gap-2">
              <span 
                className={`text-2xl lg:text-3xl font-black ${
                  theme === 'light' ? 'text-slate-800' : 'text-white'
                } drop-shadow-sm group-hover:scale-105 transition-all duration-300`}
                style={{ color }}
              >
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
              <span
                onClick={onViewClick}
                className={`cursor-pointer text-xs font-medium transition-all duration-300 hover:opacity-80 flex-shrink-0 ${
                  theme === 'light' ? 'text-blue-600' : 'text-cyan-400'
                }`}
                title={`View ${title.toLowerCase()}`}
              >
                View All
              </span>
            )}
            <div 
              className={`p-2 rounded-md backdrop-blur-sm border transition-all duration-300 ${
                theme === 'light' 
                  ? 'bg-white/30 border-white/40' 
                  : 'bg-slate-800/40 border-cyan-400/30'
              }`}
              style={{ 
                backgroundColor: theme === 'light' ? `${color}20` : `${color}15`,
                borderColor: `${color}40`
              }}
            >
              <Icon 
                className={`h-5 w-5 drop-shadow-lg transition-all duration-300 group-hover:scale-110`} 
              />
            </div>
          </div>
        </div>
        
        {/* Simple text without underline */}
        {showUnderlineText && underlineText && (
          <div className="mt-2">
            <button
              onClick={onUnderlineClick}
              disabled={value === 0}
              className={`text-xs font-medium transition-all duration-300 hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed ${
                theme === 'light' ? 'text-slate-600' : 'text-slate-300'
              }`}
              style={{ 
                color: value === 0 ? (theme === 'light' ? '#94a3b8' : '#64748b') : color
              }}
            >
              {underlineText}
            </button>
          </div>
        )}
        
        {/* Animated glow effect */}
        <div 
          className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none"
          style={{
            background: `radial-gradient(circle at center, ${color}30, transparent 70%)`
          }}
        ></div>
        
        {/* Pulse animation ring */}
        <div 
          className="absolute -inset-1 rounded-xl opacity-0 group-hover:opacity-50 transition-opacity duration-500 pointer-events-none animate-pulse"
          style={{
            background: `linear-gradient(45deg, ${color}20, transparent, ${color}20)`
          }}
        ></div>
      </div>
      
      {/* Floating particles effect for dark mode */}
      {theme === 'dark' && (
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 rounded-full animate-ping"
              style={{
                backgroundColor: color,
                left: `${15 + i * 25}%`,
                top: `${20 + (i % 2) * 40}%`,
                animationDelay: `${i * 0.3}s`,
                animationDuration: '2s'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Fallback mock 

const statusOptions = ['All', 'Pending', 'InProgress'];

const ProcessOrderValidation = () => {
  // ✅ REMOVED: apiBase variable - now using getApiUrl() from apiConfig.ts
  
  // Priority update functions
  const updateOrderPriority = async (poNumber: string, newPriority: number) => {
    try {
      const response = await apiFetch(getApiUrl(`/api/orders/${poNumber}/priority`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: newPriority })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to update priority:', error);
      throw error;
    }
  };

  const bulkUpdatePriorities = async (orderUpdates: Array<{po_number: string, priority: number}>) => {
    try {
      const response = await apiFetch(getApiUrl('/api/orders/priority/bulk'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderUpdates)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to bulk update priorities:', error);
      throw error;
    }
  };

  const [orders, setOrders] = useState<Order[]>([]);
  const [statusFilter, setStatusFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validatingOrder, setValidatingOrder] = useState<number | null>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showRejectionModal, setShowRejectionModal] = useState(false);
  const [selectedOrderId, setSelectedOrderId] = useState<number>(0);
  const [selectedOrderDetails, setSelectedOrderDetails] = useState<{
    po_number?: string;
    material?: string;
    quantity?: number;
    unit?: string;
  } | null>(null);
  const [modalDefaults, setModalDefaults] = useState<Partial<ValidationRequest & { expected_quantity?: number; unit?: string }> | undefined>(undefined);
  const [showOrdersModal, setShowOrdersModal] = useState(false);
  const [modalOrders, setModalOrders] = useState<Order[]>([]);
  const [modalTitle, setModalTitle] = useState('');
  const [modalType, setModalType] = useState<'validated' | 'rejected'>('validated');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Progress dialog state
  const [showProgressDialog, setShowProgressDialog] = useState(false);
  const [selectedOrderProgress, setSelectedOrderProgress] = useState<{
    po_number: string;
    material: string;
    expected_tons: number;
    current_tons: number;
    remaining_tons: number;
    progress_pct: number;
    status: string;
    last_tick: string | null;
  } | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const { theme } = useTheme();

  // Auto Validator state
  const [autoValidatorStatus, setAutoValidatorStatus] = useState({
    running: false,
    current_po: null as string | null,
    progress_pct: 0,
    expected_tons: 0,
    delta_tons: 0,
    baseline: null as number | null,
    last_tick: null as string | null
  });
  const [orderProgress, setOrderProgress] = useState<Record<string, number>>({});
  const [toasts, setToasts] = useState<Array<{id: string, message: string, type: 'success' | 'error' | 'info'}>>([]);
  const [previousStatus, setPreviousStatus] = useState<typeof autoValidatorStatus | null>(null);

  // Handle drag and drop reordering with API calls
  const handleReorder = async (reorderedOrders: Order[]) => {
    try {
      // Prepare bulk update data
      const orderUpdates = reorderedOrders.map((order, index) => ({
        po_number: order.po_number || '',
        priority: index + 1
      }));

      // Call bulk update API
      await bulkUpdatePriorities(orderUpdates);
      
      // Update local state
      setOrders(reorderedOrders);
      
      // Show success message
      addToast(
        'Order Priorities Updated',
        `Successfully reordered ${reorderedOrders.length} orders`,
        'success'
      );
    } catch (error) {
      console.error('Failed to update priorities:', error);
      addToast(
        'Priority Update Failed',
        'Failed to update order priorities. Please try again.',
        'error'
      );
    }
  };

  // Load orders from process_orders table with priority + FIFO ordering
  const loadOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch only Pending and InProgress orders for validation
      const response = await apiFetch(getApiUrl('/api/orders?statuses=Pending,InProgress&limit=100'));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      const apiOrders = await response.json();
      setOrders(apiOrders);
    } catch (err) {
      console.error('Failed to load orders:', err);
      setError('Failed to load orders from server.');
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  // Load orders on component mount and when filter changes
  useEffect(() => {
    loadOrders();
  }, [statusFilter]);

  // Dev helper: Seed demo order
  const seedDemoOrder = async () => {
    try {
      const response = await apiFetch(getApiUrl('/api/dev/seed-order'), { 
        method: 'POST' 
      });
      const data = await response.json();
      if (data.ok) {
        await loadOrders();
        setSelectedOrderId(data.order_id);
      }
    } catch (err) {
      console.error('Failed to seed demo order:', err);
      setError('Failed to seed demo order');
    }
  };

  // Dev helper: Load demo receipts
  const loadDemoReceipts = async (pass = true) => {
    try {
      const response = await apiFetch(getApiUrl(`/api/dev/demo-receipts/${pass ? 'pass' : 'fail'}`));
      const data = await response.json();
      setModalDefaults(data);
      setShowValidationModal(true);
    } catch (err) {
      console.error('Failed to load demo receipts:', err);
      setError('Failed to load demo receipts');
    }
  };

  // Open validation modal
  const openValidationModal = (orderId: number, preset?: typeof modalDefaults) => {
    setSelectedOrderId(orderId);
    
    // Find the order data to pre-populate the modal
    const order = orders.find(o => o.id === orderId);
    if (order) {
      setModalDefaults({
        po_number: order.po_number,
        material_code: order.material,
        expected_quantity: order.quantity || 0, // Add expected quantity
        confirmed_quantity: (order as any).confirmed_qty || 0, // Add confirmed quantity
        unit: order.unit || 'KG', // Add unit
        ...preset // Override with any preset data
      });
    } else if (preset) {
      setModalDefaults(preset);
    }
    
    setShowValidationModal(true);
  };

  // Close validation modal
  const closeValidationModal = () => {
    setShowValidationModal(false);
    setSelectedOrderId(0);
    setModalDefaults(undefined);
  };

  // Validate order function - Quantity-based validation
  const validateOrder = async (validationData: ValidationRequest): Promise<ValidationResult> => {
    try {
      setValidatingOrder(selectedOrderId);
      
      // Find the order to get expected quantity
      const order = orders.find(o => o.id === selectedOrderId);
      if (!order) {
        throw new Error('Order not found');
      }

      // Calculate total actual quantity from receipts
      const totalActualQty = validationData.receipts.reduce((sum, receipt) => {
        const netQty = receipt.gross_qty - (receipt.tare_qty || 0);
        return sum + netQty;
      }, 0);

      const expectedQty = order.quantity || 0;
      const tolerance = validationData.tolerance_pct || 0.5; // Default 0.5% tolerance
      const toleranceAmount = expectedQty * (tolerance / 100);
      
      // Check if quantity is within tolerance
      const quantityDifference = Math.abs(totalActualQty - expectedQty);
      const isWithinTolerance = quantityDifference <= toleranceAmount;
      
      // Determine validation result based on quantity match
      const isValid = isWithinTolerance && totalActualQty > 0;
      const validationStatus = isValid ? 'Validated' : 'Rejected';
      
      // Create validation message
      const quantityMatch = isWithinTolerance ? 'PASS' : 'FAIL';
      const remarks = isValid 
        ? `Quantity validation PASSED. Expected: ${expectedQty} ${order.unit}, Actual: ${totalActualQty.toFixed(2)} ${order.unit}, Difference: ${quantityDifference.toFixed(2)} ${order.unit} (within ${tolerance}% tolerance)`
        : `Quantity validation FAILED. Expected: ${expectedQty} ${order.unit}, Actual: ${totalActualQty.toFixed(2)} ${order.unit}, Difference: ${quantityDifference.toFixed(2)} ${order.unit} (exceeds ${tolerance}% tolerance)`;

      // Call the validation endpoint
      const response = await apiFetch(getApiUrl(`/api/process_orders/${selectedOrderId}/validate`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: validationStatus,
          remarks: remarks,
          expected_quantity: expectedQty,
          actual_quantity: totalActualQty,
          quantity_difference: quantityDifference,
          tolerance_percentage: tolerance,
          validation_result: quantityMatch
        })
      });
      
      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Update the order status based on validation result
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.id === selectedOrderId 
            ? { 
                ...order, 
                status: validationStatus,
                confirmed_qty: totalActualQty // Update confirmed quantity
              }
            : order
        )
      );

      // Re-fetch from API so KPIs and any other fields match backend
      await loadOrders();
      
      // Refresh KPI counts to show updated validated/rejected counts
      await loadKpiCounts();

      // Show success message
      console.log('Validation result:', result);
      return {
        order_id: selectedOrderId,
        po_number: order.po_number || '',
        valid: isValid,
        tolerance_pct: tolerance,
        mismatches: isValid ? [] : [{
          material_code: order.material || '',
          uom: order.unit || 'KG',
          expected: expectedQty,
          actual: totalActualQty,
          diff: quantityDifference,
          pct: (quantityDifference / expectedQty) * 100,
          within_tolerance: isWithinTolerance,
          reason: `Quantity mismatch: Expected ${expectedQty}, Actual ${totalActualQty.toFixed(2)}`
        }],
        actuals: { [order.material || '']: totalActualQty },
        po_items: [{
          material: order.material,
          expected_quantity: expectedQty,
          actual_quantity: totalActualQty,
          unit: order.unit
        }],
        message: result.message || `Order ${validationStatus.toLowerCase()} - Quantity ${quantityMatch}`,
        status: validationStatus
      };
    } catch (err) {
      console.error('Validation failed:', err);
      throw err;
    } finally {
      setValidatingOrder(null);
    }
  };

  // Open rejection modal
  const openRejectionModal = (orderId: number) => {
    const order = orders.find(o => o.id === orderId);
    if (order) {
      setSelectedOrderId(orderId);
      setSelectedOrderDetails({
        po_number: order.po_number,
        material: order.material,
        quantity: order.quantity,
        unit: order.unit
      });
      setShowRejectionModal(true);
    }
  };

  // Close rejection modal
  const closeRejectionModal = () => {
    setShowRejectionModal(false);
    setSelectedOrderId(0);
    setSelectedOrderDetails(null);
  };

  // Reject order function
  const rejectOrder = async (rejectionData: RejectionData) => {
    try {
      setValidatingOrder(rejectionData.order_id);
      
      // Call the new validation endpoint for rejection
      const response = await apiFetch(getApiUrl(`/api/process_orders/${rejectionData.order_id}/validate`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: 'Rejected',
          remarks: `${rejectionData.category}: ${rejectionData.reason} - ${rejectionData.description}`
        })
      });
      
      if (!response.ok) {
        throw new Error(`Rejection failed: ${response.statusText}`);
      }
      
      const result = await response.json();

      setOrders(prev =>
        prev.map(o => o.id === rejectionData.order_id ? { ...o, status: 'Rejected' } : o)
      );
      
      // Refresh KPI counts to show updated rejected count
      await loadKpiCounts();
      
      console.log('Order rejected successfully:', result.message);
    } catch (err) {
      console.error('Rejection failed:', err);
      throw new Error(`Failed to reject order ${rejectionData.order_id}`);
    } finally {
      setValidatingOrder(null);
    }
  };

  // KPI state for database counts
  const [kpiCounts, setKpiCounts] = useState({
    total: 0,
    inProgress: 0,
    validated: 0,
    rejected: 0
  });

  // Load KPI counts from database using existing endpoints
  const loadKpiCounts = async () => {
    try {
      // Fetch counts for validation-relevant orders only
      const [pendingResponse, inProgressResponse, validatedResponse, rejectedResponse] = await Promise.all([
        apiFetch(getApiUrl('/api/orders?status=Pending&limit=1000')), // Pending orders
        apiFetch(getApiUrl('/api/orders?status=InProgress&limit=1000')), // InProgress orders
        apiFetch(getApiUrl('/api/orders?status=Validated&limit=1000')), // Validated orders
        apiFetch(getApiUrl('/api/orders?status=Rejected&limit=1000')) // Rejected orders
      ]);

      const [pendingOrders, inProgressOrders, validatedOrders, rejectedOrders] = await Promise.all([
        pendingResponse.ok ? pendingResponse.json() : [],
        inProgressResponse.ok ? inProgressResponse.json() : [],
        validatedResponse.ok ? validatedResponse.json() : [],
        rejectedResponse.ok ? rejectedResponse.json() : []
      ]);

      setKpiCounts({
        total: pendingOrders.length + inProgressOrders.length, // Total orders for validation
        inProgress: inProgressOrders.length,
        validated: validatedOrders.length,
        rejected: rejectedOrders.length
      });
    } catch (err) {
      console.error('Failed to load KPI counts:', err);
    }
  };

  // Load KPI counts on component mount
  useEffect(() => {
    loadKpiCounts();
  }, []);

  // SAP Sync function
  const syncSapOrders = async () => {
    try {
      const response = await apiFetch(getApiUrl('/api/sap-sync/seed-orders'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("✅ SAP Orders synced:", data);
        addToast(`SAP Orders synced successfully! ${data.inserted_orders?.length || 0} orders added ✅`, "success");
        await loadOrders();
        await loadKpiCounts();
      } else {
        const errorData = await response.json();
        addToast(`Failed to sync SAP Orders: ${errorData.message}`, "error");
      }
    } catch (err) {
      console.error("Failed to sync SAP orders:", err);
      addToast("Failed to sync SAP Orders ❌", "error");
    }
  };

  // Fetch detailed progress for a specific order
  const fetchOrderProgress = async (poNumber: string) => {
    try {
      const response = await apiFetch(getApiUrl(`/api/orders/${poNumber}/progress`));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      const progressData = await response.json();
      return progressData;
    } catch (err) {
      console.error('Failed to fetch order progress:', err);
      return null;
    }
  };

  // Open progress dialog for InProgress order
  const openProgressDialog = async (order: Order) => {
    if (order.status === 'InProgress' && order.po_number) {
      const progressData = await fetchOrderProgress(order.po_number);
      if (progressData) {
        setSelectedOrderProgress({
          po_number: order.po_number,
          material: order.material || '',
          expected_tons: progressData.expected_tons,
          current_tons: progressData.current_tons,
          remaining_tons: progressData.remaining_tons,
          progress_pct: progressData.progress_pct,
          status: progressData.status,
          last_tick: progressData.last_tick
        });
        setShowProgressDialog(true);
      }
    }
  };

  // Auto Validator functions
  const startAllValidation = async () => {
    try {
      const response = await apiFetch(getApiUrl('/api/orders/validator/start-all'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tolerance_pct: 0.5
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("✅ AutoValidator started:", data);
        addToast("Auto Validation started ✅", "success");
        await fetchAutoValidatorStatus();
        await loadOrders();
        await loadKpiCounts();
      } else {
        const errorData = await response.json();
        addToast(`Failed to start Auto Validation: ${errorData.message}`, "error");
      }
    } catch (err) {
      console.error("Failed to start auto validator:", err);
      addToast("Failed to start Auto Validation ❌", "error");
    }
  };

  const fetchAutoValidatorStatus = async () => {
    try {
      const response = await apiFetch(getApiUrl('/api/orders/validator/status'));
      if (!response.ok) {
        return;
      }
      
      const data = await response.json();
      console.log("📊 AutoValidator status response:", data);
      
      if (data.ok && data.status) {
        const newStatus = data.status;
        
        // Only update if the status has actually changed
        setAutoValidatorStatus(prev => {
          const hasChanged = (
            prev.running !== newStatus.running ||
            prev.current_po !== newStatus.current_po ||
            prev.progress_pct !== newStatus.progress_pct
          );
          
          if (hasChanged) {
            console.log("✅ AutoValidator status updated:", newStatus);
            console.log("📊 Previous status:", prev);
            
            // Check if an order was just validated (current_po changed to a different order or null)
            if (prev.current_po && prev.current_po !== newStatus.current_po && prev.running) {
              console.log("🎉 Order validated:", prev.current_po, "->", newStatus.current_po);
              addToast(`Order ${prev.current_po} validated successfully! ✅`, "success");
              // Refresh orders list to remove validated order from table
              loadOrders();
              // Refresh KPI counts
              loadKpiCounts();
            }
            
            // If AutoValidator is not running but has current_po, clear it
            if (!newStatus.running && newStatus.current_po) {
              console.log("🔄 AutoValidator stopped, clearing current_po");
              return {
                ...newStatus,
                current_po: null,
                progress_pct: 0,
                expected_tons: 0,
                delta_tons: 0,
                baseline: null
              };
            }
            
            // Also check if AutoValidator stopped completely (all orders done)
            if (prev.running && !newStatus.running && prev.current_po) {
              console.log("🎉 Final order validated (AutoValidator stopped):", prev.current_po);
              addToast(`Order ${prev.current_po} validated successfully! ✅`, "success");
              // Refresh orders list to remove validated order from table
              loadOrders();
              // Refresh KPI counts
              loadKpiCounts();
            }
            
            return newStatus;
          } else {
            console.log("📊 AutoValidator status unchanged, skipping update");
            return prev;
          }
        });

        // Update order progress for the current order
        if (newStatus.current_po && newStatus.progress_pct > 0) {
          setOrderProgress(prev => ({
            ...prev,
            [newStatus.current_po]: newStatus.progress_pct
          }));
        }

        // Check if order was just validated (this will be handled by comparing previous state)
        // We'll track this in a separate useEffect
      } else {
        console.warn("⚠️ Invalid AutoValidator status response:", data);
      }
    } catch (err) {
      console.error("Failed to fetch validator status:", err);
    }
  };

  // Poll auto validator status every 3 seconds
  useEffect(() => {
    // Initial fetch
    fetchAutoValidatorStatus();
    
    const interval = setInterval(async () => {
      await fetchAutoValidatorStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // Periodic refresh of orders list every 10 seconds to catch status changes
  useEffect(() => {
    const interval = setInterval(async () => {
      await loadOrders();
      await loadKpiCounts();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Periodic refresh of progress dialog when open
  useEffect(() => {
    if (!showProgressDialog || !selectedOrderProgress) return;

    const interval = setInterval(async () => {
      const progressData = await fetchOrderProgress(selectedOrderProgress.po_number);
      if (progressData) {
        setSelectedOrderProgress(prev => prev ? {
          ...prev,
          current_tons: progressData.current_tons,
          remaining_tons: progressData.remaining_tons,
          progress_pct: progressData.progress_pct,
          status: progressData.status,
          last_tick: progressData.last_tick
        } : null);
      }
    }, 2000); // Refresh every 2 seconds for real-time updates

    return () => clearInterval(interval);
  }, [showProgressDialog, selectedOrderProgress]);

  // Note: Order validation detection is now handled in fetchAutoValidatorStatus function

  // Helper function to add toast notifications
  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    const newToast = { id, message, type };
    setToasts(prev => [...prev, newToast]);
    
    // Auto remove toast after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 5000);
    
    console.log(`🔔 ${type.toUpperCase()}: ${message}`);
  };

  // Open orders modal for validated or rejected orders
  const openOrdersModal = async (type: 'validated' | 'rejected') => {
    try {
      setModalType(type);
      setModalTitle(type === 'validated' ? 'Validated Orders' : 'Rejected Orders');
      
      // Fetch orders with the specific status
      const response = await apiFetch(getApiUrl(`/api/orders?status=${type === 'validated' ? 'Validated' : 'Rejected'}&limit=1000`));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      const orders = await response.json();
      setModalOrders(orders);
      setShowOrdersModal(true);
    } catch (err) {
      console.error(`Failed to load ${type} orders:`, err);
      setError(`Failed to load ${type} orders from server.`);
    }
  };

  // Close orders modal
  const closeOrdersModal = () => {
    setShowOrdersModal(false);
    setModalOrders([]);
    setModalTitle('');
    setSearchTerm('');
    setStartDate('');
    setEndDate('');
  };

  // Filter and sort orders for modal display
  const getFilteredAndSortedOrders = () => {
    let filtered = modalOrders.filter(order => {
      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch = (
          order.id.toString().includes(searchLower) ||
          (order.po_number && order.po_number.toLowerCase().includes(searchLower)) ||
          (order.material && order.material.toLowerCase().includes(searchLower)) ||
          (order.batch && order.batch.toLowerCase().includes(searchLower))
        );
        if (!matchesSearch) return false;
      }

      // Date filter
      if (startDate || endDate) {
        const orderDate = new Date((order as any).updated_at || order.created_at || 0);
        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;

        if (start && orderDate < start) return false;
        if (end && orderDate > end) return false;
      }

      return true;
    });

    // Sort by updated date (newest first)
    filtered.sort((a, b) => {
      const aDate = new Date((a as any).updated_at || a.created_at || 0).getTime();
      const bDate = new Date((b as any).updated_at || b.created_at || 0).getTime();
      return bDate - aDate; // Descending order (newest first)
    });

    return filtered;
  };

  // KPI calculations - use database counts
  const totalOrders = kpiCounts.total;
  const inProgressOrders = kpiCounts.inProgress;
  const validatedOrders = kpiCounts.validated;
  const rejectedOrders = kpiCounts.rejected;

  // Filtered orders for table (since we only fetch Pending/InProgress, just filter by status)
  const filteredOrders =
    statusFilter === 'All' ? orders : orders.filter((o) => o.status === statusFilter);

  const tableBg = theme === 'light'
    ? 'bg-white border border-blue-200 text-[#222]'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  const tableHeader = theme === 'light'
    ? 'bg-blue-100 text-[#222] border-b border-blue-300'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' ? 'bg-blue-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-blue-100' : 'border-slate-700';
  const filterSelect = theme === 'light'
    ? 'bg-white text-[#222] border border-blue-300 focus:ring-blue-300'
    : 'bg-[#0f172a] text-cyan-200 border border-cyan-500 focus:ring-cyan-400';

  return (
    <WaterSystemLayout 
      title="Process Order Validation" 
      subtitle="Process Order Validation & Approval"
    >
      <style>{`
        /* Force white text for buttons in light mode */
        .validation-refresh-light {
          color: white !important;
        }
        
        .validation-refresh-light span {
          color: white !important;
        }
        
        .validation-validate-light {
          color: white !important;
        }
        
        .validation-validate-light span {
          color: white !important;
        }
        
        .validation-reject-light {
          color: white !important;
        }
        
        .validation-reject-light span {
          color: white !important;
        }
      `}</style>
      <div className="w-full space-y-6 px-4 lg:px-6">
        <h1
          className={
            theme === 'light'
              ? 'text-xl font-bold mb-3 text-[#222]'
              : 'text-xl font-bold mb-3 text-cyan-400'
          }
        >
          Process Order Validation
        </h1>

        {/* Error Message */}
        {error && (
          <div className={`p-2 rounded-lg backdrop-blur-md border transition-all duration-300 text-sm ${
            theme === 'light' 
              ? 'bg-red-50/80 border-red-200/50 text-red-800' 
              : 'bg-red-900/20 border-red-400/30 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
          }`}>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span className="text-xs font-medium">{error}</span>
              <button
                onClick={() => setError(null)}
                className={`ml-auto p-1 rounded-full transition-colors ${
                  theme === 'light' 
                    ? 'hover:bg-red-100 text-red-600' 
                    : 'hover:bg-red-800/30 text-red-400'
                }`}
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full mb-6">
          <KpiCard
            title="Total Orders"
            value={totalOrders}
            unit=""
            Icon={ListOrdered}
            color="#2563eb"
          />
          <KpiCard
            title="In Progress"
            value={inProgressOrders}
            unit=""
            Icon={Clock3}
            color="#f59e42"
          />
          <KpiCard
            title="Validated"
            value={validatedOrders}
            unit=""
            Icon={CheckCircle}
            color="#10b981"
            showViewButton={true}
            onViewClick={() => openOrdersModal('validated')}
          />
          <KpiCard
            title="Rejected"
            value={rejectedOrders}
            unit=""
            Icon={XCircle}
            color="#ef4444"
            showViewButton={true}
            onViewClick={() => openOrdersModal('rejected')}
          />
        </div>

        {/* Auto Validation Control Panel */}
        <div className={`w-full mb-6 p-6 rounded-lg backdrop-blur-md border transition-all duration-300 ${
          theme === 'light' 
            ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30' 
            : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
        }`}>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex-1">
              <h3 className={`text-lg font-bold mb-2 ${
                theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
              }`}>
                Auto Validation Control
              </h3>
              <div className="flex flex-col sm:flex-row gap-2 text-sm">
                <div className={`flex items-center gap-2 ${
                  theme === 'light' ? 'text-slate-600' : 'text-slate-400'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${
                    autoValidatorStatus.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                  }`}></div>
                  <span>Status: {autoValidatorStatus.running ? 'Running' : 'Stopped'}</span>
                </div>
                {autoValidatorStatus.current_po && (
                  <div className={`flex items-center gap-2 ${
                    theme === 'light' ? 'text-slate-600' : 'text-slate-400'
                  }`}>
                    <span>Current Order: {autoValidatorStatus.current_po}</span>
                    <span>Progress: {autoValidatorStatus.progress_pct.toFixed(1)}%</span>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={syncSapOrders}
                className={`relative group flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all duration-300 hover:scale-105 ${
                  theme === 'light'
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-md shadow-blue-500/30 border border-blue-400/50'
                    : 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-md shadow-blue-500/25'
                }`}
                title="Sync SAP Orders"
              >
                <BarChart3 className="h-4 w-4" />
                <span>Sync SAP Orders</span>
                <div className="absolute inset-0 rounded-md bg-gradient-to-r from-blue-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </button>
              
              {!autoValidatorStatus.running ? (
                <button
                  onClick={startAllValidation}
                  className={`relative group flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all duration-300 hover:scale-105 ${
                    theme === 'light'
                      ? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-md shadow-green-500/30 border border-green-400/50'
                      : 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-md shadow-green-500/25'
                  }`}
                  title="Start Auto Validation"
                >
                  <Play className="h-4 w-4" />
                  <span>Start All Validation</span>
                  <div className="absolute inset-0 rounded-md bg-gradient-to-r from-green-400/20 to-green-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </button>
              ) : (
                <button
                  disabled
                  className={`relative group flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all duration-300 opacity-50 cursor-not-allowed ${
                    theme === 'light'
                      ? 'bg-gradient-to-r from-gray-400 to-gray-500 text-white shadow-md shadow-gray-400/30 border border-gray-300/50'
                      : 'bg-gradient-to-r from-gray-500 to-gray-600 text-white shadow-md shadow-gray-500/25'
                  }`}
                  title="Auto Validation is running"
                >
                  <Play className="h-4 w-4" />
                  <span>Auto Validation Running...</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Filter by Status */}
        <div className="w-full flex items-center gap-3 mb-6">
          <label htmlFor="statusFilter" className="text-sm font-semibold opacity-80 whitespace-nowrap">Filter by Status:</label>
          <select
            id="statusFilter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`${filterSelect} rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-opacity-50 backdrop-blur-sm border transition-all duration-300 shadow-md text-sm min-w-[150px] ${
              theme === 'light' 
                ? 'focus:ring-slate-400 focus:border-slate-400' 
                : 'focus:ring-cyan-400 focus:border-cyan-400 focus:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
            }`}
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
        </div>

        {/* Orders Table with Drag & Drop */}
        <div className={`w-full rounded-lg backdrop-blur-md shadow transition-all duration-300 ${
          theme === 'light' 
            ? 'bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30' 
            : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
        }`}>
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-current"></div>
              <span className="ml-3">Loading orders...</span>
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="flex items-center justify-center p-8 opacity-70">
              No orders found
            </div>
          ) : (
            <OrderTable 
              orders={filteredOrders.map(order => ({
                id: String(order.id),
                material: order.material,
                version: order.version,
                batch: order.batch,
                quantity: order.quantity,
                unit: order.unit,
                priority: (order as any).priority || 0,
                status: order.status,
                date: new Date().toISOString().slice(0, 10),
                plant: (order as any).plant || '—',
                confirmed_qty: (order as any).confirmed_qty || 0,
                material_desc: (order as any).material_desc || '—',
              }))}
              theme={theme}
              onReorder={handleReorder}
            />
          )}
        </div>
      {/* Progress Dialog */}
      {showProgressDialog && selectedOrderProgress && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
          <div className={`w-full max-w-2xl mx-4 rounded-lg shadow-xl ${
            theme === 'light' 
              ? 'bg-white border border-gray-200' 
              : 'bg-gray-800 border border-gray-600'
          }`}>
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              theme === 'light' ? 'border-gray-200' : 'border-gray-600'
            }`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold ${
                  theme === 'light' ? 'text-gray-900' : 'text-white'
                }`}>
                  Order Progress Details
                </h3>
                <button
                  onClick={() => setShowProgressDialog(false)}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${
                    theme === 'light' 
                      ? 'text-gray-500 hover:bg-gray-200' 
                      : 'text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-4">
              {/* Order Info */}
              <div className="mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={`text-sm font-medium ${
                      theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                    }`}>
                      PO Number
                    </label>
                    <p className={`text-lg font-mono ${
                      theme === 'light' ? 'text-gray-900' : 'text-white'
                    }`}>
                      {selectedOrderProgress.po_number}
                    </p>
                  </div>
                  <div>
                    <label className={`text-sm font-medium ${
                      theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                    }`}>
                      Material
                    </label>
                    <p className={`text-lg font-mono ${
                      theme === 'light' ? 'text-gray-900' : 'text-white'
                    }`}>
                      {selectedOrderProgress.material}
                    </p>
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-2">
                  <span className={`text-sm font-medium ${
                    theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                  }`}>
                    Progress
                  </span>
                  <span className={`text-lg font-bold ${
                    theme === 'light' ? 'text-gray-900' : 'text-white'
                  }`}>
                    {selectedOrderProgress.progress_pct.toFixed(1)}%
                  </span>
                </div>
                <div className={`w-full rounded-full h-3 ${
                  theme === 'light' ? 'bg-gray-200' : 'bg-gray-700'
                }`}>
                  <div
                    className="bg-gradient-to-r from-blue-500 to-green-500 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(selectedOrderProgress.progress_pct, 100)}%` }}
                  />
                </div>
              </div>

              {/* Weight Details */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className={`p-4 rounded-lg ${
                  theme === 'light' ? 'bg-blue-50 border border-blue-200' : 'bg-blue-900/20 border border-blue-700'
                }`}>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${
                      theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                    }`}>
                      {selectedOrderProgress.expected_tons.toFixed(2)}
                    </div>
                    <div className={`text-sm ${
                      theme === 'light' ? 'text-blue-700' : 'text-blue-300'
                    }`}>
                      Expected (tons)
                    </div>
                  </div>
                </div>
                
                <div className={`p-4 rounded-lg ${
                  theme === 'light' ? 'bg-green-50 border border-green-200' : 'bg-green-900/20 border border-green-700'
                }`}>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${
                      theme === 'light' ? 'text-green-600' : 'text-green-400'
                    }`}>
                      {selectedOrderProgress.current_tons.toFixed(2)}
                    </div>
                    <div className={`text-sm ${
                      theme === 'light' ? 'text-green-700' : 'text-green-300'
                    }`}>
                      Current (tons)
                    </div>
                  </div>
                </div>
                
                <div className={`p-4 rounded-lg ${
                  theme === 'light' ? 'bg-orange-50 border border-orange-200' : 'bg-orange-900/20 border border-orange-700'
                }`}>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${
                      theme === 'light' ? 'text-orange-600' : 'text-orange-400'
                    }`}>
                      {selectedOrderProgress.remaining_tons.toFixed(2)}
                    </div>
                    <div className={`text-sm ${
                      theme === 'light' ? 'text-orange-700' : 'text-orange-300'
                    }`}>
                      Remaining (tons)
                    </div>
                  </div>
                </div>
              </div>

              {/* Status and Last Update */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`text-sm font-medium ${
                    theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                  }`}>
                    Status
                  </label>
                  <div className="mt-1">
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                      selectedOrderProgress.status === 'InProgress'
                        ? theme === 'light' ? 'bg-blue-300 text-blue-900' : 'bg-blue-500 text-white'
                        : theme === 'light' ? 'bg-gray-300 text-gray-900' : 'bg-gray-500 text-white'
                    }`}>
                      {selectedOrderProgress.status}
                    </span>
                  </div>
                </div>
                <div>
                  <label className={`text-sm font-medium ${
                    theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                  }`}>
                    Last Update
                  </label>
                  <p className={`text-sm mt-1 ${
                    theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                  }`}>
                    {selectedOrderProgress.last_tick 
                      ? new Date(selectedOrderProgress.last_tick).toLocaleString()
                      : 'No recent updates'
                    }
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className={`px-6 py-4 border-t ${
              theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'
            }`}>
              <div className="flex justify-end">
                <button
                  onClick={() => setShowProgressDialog(false)}
                  className={`px-4 py-2 rounded-md font-medium transition-colors ${
                    theme === 'light'
                      ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                      : 'bg-gray-600 text-white hover:bg-gray-500'
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

export default ProcessOrderValidation;
