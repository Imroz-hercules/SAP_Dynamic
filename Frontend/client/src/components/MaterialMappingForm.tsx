import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { getApiUrl, API_BASE_URL, apiFetch } from '../lib/apiConfig';
import { classificationApi, type ClassificationRule } from '../lib/api';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 MaterialMappingForm.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

interface MaterialMapping {
  material: string;
  version: string;
  scale: string;
  recipe?: string; // Made optional since we're hiding this field
  packingLine: string;
}

interface MaterialMappingFormProps {
  onAdd: (mapping: MaterialMapping) => void;
}

const MaterialMappingForm: React.FC<MaterialMappingFormProps> = ({ onAdd }) => {
  const [mapping, setMapping] = useState<MaterialMapping>({
    material: '',
    version: '',
    scale: '',
    recipe: '', // Will be set automatically based on material code
    packingLine: '',
  });
  const [scaleOptions, setScaleOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const { theme } = useTheme();

  // ✅ DYNAMIC: Version options fetched from API instead of hardcoded
  const [millingVersions, setMillingVersions] = useState<string[]>([]);
  const [packingVersions, setPackingVersions] = useState<string[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(true);
  
  // A6: packing lines come from the mappings that actually exist. The list
  // used to be hardcoded and offered PL604 and PL605, which have no row in
  // palletizer_mapping - an order on either would never have tracked.
  const [packingLineOptions, setPackingLineOptions] = useState<string[]>([]);

  // A6: classification rules, so this form routes a material the same way the
  // backend does. See getMaterialType below.
  const [prefixRules, setPrefixRules] = useState<ClassificationRule[]>([]);
  
  // ✅ Fetch versions from API on component mount
  useEffect(() => {
    const fetchVersions = async () => {
      setVersionsLoading(true);
      try {
        // Fetch milling versions from API
        const millingResponse = await apiFetch(getApiUrl('/api/milling-mapping'));
        if (millingResponse.ok) {
          const millingData = await millingResponse.json();
          const millingVersionList = millingData.map((m: { version: string }) => m.version).sort();
          setMillingVersions(millingVersionList);
          console.log('✅ Loaded milling versions from API:', millingVersionList);
        } else {
          // A6: was a hardcoded list that still included BRF1, which A4 retired
          // — it has no milling_version_mappings row, so an order on it fails
          // classification. Showing versions that do not exist invites exactly
          // that. Empty is honest.
          console.warn('⚠️ Failed to fetch milling versions');
          setMillingVersions([]);
        }
        
        // Fetch packing versions from API
        const packingResponse = await apiFetch(getApiUrl('/api/orders/palletizer-mapping'));
        if (packingResponse.ok) {
          const packingData = await packingResponse.json();
          const packingVersionList = packingData.map((p: { version: string }) => p.version).sort();
          setPackingVersions(packingVersionList);
          // A6: the lines that actually have a mapping.
          setPackingLineOptions(
            Array.from(new Set(
              packingData.map((p: { palletizer: string }) => p.palletizer).filter(Boolean),
            )).sort() as string[],
          );
          console.log('✅ Loaded packing versions from API:', packingVersionList);
        } else {
          console.warn('⚠️ Failed to fetch packing versions');
          setPackingVersions([]);
        }
      } catch (error) {
        console.error('❌ Error fetching versions:', error);
        setMillingVersions([]);
        setPackingVersions([]);
      } finally {
        setVersionsLoading(false);
      }
    };
    
    fetchVersions();
  }, []);

  // A6: load the classification rules once, so getMaterialType can resolve a
  // material the same way the backend does without a request per keystroke.
  useEffect(() => {
    classificationApi
      .getRules('material_prefix')
      .then((rules) =>
        setPrefixRules(
          rules
            .filter((r) => r.is_active)
            .sort(
              (a, b) =>
                a.priority - b.priority ||
                Number(a.match_value === '*') - Number(b.match_value === '*') ||
                a.match_value.localeCompare(b.match_value),
            ),
        ),
      )
      .catch((err) => console.warn('⚠️ Could not load classification rules:', err));
  }, []);

  // Helper function to determine material type from code.
  //
  // A6: this used to be `materialCode.includes('13')` - a SUBSTRING test, and
  // checked first, so a packing material that happened to contain "13"
  // anywhere (000000000014130001, say) was shown the MILLING version list.
  // Same bug A1 fixed in material_routes.py on the backend.
  //
  // Now resolved against classification_rules, matching the backend exactly:
  // prefix of the zero-stripped code, lowest priority first, '*' last.
  const getMaterialType = (materialCode: string): 'milling' | 'packing' | null => {
    if (materialCode.length !== 18) return null;

    const stripped = materialCode.replace(/^0+/, '');
    if (stripped.length < 2) return null;

    for (const rule of prefixRules) {
      if (rule.match_value === '*' || stripped.startsWith(rule.match_value)) {
        return rule.result_value === 'MILLING' ? 'milling' : 'packing';
      }
    }
    return null;
  };

  // Get available versions based on material type
  const getAvailableVersions = (materialCode: string): string[] => {
    const materialType = getMaterialType(materialCode);
    if (materialType === 'milling') return millingVersions;
    if (materialType === 'packing') return packingVersions;
    return [];
  };

  // Validate material code format
  const validateMaterialCode = (code: string): boolean => {
    // Must be exactly 18 digits
    return /^\d{18}$/.test(code);
  };

  // Fetch existing data for dropdowns
  useEffect(() => {
    const fetchDropdownData = async () => {
      try {
        setLoading(true);
        const response = await apiFetch(getApiUrl('/api/materials'), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Extract unique values from existing data
        const uniqueScales = Array.from(new Set(data.map((item: any) => item.scale).filter(Boolean))) as string[];

        // A6: the fallback here used to offer 'Small Scale', 'Medium Scale',
        // 'Large Scale'… — placeholder strings, not SCADA tags. Since A7 that is
        // no longer merely useless: a mapping saved with one of those names has
        // no baseline column, so every order on that version now HALTS. An
        // empty list and a visible message is the correct failure.
        setScaleOptions(uniqueScales);
      } catch (error) {
        console.error('Error fetching dropdown data:', error);
        setScaleOptions([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDropdownData();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate material code format
    if (!validateMaterialCode(mapping.material)) {
      alert('Material code must be exactly 18 digits (e.g., 000000000001400000)');
      return;
    }
    
    // Check if all required fields are filled
    const materialType = getMaterialType(mapping.material);
    const isPackingMaterial = materialType === 'packing';
    const hasRequiredFields = mapping.material && mapping.version && mapping.scale && 
                             (!isPackingMaterial || mapping.packingLine);
    
    if (hasRequiredFields) {
      // Automatically set recipe based on material type
      const recipeValue = materialType === 'milling' ? 'Milling Recipe' : 
                         materialType === 'packing' ? 'Packing Recipe' : 'Default Recipe';
      
      // For milling materials, set a default packing line or leave empty
      const finalPackingLine = isPackingMaterial ? mapping.packingLine : 'N/A';
      
      const finalMapping = { 
        ...mapping, 
        recipe: recipeValue,
        packingLine: finalPackingLine
      };
      onAdd(finalMapping);
      setMapping({ material: '', version: '', scale: '', recipe: '', packingLine: '' });
    }
  };

  const inputClass = theme === 'light'
    ? 'w-full px-4 py-3 rounded-xl bg-white/95 border-2 border-slate-200 text-slate-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl backdrop-blur-sm text-sm'
    : 'w-full px-4 py-3 rounded-xl bg-slate-800/95 border-2 border-cyan-500/50 text-cyan-100 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl focus:shadow-cyan-500/30 backdrop-blur-sm text-sm';

  const selectClass = theme === 'light'
    ? 'w-full px-4 py-3 pr-10 rounded-xl bg-white/95 border-2 border-slate-200 text-slate-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl appearance-none cursor-pointer bg-no-repeat bg-right bg-[length:20px] bg-[url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%234b5563\'%3e%3cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'/%3e%3c/svg%3e")] hover:border-slate-300 backdrop-blur-sm text-sm'
    : 'w-full px-4 py-3 pr-10 rounded-xl bg-slate-800/95 border-2 border-cyan-500/50 text-cyan-100 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 transition-all duration-300 shadow-lg hover:shadow-xl focus:shadow-xl focus:shadow-cyan-500/30 appearance-none cursor-pointer bg-no-repeat bg-right bg-[length:20px] bg-[url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%2306b6d4\'%3e%3cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'/%3e%3c/svg%3e")] hover:border-cyan-400/70 backdrop-blur-sm text-sm';

  return (
    <>
      <style>{`
        /* Force white text for form submit button in light mode */
        .material-form-submit-light {
          color: white !important;
        }
        
        .material-form-submit-light span {
          color: white !important;
        }
        
        /* Modern glassmorphism effect */
        .glass-card {
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
        }
        
        /* Enhanced focus states */
        .modern-input:focus {
          transform: translateY(-1px);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .modern-select:focus {
          transform: translateY(-1px);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        /* Completely hide all scrollbars */
        .material-form-container * {
          scrollbar-width: none !important; /* Firefox */
          -ms-overflow-style: none !important; /* Internet Explorer 10+ */
        }
        
        .material-form-container *::-webkit-scrollbar {
          display: none !important; /* WebKit */
        }
        
        .glass-card {
          overflow: hidden !important;
        }
        
        /* Hide scrollbars for the entire form */
        .material-form-container {
          overflow: hidden !important;
        }
        
        /* Custom scrollbar for dropdowns only */
        select::-webkit-scrollbar {
          width: 6px;
        }
        select::-webkit-scrollbar-track {
          background: ${theme === 'light' ? '#f1f5f9' : '#1e293b'};
          border-radius: 3px;
        }
        select::-webkit-scrollbar-thumb {
          background: ${theme === 'light' ? '#cbd5e1' : '#475569'};
          border-radius: 3px;
        }
        select::-webkit-scrollbar-thumb:hover {
          background: ${theme === 'light' ? '#94a3b8' : '#64748b'};
        }
      `}</style>
      
      <div className={`material-form-container relative overflow-hidden rounded-2xl glass-card border transition-all duration-500 ${
        theme === 'light' 
          ? 'bg-gradient-to-br from-white/95 via-blue-50/90 to-white/95 border-blue-200/60 shadow-2xl shadow-blue-500/10' 
          : 'bg-gradient-to-br from-slate-800/95 via-slate-900/90 to-slate-800/95 border-cyan-500/40 shadow-2xl shadow-cyan-500/20'
      }`}>
        {/* Animated background pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent transform -skew-x-12 animate-pulse"></div>
        </div>
        
        <form onSubmit={handleSubmit} className="relative p-6 space-y-6">
          {/* Header Section */}
          <div className="text-center space-y-2">
            <h3 className={`text-2xl font-bold tracking-tight ${
              theme === 'light' ? 'text-slate-800' : 'text-white'
            }`}>
              Add Material Mapping
            </h3>
            <p className={`text-sm ${
              theme === 'light' ? 'text-slate-600' : 'text-slate-300'
            }`}>
              Configure material specifications and line assignments
            </p>
          </div>

          {/* 2x2 Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Material Code Field */}
            <div className="space-y-2">
              <label className={`block text-sm font-semibold ${
                theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
              }`}>
                Material Code
              </label>
              <input
                type="text"
                value={mapping.material}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, ''); // Only allow digits
                  if (value.length <= 18) {
                    setMapping({ ...mapping, material: value, version: '' }); // Reset version when material changes
                  }
                }}
                className={`${inputClass} modern-input`}
                placeholder="000000000001400000"
                required
                maxLength={18}
              />
              {mapping.material && !validateMaterialCode(mapping.material) && (
                <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 bg-red-500 rounded-full"></span>
                  Material code must be exactly 18 digits
                </p>
              )}
              {mapping.material && validateMaterialCode(mapping.material) && (
                <p className={`text-xs mt-1 flex items-center gap-1 ${
                  getMaterialType(mapping.material) === 'milling' ? 'text-blue-600' : 
                  getMaterialType(mapping.material) === 'packing' ? 'text-green-600' : 'text-gray-600'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    getMaterialType(mapping.material) === 'milling' ? 'bg-blue-500' : 
                    getMaterialType(mapping.material) === 'packing' ? 'bg-green-500' : 'bg-gray-500'
                  }`}></span>
                  Type: {getMaterialType(mapping.material) || 'Unknown'}
                </p>
              )}
            </div>

            {/* Version Field */}
            <div className="space-y-2">
              <label className={`block text-sm font-semibold ${
                theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
              }`}>
                Version
              </label>
              <select
                value={mapping.version}
                onChange={(e) => setMapping({ ...mapping, version: e.target.value })}
                className={`${selectClass} modern-select`}
                required
                disabled={!mapping.material || !validateMaterialCode(mapping.material) || versionsLoading}
              >
                <option value="">
                  {versionsLoading ? 'Loading versions...' :
                   !mapping.material ? 'Enter material code first' : 
                   !validateMaterialCode(mapping.material) ? 'Invalid material code' :
                   getAvailableVersions(mapping.material).length === 0 ? 'No versions configured - add via Version Mapping' :
                   'Select Version'}
                </option>
                {getAvailableVersions(mapping.material).map((version) => (
                  <option key={version} value={version} className={theme === 'light' ? 'bg-white text-slate-800' : 'bg-slate-800 text-cyan-100'}>
                    {version}
                  </option>
                ))}
              </select>
              {mapping.material && validateMaterialCode(mapping.material) && getAvailableVersions(mapping.material).length > 0 && (
                <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 bg-slate-400 rounded-full"></span>
                  Available versions for {getMaterialType(mapping.material)}: {getAvailableVersions(mapping.material).length} (from database)
                </p>
              )}
              {mapping.material && validateMaterialCode(mapping.material) && getAvailableVersions(mapping.material).length === 0 && !versionsLoading && (
                <p className="text-xs text-orange-600 mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 bg-orange-500 rounded-full"></span>
                  No versions found. Add versions via {getMaterialType(mapping.material) === 'milling' ? 'Milling Version Mapping' : 'Palletizer Mapping'} page.
                </p>
              )}
            </div>

            {/* Scale Field */}
            <div className="space-y-2">
              <label className={`block text-sm font-semibold ${
                theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
              }`}>
                Scale
              </label>
              <select
                value={mapping.scale}
                onChange={(e) => setMapping({ ...mapping, scale: e.target.value })}
                className={`${selectClass} modern-select`}
                required
                disabled={loading}
              >
                <option value="">
                  {loading ? 'Loading scales...' : 'Select Scale'}
                </option>
                {scaleOptions.map((option) => (
                  <option key={option} value={option} className={theme === 'light' ? 'bg-white text-slate-800' : 'bg-slate-800 text-cyan-100'}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            {/* Packing Line Field */}
            <div className="space-y-2">
              <label className={`block text-sm font-semibold ${
                theme === 'light' ? 'text-slate-700' : 'text-cyan-300'
              }`}>
                Packing Line
              </label>
              <select
                value={mapping.packingLine}
                onChange={(e) => setMapping({ ...mapping, packingLine: e.target.value })}
                className={`${selectClass} modern-select`}
                required
                disabled={loading || !mapping.material || !validateMaterialCode(mapping.material) || getMaterialType(mapping.material) !== 'packing'}
              >
                <option value="">
                  {!mapping.material ? 'Enter material code first' : 
                   !validateMaterialCode(mapping.material) ? 'Invalid material code' :
                   getMaterialType(mapping.material) !== 'packing' ? 'Only available for packing materials' :
                   loading ? 'Loading packing lines...' : 'Select Packing Line'}
                </option>
                {getMaterialType(mapping.material) === 'packing' && packingLineOptions.map((option) => (
                  <option key={option} value={option} className={theme === 'light' ? 'bg-white text-slate-800' : 'bg-slate-800 text-cyan-100'}>
                    {option}
                  </option>
                ))}
              </select>
              {mapping.material && validateMaterialCode(mapping.material) && getMaterialType(mapping.material) === 'packing' && (
                <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 bg-green-500 rounded-full"></span>
                  Available packing lines: {packingLineOptions.length}
                </p>
              )}
              {mapping.material && validateMaterialCode(mapping.material) && getMaterialType(mapping.material) === 'milling' && (
                <p className="text-xs text-orange-600 mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 bg-orange-500 rounded-full"></span>
                  Packing lines are not available for milling materials
                </p>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className={`relative group w-full px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] !text-white material-form-submit-light disabled:opacity-50 disabled:hover:scale-100 ${
                theme === 'light'
                  ? 'bg-gradient-to-r from-cyan-500 via-blue-600 to-cyan-600 shadow-lg shadow-cyan-500/30 border border-cyan-400/50'
                  : 'bg-gradient-to-r from-cyan-500 via-blue-600 to-cyan-600 shadow-lg shadow-cyan-500/25'
              }`}
              style={{ color: 'white !important' }}
              title="Add New Material"
            >
              <div className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                <span className="font-bold tracking-wide !text-white material-form-submit-light" style={{ color: 'white !important' }}>
                  {loading ? 'Processing...' : 'Add Material Mapping'}
                </span>
              </div>
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-400/20 via-blue-500/20 to-cyan-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
          </div>
        </form>
      </div>
    </>
  );
};

export default MaterialMappingForm;