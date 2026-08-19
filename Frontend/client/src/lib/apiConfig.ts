/**
 * 🎯 SINGLE API CONFIGURATION - CHANGE THIS ONE VARIABLE TO UPDATE ALL API CALLS
 * 
 * Instructions:
 * - For localhost: Set to 'http://localhost:5000'
 * - For VM/production: Set to 'http://10.140.121.85:5000' (or your URL)
 * - For same host (recommended): Set to '' (empty string)
 */

// ✅ API base URL: use VITE_API_BASE_URL from env (e.g. Netlify/ngrok) or relative URLs
// Default '' uses same origin; with `npm run dev`, Vite proxies /api → http://localhost:5000 (see vite.config.ts)
const envApiUrl = typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL;
export const API_BASE_URL = (envApiUrl && String(envApiUrl).trim()) || '';

// ✅ Console log on module load to show which API is configured
if (typeof window !== 'undefined') {
  if (API_BASE_URL) {
    console.log('🌐 API Configuration:', API_BASE_URL);
    console.log('📡 All API calls will use:', API_BASE_URL);
  } else {
    console.log('🌐 API Configuration: Relative URLs (same host)');
    console.log('📡 All API calls will use: Current page origin');
  }
}

/**
 * Helper function to build complete API URLs
 * All API calls should use: getApiUrl('/api/endpoint')
 */
export function getApiUrl(endpoint: string): string {
  // Ensure endpoint starts with /
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  // If API_BASE_URL is set, use it; otherwise use relative URL
  if (API_BASE_URL) {
    // Remove trailing slash from API_BASE_URL if present
    const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const fullUrl = `${base}${cleanEndpoint}`;
    
    // Log API calls in development mode
    if (import.meta.env.DEV) {
      console.log('🔗 API Call:', fullUrl);
    }
    
    return fullUrl;
  }
  
  // Relative URL - works on same host (recommended for production)
  const relativeUrl = cleanEndpoint;
  
  // Log API calls in development mode
  if (import.meta.env.DEV) {
    console.log('🔗 API Call (relative):', relativeUrl);
  }
  
  return relativeUrl;
}

/**
 * Get headers needed for API calls (includes ngrok bypass header)
 */
export function getApiHeaders(additionalHeaders?: Record<string, string>): Record<string, string> {
  return {
    'ngrok-skip-browser-warning': 'true',  // Skip ngrok free tier interstitial page
    ...additionalHeaders,
  };
}

/**
 * Fetch wrapper that automatically adds ngrok headers and auth token when present.
 * Sending the token ensures the backend can log the current user (e.g. User Activity log).
 */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    'ngrok-skip-browser-warning': 'true',
    ...(init?.headers as Record<string, string> || {}),
  };
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, {
    ...init,
    headers,
  });
}
