import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { TextPreferencesProvider } from "@/contexts/TextPreferencesContext";
import { ScadaProvider } from "@/contexts/ScadaContext";
import { AppLayout } from "@/components/AppLayout";
import { NotificationProvider } from "@/components/NotificationSystem";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { LoginForm } from "@/components/LoginForm";
import ErrorBoundary from "./components/ErrorBoundary";


// Hercules SFMS Core System Pages
// import { Dashboard as WaterDashboard } from "./pages/hercules-sfms/Dashboard";


// New SFMS Pages
import KpiCalculations from "./pages/hercules-sfms/KpiCalculations";
import LiveMonitor from "./pages/hercules-sfms/LiveMonitor";
import Logs from "./pages/hercules-sfms/Logs";
import MaterialMap from "./pages/hercules-sfms/MaterialMap";
import PalletizerMapping from "./pages/hercules-sfms/PalletizerMapping";
import ProcessOrdersPage from "./pages/hercules-sfms/ProcessOrdersPage";
import ProcessOrderValidation from "./pages/hercules-sfms/ProcessOrderValidation";
import ScadaReadings from "./pages/hercules-sfms/ScadaReadings";
import SAPDashboard from "./pages/hercules-sfms/SAPDashboard";
import Reports from "./pages/hercules-sfms/Reportss";
import { Admin } from "./pages/hercules-sfms/Admin";
import { OfflineOrderValidation } from "./pages/hercules-sfms/OfflineOrderValidation";
import UserManagement from "./pages/hercules-sfms/UserManagement";
import { UserActivityLog } from "./pages/hercules-sfms/UserActivityLog";


// AuthGuard component to protect routes
function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAuthResolved, isSessionInvalid } = useAuth();
  
  // Check if token exists in localStorage as fallback
  const hasToken = !!localStorage.getItem('auth_token');
  
  // Wait until /api/auth/me settles; if 401, keep splash until AuthContext clears token and redirects
  if (!isAuthResolved || isSessionInvalid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 dark:bg-slate-900">
        <div className="text-white">Loading...</div>
      </div>
    );
  }
  
  // Allow access if either authenticated or token exists
  if (!isAuthenticated && !hasToken) {
    window.location.href = '/auth';
    return null;
  }
  
  return <>{children}</>;
}

// AdminGuard: redirect non-admin users away from admin-only routes (e.g. /admin, /user-management, /activity-log)
function AdminGuard({ children }: { children: React.ReactNode }) {
  const { hasRole, isAuthResolved, isAuthenticated } = useAuth();

  if (!isAuthResolved) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 dark:bg-slate-900">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    window.location.href = '/auth';
    return null;
  }

  if (!hasRole('admin')) {
    window.location.href = '/sap-dashboard';
    return null;
  }

  return <>{children}</>;
}

function Router() {
  return (
    <Switch>
      {/* Auth Route */}
      <Route path="/auth" component={() => <LoginForm />} />
      
      {/* Protected Routes - wrapped with AuthGuard */}
      <Route path="/" component={() => <AuthGuard><SAPDashboard /></AuthGuard>} />
      <Route path="/dashboard" component={() => <AuthGuard><SAPDashboard /></AuthGuard>} />
      <Route path="/overview" component={() => { window.location.href = '/sap-dashboard'; return null; }} />
      <Route path="/sap-dashboard" component={() => <AuthGuard><SAPDashboard /></AuthGuard>} />
      
      {/* New SFMS Feature Routes */}
      <Route path="/kpi-calculations" component={() => <AuthGuard><KpiCalculations /></AuthGuard>} />
      <Route path="/live-monitor" component={() => <AuthGuard><LiveMonitor /></AuthGuard>} />
      <Route path="/logs" component={() => <AuthGuard><Logs /></AuthGuard>} />
      <Route path="/material-map" component={() => <AuthGuard><MaterialMap /></AuthGuard>} />
      <Route path="/palletizer-mapping" component={() => <AuthGuard><PalletizerMapping /></AuthGuard>} />
      <Route path="/offline-validation" component={() => <AuthGuard><OfflineOrderValidation /></AuthGuard>} />
      <Route path="/process-orders" component={() => <AuthGuard><ProcessOrdersPage /></AuthGuard>} />
      <Route path="/process-validation" component={() => <AuthGuard><ProcessOrderValidation /></AuthGuard>} />
      <Route path="/scada-readings" component={() => <AuthGuard><ScadaReadings /></AuthGuard>} />
      <Route path="/reports" component={() => <AuthGuard><Reports /></AuthGuard>} />
      <Route path="/admin" component={() => <AuthGuard><AdminGuard><Admin /></AdminGuard></AuthGuard>} />
      <Route path="/user-management" component={() => <AuthGuard><AdminGuard><UserManagement /></AdminGuard></AuthGuard>} />
      <Route path="/activity-log" component={() => <AuthGuard><AdminGuard><UserActivityLog /></AdminGuard></AuthGuard>} />
      
      {/* Legacy routes redirect to SAP Dashboard */}
      <Route path="/water-system" component={() => { window.location.href = '/sap-dashboard'; return null; }} />
      <Route path="/water-system/dashboard" component={() => { window.location.href = '/sap-dashboard'; return null; }} />
      
      {/* Catch all - redirect to auth if not authenticated, otherwise SAP Dashboard */}
      <Route component={() => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          window.location.href = '/auth';
          return null;
        }
        window.location.href = '/sap-dashboard';
        return null;
      }} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TextPreferencesProvider>
        <ScadaProvider>
          <AuthProvider>
            <NotificationProvider>
              <TooltipProvider>
                <ErrorBoundary>
                  <Toaster />
                  <Router />
                </ErrorBoundary>
              </TooltipProvider>
            </NotificationProvider>
          </AuthProvider>
        </ScadaProvider>
        </TextPreferencesProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
