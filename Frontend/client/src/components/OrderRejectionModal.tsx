import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { X, AlertCircle, Loader2, User, Calendar, FileText } from 'lucide-react';

interface OrderRejectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: number;
  orderDetails?: {
    po_number?: string;
    material?: string;
    quantity?: number;
    unit?: string;
  };
  onReject: (rejectionData: RejectionData) => Promise<void>;
}

export interface RejectionData {
  reason: string;
  category: string;
  description: string;
  rejected_by: string;
  rejected_at: string;
  order_id: number;
  order_details: {
    po_number?: string;
    material?: string;
    quantity?: number;
    unit?: string;
  };
}

const OrderRejectionModal: React.FC<OrderRejectionModalProps> = ({
  isOpen,
  onClose,
  orderId,
  orderDetails,
  onReject,
}) => {
  const { theme } = useTheme();
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedReason, setSelectedReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [description, setDescription] = useState('');
  const [rejectedBy, setRejectedBy] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Predefined rejection categories and reasons
  const rejectionCategories = {
    'Quantity Issues': [
      'Target vs. Actual Quantity mismatch (beyond tolerance)',
      'Overproduction (exceeded SAP order qty)',
      'Underproduction (not meeting SAP order qty)'
    ],
    'Material Issues': [
      'Wrong material consumed',
      'Wrong batch used',
      'Material substitution not approved'
    ],
    'Recipe / Process Issues': [
      'Incorrect recipe version used',
      'Missing ingredients/components',
      'Process deviation outside limits'
    ],
    'Equipment / Scale Issues': [
      'Faulty scale readings',
      'Equipment malfunction / breakdown',
      'Data transmission error from SCADA'
    ],
    'Documentation / SAP Sync Issues': [
      'SAP order data mismatch',
      'Missing or duplicate PO',
      'Invalid order (cancelled/closed in SAP)'
    ],
    'Quality / Compliance Issues': [
      'Quality test failed (lab check)',
      'Safety/Regulatory non-compliance',
      'Contamination risk detected'
    ],
    'Operational Issues': [
      'Operator error / manual intervention mistake',
      'Line stoppage / unexpected downtime',
      'Order partially completed (remaining pending next shift)'
    ],
    'Other': [
      'Custom reason'
    ]
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedCategory || (!selectedReason && !customReason) || !description || !rejectedBy) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const rejectionData: RejectionData = {
        reason: customReason || selectedReason,
        category: selectedCategory,
        description: description,
        rejected_by: rejectedBy,
        rejected_at: new Date().toISOString(),
        order_id: orderId,
        order_details: orderDetails || {}
      };

      await onReject(rejectionData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rejection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setSelectedReason('');
    setCustomReason('');
  };

  const handleReasonChange = (reason: string) => {
    setSelectedReason(reason);
    setCustomReason('');
  };

  const resetForm = () => {
    setSelectedCategory('');
    setSelectedReason('');
    setCustomReason('');
    setDescription('');
    setRejectedBy('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-8">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className={`relative w-full max-w-3xl max-h-[80vh] rounded-lg backdrop-blur-md border transition-all duration-300 overflow-y-auto ${
        theme === 'light' 
          ? 'bg-white border-slate-200 shadow-2xl' 
          : 'bg-slate-900/95 border-cyan-400/30 shadow-[0_0_40px_rgba(0,255,255,0.2)]'
      }`}>
        
        {/* Header */}
        <div className={`flex items-center justify-between p-4 border-b ${
          theme === 'light' ? 'border-slate-200' : 'border-slate-700'
        }`}>
          <div>
            <h2 className={`text-lg font-bold ${
              theme === 'light' ? 'text-slate-800' : 'text-cyan-400'
            }`}>
              Reject Order: {orderId}
            </h2>
            {orderDetails?.po_number && (
              <p className={`text-xs mt-1 ${
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              }`}>
                PO: {orderDetails.po_number} | Material: {orderDetails.material} | Qty: {orderDetails.quantity} {orderDetails.unit}
              </p>
            )}
          </div>
          <button
            onClick={handleClose}
            className={`p-2 rounded-lg transition-colors ${
              theme === 'light' 
                ? 'hover:bg-slate-100 text-slate-600' 
                : 'hover:bg-slate-800 text-slate-400'
            }`}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 max-h-[calc(80vh-100px)] overflow-y-auto">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Rejection Category */}
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              }`}>
                Rejection Category *
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.keys(rejectionCategories).map((category) => (
                  <button
                    key={category}
                    type="button"
                    onClick={() => handleCategoryChange(category)}
                    className={`p-2 rounded-md border-2 transition-all duration-300 text-left ${
                      selectedCategory === category
                        ? theme === 'light'
                          ? 'border-red-500 bg-red-50 text-red-700'
                          : 'border-red-400 bg-red-900/20 text-red-300'
                        : theme === 'light'
                          ? 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                          : 'border-slate-600 bg-slate-800 hover:border-slate-500 text-slate-300'
                    }`}
                  >
                    <div className="font-medium text-xs">{category}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Rejection Reason */}
            {selectedCategory && (
              <div>
                <label className={`block text-sm font-medium mb-2 ${
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Rejection Reason *
                </label>
                {selectedCategory === 'Other' ? (
                  <input
                    type="text"
                    value={customReason}
                    onChange={(e) => setCustomReason(e.target.value)}
                    placeholder="Enter custom rejection reason..."
                    className={`w-full px-3 py-2 rounded-md border transition-all duration-300 ${
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-800 focus:border-red-500 focus:ring-red-500'
                        : 'bg-slate-800 border-slate-600 text-white focus:border-red-400 focus:ring-red-400'
                    }`}
                    required
                  />
                ) : (
                  <div className="space-y-2">
                    {rejectionCategories[selectedCategory as keyof typeof rejectionCategories].map((reason) => (
                      <button
                        key={reason}
                        type="button"
                        onClick={() => handleReasonChange(reason)}
                        className={`w-full p-2 rounded-md border-2 transition-all duration-300 text-left ${
                          selectedReason === reason
                            ? theme === 'light'
                              ? 'border-red-500 bg-red-50 text-red-700'
                              : 'border-red-400 bg-red-900/20 text-red-300'
                            : theme === 'light'
                              ? 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                              : 'border-slate-600 bg-slate-800 hover:border-slate-500 text-slate-300'
                        }`}
                      >
                        {reason}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Detailed Description */}
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              }`}>
                Detailed Description *
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide detailed explanation of the rejection reason..."
                rows={3}
                className={`w-full px-3 py-2 rounded-md border transition-all duration-300 resize-none ${
                  theme === 'light'
                    ? 'bg-white border-slate-300 text-slate-800 focus:border-red-500 focus:ring-red-500'
                    : 'bg-slate-800 border-slate-600 text-white focus:border-red-400 focus:ring-red-400'
                }`}
                required
              />
            </div>

            {/* Rejected By */}
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              }`}>
                Rejected By *
              </label>
              <div className="relative">
                <User className={`absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 ${
                  theme === 'light' ? 'text-slate-400' : 'text-slate-500'
                }`} />
                <input
                  type="text"
                  value={rejectedBy}
                  onChange={(e) => setRejectedBy(e.target.value)}
                  placeholder="Enter your name or ID..."
                  className={`w-full pl-10 pr-3 py-2 rounded-md border transition-all duration-300 ${
                    theme === 'light'
                      ? 'bg-white border-slate-300 text-slate-800 focus:border-red-500 focus:ring-red-500'
                      : 'bg-slate-800 border-slate-600 text-white focus:border-red-400 focus:ring-red-400'
                  }`}
                  required
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className={`p-4 rounded-lg border ${
                theme === 'light' 
                  ? 'bg-red-50 border-red-200 text-red-800' 
                  : 'bg-red-900/20 border-red-400/30 text-red-300'
              }`}>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">{error}</span>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={handleClose}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  theme === 'light'
                    ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className={`px-4 py-1.5 rounded-md font-medium transition-all duration-300 ${
                  loading
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:scale-105'
                } ${
                  theme === 'light'
                    ? 'bg-red-600 text-white hover:bg-red-700 shadow-lg'
                    : 'bg-red-500 text-white hover:bg-red-400 shadow-[0_4px_16px_rgba(239,68,68,0.3)]'
                }`}
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Rejecting...
                  </div>
                ) : (
                  'Reject Order'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OrderRejectionModal;
