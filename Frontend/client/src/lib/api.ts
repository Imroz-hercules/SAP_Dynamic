// // API service for backend communication
// const API_BASE_URL = 'http://localhost:5000';

// export interface KpiData {
//   milling_kpis: {
//     "Mill Throughput (%)": number;
//     "Mill Time Efficiency (%)": number;
//     "Total Utilization (%)": number;
//     "Milling Gain": number;
//     "Milling Screening (%)": number;
//     "Flour Extraction (%)": number;
//     "Milling Loss (%)": number;
//     "Net Hours (hrs)": number;
//     "Downtime (hrs)": number;
//     "Max Utilization of Milling Capacity (%)": number;
//     "Pre Cleaning Screening (%)": number;
//     "1st Break Capacity per Hour (t/h)": number;
//     "Bran Extraction (%)": number;
//   };
//   packing_kpis: {
//     "Packing Line Capacity (bags/hr)": number;
//     "Daily Packing Output (bags)": number;
//     "Net Hours (hrs)": number;
//     "Downtime (hrs)": number;
//     "Machine Utilization (%)": number;
//     "Packing Line Capacity (tons/hr)": number;
//   };
//   timestamp?: string;
//   data_source?: string;
// }

// // Order validation interfaces
// export interface Order {
//   id: number;
//   po_number?: string;
//   material?: string;
//   version?: string;
//   batch?: string;
//   quantity?: number;
//   unit?: string;        // backend field (was uom)
//   status: 'Pending' | 'Validated' | 'Rejected' | 'InProgress' | string;
//   created_at?: string;
//   updated_at?: string;
// }

// export interface ReceiptLine {
//   material_code: string;
//   gross_qty: number;
//   tare_qty?: number;
//   uom?: string;         // client can send; backend treats base as KG
// }

// export interface ValidationRequest {
//   po_number: string;
//   material_code?: string;     // pre-populated from order
//   receipts: ReceiptLine[];    // kept for backward compatibility, but backend ignores this
//   tolerance_pct?: number;     // default 0.5
//   auto_confirm?: boolean;     // default false
//   expected_quantity?: number; // expected quantity from order
//   confirmed_quantity?: number; // confirmed quantity from order
//   scale_quantity?: number;    // live scale value from backend
//   unit?: string;              // unit of measure
//   confirmed_text?: string;    // optional text for manual processing - will be reflected in SAP
//   scrap?: number;             // damaged qty during production process
//   manual_weight?: number;     // manually entered weight for manual validation
//   expected_weight?: number;   // expected weight for manual validation comparison
//   validation_type?: 'manual' | 'auto' | 'partial'; // type of validation being performed
//   confirmed_qty?: number;     // partial confirmation quantity (allows confirming less than total)
// }

// export interface Mismatch {
//   material_code: string;
//   uom: string;
//   expected: number;
//   actual: number;
//   diff: number;
//   pct: number;
//   within_tolerance: boolean;
//   reason?: string;
// }

// export interface ValidationResult {
//   order_id: number;
//   po_number: string;
//   valid: boolean;
//   tolerance_pct: number;
//   mismatches: Mismatch[];
//   actuals: {
//     WG202?: number;           // Input scale actual tons
//     "WG501+WG502"?: number;   // Flour output actual tons
//     WG503?: number;           // Bran output actual tons
//     [key: string]: number | undefined;
//   };
//   expected_tons?: number;
//   po_items: Array<Record<string, unknown>>;
//   result_id?: number | null;
//   auto_confirmation?: unknown;
//   message?: string;
//   status?: string;
// }

// const base = (import.meta as any).env?.VITE_API_BASE || API_BASE_URL;

// async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
//   const res = await fetch(url, init);
//   const text = await res.text();
//   if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
//   try { return JSON.parse(text) as T; } catch { throw new Error('Non-JSON response'); }
// }

// export const kpiApi = {
//   async getKpis(): Promise<KpiData> {
//     try {
//       const response = await fetch(`${API_BASE_URL}/api/kpi`, {
//         method: 'GET',
//         headers: {
//           'Content-Type': 'application/json',
//           'Accept': 'application/json',
//         },
//         mode: 'cors',
//       });
      
//       if (!response.ok) {
//         if (response.status === 404) {
//           throw new Error('No KPI data found in database');
//         } else if (response.status === 500) {
//           throw new Error('Server error - check if backend is running');
//         } else {
//           throw new Error(`HTTP error! status: ${response.status}`);
//         }
//       }
      
//       const data = await response.json();
      
//       // Validate the response structure
//       if (!data.milling_kpis || !data.packing_kpis) {
//         throw new Error('Invalid response format from server');
//       }
      
//       return data;
//     } catch (error) {
//       console.error('Error fetching KPI data:', error);
      
//       // Provide more specific error messages
//       if (error instanceof TypeError && error.message.includes('fetch')) {
//         throw new Error('Cannot connect to backend server. Please ensure the backend is running on http://localhost:5000');
//       }
      
//       throw error;
//     }
//   },

//   // Health check method
//   async healthCheck(): Promise<boolean> {
//     try {
//       const response = await fetch(`${API_BASE_URL}/`, {
//         method: 'GET',
//         mode: 'cors',
//       });
//       return response.ok;
//     } catch {
//       return false;
//     }
//   }
// };

// // Order validation API
// export const orderApi = {
//   async getOrders(status?: string): Promise<Order[]> {
//     const qs = status && status !== 'All' ? `?status=${encodeURIComponent(status)}` : '';
//     return getJSON<Order[]>(`${base}/api/orders${qs}`);
//   },

//   async validateOrder(orderId: number, body: ValidationRequest): Promise<ValidationResult> {
//     return getJSON<ValidationResult>(`${base}/api/orders/${orderId}/validate`, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(body),
//     });
//   },

//   async confirmOrder(orderId: number, payload: { status: 'Completed'|'Partial'|'Rejected'; remarks?: string; confirmed_by?: string; po_number?: string; }) {
//     return getJSON(`${base}/api/orders/${orderId}/confirm`, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload),
//     });
//   },

// //   async pushConfirmation(payload: { order_ids?: number[]; status?: string }) {
// //     return getJSON(`${base}/api/process_orders/push-confirmation`, {
// //       method: 'POST',
// //       headers: { 'Content-Type': 'application/json' },
// //       body: JSON.stringify(payload),
// //     });
// //   },
// // }; 
//   async pushConfirmation(payload: { order_ids?: number[]; status?: string }) {
//     return getJSON(`${base}/api/process_orders/push-confirmation`, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload),
//     });
//   },
// };

// // Palletizer Mapping API
// export interface PalletizerMapping {
//   id: number;
//   version: string;
//   palletizer: string;
//   bag_size_kg: number;
//   bags_per_pallet: number;
//   kg_per_pallet: number;
// }

// export interface PalletizerMappingRequest {
//   version: string;
//   palletizer: string;
//   bag_size_kg: number;
//   bags_per_pallet: number;
//   kg_per_pallet: number;
// }

// export const palletizerApi = {
//   async getPalletizerMappings(): Promise<PalletizerMapping[]> {
//     return getJSON<PalletizerMapping[]>(`${base}/api/orders/palletizer-mapping`, {
//       method: 'GET',
//       headers: { 'Content-Type': 'application/json' },
//     });
//   },

//   async createOrUpdatePalletizerMapping(payload: PalletizerMappingRequest): Promise<{ success: boolean; message: string; mode: 'create' | 'update' }> {
//     return getJSON(`${base}/api/orders/palletizer-mapping`, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload),
//     });
//   },
// };

// // Shift Master API
// export interface ShiftMaster {
//   id: number;
//   plant: string;
//   department: string;
//   shift_code: string;
//   start_time: string; // HH:MM format
//   end_time: string; // HH:MM format
//   sort_order: number;
// }

// export const shiftApi = {
//   async getShifts(): Promise<ShiftMaster[]> {
//     return getJSON<ShiftMaster[]>(`${base}/api/shifts`, {
//       method: 'GET',
//       headers: { 'Content-Type': 'application/json' },
//     });
//   },

//   async createOrUpdateShift(payload: {
//     id?: number;
//     plant: string;
//     department: string;
//     shift_code: string;
//     start_time: string;
//     end_time: string;
//     sort_order: number;
//   }): Promise<{ success: boolean; id?: number }> {
//     return getJSON(`${base}/api/shifts`, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload),
//     });
//   },

//   async deleteShift(shiftId: number): Promise<{ success: boolean }> {
//     return getJSON(`${base}/api/shifts/${shiftId}`, {
//       method: 'DELETE',
//       headers: { 'Content-Type': 'application/json' },
//     });
//   },
// };

// // Server Time API
// export interface ServerTimeInfo {
//   server_time: string;
//   server_time_utc: string;
//   server_timestamp: number;
//   server_timezone: string;
//   server_time_formatted: string;
//   server_date: string;
//   server_time_only: string;
// }

// export const timeApi = {
//   async getServerTime(): Promise<ServerTimeInfo> {
//     return getJSON<ServerTimeInfo>(`${base}/api/time`, {
//       method: 'GET',
//       headers: { 'Content-Type': 'application/json' },
//     });
//   },
// }; 
// API service for backend communication
import { apiRequest } from './queryClient';
import { getApiUrl, API_BASE_URL, apiFetch } from './apiConfig';

// Log API configuration when module loads
if (typeof window !== 'undefined') {
  console.log('📄 api.ts: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

export interface KpiData {
  milling_kpis: {
    "Mill Throughput (%)": number;
    "Mill Time Efficiency (%)": number;
    "Total Utilization (%)": number;
    "Milling Gain": number;
    "Milling Screening (%)": number;
    "Flour Extraction (%)": number;
    "Milling Loss (%)": number;
    "Net Hours (hrs)": number;
    "Downtime (hrs)": number;
    "Max Utilization of Milling Capacity (%)": number;
    "Pre Cleaning Screening (%)": number;
    "1st Break Capacity per Hour (t/h)": number;
    "Bran Extraction (%)": number;
  };
  packing_kpis: {
    "Packing Line Capacity (bags/hr)": number;
    "Daily Packing Output (bags)": number;
    "Net Hours (hrs)": number;
    "Downtime (hrs)": number;
    "Machine Utilization (%)": number;
    "Packing Line Capacity (tons/hr)": number;
  };
  timestamp?: string;
  data_source?: string;
}

// Order validation interfaces
export interface Order {
  id: number;
  po_number?: string;
  material?: string;
  version?: string;
  batch?: string;
  quantity?: number;
  unit?: string;
  status: 'Pending' | 'Validated' | 'Rejected' | 'InProgress' | string;
  created_at?: string;
  updated_at?: string;
}

export interface ReceiptLine {
  material_code: string;
  gross_qty: number;
  tare_qty?: number;
  uom?: string;
}

export interface ValidationRequest {
  po_number: string;
  material_code?: string;
  receipts: ReceiptLine[];
  tolerance_pct?: number;
  auto_confirm?: boolean;
  expected_quantity?: number;
  confirmed_quantity?: number;
  scale_quantity?: number;
  unit?: string;
  confirmed_text?: string;
  scrap?: number;
  manual_weight?: number;
  expected_weight?: number;
  validation_type?: 'manual' | 'auto' | 'partial';
  confirmed_qty?: number;
}

export interface Mismatch {
  material_code: string;
  uom: string;
  expected: number;
  actual: number;
  diff: number;
  pct: number;
  within_tolerance: boolean;
  reason?: string;
}

export interface ValidationResult {
  order_id: number;
  po_number: string;
  valid: boolean;
  tolerance_pct: number;
  mismatches: Mismatch[];
  actuals: {
    WG202?: number;
    "WG501+WG502"?: number;
    WG503?: number;
    [key: string]: number | undefined;
  };
  expected_tons?: number;
  po_items: Array<Record<string, unknown>>;
  result_id?: number | null;
  auto_confirmation?: unknown;
  message?: string;
  status?: string;
}

// ✅ NEW: Push Confirmation interfaces
export interface PushConfirmationRequest {
  order_ids: number[];                    // Required: List of order IDs to confirm
  confirm_current_shift?: boolean;        // ✅ NEW: True for mid-shift, false for shift-end
  operator?: string;                      // Optional: Username/operator
  status?: string;                        // Deprecated (kept for backward compatibility)
}

export interface PushConfirmationResult {
  process_order: string;                  // PO number (e.g., "000012002902")
  status: string;                         // "Mid-Shift Confirmed" | "Shift-End Confirmed" | "Failed"
  confirmed_weight?: number;              // Weight sent to SAP
  shift?: string;                         // "A" | "B" | "C"
  final?: boolean;                        // True if order complete
}

export interface PushConfirmationResponse {
  message: string;                        // Summary message
  successful_count: number;               // Count of successful confirmations
  failed_count: number;                   // Count of failed confirmations
  results: PushConfirmationResult[]; 
  successful_orders?: number[];       // ✅ Added
  failed_orders?: string[];        // Detailed results per order
}

async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = {
    'ngrok-skip-browser-warning': 'true',
    ...(init?.headers as Record<string, string> || {}),
  };
  const res = await fetch(url, { ...init, headers });
  const text = await res.text();
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
  try { return JSON.parse(text) as T; } catch { throw new Error('Non-JSON response'); }
}

// Historical KPI response interface
export interface HistoricalKpiPeriod {
  period_start: string;
  period_end: string;
  period_label: string;
  milling_kpis: KpiData['milling_kpis'];
  packing_kpis: KpiData['packing_kpis'];
  record_count: number;
  total_hours?: number;
  approx_run_hours?: number;
}

export interface HistoricalKpiResponse {
  success: boolean;
  data: HistoricalKpiPeriod[];
  summary: {
    total_periods: number;
    start_date: string;
    end_date: string;
    period: string;
    department: string;
    shifts_filter?: string;
  };
}

export const kpiApi = {
  async getKpis(): Promise<KpiData> {
    try {
      const data = await apiRequest('GET', '/api/kpi');
      
      if (!data.milling_kpis || !data.packing_kpis) {
        throw new Error('Invalid response format from server');
      }
      
      return data;
    } catch (error) {
      console.error('Error fetching KPI data:', error);
      
      if (error instanceof Error && error.message.includes('401')) {
        throw new Error('Authentication required. Please login again.');
      }
      
      throw error;
    }
  },

  // ✅ NEW: Get historical KPI data with time filters
  // ✅ Always uses aggregation_mode='average' to average raw data first, then calculate KPIs once
  async getHistoricalKpis(params: {
    startDate: string;  // YYYY-MM-DD or YYYY-MM-DD HH:mm:ss
    endDate: string;    // YYYY-MM-DD or YYYY-MM-DD HH:mm:ss
    period?: 'hour' | 'day' | 'week' | 'month';
    department?: 'MILLING' | 'PACKING' | 'ALL';
    shifts?: string[];  // ['A', 'B', 'C']
  }): Promise<HistoricalKpiResponse> {
    try {
      // Build query string
      const queryParams = new URLSearchParams();
      
      // Extract just the date part (YYYY-MM-DD) from datetime strings
      const startDateOnly = params.startDate.split(' ')[0];
      const endDateOnly = params.endDate.split(' ')[0];
      
      queryParams.append('start_date', startDateOnly);
      queryParams.append('end_date', endDateOnly);
      
      // ✅ Always use average aggregation mode (average raw data first, then calculate KPIs once)
      queryParams.append('aggregation_mode', 'average');
      
      if (params.period) {
        queryParams.append('period', params.period);
      }
      if (params.department) {
        queryParams.append('department', params.department);
      }
      if (params.shifts && params.shifts.length > 0) {
        queryParams.append('shifts', params.shifts.join(','));
      }
      
      const url = `/api/kpi/historical?${queryParams.toString()}`;
      console.log('📊 Fetching historical KPIs with average aggregation:', url);
      
      const data = await apiRequest('GET', url);
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch historical KPI data');
      }
      
      return data;
    } catch (error) {
      console.error('Error fetching historical KPI data:', error);
      throw error;
    }
  },

  async healthCheck(): Promise<boolean> {
    try {
      const response = await apiFetch(getApiUrl('/'), {
        method: 'GET',
        mode: 'cors',
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  // Get per-day KPI breakdown for charts (uses period aggregation, not average)
  async getHistoricalKpisForCharts(params: {
    startDate: string;
    endDate: string;
    period?: 'hour' | 'day' | 'week' | 'month';
    department?: 'MILLING' | 'PACKING' | 'ALL';
  }): Promise<HistoricalKpiResponse> {
    try {
      const queryParams = new URLSearchParams();
      
      const startDateOnly = params.startDate.split(' ')[0];
      const endDateOnly = params.endDate.split(' ')[0];
      
      queryParams.append('start_date', startDateOnly);
      queryParams.append('end_date', endDateOnly);
      
      // Use period aggregation mode for per-day/per-week breakdown (for charts)
      queryParams.append('aggregation_mode', 'period');
      queryParams.append('period', params.period || 'day');
      
      if (params.department) {
        queryParams.append('department', params.department);
      }
      
      const url = `/api/kpi/historical?${queryParams.toString()}`;
      console.log('📊 Fetching per-period KPIs for charts:', url);
      
      const data = await apiRequest('GET', url);
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch chart KPI data');
      }
      
      return data;
    } catch (error) {
      console.error('Error fetching chart KPI data:', error);
      throw error;
    }
  },

  // Manual sync to SAP endpoints
  async sendMillingToSap(): Promise<{ success: boolean; message: string; response?: string; payload_sent?: any; timestamp?: string }> {
    return apiRequest('POST', '/api/kpi/send-milling-to-sap');
  },

  async sendPackingToSap(): Promise<{ success: boolean; message: string; response?: string; payload_sent?: any; timestamp?: string }> {
    return apiRequest('POST', '/api/kpi/send-packing-to-sap');
  },

  async sendScadaToSap(): Promise<{ success: boolean; message: string; response?: string; record_id?: number; timestamp?: string }> {
    return apiRequest('POST', '/api/hercules/send-to-sap');
  },

  // Get KPI tracking data from kpi_send_tracking table
  async getKpiTracking(params: {
    startDate: string;
    endDate: string;
    shifts?: string[];
    department?: 'MILLING' | 'PACKING';
    limit?: number;
    offset?: number;
  }): Promise<{
    success: boolean;
    data: Array<{
      id: number;
      department: string;
      shift_code: string | null;
      last_sent_at: string;
      send_type: string;
      kpi_payload: Record<string, string>;
    }>;
    total_count: number;
    limit: number;
    offset: number;
  }> {
    const queryParams = new URLSearchParams();
    queryParams.append('start_date', params.startDate);
    queryParams.append('end_date', params.endDate);
    if (params.shifts && params.shifts.length > 0) {
      queryParams.append('shifts', params.shifts.join(','));
    }
    if (params.department) {
      queryParams.append('department', params.department);
    }
    if (params.limit) {
      queryParams.append('limit', params.limit.toString());
    }
    if (params.offset) {
      queryParams.append('offset', params.offset.toString());
    }
    
    return apiRequest('GET', `/api/reports/kpi-tracking?${queryParams.toString()}`);
  },

  // Get shift-based KPI history for charts (from kpi_send_tracking table)
  async getShiftKpiHistory(params: {
    date?: string;  // YYYY-MM-DD (optional, defaults to today)
    department?: 'MILLING' | 'PACKING' | 'ALL';
  }): Promise<{
    success: boolean;
    milling_data: Array<{
      shift_code: string;
      department: string;
      timestamp: string;
      time_label: string;
      sort_order: number;
      kpis: Record<string, string>;
    }>;
    packing_data: Array<{
      shift_code: string;
      department: string;
      timestamp: string;
      time_label: string;
      sort_order: number;
      kpis: Record<string, string>;
    }>;
    date: string;
  }> {
    const queryParams = new URLSearchParams();
    if (params.date) {
      queryParams.append('date', params.date);
    }
    if (params.department) {
      queryParams.append('department', params.department);
    }
    
    const url = `/api/kpi/shift-history${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return apiRequest('GET', url);
  },
};

// Order validation API
export const orderApi = {
  async getOrders(status?: string): Promise<Order[]> {
    const qs = status && status !== 'All' ? `?status=${encodeURIComponent(status)}` : '';
    return getJSON<Order[]>(getApiUrl(`/api/orders${qs}`));
  },

  async validateOrder(orderId: number, body: ValidationRequest): Promise<ValidationResult> {
    return getJSON<ValidationResult>(getApiUrl(`/api/orders/${orderId}/validate`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  },

  async confirmOrder(orderId: number, payload: { 
    status: 'Completed'|'Partial'|'Rejected'; 
    remarks?: string; 
    confirmed_by?: string; 
    po_number?: string; 
  }) {
    return getJSON(getApiUrl(`/api/orders/${orderId}/confirm`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  // ✅ UPDATED: Push confirmation with mid-shift support
  async pushConfirmation(payload: PushConfirmationRequest): Promise<PushConfirmationResponse> {
    return getJSON<PushConfirmationResponse>(getApiUrl('/api/process_orders/push-confirmation'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  // ✅ NEW: Convenience method for mid-shift confirmation
  async pushMidShiftConfirmation(orderIds: number[], operator?: string): Promise<PushConfirmationResponse> {
    return this.pushConfirmation({
      order_ids: orderIds,
      confirm_current_shift: true,  // ✅ Mid-shift flag
      operator: operator || 'manual',
    });
  },

  // ✅ NEW: Convenience method for shift-end confirmation
  async pushShiftEndConfirmation(orderIds: number[], operator?: string): Promise<PushConfirmationResponse> {
    return this.pushConfirmation({
      order_ids: orderIds,
      confirm_current_shift: false,  // ✅ Shift-end flag (skip active shift)
      operator: operator || 'auto_scheduler',
    });
  },
};

// Palletizer Mapping API
export interface PalletizerMapping {
  id: number;
  version: string;
  palletizer: string;
  bag_size_kg: number;
  bags_per_pallet: number;
  kg_per_pallet: number;
  description?: string;
}

export interface PalletizerMappingRequest {
  version: string;
  palletizer: string;
  bag_size_kg: number;
  bags_per_pallet: number;
  kg_per_pallet: number;
  description?: string;
}

export const palletizerApi = {
  async getPalletizerMappings(): Promise<PalletizerMapping[]> {
    return getJSON<PalletizerMapping[]>(getApiUrl('/api/orders/palletizer-mapping'), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  async createOrUpdatePalletizerMapping(payload: PalletizerMappingRequest): Promise<{ 
    success: boolean; 
    message: string; 
    mode: 'create' | 'update' 
  }> {
    return getJSON(getApiUrl('/api/orders/palletizer-mapping'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async deletePalletizerMapping(id: number): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl(`/api/orders/palletizer-mapping/${id}`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

// Shift Master API
export interface ShiftMaster {
  id: number;
  plant: string;
  department: string;
  shift_code: string;
  start_time: string;
  end_time: string;
  sort_order: number;
}

export const shiftApi = {
  async getShifts(): Promise<ShiftMaster[]> {
    return getJSON<ShiftMaster[]>(getApiUrl('/api/shifts'), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  async createOrUpdateShift(payload: {
    id?: number;
    plant: string;
    department: string;
    shift_code: string;
    start_time: string;
    end_time: string;
    sort_order: number;
  }): Promise<{ success: boolean; id?: number }> {
    return getJSON(getApiUrl('/api/shifts'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async deleteShift(shiftId: number): Promise<{ success: boolean }> {
    return getJSON(getApiUrl(`/api/shifts/${shiftId}`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

// Server Time API
export interface ServerTimeInfo {
  server_time: string;
  server_time_utc: string;
  server_timestamp: number;
  server_timezone: string;
  server_time_formatted: string;
  server_date: string;
  server_time_only: string;
}

export const timeApi = {
  async getServerTime(): Promise<ServerTimeInfo> {
    return getJSON<ServerTimeInfo>(getApiUrl('/api/time'), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

// System Mode API - For checking demo/production mode
export interface SystemModeInfo {
  demo_mode: boolean;
  mock_sap: boolean;
  emulator_auto_start: boolean;
  emulator_running: boolean;
  emulator_active_scales: number;
  emulator_last_update: string | null;
  settings?: Record<string, unknown>;
}

export const systemApi = {
  /**
   * Get current system mode (demo/production)
   * - demo_mode: true = Using embedded SCADA emulator
   * - demo_mode: false = Using production MSSQL database
   */
  async getSystemMode(): Promise<SystemModeInfo> {
    return getJSON<SystemModeInfo>(getApiUrl('/api/system/mode'), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  /**
   * Check if demo mode is enabled (quick check)
   */
  async isDemoMode(): Promise<boolean> {
    try {
      const mode = await this.getSystemMode();
      return mode.demo_mode;
    } catch (error) {
      console.warn('Could not fetch system mode, defaulting to demo mode:', error);
      return true; // Default to demo mode if can't fetch
    }
  },
};

// ============================================================================
// Dynamic configuration APIs (added in commit 0 — see backend/CONTRACTS.md)
//
// Stubs so both workstreams can add their client here without colliding on
// this file. Fill in your own block; leave the other one alone.
// ============================================================================

// ---------------------------------------------------------------- Workstream A
export interface ClassificationRule {
  id: number;
  rule_type: 'material_prefix' | 'plant_department';
  match_value: string;   // '13', '14', '3130', or '*'
  result_value: string;  // 'MILLING' | 'PACKING'
  priority: number;
  is_active: boolean;
  description?: string | null;
}

export interface ClassificationRuleRequest {
  id?: number;
  rule_type: 'material_prefix' | 'plant_department';
  match_value: string;
  result_value: string;
  priority?: number;
  is_active?: boolean;
  description?: string | null;
}

export const classificationApi = {
  async getRules(): Promise<ClassificationRule[]> {
    return getJSON<ClassificationRule[]>(getApiUrl('/api/classification/rules'), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  async createOrUpdateRule(
    payload: ClassificationRuleRequest,
  ): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl('/api/classification/rules'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async deleteRule(id: number): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl(`/api/classification/rules/${id}`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

// ---------------------------------------------------------------- Workstream B
export interface ScadaTag {
  id: number;
  tag: string;
  category: 'INPUT' | 'MILLING' | 'WATER' | 'PACKING' | 'DAMAGED';
  reading_type: 'hi_lo' | 'single' | 'average';
  source_column?: string | null;
  rollover_max?: number | null;
  unit?: string | null;
  is_pollable: boolean;
  is_active: boolean;
  emulator_seed: number;
  display_name?: string | null;
  sort_order: number;
}

export interface ScadaTagRequest extends Partial<ScadaTag> {
  tag: string;
  category: ScadaTag['category'];
  reading_type: ScadaTag['reading_type'];
}

export const scadaConfigApi = {
  async getTags(category?: string): Promise<ScadaTag[]> {
    const suffix = category ? `?category=${encodeURIComponent(category)}` : '';
    return getJSON<ScadaTag[]>(getApiUrl(`/api/scada-config/tags${suffix}`), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  async createOrUpdateTag(
    payload: ScadaTagRequest,
  ): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl('/api/scada-config/tags'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async deleteTag(id: number): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl(`/api/scada-config/tags/${id}`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

export interface KpiDefinition {
  id: number;
  kpi_key: string;
  display_name: string;
  department: 'MILLING' | 'PACKING';
  target_column?: string | null;
  max_value?: number | null;
  unit?: string | null;
  is_active: boolean;
  sort_order: number;
}

export interface KpiDefinitionRequest extends Partial<KpiDefinition> {
  kpi_key: string;
  display_name: string;
  department: KpiDefinition['department'];
}

export const kpiConfigApi = {
  async getDefinitions(department?: string): Promise<KpiDefinition[]> {
    const suffix = department ? `?department=${encodeURIComponent(department)}` : '';
    return getJSON<KpiDefinition[]>(getApiUrl(`/api/kpi-config/definitions${suffix}`), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
  },

  async upsertDefinition(
    payload: KpiDefinitionRequest,
  ): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl('/api/kpi-config/definitions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async deleteDefinition(id: number): Promise<{ success: boolean; message: string }> {
    return getJSON(getApiUrl(`/api/kpi-config/definitions/${id}`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
