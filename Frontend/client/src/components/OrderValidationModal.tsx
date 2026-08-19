import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ValidationRequest, ValidationResult } from '../lib/api';
import { X } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  orderId: number;
  defaults?: Partial<ValidationRequest>;
  onValidate: (data: ValidationRequest) => Promise<ValidationResult>;
  validationResult?: ValidationResult | null;
}

const emptyLine = { material_code: '', gross_qty: 0, tare_qty: 0, uom: 'KG' as const };

const OrderValidationModal: React.FC<Props> = ({ isOpen, onClose, orderId, defaults, onValidate, validationResult }) => {
  const { theme } = useTheme();
  const [poNumber, setPoNumber] = useState(defaults?.po_number || '');
  const [tolerance, setTolerance] = useState<number>(defaults?.tolerance_pct ?? 0.5);
  const [autoConfirm, setAutoConfirm] = useState<boolean>(false);
  const [rows, setRows] = useState(() => {
    if (defaults?.receipts?.length) {
      return defaults.receipts;
    }
    // Pre-populate with material code if available
    if (defaults?.material_code) {
      return [{ ...emptyLine, material_code: defaults.material_code }];
    }
    return [emptyLine];
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expectedQuantity, setExpectedQuantity] = useState<number>(0);
  const [confirmedQuantity, setConfirmedQuantity] = useState<number>(0);
  const [scaleQuantity, setScaleQuantity] = useState<number>(0);
  const [unit, setUnit] = useState<string>('KG');
  const [autoValidationStatus, setAutoValidationStatus] = useState<'pending' | 'valid' | 'invalid' | 'auto-validating'>('pending');
  const autoValidationInProgress = useRef(false);
  const [confirmedText, setConfirmedText] = useState<string>('');
  const [scrap, setScrap] = useState<number>(0);
  const [matchedWeight, setMatchedWeight] = useState<number>(0);
  const [expectedWeight, setExpectedWeight] = useState<number>(0);
  const [manualValidationEnabled, setManualValidationEnabled] = useState<boolean>(false);
  const [allowPartialConfirmation, setAllowPartialConfirmation] = useState<boolean>(false);
  const [partialConfirmedQty, setPartialConfirmedQty] = useState<number>(0);

  useEffect(() => {
    if (defaults) {
setPoNumber(defaults.po_number || '');
      setTolerance(defaults.tolerance_pct ?? 0.5);
      setExpectedQuantity((defaults as any).expected_quantity || 0);
      setConfirmedQuantity((defaults as any).confirmed_quantity || 0);
      setScaleQuantity((defaults as any).scale_quantity || 0);
      setUnit((defaults as any).unit || 'KG');
      setConfirmedText((defaults as any).confirmed_text || '');
      setScrap((defaults as any).scrap || 0);
      const expectedWeightValue = (defaults as any).expected_weight || 0;
      setExpectedWeight(expectedWeightValue);
console.log("📊 Modal scale data:", {
        expectedQuantity: (defaults as any).expected_quantity || 0,
        expectedWeight: (defaults as any).expected_weight || 0,
        scaleQuantity: (defaults as any).scale_quantity || 0,
        confirmedQuantity: (defaults as any).confirmed_quantity || 0,
        unit: (defaults as any).unit || 'KG'
      });
      
      if (defaults.receipts?.length) {
        setRows(defaults.receipts);
      } else if (defaults.material_code) {
        setRows([{ ...emptyLine, material_code: defaults.material_code, uom: (defaults as any).unit || 'KG' }]);
      } else {
        setRows([{ ...emptyLine, uom: (defaults as any).unit || 'KG' }]);
      }
    }
  }, [defaults]);

  // Calculate validation status function - moved before useEffect to avoid initialization error
  const calculateValidationStatus = () => {
    // Use scale quantity if available, otherwise fallback to confirmed quantity
    const actualQty = scaleQuantity > 0 ? scaleQuantity : confirmedQuantity;
    const difference = Math.abs(actualQty - expectedQuantity);
    const toleranceAmount = expectedQuantity * (tolerance / 100);
    const isValid = difference <= toleranceAmount && actualQty > 0;
return {
      difference,
      isValid,
      toleranceAmount,
      actualQty
    };
  };

  // Calculate manual validation status
  const calculateManualValidationStatus = () => {
    if (matchedWeight <= 0 || expectedWeight <= 0) {
      return {
        isValid: false,
        difference: 0,
        toleranceAmount: 0,
        withinTolerance: false
      };
    }

    const difference = Math.abs(matchedWeight - expectedWeight);
    const toleranceAmount = expectedWeight * (tolerance / 100);
    const withinTolerance = difference <= toleranceAmount;
return {
      isValid: withinTolerance,
      difference,
      toleranceAmount,
      withinTolerance
    };
  };

  // Single effect for auto-validation - simplified to avoid hooks issues
  useEffect(() => {
    const { isValid, actualQty } = calculateValidationStatus();
    
    // Update status based on validation
    if (isValid && expectedQuantity > 0 && actualQty > 0) {
      setAutoValidationStatus('valid');
    } else if (expectedQuantity > 0 && actualQty > 0) {
      setAutoValidationStatus('invalid');
    } else {
      setAutoValidationStatus('pending');
    }

    // Handle auto-validation trigger
    if (autoConfirm && isValid && expectedQuantity > 0 && !submitting && !autoValidationInProgress.current) {
      setAutoValidationStatus('auto-validating');
      autoValidationInProgress.current = true;
      
      // Auto-submit validation after a short delay
      const timer = setTimeout(async () => {
        if (autoConfirm && isValid && !submitting) {
          // Inline the submit logic to avoid function reference issues
          setError(null);
          setResult(null);
          if (!poNumber.trim()) { setError('PO number is required.'); return; }
          const payload: ValidationRequest = {
            po_number: poNumber.trim(),
            tolerance_pct: Number.isFinite(tolerance) ? tolerance : 0.5,
            auto_confirm: !!autoConfirm,
            receipts: [], // Backend handles all calculations
            confirmed_text: confirmedText.trim() || undefined,
            scrap: scrap > 0 ? scrap : undefined
          };

          try {
            setSubmitting(true);
            const res = await onValidate(payload);
            setResult(res);
          } catch (e: any) {
            setError(e?.message || 'Validation failed.');
          } finally {
            setSubmitting(false);
          }
        }
        autoValidationInProgress.current = false;
      }, 2000);
      
      return () => {
        clearTimeout(timer);
        autoValidationInProgress.current = false;
      };
    }
  }, [expectedQuantity, confirmedQuantity, scaleQuantity, tolerance, autoConfirm, submitting, poNumber, rows, onValidate]);

  // Monitor matched weight for manual validation
  useEffect(() => {
    const manualStatus = calculateManualValidationStatus();
    setManualValidationEnabled(manualStatus.isValid);
  }, [matchedWeight, expectedWeight, tolerance]);

  if (!isOpen) return null;

  const addRow = () => setRows([...rows, { ...emptyLine, uom: unit }]);
  const removeRow = (i: number) => setRows(rows.filter((_, idx) => idx !== i));
  const updateRow = (i: number, key: 'material_code'|'gross_qty'|'tare_qty'|'uom', val: any) => {
    const next = [...rows];
    (next[i] as any)[key] = key === 'gross_qty' || key === 'tare_qty' ? Number(val) : val;
    setRows(next);
  };

  const submit = async () => {
    setError(null);
    setResult(null);
    if (!poNumber.trim()) { setError('PO number is required.'); return; }
    
    // Check if manual validation is being used
    const isManualValidation = matchedWeight > 0;
    const manualStatus = isManualValidation ? calculateManualValidationStatus() : null;
    
    // Check if partial confirmation is being used
    const isPartialConfirmation = allowPartialConfirmation && partialConfirmedQty > 0;
    
    if (isManualValidation && !manualStatus?.isValid) {
      setError('Matched weight is outside tolerance range. Please adjust the weight or tolerance.');
      return;
    }
    
    if (isPartialConfirmation && partialConfirmedQty > expectedQuantity) {
      setError('Partial confirmed quantity cannot exceed expected quantity.');
      return;
    }
    
    // Simplified payload - backend handles all calculations
    const payload: ValidationRequest = {
      po_number: poNumber.trim(),
      tolerance_pct: Number.isFinite(tolerance) ? tolerance : 0.5,
      auto_confirm: !!autoConfirm,
      receipts: [], // Backend doesn't need receipts anymore
      confirmed_text: confirmedText.trim() || undefined,
      scrap: scrap > 0 ? scrap : undefined,
      // Add manual validation data
      ...(isManualValidation && {
        manual_weight: matchedWeight,
        expected_weight: expectedWeight,
        validation_type: 'manual'
      }),
      // Add partial confirmation data
      ...(isPartialConfirmation && {
        confirmed_qty: partialConfirmedQty,
        validation_type: 'partial'
      })
    };

    try {
      setSubmitting(true);
      const res = await onValidate(payload);
      setResult(res);
    } catch (e: any) {
      setError(e?.message || 'Validation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const card = theme === 'light'
    ? 'bg-white border border-slate-300 shadow-2xl'
    : 'bg-slate-900/95 border border-cyan-500/50 shadow-2xl shadow-cyan-500/20';

  const headerBorder = theme === 'light'
    ? 'border-slate-200'
    : 'border-slate-700';

  const inputClass = theme === 'light'
    ? 'w-full px-2 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all'
    : 'w-full px-2 py-1.5 rounded-lg border border-slate-600 bg-slate-800/50 text-white focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all';

  const labelClass = theme === 'light'
    ? 'block text-sm font-semibold mb-1 text-slate-700'
    : 'block text-sm font-semibold mb-1 text-slate-300';

  const tableHeaderClass = theme === 'light'
    ? 'px-3 py-2 bg-slate-50 text-slate-700 font-semibold'
    : 'px-3 py-2 bg-slate-800/50 text-slate-300 font-semibold';

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}>
      <div className={`w-full max-w-3xl max-h-[85vh] rounded-xl ${card} flex flex-col overflow-hidden shadow-2xl`}>
        <div className={`flex items-center justify-between p-3 border-b ${headerBorder}`}>
          <h3 className={`text-xl font-bold ${theme === 'light' ? 'text-slate-800' : 'text-white'}`}>
            Validate Order #{orderId}
          </h3>
          <button 
            onClick={onClose} 
            className={`p-2 rounded-lg transition-colors ${
              theme === 'light' 
                ? 'hover:bg-slate-100 text-slate-600 hover:text-slate-800' 
                : 'hover:bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-3 space-y-2 flex-1 overflow-y-auto">
          {error && (
            <div className={`p-4 rounded-lg border ${
              theme === 'light'
                ? 'bg-red-50 text-red-700 border-red-200'
                : 'bg-red-500/10 text-red-300 border-red-500/30'
            }`}>
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className={labelClass}>PO Number</label>
              <input 
                value={poNumber} 
                readOnly
                className={`${inputClass} text-sm ${
                  theme === 'light' 
                    ? 'bg-slate-100 text-slate-600 cursor-not-allowed border-slate-200' 
                    : 'bg-slate-800/50 text-slate-400 cursor-not-allowed border-slate-600'
                }`} 
                placeholder="4500003155" 
                title="PO Number is pre-filled from the order"
              />
            </div>
            <div>
              <label className={labelClass}>Tolerance (%)</label>
              <input 
                type="number" 
                step="0.01" 
                value={tolerance}
                onChange={e => setTolerance(Number(e.target.value))}
                className={`${inputClass} text-sm`} 
              />
            </div>
            <div className="flex items-end">
              <div className="flex flex-col gap-2">
                <label className={`inline-flex items-center gap-2 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
                  <input 
                    type="checkbox" 
                    checked={autoConfirm} 
                    onChange={e => setAutoConfirm(e.target.checked)}
                    className="rounded"
                  />
                  Auto confirm if valid
                </label>
                {autoConfirm && (
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    autoValidationStatus === 'auto-validating'
                      ? theme === 'light' ? 'bg-blue-100 text-blue-700' : 'bg-blue-900/30 text-blue-300'
                      : autoValidationStatus === 'valid'
                      ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                      : autoValidationStatus === 'invalid'
                      ? theme === 'light' ? 'bg-red-100 text-red-700' : 'bg-red-900/30 text-red-300'
                      : theme === 'light' ? 'bg-gray-100 text-gray-700' : 'bg-gray-900/30 text-gray-300'
                  }`}>
                    {autoValidationStatus === 'auto-validating' ? '⏳ Auto-validating...' :
                     autoValidationStatus === 'valid' ? '✅ Ready to auto-validate' :
                     autoValidationStatus === 'invalid' ? '❌ Cannot auto-validate' : '⏸️ Waiting for data'}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SAP Order Information */}
          <div className={`p-3 rounded-lg border ${
            theme === 'light' 
              ? 'bg-slate-50 border-slate-200' 
              : 'bg-slate-800/20 border-slate-600'
          }`}>
            <h4 className={`font-semibold text-sm mb-2 ${theme === 'light' ? 'text-slate-800' : 'text-slate-300'}`}>
              📋 SAP Order Information
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div>
                <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                  Expected Quantity:
                </span>
                <div className={`font-mono font-bold ${theme === 'light' ? 'text-slate-900' : 'text-slate-200'}`}>
                  {expectedQuantity} {unit}
                </div>
              </div>
              <div>
                <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                  Expected Weight:
                </span>
                <div className={`font-mono font-bold ${theme === 'light' ? 'text-blue-700' : 'text-blue-300'}`}>
                  {expectedWeight} {unit}
                </div>
              </div>
              <div>
                <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                  Material Code:
                </span>
                <div className={`font-mono font-bold ${theme === 'light' ? 'text-slate-900' : 'text-slate-200'}`}>
                  {defaults?.material_code || 'N/A'}
                </div>
              </div>
              <div>
                <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                  Previous Confirmed:
                </span>
                <div className={`font-mono font-bold ${theme === 'light' ? 'text-slate-900' : 'text-slate-200'}`}>
                  {confirmedQuantity.toFixed(2)} TON
                </div>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
              <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                💡 Backend will convert SAP order to TON and validate against WG202 scale readings
              </div>
            </div>
          </div>

          {/* Manual Processing Fields */}
          <div className={`p-4 rounded-lg border ${
            theme === 'light' 
              ? 'bg-slate-50 border-slate-200' 
              : 'bg-slate-800/20 border-slate-600'
          }`}>
            <h4 className={`font-semibold text-sm mb-4 ${theme === 'light' ? 'text-slate-800' : 'text-slate-300'}`}>
              Manual Processing Fields
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Expected Weight (from table)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={expectedWeight}
                    readOnly
                    className={`${inputClass} text-sm flex-1 ${
                      theme === 'light' 
                        ? 'bg-slate-100 text-slate-600 cursor-not-allowed border-slate-200' 
                        : 'bg-slate-800/50 text-slate-400 cursor-not-allowed border-slate-600'
                    }`}
                    placeholder="Expected weight from table"
                    title="Expected weight from the main table (read-only)"
                  />
                  <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    theme === 'light' 
                      ? 'bg-slate-100 text-slate-700 border border-slate-300' 
                      : 'bg-slate-700 text-slate-300 border border-slate-600'
                  }`}>
                    {unit}
                  </span>
                </div>
              </div>
              <div>
                <label className={labelClass}>Matched Weight</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={matchedWeight}
                    onChange={(e) => setMatchedWeight(Number(e.target.value))}
                    className={`${inputClass} text-sm flex-1`}
                    placeholder="Enter actual measured weight"
                  />
                  <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    theme === 'light' 
                      ? 'bg-slate-100 text-slate-700 border border-slate-300' 
                      : 'bg-slate-700 text-slate-300 border border-slate-600'
                  }`}>
                    {unit}
                  </span>
                </div>
                {matchedWeight > 0 && expectedWeight > 0 && (
                  <div className="mt-2">
                    {(() => {
                      const manualStatus = calculateManualValidationStatus();
                      return (
                        <div className={`text-xs p-2 rounded ${
                          manualStatus.isValid
                            ? theme === 'light' 
                              ? 'bg-green-100 text-green-700 border border-green-200' 
                              : 'bg-green-900/30 text-green-300 border border-green-700'
                            : theme === 'light' 
                              ? 'bg-red-100 text-red-700 border border-red-200' 
                              : 'bg-red-900/30 text-red-300 border border-red-700'
                        }`}>
                          <div className="font-medium">
                            {manualStatus.isValid ? '✅ Within Tolerance' : '❌ Outside Tolerance'}
                          </div>
                          <div className="mt-1">
                            Expected: {expectedWeight} {unit} | 
                            Matched: {matchedWeight} {unit} | 
                            Difference: {manualStatus.difference.toFixed(2)} {unit} | 
                            Tolerance: ±{manualStatus.toleranceAmount.toFixed(2)} {unit}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className={labelClass}>Scrap Quantity</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={scrap}
                    onChange={(e) => setScrap(Number(e.target.value))}
                    className={`${inputClass} text-sm flex-1`}
                    placeholder="0.00"
                  />
                  <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    theme === 'light' 
                      ? 'bg-slate-100 text-slate-700 border border-slate-300' 
                      : 'bg-slate-700 text-slate-300 border border-slate-600'
                  }`}>
                    {unit}
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4">
              <label className={labelClass}>Confirmed Text</label>
              <textarea
                value={confirmedText}
                onChange={(e) => setConfirmedText(e.target.value)}
                placeholder="Additional notes or comments..."
                className={`${inputClass} text-sm min-h-[80px] resize-y`}
                maxLength={500}
              />
            </div>
          </div>

          {/* Partial Confirmation Section */}
          <div className={`p-3 rounded-lg border ${
            theme === 'light' 
              ? 'bg-orange-50 border-orange-200' 
              : 'bg-orange-900/20 border-orange-500/30'
          }`}>
            <h4 className={`font-semibold text-sm mb-3 ${theme === 'light' ? 'text-orange-800' : 'text-orange-300'}`}>
              🔄 Partial Confirmation Options
            </h4>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <label className={`inline-flex items-center gap-2 ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'}`}>
                  <input 
                    type="checkbox" 
                    checked={allowPartialConfirmation} 
                    onChange={e => {
                      setAllowPartialConfirmation(e.target.checked);
                      if (!e.target.checked) {
                        setPartialConfirmedQty(0);
                      }
                    }}
                    className="rounded"
                  />
                  Allow partial confirmation (confirm less than total quantity)
                </label>
              </div>
              
              {allowPartialConfirmation && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Partial Confirmed Quantity</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max={expectedQuantity}
                        value={partialConfirmedQty}
                        onChange={(e) => setPartialConfirmedQty(Number(e.target.value))}
                        className={`${inputClass} text-sm flex-1`}
                        placeholder={`Enter quantity to confirm (max: ${expectedQuantity})`}
                      />
                      <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                        theme === 'light' 
                          ? 'bg-slate-100 text-slate-700 border border-slate-300' 
                          : 'bg-slate-700 text-slate-300 border border-slate-600'
                      }`}>
                        {unit}
                      </span>
                    </div>
                    {partialConfirmedQty > 0 && (
                      <div className="mt-2">
                        <div className={`text-xs p-2 rounded ${
                          theme === 'light' 
                            ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                            : 'bg-blue-900/30 text-blue-300 border border-blue-700'
                        }`}>
                          <div className="font-medium">
                            📊 Partial Confirmation Summary
                          </div>
                          <div className="mt-1">
                            Confirming: {partialConfirmedQty} {unit} out of {expectedQuantity} {unit} 
                            ({((partialConfirmedQty / expectedQuantity) * 100).toFixed(1)}% completion)
                          </div>
                          <div className="mt-1 text-xs">
                            Remaining: {(expectedQuantity - partialConfirmedQty).toFixed(2)} {unit}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Quick Fill Options</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setPartialConfirmedQty(expectedQuantity * 0.1)}
                        className={`px-3 py-1 text-xs rounded ${
                          theme === 'light' 
                            ? 'bg-orange-100 text-orange-700 border border-orange-200 hover:bg-orange-200' 
                            : 'bg-orange-900/30 text-orange-300 border border-orange-700 hover:bg-orange-900/50'
                        }`}
                      >
                        10%
                      </button>
                      <button
                        type="button"
                        onClick={() => setPartialConfirmedQty(expectedQuantity * 0.25)}
                        className={`px-3 py-1 text-xs rounded ${
                          theme === 'light' 
                            ? 'bg-orange-100 text-orange-700 border border-orange-200 hover:bg-orange-200' 
                            : 'bg-orange-900/30 text-orange-300 border border-orange-700 hover:bg-orange-900/50'
                        }`}
                      >
                        25%
                      </button>
                      <button
                        type="button"
                        onClick={() => setPartialConfirmedQty(expectedQuantity * 0.5)}
                        className={`px-3 py-1 text-xs rounded ${
                          theme === 'light' 
                            ? 'bg-orange-100 text-orange-700 border border-orange-200 hover:bg-orange-200' 
                            : 'bg-orange-900/30 text-orange-300 border border-orange-700 hover:bg-orange-900/50'
                        }`}
                      >
                        50%
                      </button>
                      <button
                        type="button"
                        onClick={() => setPartialConfirmedQty(expectedQuantity * 0.75)}
                        className={`px-3 py-1 text-xs rounded ${
                          theme === 'light' 
                            ? 'bg-orange-100 text-orange-700 border border-orange-200 hover:bg-orange-200' 
                            : 'bg-orange-900/30 text-orange-300 border border-orange-700 hover:bg-orange-900/50'
                        }`}
                      >
                        75%
                      </button>
                      <button
                        type="button"
                        onClick={() => setPartialConfirmedQty(expectedQuantity)}
                        className={`px-3 py-1 text-xs rounded ${
                          theme === 'light' 
                            ? 'bg-green-100 text-green-700 border border-green-200 hover:bg-green-200' 
                            : 'bg-green-900/30 text-green-300 border border-green-700 hover:bg-green-900/50'
                        }`}
                      >
                        100%
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Backend Validation Results Display */}
          {validationResult && (
            <div className="space-y-4">
              <h4 className={`font-semibold text-base ${theme === 'light' ? 'text-slate-800' : 'text-white'}`}>
                Backend Validation Results
              </h4>
              
              {/* Overall Status */}
              <div className={`p-4 rounded-lg border ${
                validationResult.valid 
                  ? theme === 'light' 
                    ? 'bg-emerald-50 border-emerald-200' 
                    : 'bg-emerald-500/10 border-emerald-500/30'
                  : theme === 'light' 
                    ? 'bg-red-50 border-red-200' 
                    : 'bg-red-500/10 border-red-500/30'
              }`}>
                <div className={`flex items-center gap-2 font-semibold text-lg ${
                  validationResult.valid 
                    ? theme === 'light' ? 'text-emerald-700' : 'text-emerald-300'
                    : theme === 'light' ? 'text-red-700' : 'text-red-300'
                }`}>
                  {validationResult.valid ? '✅ Validation Passed' : '❌ Validation Failed'}
                </div>
                <div className={`text-sm mt-2 ${
                  validationResult.valid 
                    ? theme === 'light' ? 'text-emerald-600' : 'text-emerald-400'
                    : theme === 'light' ? 'text-red-600' : 'text-red-400'
                }`}>
                  {validationResult.valid 
                    ? `All quantities within ±${validationResult.tolerance_pct}% tolerance`
                    : `Found ${validationResult.mismatches?.length || 0} mismatches outside tolerance`
                  }
                </div>
              </div>

              {/* Input Validation Section */}
              <div className={`p-4 rounded-lg border ${
                theme === 'light' 
                  ? 'bg-blue-50 border-blue-200' 
                  : 'bg-blue-900/20 border-blue-500/30'
              }`}>
                <h5 className={`font-semibold text-sm mb-3 ${theme === 'light' ? 'text-blue-800' : 'text-blue-300'}`}>
                  📥 Input Validation (WG202 Scale)
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-blue-700' : 'text-blue-400'}`}>
                      Expected Input:
                    </span>
                    <div className={`font-mono font-bold text-lg ${theme === 'light' ? 'text-blue-900' : 'text-blue-200'}`}>
                      {((validationResult as any).expected_tons * 1000).toFixed(2)} KG
                    </div>
                    <div className={`text-xs ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`}>
                      ({((validationResult as any).expected_tons || 0).toFixed(3)} T)
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-blue-700' : 'text-blue-400'}`}>
                      Actual Input (WG202):
                    </span>
                    <div className={`font-mono font-bold text-lg ${theme === 'light' ? 'text-blue-900' : 'text-blue-200'}`}>
                      {((validationResult.actuals.WG202 || 0) * 1000).toFixed(2)} KG
                    </div>
                    <div className={`text-xs ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`}>
                      ({(validationResult.actuals.WG202 || 0).toFixed(3)} T)
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-blue-700' : 'text-blue-400'}`}>
                      Input Difference:
                    </span>
                    <div className={`font-mono font-bold text-lg ${
                      Math.abs(((validationResult.actuals.WG202 || 0) - ((validationResult as any).expected_tons || 0)) * 1000) <= 
                      (((validationResult as any).expected_tons || 0) * validationResult.tolerance_pct / 100 * 1000)
                        ? theme === 'light' ? 'text-green-700' : 'text-green-400'
                        : theme === 'light' ? 'text-red-700' : 'text-red-400'
                    }`}>
                      {(((validationResult.actuals.WG202 || 0) - ((validationResult as any).expected_tons || 0)) * 1000).toFixed(2)} KG
                    </div>
                  </div>
                </div>
              </div>

              {/* Output Validation Section */}
              <div className={`p-4 rounded-lg border ${
                theme === 'light' 
                  ? 'bg-purple-50 border-purple-200' 
                  : 'bg-purple-900/20 border-purple-500/30'
              }`}>
                <h5 className={`font-semibold text-sm mb-3 ${theme === 'light' ? 'text-purple-800' : 'text-purple-300'}`}>
                  📤 Output Validation (Recipe Distribution)
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-purple-700' : 'text-purple-400'}`}>
                      Flour Output (WG501+WG502):
                    </span>
                    <div className={`font-mono font-bold text-lg ${theme === 'light' ? 'text-purple-900' : 'text-purple-200'}`}>
                      {((validationResult.actuals["WG501+WG502"] || 0) * 1000).toFixed(2)} KG
                    </div>
                    <div className={`text-xs ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                      ({(validationResult.actuals["WG501+WG502"] || 0).toFixed(3)} T)
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-purple-700' : 'text-purple-400'}`}>
                      Bran Output (WG503):
                    </span>
                    <div className={`font-mono font-bold text-lg ${theme === 'light' ? 'text-purple-900' : 'text-purple-200'}`}>
                      {((validationResult.actuals.WG503 || 0) * 1000).toFixed(2)} KG
                    </div>
                    <div className={`text-xs ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                      ({(validationResult.actuals.WG503 || 0).toFixed(3)} T)
                    </div>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-purple-200 dark:border-purple-700">
                  <span className={`font-medium ${theme === 'light' ? 'text-purple-700' : 'text-purple-400'}`}>
                    Total Output:
                  </span>
                  <div className={`font-mono font-bold text-lg ${theme === 'light' ? 'text-purple-900' : 'text-purple-200'}`}>
                    {(((validationResult.actuals["WG501+WG502"] || 0) + (validationResult.actuals.WG503 || 0)) * 1000).toFixed(2)} KG
                  </div>
                </div>
              </div>

              {/* Detailed Mismatches Table */}
              {validationResult.mismatches && validationResult.mismatches.length > 0 && (
                <div className={`overflow-x-auto rounded-lg border ${theme === 'light' ? 'border-slate-200' : 'border-slate-700'}`}>
                  <h5 className={`font-semibold text-sm mb-3 px-4 pt-4 ${theme === 'light' ? 'text-slate-800' : 'text-slate-300'}`}>
                    🔍 Detailed Mismatch Analysis
                  </h5>
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr className="text-left">
                        <th className={tableHeaderClass}>Material/Process</th>
                        <th className={tableHeaderClass}>Expected</th>
                        <th className={tableHeaderClass}>Actual</th>
                        <th className={tableHeaderClass}>Difference</th>
                        <th className={tableHeaderClass}>% Error</th>
                        <th className={tableHeaderClass}>Reason</th>
                        <th className={tableHeaderClass}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validationResult.mismatches.map((m, i) => (
                        <tr key={i} className={`border-b ${theme === 'light' ? 'border-slate-100' : 'border-slate-700'}`}>
                          <td className={`px-3 py-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                            <div className="font-medium">{m.material_code}</div>
                            <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                              {m.uom}
                            </div>
                          </td>
                          <td className={`px-3 py-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                            <div className="font-mono">{(m.expected * 1000).toFixed(2)} KG</div>
                            <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                              ({m.expected.toFixed(3)} T)
                            </div>
                          </td>
                          <td className={`px-3 py-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                            <div className="font-mono">{(m.actual * 1000).toFixed(2)} KG</div>
                            <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                              ({m.actual.toFixed(3)} T)
                            </div>
                          </td>
                          <td className={`px-3 py-2 font-mono ${
                            m.within_tolerance 
                              ? theme === 'light' ? 'text-green-700' : 'text-green-400'
                              : theme === 'light' ? 'text-red-700' : 'text-red-400'
                          }`}>
                            <div className="font-bold">{(m.diff * 1000).toFixed(2)} KG</div>
                            <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'}`}>
                              ({m.diff.toFixed(3)} T)
                            </div>
                          </td>
                          <td className={`px-3 py-2 font-mono ${
                            m.within_tolerance 
                              ? theme === 'light' ? 'text-green-700' : 'text-red-700'
                              : theme === 'light' ? 'text-red-700' : 'text-red-400'
                          }`}>
                            <div className="font-bold">{m.pct.toFixed(2)}%</div>
                          </td>
                          <td className={`px-3 py-2 ${theme === 'light' ? 'text-slate-900' : 'text-white'}`}>
                            <div className="text-xs">{m.reason || 'QUANTITY_MISMATCH'}</div>
                          </td>
                          <td className={`px-3 py-2 ${
                            m.within_tolerance 
                              ? theme === 'light' ? 'text-green-700' : 'text-green-400'
                              : theme === 'light' ? 'text-red-700' : 'text-red-400'
                          }`}>
                            <div className="font-bold">
                              {m.within_tolerance ? '✅ OK' : '❌ FAIL'}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Validation Summary */}
              <div className={`p-4 rounded-lg border ${
                theme === 'light' 
                  ? 'bg-slate-50 border-slate-200' 
                  : 'bg-slate-800/20 border-slate-600'
              }`}>
                <h5 className={`font-semibold text-sm mb-2 ${theme === 'light' ? 'text-slate-800' : 'text-slate-300'}`}>
                  📊 Validation Summary
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                      Total Checks:
                    </span>
                    <div className={`font-bold ${theme === 'light' ? 'text-slate-900' : 'text-slate-200'}`}>
                      {validationResult.mismatches?.length || 0}
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                      Passed:
                    </span>
                    <div className={`font-bold ${theme === 'light' ? 'text-green-700' : 'text-green-400'}`}>
                      {validationResult.mismatches?.filter(m => m.within_tolerance).length || 0}
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                      Failed:
                    </span>
                    <div className={`font-bold ${theme === 'light' ? 'text-red-700' : 'text-red-400'}`}>
                      {validationResult.mismatches?.filter(m => !m.within_tolerance).length || 0}
                    </div>
                  </div>
                  <div>
                    <span className={`font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-400'}`}>
                      Tolerance:
                    </span>
                    <div className={`font-bold ${theme === 'light' ? 'text-slate-900' : 'text-slate-200'}`}>
                      ±{validationResult.tolerance_pct}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-4 pt-2 border-t border-slate-200 dark:border-slate-700 mt-2">
            <button 
              disabled={submitting || autoValidationStatus === 'auto-validating' || (expectedWeight > 0 && (matchedWeight <= 0 || !manualValidationEnabled))} 
              onClick={submit}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors disabled:opacity-50 ${
                autoValidationStatus === 'auto-validating'
                  ? theme === 'light' ? 'bg-blue-600 text-white' : 'bg-blue-600 text-white'
                  : (expectedWeight > 0 && (matchedWeight <= 0 || !manualValidationEnabled))
                  ? theme === 'light' ? 'bg-gray-400 text-white cursor-not-allowed' : 'bg-gray-600 text-white cursor-not-allowed'
                  : theme === 'light'
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
              title={
                expectedWeight > 0 && matchedWeight <= 0 
                  ? 'Please enter a matched weight' 
                  : expectedWeight > 0 && !manualValidationEnabled 
                    ? 'Matched weight is outside tolerance range' 
                    : ''
              }
            >
              {submitting ? 'Validating…' : 
               autoValidationStatus === 'auto-validating' ? 'Auto-Validating...' :
               expectedWeight > 0 ? 'Validate (Manual)' :
               'Validate'}
            </button>
            <button 
              onClick={onClose} 
              className={`px-4 py-2 rounded-lg font-semibold border transition-colors ${
                theme === 'light'
                  ? 'border-slate-300 text-slate-700 hover:bg-slate-50'
                  : 'border-slate-600 text-slate-300 hover:bg-slate-800'
              }`}
            >
              Close
            </button>
          </div>

        </div>
      </div>
    </div>,
    document.body
  );
};

export default OrderValidationModal;
