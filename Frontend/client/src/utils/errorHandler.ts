/**
 * Global Error Handler Utility
 * Provides consistent error handling across the application
 */

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: any;
}

/**
 * Parse error from various sources (API response, Error object, etc.)
 */
export const parseError = (error: any): ApiError => {
  // Already parsed error
  if (error?.message && typeof error.message === 'string') {
    return {
      message: error.message,
      status: error.status || error.response?.status,
      code: error.code,
      details: error.details
    };
  }

  // Response object with error field
  if (error?.error) {
    return {
      message: typeof error.error === 'string' ? error.error : JSON.stringify(error.error),
      status: error.status,
      details: error
    };
  }

  // Axios-style error
  if (error?.response?.data) {
    const data = error.response.data;
    return {
      message: data.error || data.message || data.detail || 'An error occurred',
      status: error.response.status,
      details: data
    };
  }

  // String error
  if (typeof error === 'string') {
    return { message: error };
  }

  // Unknown error
  return { message: 'An unexpected error occurred' };
};

/**
 * Get user-friendly error message based on error type
 */
export const getErrorMessage = (error: any): string => {
  const parsed = parseError(error);
  const message = parsed.message.toLowerCase();

  // Network errors
  if (message.includes('network') || 
      message.includes('fetch') || 
      message.includes('failed to fetch') ||
      message.includes('econnrefused') ||
      message.includes('connection refused')) {
    return 'Network error: Unable to connect to server. Please check your connection.';
  }

  // VPN errors
  if (message.includes('vpn') && message.includes('disconnect')) {
    return 'VPN disconnected: Cannot send to SAP. Order will be stored for offline confirmation.';
  }

  // Timeout errors
  if (message.includes('timeout') || message.includes('timed out')) {
    return 'Request timed out. Please try again.';
  }

  // Authentication errors
  if (parsed.status === 401 || message.includes('unauthorized') || message.includes('unauthenticated')) {
    return 'Session expired. Please log in again.';
  }

  // Authorization errors
  if (parsed.status === 403 || message.includes('forbidden') || message.includes('permission')) {
    return 'You do not have permission for this action.';
  }

  // Not found errors
  if (parsed.status === 404 || message.includes('not found')) {
    return parsed.message.includes('Order') ? parsed.message : 'Resource not found.';
  }

  // Validation errors (bypass value, etc.)
  if (message.includes('invalid bypass') || message.includes('exceeds current')) {
    return parsed.message;
  }

  // SAP-specific errors
  if (message.includes('sap') || message.includes('classification')) {
    return parsed.message;
  }

  // Server errors
  if (parsed.status && parsed.status >= 500) {
    return 'Server error. Please try again later or contact support.';
  }

  // Default: return parsed message
  return parsed.message || 'An unexpected error occurred';
};

/**
 * Determine toast type based on error
 */
export const getErrorToastType = (error: any): 'error' | 'warning' | 'info' => {
  const parsed = parseError(error);
  const message = parsed.message.toLowerCase();

  // Warnings (not critical failures)
  if (message.includes('vpn') || 
      message.includes('offline') ||
      message.includes('stored for later') ||
      message.includes('queued')) {
    return 'warning';
  }

  // Info (informational, not errors)
  if (message.includes('already') || 
      message.includes('no changes') ||
      message.includes('skipped')) {
    return 'info';
  }

  return 'error';
};

/**
 * Handle API error with toast notification
 * @param error - The error to handle
 * @param addToast - Toast function from component
 * @param context - Optional context for logging (e.g., "Starting order")
 */
export const handleApiError = (
  error: any, 
  addToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void,
  context?: string
): void => {
  const message = getErrorMessage(error);
  const toastType = getErrorToastType(error);

  // Log error with context
  if (context) {
    console.error(`❌ ${context}:`, error);
  } else {
    console.error('❌ Error:', error);
  }

  // Show toast
  addToast(message, toastType);
};

/**
 * Safely extract error message from API response
 * Handles both JSON and non-JSON responses
 */
export const extractApiErrorMessage = async (response: Response): Promise<string> => {
  try {
    const contentType = response.headers.get('content-type');
    
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      return data.error || data.message || data.detail || `HTTP ${response.status}: ${response.statusText}`;
    }
    
    const text = await response.text();
    
    // If it's HTML (error page), return generic message
    if (text.includes('<!DOCTYPE') || text.startsWith('<html')) {
      return `Server error (${response.status}): ${response.statusText}`;
    }
    
    // Return text if it's a simple message
    if (text.trim()) {
      return text.trim();
    }
    
    return `HTTP ${response.status}: ${response.statusText}`;
  } catch (e) {
    return `HTTP ${response.status}: ${response.statusText}`;
  }
};

/**
 * Check if error is a network error
 */
export const isNetworkError = (error: any): boolean => {
  const message = (error?.message || String(error)).toLowerCase();
  return message.includes('network') || 
         message.includes('fetch') || 
         message.includes('econnrefused') ||
         message.includes('connection refused') ||
         message.includes('failed to fetch');
};

/**
 * Check if error is a VPN disconnection error
 */
export const isVpnError = (error: any): boolean => {
  const message = (error?.message || String(error)).toLowerCase();
  return message.includes('vpn') && 
         (message.includes('disconnect') || message.includes('not connected'));
};

