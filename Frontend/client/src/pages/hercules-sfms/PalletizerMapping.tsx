import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { Package, Plus, X, Edit, Trash2 } from 'lucide-react';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { palletizerApi, PalletizerMapping as PalletizerMappingType, PalletizerMappingRequest } from '../../lib/api';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { useLocation } from 'wouter';

interface UserInfo {
  id: number;
  username: string;
  roles: string[];
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
      </div>
    </div>
  );
};

const PalletizerMapping = () => {
  const { theme } = useTheme();

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
  const canAccess = isAdmin || currentUser?.roles?.includes('packing_operator');
  const [, setLocation] = useLocation();
  useEffect(() => {
    if (userData !== undefined && currentUser && !canAccess) {
      setLocation('/process-validation');
    }
  }, [userData, currentUser, canAccess, setLocation]);

  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [filterVersion, setFilterVersion] = useState('');
  const [palletizers, setPalletizers] = useState<PalletizerMappingType[]>([]);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{ show: boolean; message: string; type: 'success' | 'error' }>({ show: false, message: '', type: 'success' });

  const [formData, setFormData] = useState<Omit<PalletizerMappingType, 'id'>>({
    version: '',
    palletizer: '',
    bag_size_kg: 0,
    bags_per_pallet: 0,
    kg_per_pallet: 0,
    description: '',
  });

  // Track if we're editing an existing palletizer
  const [editingId, setEditingId] = useState<number | null>(null);

  // Delete confirmation modal state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; version: string; palletizer: string } | null>(null);

  // Show notification
  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ show: true, message, type });
    setTimeout(() => {
      setNotification({ show: false, message: '', type: 'success' });
    }, 3000);
  };

  // Fetch palletizers from backend
  const fetchPalletizers = async () => {
    try {
      setLoading(true);
      const data = await palletizerApi.getPalletizerMappings();
      setPalletizers(data);
    } catch (error: any) {
      console.error('Error fetching palletizers:', error);
      showNotification(`Failed to load palletizers: ${error.message || 'Unknown error'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Load palletizers on component mount
  useEffect(() => {
    fetchPalletizers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Get unique versions for filter
  const uniqueVersions = Array.from(new Set(palletizers.map(p => p.version)));

  // Filter palletizers
  const filteredPalletizers = palletizers.filter(p => {
    const matchesSearch = search === '' || 
      p.version.toLowerCase().includes(search.toLowerCase()) ||
      p.palletizer.toLowerCase().includes(search.toLowerCase());
    const matchesVersion = filterVersion === '' || p.version === filterVersion;
    return matchesSearch && matchesVersion;
  });

  const handleAddPalletizer = async () => {
    if (!formData.version || !formData.palletizer || formData.bag_size_kg <= 0 || 
        formData.bags_per_pallet <= 0 || formData.kg_per_pallet <= 0) {
      showNotification('Please fill in all fields with valid values', 'error');
      return;
    }

    try {
      const payload: PalletizerMappingRequest = {
        version: formData.version.toUpperCase(),
        palletizer: formData.palletizer,
        bag_size_kg: formData.bag_size_kg,
        bags_per_pallet: formData.bags_per_pallet,
        kg_per_pallet: formData.kg_per_pallet,
        description: formData.description || '',
      };

      const result = await palletizerApi.createOrUpdatePalletizerMapping(payload);
      
      if (result.success) {
        showNotification(result.message || `Palletizer mapping ${result.mode === 'create' ? 'created' : 'updated'} successfully`, 'success');
        // Refresh the list
        await fetchPalletizers();
        // Reset form and close modal
        setFormData({
          version: '',
          palletizer: '',
          bag_size_kg: 0,
          bags_per_pallet: 0,
          kg_per_pallet: 0,
          description: '',
        });
        setModalOpen(false);
      } else {
        showNotification(result.message || 'Failed to save palletizer mapping', 'error');
      }
    } catch (error: any) {
      console.error('Error saving palletizer:', error);
      showNotification(`Failed to save palletizer: ${error.message || 'Unknown error'}`, 'error');
    }
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditingId(null);
    setFormData({
      version: '',
      palletizer: '',
      bag_size_kg: 0,
      bags_per_pallet: 0,
      kg_per_pallet: 0,
      description: '',
    });
  };

  // Handle editing a palletizer
  const handleEditPalletizer = (palletizer: PalletizerMappingType) => {
    setEditingId(palletizer.id);
    setFormData({
      version: palletizer.version,
      palletizer: palletizer.palletizer,
      bag_size_kg: palletizer.bag_size_kg,
      bags_per_pallet: palletizer.bags_per_pallet,
      kg_per_pallet: palletizer.kg_per_pallet,
      description: palletizer.description || '',
    });
    setModalOpen(true);
  };

  // Handle initiating delete (opens confirmation modal)
  const handleDeletePalletizer = (id: number, version: string, palletizer: string) => {
    setDeleteTarget({ id, version, palletizer });
    setDeleteConfirmOpen(true);
  };

  // Handle confirmed delete
  const confirmDeletePalletizer = async () => {
    if (!deleteTarget) return;
    
    try {
      const result = await palletizerApi.deletePalletizerMapping(deleteTarget.id);
      if (result.success) {
        showNotification(result.message || 'Palletizer mapping deleted successfully', 'success');
        await fetchPalletizers();
      } else {
        showNotification(result.message || 'Failed to delete palletizer mapping', 'error');
      }
    } catch (error: any) {
      console.error('Error deleting palletizer:', error);
      showNotification(`Failed to delete palletizer: ${error.message || 'Unknown error'}`, 'error');
    } finally {
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
    }
  };

  // Handle cancel delete
  const cancelDeletePalletizer = () => {
    setDeleteConfirmOpen(false);
    setDeleteTarget(null);
  };

  // Theme classes
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
  const inputClass = theme === 'light'
    ? 'w-full px-4 py-3 rounded-xl bg-white/95 border-2 border-slate-200 text-slate-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl backdrop-blur-sm text-sm'
    : 'w-full px-4 py-3 rounded-xl bg-slate-800/95 border-2 border-cyan-500/50 text-cyan-100 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl focus:shadow-cyan-500/30 backdrop-blur-sm text-sm';
  const selectClass = theme === 'light'
    ? 'w-full px-4 py-3 pr-10 rounded-xl bg-white/95 border-2 border-slate-200 text-slate-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl appearance-none cursor-pointer bg-no-repeat bg-right bg-[length:20px] bg-[url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%234b5563\'%3e%3cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'/%3e%3c/svg%3e")] hover:border-slate-300 backdrop-blur-sm text-sm'
    : 'w-full px-4 py-3 pr-10 rounded-xl bg-slate-800/95 border-2 border-cyan-500/50 text-cyan-100 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl focus:shadow-cyan-500/30 appearance-none cursor-pointer bg-no-repeat bg-right bg-[length:20px] bg-[url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%2306b6d4\'%3e%3cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'/%3e%3c/svg%3e")] hover:border-cyan-400/70 backdrop-blur-sm text-sm';

  // Palletizer options
  const palletizerOptions = ['PL601', 'PL602', 'PL603', 'PL606', 'PL607'];
  
  // Production Version options
  const versionOptions = [
    'CKL1', 'CKL2', 'BKL1', 'BKL2', 'BWL1', 'BWL2', 
    'IWL1', 'IWL2', 'BK10', 'BW10', 'IW10', 'CK10', 
    'EB25', 'BR40', 'CM01', 'BM01', 'QRC1', 'QRW1', 
    'MM01', 'BK05', 'CK05'
  ];

  return (
    <WaterSystemLayout 
      title="Palletizer Mapping" 
      subtitle="Palletizer Configuration Management"
    >
      <style>{`
        .palletizer-add-light {
          color: white !important;
        }
        
        .palletizer-add-light span {
          color: white !important;
        }
        
        .palletizer-modal-container {
          min-height: 100vh;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding-top: 1rem;
          padding-bottom: 2rem;
        }
        
        .palletizer-modal-content {
          margin-top: 0;
          margin-bottom: auto;
        }
      `}</style>
      
      <div className="space-y-6 w-full px-4 py-6">
        {/* Notification */}
        {notification.show && (
          <div
            className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-md shadow-lg transition-all duration-500 text-sm ${
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
          Palletizer Mapping
        </h2>

        {/* Add Button and Refresh */}
        <div className="w-full flex justify-between items-center mb-4">
          <button
            onClick={fetchPalletizers}
            disabled={loading}
            className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white disabled:opacity-50 disabled:hover:scale-100 ${
              theme === 'light'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
            }`}
            style={{ color: 'white !important' }}
            title="Refresh Palletizers"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="font-semibold tracking-wide !text-white" style={{ color: 'white !important' }}>
              {loading ? 'Loading...' : 'Refresh'}
            </span>
          </button>
          
          {/* Add Palletizer button - Only visible for admin users */}
          {isAdmin && (
            <button
              onClick={() => setModalOpen(true)}
              className={`relative group flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-300 hover:scale-105 !text-white palletizer-add-light ${
                theme === 'light'
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/30 border border-cyan-400/50'
                  : 'bg-gradient-to-r from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/25'
              }`}
              style={{ color: 'white !important' }}
              title="Add New Palletizer"
            >
              <Plus className="w-4 h-4" />
              <span className="font-semibold tracking-wide !text-white palletizer-add-light" style={{ color: 'white !important' }}>
                Add Palletizer
              </span>
              <div className="absolute inset-0 rounded-md bg-gradient-to-r from-cyan-400/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="w-full flex flex-col md:flex-row gap-4 mb-4 items-center justify-between">
          <input
            type="text"
            placeholder="Search by version or palletizer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={`${filterInput} rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-opacity-50 backdrop-blur-sm border transition-all duration-300 w-full md:w-1/3 shadow-md text-sm ${
              theme === 'light' 
                ? 'focus:ring-slate-400 focus:border-slate-400' 
                : 'focus:ring-cyan-400 focus:border-cyan-400 focus:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
            }`}
          />
          <select
            value={filterVersion}
            onChange={(e) => setFilterVersion(e.target.value)}
            className={`${filterSelect} rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-opacity-50 backdrop-blur-sm border transition-all duration-300 w-full md:w-1/4 shadow-md text-sm ${
              theme === 'light' 
                ? 'focus:ring-slate-400 focus:border-slate-400' 
                : 'focus:ring-cyan-400 focus:border-cyan-400 focus:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
            }`}
          >
            <option value="">All Versions</option>
            {uniqueVersions.map((version) => (
              <option key={version} value={version}>{version}</option>
            ))}
          </select>
        </div>

        {/* Count */}
        <div className="mb-4 w-full flex justify-end pr-2">
          <span className={theme === 'light' ? 'text-slate-500 text-xs font-semibold' : 'text-cyan-300 text-xs font-semibold'}>
            Total Palletizers: {filteredPalletizers.length}
          </span>
        </div>

        {/* Loading State */}
        {loading && (
          <div className={`w-full flex justify-center items-center py-8 ${theme === 'light' ? 'text-slate-600' : 'text-cyan-300'}`}>
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current"></div>
            <span className="ml-2 text-sm">Loading palletizers...</span>
          </div>
        )}

        {/* Table */}
        {!loading && (
          <div className={`overflow-x-auto rounded-lg backdrop-blur-md shadow w-full transition-all duration-300 ${
            theme === 'light' 
              ? 'bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30' 
              : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
          }`}>
            <table className={`min-w-full text-xs text-left font-mono border-collapse border ${tableBorder} ${theme === 'light' ? 'text-black' : 'text-cyan-200'}`}>
              <thead className={`${tableHeader} uppercase text-xs tracking-wider sticky top-0 z-10`}>
                <tr>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>ID</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>Version</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>Palletizer</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>Bag Size (KG)</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>Bags Per Pallet</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>KG Per Pallet</th>
                  <th className={`px-4 py-3 border-r ${cellBorder}`}>Description</th>
                  {isAdmin && <th className={`px-4 py-3`}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredPalletizers.length === 0 ? (
                  <tr>
                    <td colSpan={isAdmin ? 8 : 7} className={`px-4 py-8 text-center text-sm border-r ${cellBorder} ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'}`}>
                      {palletizers.length === 0 ? 'No palletizers found. Add your first palletizer!' : 'No palletizers match your search criteria.'}
                    </td>
                  </tr>
                ) : (
                  filteredPalletizers.map((palletizer, idx) => (
                    <tr
                      key={palletizer.id}
                      className={`transition-all duration-200 border-b ${
                        theme === 'light' ? 'border-blue-100' : 'border-slate-700'
                      } ${idx % 2 === 0 ? tableRowEven : tableRowOdd}`}
                    >
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.id}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.version}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.palletizer}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.bag_size_kg}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.bags_per_pallet}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.kg_per_pallet}</td>
                      <td className={`px-4 py-3 border-r ${cellBorder} ${tableCellHighlight}`}>{palletizer.description || '-'}</td>
                      {isAdmin && (
                        <td className={`px-4 py-3 ${tableCellHighlight}`}>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleEditPalletizer(palletizer)}
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
                              onClick={() => handleDeletePalletizer(palletizer.id, palletizer.version, palletizer.palletizer)}
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
          <div className={`palletizer-modal-container fixed inset-0 z-[60] backdrop-blur-lg animate-in fade-in duration-300 ${
            theme === "light" 
              ? "bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30" 
              : "bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20"
          }`}>
            <div className={`palletizer-modal-content relative z-10 w-full max-w-2xl mx-4 rounded-xl shadow-2xl transform transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 max-h-[calc(100vh-4rem)] overflow-y-auto ${
              theme === "light" 
                ? "bg-white/98 border border-gray-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]" 
                : "bg-slate-800/95 border border-slate-700 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]"
            }`}>
              {/* Header */}
              <div className={`px-6 py-4 border-b sticky top-0 ${
                theme === "light" ? "bg-white/98 border-gray-200" : "bg-slate-800/95 border-slate-700"
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${
                      theme === "light" 
                        ? "bg-blue-100 text-blue-600" 
                        : "bg-blue-900/30 text-blue-400"
                    }`}>
                      <Package className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className={`text-lg font-semibold ${
                        theme === "light" ? "text-gray-900" : "text-white"
                      }`}>
                        {editingId ? 'Edit Palletizer Mapping' : 'Add Palletizer Mapping'}
                      </h3>
                      <p className={`text-sm ${
                        theme === "light" ? "text-gray-500" : "text-gray-400"
                      }`}>
                        {editingId ? 'Update palletizer specifications' : 'Configure palletizer specifications'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleCloseModal}
                    className={`p-2 rounded-full transition-all duration-200 hover:scale-110 ${
                      theme === "light" 
                        ? "hover:bg-gray-100 text-gray-500 hover:text-gray-700" 
                        : "hover:bg-slate-700/50 text-gray-400 hover:text-gray-200"
                    }`}
                    title="Close modal"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
              
              {/* Form Content */}
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Version */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Version
                    </label>
                    <select
                      value={formData.version}
                      onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                      className={selectClass}
                      required
                    >
                      <option value="">Select Version</option>
                      {versionOptions.map((version) => (
                        <option key={version} value={version} className={theme === 'light' ? 'bg-white text-slate-800' : 'bg-slate-800 text-cyan-100'}>
                          {version}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Palletizer */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Palletizer
                    </label>
                    <select
                      value={formData.palletizer}
                      onChange={(e) => setFormData({ ...formData, palletizer: e.target.value })}
                      className={selectClass}
                      required
                    >
                      <option value="">Select Palletizer</option>
                      {palletizerOptions.map((option) => (
                        <option key={option} value={option} className={theme === 'light' ? 'bg-white text-slate-800' : 'bg-slate-800 text-cyan-100'}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Bag Size (KG) */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Bag Size (KG)
                    </label>
                    <input
                      type="number"
                      value={formData.bag_size_kg || ''}
                      onChange={(e) => setFormData({ ...formData, bag_size_kg: parseFloat(e.target.value) || 0 })}
                      className={inputClass}
                      placeholder="e.g., 45"
                      min="0"
                      step="0.01"
                      required
                    />
                  </div>

                  {/* Bags Per Pallet */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Bags Per Pallet
                    </label>
                    <input
                      type="number"
                      value={formData.bags_per_pallet || ''}
                      onChange={(e) => setFormData({ ...formData, bags_per_pallet: parseInt(e.target.value) || 0 })}
                      className={inputClass}
                      placeholder="e.g., 32"
                      min="0"
                      required
                    />
                  </div>

                  {/* KG Per Pallet */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      KG Per Pallet
                    </label>
                    <input
                      type="number"
                      value={formData.kg_per_pallet || ''}
                      onChange={(e) => setFormData({ ...formData, kg_per_pallet: parseFloat(e.target.value) || 0 })}
                      className={inputClass}
                      placeholder="e.g., 1440"
                      min="0"
                      step="0.01"
                      required
                    />
                  </div>

                  {/* Description */}
                  <div className="space-y-2">
                    <label className={`block text-sm font-semibold ${
                      theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
                    }`}>
                      Description
                    </label>
                    <input
                      type="text"
                      value={formData.description || ''}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className={inputClass}
                      placeholder="Enter description (optional)"
                    />
                  </div>
                </div>

                {/* Submit Button */}
                <div className="pt-4">
                  <button
                    type="button"
                    onClick={handleAddPalletizer}
                    className={`relative group w-full px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] !text-white disabled:opacity-50 disabled:hover:scale-100 ${
                      theme === 'light'
                        ? 'bg-gradient-to-r from-cyan-500 via-blue-600 to-cyan-600 shadow-lg shadow-cyan-500/30 border border-cyan-400/50'
                        : 'bg-gradient-to-r from-cyan-500 via-blue-600 to-cyan-600 shadow-lg shadow-cyan-500/25'
                    }`}
                    style={{ color: 'white !important' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      {editingId ? <Edit className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                      <span className="font-bold tracking-wide !text-white" style={{ color: 'white !important' }}>
                        {editingId ? 'Update Palletizer Mapping' : 'Add Palletizer Mapping'}
                      </span>
                    </div>
                    <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-400/20 via-blue-500/20 to-cyan-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  </button>
                </div>
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
                  Are you sure you want to delete the palletizer mapping for:
                </p>
                <div className={`mt-3 p-3 rounded-lg ${
                  theme === "light" 
                    ? "bg-gray-100 border border-gray-200" 
                    : "bg-slate-900/50 border border-slate-700"
                }`}>
                  <p className={`font-semibold ${
                    theme === "light" ? "text-gray-900" : "text-white"
                  }`}>
                    {deleteTarget.version} - {deleteTarget.palletizer}
                  </p>
                </div>
              </div>
              
              {/* Actions */}
              <div className={`px-6 py-4 border-t flex justify-end gap-3 ${
                theme === "light" ? "border-gray-200 bg-gray-50" : "border-slate-700 bg-slate-900/30"
              }`}>
                <button
                  onClick={cancelDeletePalletizer}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 hover:scale-105 ${
                    theme === "light" 
                      ? "bg-gray-200 text-gray-700 hover:bg-gray-300" 
                      : "bg-slate-700 text-gray-300 hover:bg-slate-600"
                  }`}
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeletePalletizer}
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

export default PalletizerMapping;

