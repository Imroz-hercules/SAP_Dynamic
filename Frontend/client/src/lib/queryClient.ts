import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { getApiUrl, API_BASE_URL } from './apiConfig';

// Log API configuration on module load
if (typeof window !== 'undefined') {
  console.log('🔧 queryClient.ts: API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<any> {
  // ✅ FIX: Use relative URLs via getApiUrl
  const fullUrl = url.startsWith('http') ? url : getApiUrl(url);
  
  // Log API request in development
  if (import.meta.env.DEV) {
    console.log(`📤 API Request [${method}]:`, fullUrl);
  }

  // Get auth token from localStorage
  const token = localStorage.getItem('auth_token');
  
  const headers: Record<string, string> = {
    "ngrok-skip-browser-warning": "true",  // Skip ngrok interstitial page
  };
  if (data) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  try {
    const res = await fetch(fullUrl, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: "same-origin",
    });

    await throwIfResNotOk(res);
    return await res.json();
  } catch (error: any) {
    throw error;
  }
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const url = queryKey[0] as string;
    // ✅ FIX: Use relative URLs via getApiUrl
    const fullUrl = url.startsWith('http') ? url : getApiUrl(url);
    
    // Log API query in development
    if (import.meta.env.DEV) {
      console.log('📥 API Query:', fullUrl);
    }
    
    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');
    
    const headers: Record<string, string> = {
      "ngrok-skip-browser-warning": "true",  // Skip ngrok interstitial page
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const res = await fetch(fullUrl, {
      headers,
      credentials: "same-origin",
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
