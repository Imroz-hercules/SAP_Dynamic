import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { Layers3, TrendingUp, Target, Trash2 } from 'lucide-react';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';
import { useLocation } from 'wouter';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 MaterialMap.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

interface UserInfo {
  id: number;
  username: string;
  roles: string[];
}

interface MillingVersionMapping {
  id?: number;
  version: string;
  scales: string[] | string; // Can be array or JSON string
  formula: string;
  scale1?: string | null;
  scale2?: string | null;
  description?: string | null;
  scada_recipe_name?: string | null;
}

interface KpiCardProps {
  title: string;
  value: number;
  unit: string;
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, unit, Icon, color }) => {
  const { theme } = useTheme();
  
  return (
    <div className="relative group">
      {/* Glassmorphism card with transparent background */}
      <div className={`p-3 rounded-lg backdrop-blur-md border transition-all duration-500 shadow-md hover:shadow-lg ${
        theme === 'light' 
          ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
          : 'bg-slate-900/20 border-cyan-400/30 hover:border-cyan-400/50 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_30px_rgba(0,255,255,0.2)]'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h3 className={`text-xs font-bold uppercase tracking-widest mb-0.5 ${
              theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            } group-hover:text-opacity-80 transition-all duration-300`}>
              {title}
            </h3>
            <div className="flex items-baseline gap-1">
              <span 
                className={`text-xl font-black ${
                  theme === 'light' ? 'text-slate-800' : 'text-white'
                } drop-shadow-sm group-hover:scale-105 transition-all duration-300`}
                style={{ color }}
              >
                {value}
              </span>
              <span className={`text-xs font-medium ${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                {unit}
              </span>
            </div>
          </div>
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
            <div style={{ color }}>
              <Icon 
                className={`h-5 w-5 drop-shadow-lg transition-all duration-300 group-hover:scale-110`}
              />
            </div>
          </div>
        </div>
        
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

const MaterialMap = () => {
  const [mappings, setMappings] = useState<MillingVersionMapping[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<MillingVersionMapping | null>(null);
  const [search, setSearch] = useState('');
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  const [loading, setLoading] = useState(true);
  const { theme } = useTheme();

  // Delete confirmation modal state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; version: string } | null>(null);

  // Fetch current user info to check admin role
  const { data: userData } = useQuery({
    queryKey: ['/api/auth/me'],
    queryFn: () => apiRequest('GET', '/api/auth/me'),
    select: (data) => data.user || null,
    retry: false,
    enabled: !!localStorage.getItem('auth_token')
  });

  const currentUser = userData as UserInfo | null;
  const isAdmin = currentUser?.roles?.includes('admin') || false;
  const canAccess = isAdmin || currentUser?.roles?.includes('milling_operator');
  const [, setLocation] = useLocation();
  useEffect(() => {
    if (userData !== undefined && currentUser && !canAccess) {
      setLocation('/process-validation');
    }
  }, [userData, currentUser, canAccess, setLocation]);
  
  // Form state
  const [formData, setFormData] = useState<MillingVersionMapping>({
    version: '',
    scales: [],
    formula: '',
    scale1: null,
    scale2: null,
    description: '',
    scada_recipe_name: null,
  });
  const [scalesInput, setScalesInput] = useState(''); // For comma-separated input

  // Show notification function
  const showNotification = (message: string, type = 'success') => {
    setNotification({ show: true, message, type });
    setTimeout(() => {
      setNotification({ show: false, message: '', type: '' });
    }, 3000);
  };

  // Fetch milling mappings from backend
  const fetchMappings = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(getApiUrl('/api/milling-mapping'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setMappings(data);
    } catch (error) {
      console.error('Error fetching milling mappings:', error);
      showNotification('Failed to fetch milling mappings from server', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Add new milling mapping to backend
  const addMapping = async () => {
    try {
      // Validate required fields
      if (!formData.version || !formData.scales || !formData.formula) {
        showNotification('Please fill in all required fields (Version, Scales, Formula)', 'error');
        return;
      }

      // Convert scales input to array
      const scalesArray = handleScalesSplit(scalesInput);
      if (scalesArray.length === 0) {
        showNotification('Please enter at least one scale', 'error');
        return;
      }

      const payload = {
        version: formData.version.toUpperCase().trim(),
        scales: scalesArray,
        formula: formData.formula.trim(),
        scale1: formData.scale1 || null,
        scale2: formData.scale2 || null,
        description: formData.description || '',
        scada_recipe_name: (formData.scada_recipe_name || '').trim() || null,
      };

      const response = await apiFetch(getApiUrl('/api/milling-mapping'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      // Refresh the mappings list
      await fetchMappings();
      showNotification('Milling mapping added successfully!', 'success');
      setModalOpen(false);
      resetForm();
    } catch (error: any) {
      console.error('Error adding milling mapping:', error);
      showNotification(error.message || 'Failed to add milling mapping', 'error');
    }
  };

  // Update existing milling mapping
  const updateMapping = async () => {
    if (!editingMapping || !editingMapping.id) {
      showNotification('No mapping selected for update', 'error');
      return;
    }

    try {
      // Validate required fields
      if (!formData.version || !formData.scales || !formData.formula) {
        showNotification('Please fill in all required fields (Version, Scales, Formula)', 'error');
        return;
      }

      // Convert scales input to array
      const scalesArray = handleScalesSplit(scalesInput);
      if (scalesArray.length === 0) {
        showNotification('Please enter at least one scale', 'error');
        return;
      }

      const payload = {
        version: formData.version.toUpperCase().trim(),
        scales: scalesArray,
        formula: formData.formula.trim(),
        scale1: formData.scale1 || null,
        scale2: formData.scale2 || null,
        description: formData.description || '',
        scada_recipe_name: (formData.scada_recipe_name || '').trim() || null,
      };

      const response = await apiFetch(getApiUrl(`/api/milling-mapping/${editingMapping.id}`), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      // Refresh the mappings list
      await fetchMappings();
      showNotification('Milling mapping updated successfully!', 'success');
      setModalOpen(false);
      setEditingMapping(null);
      resetForm();
    } catch (error: any) {
      console.error('Error updating milling mapping:', error);
      showNotification(error.message || 'Failed to update milling mapping', 'error');
    }
  };

  // Handle initiating delete (opens confirmation modal)
  const deleteMapping = (id: number, version: string) => {
    setDeleteTarget({ id, version });
    setDeleteConfirmOpen(true);
  };

  // Handle confirmed delete
  const confirmDeleteMapping = async () => {
    if (!deleteTarget) return;

    try {
      const response = await apiFetch(getApiUrl(`/api/milling-mapping/${deleteTarget.id}`), {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      // Refresh the mappings list
      await fetchMappings();
      showNotification('Milling mapping deleted successfully!', 'success');
    } catch (error: any) {
      console.error('Error deleting milling mapping:', error);
      showNotification(error.message || 'Failed to delete milling mapping', 'error');
    } finally {
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
    }
  };

  // Handle cancel delete
  const cancelDeleteMapping = () => {
    setDeleteConfirmOpen(false);
    setDeleteTarget(null);
  };

  // Edit mapping - open modal with existing data
  const handleEdit = (mapping: MillingVersionMapping) => {
    setEditingMapping(mapping);
    setFormData({
      version: mapping.version,
      scales: mapping.scales,
      formula: mapping.formula,
      scale1: mapping.scale1 || null,
      scale2: mapping.scale2 || null,
      description: mapping.description || '',
      scada_recipe_name: mapping.scada_recipe_name || null,
    });
    // Set scales input for editing
    if (Array.isArray(mapping.scales)) {
      setScalesInput(mapping.scales.join(', '));
    } else if (typeof mapping.scales === 'string') {
      try {
        const parsed = JSON.parse(mapping.scales);
        setScalesInput(Array.isArray(parsed) ? parsed.join(', ') : mapping.scales);
      } catch {
        setScalesInput(mapping.scales);
      }
    } else {
      setScalesInput('');
    }
    setModalOpen(true);
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      version: '',
      scales: [],
      formula: '',
      scale1: null,
      scale2: null,
      description: '',
      scada_recipe_name: null,
    });
    setScalesInput('');
    setEditingMapping(null);
  };

  // Handle modal close
  const handleModalClose = () => {
    setModalOpen(false);
    setEditingMapping(null);
    resetForm();
  };

  // Initialize by fetching data from backend
  useEffect(() => {
    fetchMappings();
  }, []);

  const filteredMappings = mappings.filter((m: MillingVersionMapping) => {
    const matchesSearch = m.version.toLowerCase().includes(search.toLowerCase()) ||
      (Array.isArray(m.scales) ? m.scales.join(', ') : String(m.scales)).toLowerCase().includes(search.toLowerCase()) ||
      m.formula.toLowerCase().includes(search.toLowerCase());
    return matchesSearch;
  });

  // Helper to format scales for display
  const formatScales = (scales: string[] | string): string => {
    if (Array.isArray(scales)) {
      return scales.join(', ');
    }
    if (typeof scales === 'string') {
      try {
        const parsed = JSON.parse(scales);
        return Array.isArray(parsed) ? parsed.join(', ') : scales;
      } catch {
        return scales;
      }
    }
    return '';
  };

  // Fix type annotations
  const handleScalesSplit = (input: string): string[] => {
    return input.split(',').map((s: string) => s.trim()).filter((s: string) => s.length > 0);
  };

  // Styling logic
  const bgMain = theme === 'light'
    ? 'bg-slate-100 text-slate-800'
    : 'bg-gradient-to-br from-[#0f172a] to-[#1e293b] text-white';
  const filterInput = theme === 'light'
    ? 'bg-white text-slate-900 border border-slate-300 focus:ring-slate-300'
    : 'bg-[#0f172a] text-cyan-200 border border-cyan-500 focus:ring-cyan-400';
  const filterSelect = theme === 'light'
    ? 'bg-white text-slate-900 border border-slate-300 focus:ring-slate-300'
    : 'bg-[#0f172a] text-cyan-200 border border-cyan-500 focus:ring-cyan-400';
  const tableBg = theme === 'light'
    ? 'bg-white border border-slate-200 text-slate-900'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  const tableHeader = theme === 'light'
    ? 'bg-blue-50 text-black border-b border-blue-200'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' 
    ? 'bg-white hover:bg-gray-50 cursor-pointer transition-all duration-200'
    : 'bg-[#22304a]/60 hover:bg-[#2d4065] cursor-pointer transition-all duration-200';
  
  const tableRowOdd = theme === 'light'
    ? 'bg-gray-50 hover:bg-gray-100 cursor-pointer transition-all duration-200'
    : 'bg-[#1a2532] hover:bg-[#2d4065] cursor-pointer transition-all duration-200';

  const tableBorder = theme === 'light' ? 'border-blue-200' : 'border-slate-600';
  const cellBorder = theme === 'light' ? 'border-blue-200' : 'border-slate-600';

  const tableCellHighlight = theme === 'light'
    ? 'hover:text-gray-700 hover:font-semibold transition-all duration-200'
    : 'hover:text-cyan-300 hover:font-semibold transition-all duration-200';
  const modalBg = theme === 'light'
    ? 'bg-white border border-blue-300 text-blue-900'
    : 'bg-[#1e293b] border border-cyan-500 text-white';
  const closeBtn = theme === 'light'
    ? 'text-blue-400 hover:text-blue-600'
    : 'text-cyan-300 hover:text-cyan-100';

  return (
    <WaterSystemLayout 
      title="Milling Version Mapping" 
      subtitle="Milling Version Mapping Management"
    >
      <style>{`
        /* Force white text for buttons in light mode */
        .material-refresh-light {
          color: white !important;
        }
        
        .material-refresh-light span {
          color: white !important;
        }
        
        .material-refresh-light svg {
          color: white !important;
        }
        
        .material-add-light {
          color: white !important;
        }
        
        .material-add-light span {
          color: white !important;
        }
        
        /* Ensure modal is fully visible */
        .material-modal-container {
          min-height: 100vh;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding-top: 1rem;
          padding-bottom: 2rem;
        }
        
        .material-modal-content {
          margin-top: 0;
          margin-bottom: auto;
        }
        
      `}</style>
      <div className="space-y-6 w-full px-4 py-6">
      {/* Notification */}
      {notification.show && (
        <div
          className={`fixed top-4 right-4 z-50 px-3 py-1.5 rounded-md shadow-lg transition-all duration-500 text-sm ${
            notification.type === 'success'
              ? theme === 'light'
                ? 'bg-green-100 border border-green-500 text-green-700'
                : 'bg-green-500/20 border border-green-500 text-green-300'
              : theme === 'light'
              ? 'bg-red-100 border border-red-500 text-red-700' 
              : 'bg-red-500/20 border border-red-500 text-red-300'
          }`}
        >
          {notification.message}
        </div>
      )}

      <h2 className={`text-xl font-bold mb-2 ${theme === 'light' ? 'text-slate-700' : 'text-cyan-400'}`}>
        Milling Version Mapping
      </h2>

      {/* Add Button and Refresh */}
      <div className="w-full flex justify-between items-center mb-4">
        <button
          onClick={fetchMappings}
          disabled={loading}
          className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white material-refresh-light ${
            theme === 'light'
              ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
              : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
          } disabled:opacity-50 disabled:hover:scale-100`}
          style={{
            color: 'white !important'
          }}
          title="Refresh Mappings"
        >
          <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''} !text-white material-refresh-light`} style={{ color: 'white !important' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span className="font-semibold tracking-wide !text-white material-refresh-light" style={{ color: 'white !important' }}>{loading ? 'Refreshing...' : 'Refresh'}</span>
          <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </button>
        
        {/* Add Mapping button - Only visible for admin users */}
        {isAdmin && (
          <button
            onClick={() => setModalOpen(true)}
            className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white material-add-light ${
              theme === 'light'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
            }`}
            style={{
              color: 'white !important'
            }}
            title="Add New Milling Mapping"
          >
            <span className="font-semibold tracking-wide !text-white material-add-light" style={{ color: 'white !important' }}>+ Add Mapping</span>
            <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="w-full flex flex-col md:flex-row gap-4 mb-4 items-center justify-between">
        <input
          type="text"
          placeholder="Search by version, scales, or formula..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${filterInput} rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-opacity-50 backdrop-blur-sm border transition-all duration-300 w-full md:w-1/2 shadow-md text-sm ${
            theme === 'light' 
              ? 'focus:ring-slate-400 focus:border-slate-400' 
              : 'focus:ring-cyan-400 focus:border-cyan-400 focus:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
          }`}
        />
      </div>

      {/* Mapping Count */}
      <div className="mb-4 w-full flex justify-end pr-2">
        <span className={theme === 'light' ? 'text-slate-500 text-xs font-semibold' : 'text-cyan-300 text-xs font-semibold'}>
          Total Mappings: {filteredMappings.length}
        </span>
      </div>

      {/* Loading State */}
      {loading && (
        <div className={`w-full flex justify-center items-center py-8 ${theme === 'light' ? 'text-slate-600' : 'text-cyan-300'}`}>
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current"></div>
          <span className="ml-2 text-sm">Loading materials...</span>
        </div>
      )}

      {/* Mapping Table */}
      {!loading && (
        <div className={`overflow-x-auto rounded-lg backdrop-blur-md shadow w-full transition-all duration-300 ${
          theme === 'light' 
            ? 'bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30' 
            : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
        }`}>
          <table className={`min-w-full text-xs text-left font-mono border-collapse border ${tableBorder} ${theme === 'light' ? 'text-black' : 'text-cyan-200'}`}>
            <thead className={`${tableHeader} uppercase text-xs tracking-wider sticky top-0 z-10`}>
              <tr>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>Version</th>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>SCADA Recipe Name</th>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>Scales</th>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>Formula</th>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>Scale1</th>
                <th className={`px-4 py-3 border-r ${cellBorder}`}>Scale2</th>
                <th className={`px-4 py-3 ${isAdmin ? `border-r ${cellBorder}` : ''}`}>Description</th>
                {isAdmin && <th className="px-4 py-3">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {filteredMappings.length === 0 ? (
                <tr>
                    <td colSpan={isAdmin ? 8 : 7} className={`px-4 py-8 text-center text-sm border-r ${cellBorder} ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`}>
                    {mappings.length === 0 ? 'No milling mappings found. Add your first mapping!' : 'No mappings match your search criteria.'}
                  </td>
                </tr>
              ) : (
                filteredMappings.map((map: MillingVersionMapping, idx: number) => (
                  <tr
                    key={map.id || idx}
                    className={`transition-all duration-200 border-b ${
                      theme === 'light' ? 'border-blue-100' : 'border-slate-700'
                    } ${idx % 2 === 0 ? tableRowEven : tableRowOdd}`}
                  >
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight} font-bold`}>{map.version}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{map.scada_recipe_name || '-'}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{formatScales(map.scales)}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{map.formula || '-'}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{map.scale1 || '-'}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{map.scale2 || '-'}</td>
                    <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{map.description || '-'}</td>
                    {/* Actions column - Only visible for admin users */}
                    {isAdmin && (
                      <td className={`px-4 py-3 ${tableCellHighlight}`}>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleEdit(map)}
                            className={`px-2 py-1 rounded text-xs font-medium transition-all duration-200 hover:scale-105 !text-white ${
                              theme === 'light'
                                ? 'bg-blue-500 hover:bg-blue-600'
                                : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                            style={{ color: 'white !important' }}
                            title="Edit mapping"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => map.id && deleteMapping(map.id, map.version)}
                            className={`px-2 py-1 rounded text-xs font-medium transition-all duration-200 hover:scale-105 ${
                              theme === 'light'
                                ? 'bg-red-500 text-white hover:bg-red-600'
                                : 'bg-red-600 text-white hover:bg-red-700'
                            }`}
                            title="Delete mapping"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <div className={`material-modal-container fixed inset-0 z-[60] backdrop-blur-lg animate-in fade-in duration-300 ${
          theme === "light" 
            ? "bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30" 
            : "bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20"
        }`}>
          <div className={`material-modal-content relative z-10 w-full max-w-4xl mx-4 rounded-xl shadow-2xl transform transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 max-h-[calc(100vh-4rem)] overflow-hidden ${
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
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  </div>
                  <div>
                    <h3 className={`text-lg font-semibold ${
                      theme === "light" ? "text-gray-900" : "text-white"
                    }`}>
                      {editingMapping ? 'Edit Milling Version Mapping' : 'Add Milling Version Mapping'}
                    </h3>
                    <p className={`text-sm ${
                      theme === "light" ? "text-gray-500" : "text-gray-400"
                    }`}>
                      {editingMapping ? 'Update milling version specifications and scales' : 'Configure milling version specifications and scales'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleModalClose}
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
            <div className="p-6 overflow-y-auto max-h-[calc(100vh-12rem)]">
              <form onSubmit={(e: React.FormEvent) => { 
                e.preventDefault(); 
                if (editingMapping) {
                  updateMapping();
                } else {
                  addMapping();
                }
              }} className="space-y-4">
                {/* Version */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${
                    theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                  }`}>
                    Version <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.version}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, version: e.target.value.toUpperCase() })}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                        : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                    } focus:outline-none focus:ring-2`}
                    placeholder="e.g., LWSM, CKF1"
                    required
                  />
                </div>

                {/* SCADA Recipe Name */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${
                    theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                  }`}>
                    SCADA Recipe Name
                  </label>
                  <input
                    type="text"
                    value={formData.scada_recipe_name || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, scada_recipe_name: e.target.value || null })}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                        : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                    } focus:outline-none focus:ring-2`}
                    placeholder="e.g., F80, F80 + F70"
                  />
                </div>

                {/* Scales */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${
                    theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                  }`}>
                    Scales (comma-separated) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={scalesInput}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setScalesInput(e.target.value)}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                        : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                    } focus:outline-none focus:ring-2`}
                    placeholder="e.g., WG101, WG302, DM101"
                    required
                  />
                  <p className={`text-xs mt-1 ${
                    theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    Enter scale tags separated by commas
                  </p>
                </div>

                {/* Formula */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${
                    theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                  }`}>
                    Formula <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.formula}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, formula: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                        : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                    } focus:outline-none focus:ring-2`}
                    placeholder="e.g., (WG101-WG302)+(DM101+DM102)"
                    required
                  />
                </div>

                {/* Byproduct Scales */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Scale1 (Byproduct)
                    </label>
                    <input
                      type="text"
                      value={formData.scale1 || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, scale1: e.target.value || null })}
                      className={`w-full px-4 py-2 rounded-lg border ${
                        theme === 'light'
                          ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                          : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                      } focus:outline-none focus:ring-2`}
                      placeholder="e.g., WG302"
                    />
                  </div>
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Scale2 (Byproduct)
                    </label>
                    <input
                      type="text"
                      value={formData.scale2 || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, scale2: e.target.value || null })}
                      className={`w-full px-4 py-2 rounded-lg border ${
                        theme === 'light'
                          ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                          : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                      } focus:outline-none focus:ring-2`}
                      placeholder="e.g., WG503"
                    />
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${
                    theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                  }`}>
                    Description
                  </label>
                  <input
                    type="text"
                    value={formData.description || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, description: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 focus:ring-blue-500'
                        : 'bg-slate-700 border-cyan-500/50 text-cyan-100 focus:ring-cyan-400'
                    } focus:outline-none focus:ring-2`}
                    placeholder="Enter description (optional)"
                  />
                </div>

                {/* Submit Button */}
                <div className="pt-4 flex gap-3">
                  <button
                    type="button"
                    onClick={handleModalClose}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                      theme === 'light'
                        ? 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                        : 'bg-slate-700 text-cyan-100 hover:bg-slate-600'
                    }`}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className={`flex-1 px-4 py-2 rounded-lg font-medium text-white transition-all ${
                      theme === 'light'
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700'
                        : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700'
                    }`}
                  >
                    {editingMapping ? 'Update Mapping' : 'Add Mapping'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmOpen && deleteTarget && (
        <div className={`fixed inset-0 z-[70] flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200 ${
          theme === "light" 
            ? "bg-black/30" 
            : "bg-black/50"
        }`}>
          <div className={`relative w-full max-w-md rounded-xl shadow-2xl transform transition-all duration-200 animate-in zoom-in-95 fade-in ${
            theme === "light" 
              ? "bg-white border border-gray-200" 
              : "bg-slate-800 border border-slate-700"
          }`}>
            {/* Header with Warning Icon */}
            <div className={`px-6 py-4 border-b flex items-center gap-4 ${
              theme === "light" ? "border-gray-200" : "border-slate-700"
            }`}>
              <div className={`p-3 rounded-full ${
                theme === "light" 
                  ? "bg-red-100" 
                  : "bg-red-900/30"
              }`}>
                <Trash2 className={`w-6 h-6 ${
                  theme === "light" ? "text-red-600" : "text-red-400"
                }`} />
              </div>
              <div>
                <h3 className={`text-lg font-semibold ${
                  theme === "light" ? "text-gray-900" : "text-white"
                }`}>
                  Confirm Delete
                </h3>
                <p className={`text-sm ${
                  theme === "light" ? "text-gray-500" : "text-gray-400"
                }`}>
                  This action cannot be undone
                </p>
              </div>
            </div>
            
            {/* Content */}
            <div className="px-6 py-4">
              <p className={`text-sm ${
                theme === "light" ? "text-gray-700" : "text-gray-300"
              }`}>
                Are you sure you want to delete the milling mapping for:
              </p>
              <div className={`mt-3 p-3 rounded-lg ${
                theme === "light" 
                  ? "bg-gray-100 border border-gray-200" 
                  : "bg-slate-900/50 border border-slate-700"
              }`}>
                <p className={`font-semibold ${
                  theme === "light" ? "text-gray-900" : "text-white"
                }`}>
                  Version: {deleteTarget.version}
                </p>
              </div>
            </div>
            
            {/* Actions */}
            <div className={`px-6 py-4 border-t flex justify-end gap-3 ${
              theme === "light" ? "border-gray-200 bg-gray-50" : "border-slate-700 bg-slate-900/30"
            }`}>
              <button
                onClick={cancelDeleteMapping}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 ${
                  theme === "light" 
                    ? "bg-gray-200 text-gray-700 hover:bg-gray-300" 
                    : "bg-slate-700 text-gray-300 hover:bg-slate-600"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteMapping}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 ${
                  theme === "light" 
                    ? "bg-red-600 text-white hover:bg-red-700 shadow-md shadow-red-500/30" 
                    : "bg-red-600 text-white hover:bg-red-500 shadow-md shadow-red-500/25"
                }`}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </WaterSystemLayout>
  );
};

export default MaterialMap;