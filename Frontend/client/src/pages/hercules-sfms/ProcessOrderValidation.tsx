
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { ListOrdered, CheckCircle, XCircle, Clock3, AlertCircle, X, Search, Filter, Play, BarChart3, GripVertical, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Square, RotateCcw, Weight, Scale, WifiOff, AlertTriangle, Loader2 } from 'lucide-react';
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout';
import { orderApi, Order, ValidationRequest, ValidationResult } from '../../lib/api';
import OrderValidationModal from '../../components/OrderValidationModal';
import OrderRejectionModal, { RejectionData } from '../../components/OrderRejectionModal';
import ShiftIndicator from '../../components/ShiftIndicator';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { getApiUrl, API_BASE_URL, apiFetch } from '../../lib/apiConfig';

// Log API configuration when component loads
if (typeof window !== 'undefined') {
  console.log('📄 ProcessOrderValidation.tsx: Using API_BASE_URL =', API_BASE_URL || '(relative URLs)');
}

interface UserInfo {
  id: number;
  username: string;
  roles: string[];
}

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface KpiCardProps {
  title: string;
  value: number;
  unit: string;
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
  showViewButton?: boolean;
  onViewClick?: () => void;
  showUnderlineText?: boolean;
  underlineText?: string;
  onUnderlineClick?: () => void;
  /** When set, rendered instead of value+unit (e.g. separate Mill/Pack lines for Total Orders) */
  valueNode?: React.ReactNode;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, unit, Icon, color, showViewButton, onViewClick, showUnderlineText, underlineText, onUnderlineClick, valueNode }) => {
  const { theme } = useTheme();

  return (
    <div 
      className={`relative group cursor-pointer transition-all duration-200 ${theme === 'light'
          ? 'bg-white border border-gray-200 hover:border-gray-300 hover:shadow-md'
          : 'bg-slate-800 border border-slate-700 hover:border-slate-600 hover:shadow-lg'
        } rounded-lg p-4 h-full`}
      onClick={onViewClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <h3 className={`text-xs font-semibold uppercase tracking-wide mb-2 ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'
            }`}>
            {title}
          </h3>
          <div className="flex items-baseline gap-1 flex-wrap">
            {valueNode != null ? (
              valueNode
            ) : (
              <span
                className={`text-3xl font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'
                  }`}
                style={{ color }}
              >
                {value}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {showViewButton && (
            <span
              onClick={(e) => {
                e.stopPropagation();
                onViewClick?.();
              }}
              className={`cursor-pointer text-xs font-medium transition-all duration-200 hover:opacity-80 flex-shrink-0 ${theme === 'light' ? 'text-blue-600 hover:text-blue-700' : 'text-cyan-400 hover:text-cyan-300'
                }`}
              title={`View ${title.toLowerCase()}`}
            >
              VIEW ALL
            </span>
          )}
          <div
            className={`p-2 rounded-md transition-all duration-200 ${theme === 'light'
                ? 'bg-gray-50'
                : 'bg-slate-700'
              }`}
          >
            <Icon
              className={`h-5 w-5`}
              style={{ color: color } as React.CSSProperties}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

// Pagination Component
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (itemsPerPage: number) => void;
  theme: 'light' | 'dark';
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
  theme
}) => {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, currentPage - 2);
      const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

      if (startPage > 1) {
        pages.push(1);
        if (startPage > 2) {
          pages.push('...');
        }
      }

      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }

      if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
          pages.push('...');
        }
        pages.push(totalPages);
      }
    }

    return pages;
  };

  return (
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
        ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
        : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
      }`}>
      {/* Items per page selector and info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className={`text-sm font-medium ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            }`}>
            Show:
          </label>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className={`px-2 py-1 rounded border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
                ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
              }`}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>

        <div className={`text-sm ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
          }`}>
          Showing {startItem}-{endItem} of {totalItems} orders
        </div>
      </div>

      {/* Pagination controls */}
      <div className="flex items-center gap-2">
        {/* First page */}
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === 1
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
            } ${theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
            }`}
          title="First page"
        >
          <ChevronsLeft className="h-4 w-4" />
        </button>

        {/* Previous page */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === 1
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
            } ${theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
            }`}
          title="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {/* Page numbers */}
        <div className="flex items-center gap-1">
          {getPageNumbers().map((page, index) => (
            <button
              key={index}
              onClick={() => typeof page === 'number' ? onPageChange(page) : undefined}
              disabled={page === '...'}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all duration-200 ${page === '...'
                  ? 'cursor-default'
                  : 'hover:scale-105'
                } ${page === currentPage
                  ? theme === 'light'
                    ? 'bg-blue-500 text-white shadow-md'
                    : 'bg-cyan-500 text-white shadow-md shadow-cyan-500/25'
                  : page === '...'
                    ? theme === 'light'
                      ? 'text-slate-400'
                      : 'text-slate-500'
                    : theme === 'light'
                      ? 'text-slate-700 hover:bg-slate-100'
                      : 'text-slate-300 hover:bg-slate-700'
                }`}
            >
              {page}
            </button>
          ))}
        </div>

        {/* Next page */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === totalPages
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
            } ${theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
            }`}
          title="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        {/* Last page */}
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className={`p-2 rounded-md transition-all duration-200 ${currentPage === totalPages
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:scale-105'
            } ${theme === 'light'
              ? 'text-slate-600 hover:bg-slate-100'
              : 'text-slate-400 hover:bg-slate-700'
            }`}
          title="Last page"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

// Sortable Row Component
interface SortableRowProps {
  order: Order;
  index: number;
  theme: 'light' | 'dark';
  validatingOrders: Set<string>;
  autoValidatorStatus: any;
  orderProgress: Record<string, number>;
  tableRowEven: string;
  tableRowOdd: string;
  borderRow: string;
  onValidate: (poNumber: string) => void;
  onReject: (orderId: number) => void;
  onProgressClick: (order: Order) => void;
  isAdmin?: boolean;
  onClassify?: (poNumber: string) => void;
  onViewValidationDetails?: (order: Order) => void;
  onStartOrder?: (poNumber: string) => void;
  onStopOrder?: (poNumber: string) => void;
  onManualConfirm?: (order: Order) => void;
  onPushConfirmation?: (order: Order) => void;
  pushingConfirmation?: boolean;
  priority: number;
  showByproducts?: boolean;
  isTopPriority?: boolean;  // ✅ Jan 30, 2026: Only top priority orders can start
  minPendingPriority?: number;  // ✅ Jan 30, 2026: Minimum priority among pending orders (for tooltip)
}

const SortableRow: React.FC<SortableRowProps> = ({
  order,
  index,
  theme,
  validatingOrders,
  autoValidatorStatus,
  orderProgress,
  tableRowEven,
  tableRowOdd,
  borderRow,
  onValidate,
  onReject,
  onProgressClick,
  isAdmin = false,
  onClassify,
  onViewValidationDetails,
  onStartOrder,
  onStopOrder,
  onManualConfirm,
  onPushConfirmation,
  pushingConfirmation = false,
  priority,
  showByproducts = true,
  isTopPriority = true,  // ✅ Jan 30, 2026: Default to true for backward compatibility
  minPendingPriority = 1,  // ✅ Jan 30, 2026: Default to 1
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: order.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Get confirmed quantity for display
  const confirmedQty = (order as any).confirmed_qty || 0;

  // Get expected weight directly from database (used elsewhere)
  const expectedWeight = (order as any).expected_weight ?
    parseFloat((order as any).expected_weight).toFixed(2) :
    '0.00';

  const isRunning = order.status === 'InProgress' || order.status === 'RUNNING';
  const isPending = order.status === 'Pending' || order.status === 'Planned';
  // ✅ Feb 5, 2026: Completed = 100% progress, Validated = confirmed to SAP
  const isCompleted = order.status === 'Completed';
  const isValidated = order.status === 'Validated';
  const isFinished = isCompleted || isValidated;

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`transition duration-150 border-b ${borderRow} ${index % 2 === 0 ? tableRowEven : tableRowOdd} ${isRunning ? 'cursor-pointer hover:bg-opacity-80 border-l-4' : ''
        } ${isRunning ? 'border-l-green-500' : ''} ${isDragging ? 'z-50 shadow-lg' : ''}`}
      onClick={(e) => {
        // Only open progress for InProgress orders
        if (order.status === 'InProgress') {
          // Don't trigger if clicking on buttons or interactive elements
          const target = e.target as HTMLElement;
          if (!target.closest('button') && !target.closest('[role="button"]') && !target.closest('input') && !target.closest('select')) {
            onProgressClick(order);
          }
        }
      }}
    >
      {/* Drag Handle Column */}
      <td className="px-2 py-1.5 w-8">
        <div
          {...attributes}
          {...listeners}
          className={`cursor-grab active:cursor-grabbing p-1 rounded hover:bg-opacity-20 transition-colors ${theme === 'light' ? 'hover:bg-gray-200' : 'hover:bg-gray-600'
            }`}
          title="Drag to reorder"
        >
          <GripVertical className={`h-4 w-4 ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`} />
        </div>
      </td>

      <td className="px-2 py-1.5 font-mono text-xs w-16 truncate" title={String(order.id)}>{order.id}</td>
      <td className="px-2 py-1.5 font-mono text-xs w-28 truncate" title={order.po_number}>{order.po_number}</td>
      {/* Material - Show last 8 digits with tooltip for full number */}
      <td className="px-2 py-1.5 font-mono text-xs w-32 truncate cursor-help" title={`Full: ${order.material}`}>
        {order.material && order.material.length > 8 ? `...${order.material.slice(-8)}` : order.material}
      </td>
      <td className="px-2 py-1.5 font-mono text-xs w-12 truncate font-bold" title={order.version}>{order.version}</td>

      {/* Order Type Column - Reference Design: MILLING green, PACKING orange */}
      <td className="px-2 py-1.5 w-20">
        <span 
          className="px-2 py-1 rounded text-xs font-bold"
          style={{
            backgroundColor: (order as any).order_type === 'MILLING' 
              ? '#10b981'  // green-500
              : (order as any).order_type === 'PACKING' 
                ? '#f97316'  // orange-500
                : '#6b7280', // gray-500
            color: '#ffffff'
          }}
        >
          {(order as any).order_type || 'Unknown'}
        </span>
      </td>

      {/* Target Column - Reference Design: Boxed numbers with subtle background */}
      {/* ✅ CRITICAL FIX (Jan 23, 2026): Use backend-provided target (already converted for PACKING) */}
      <td className="px-2 py-1.5 w-24 text-center">
        <div className={`inline-block px-2 py-1 rounded ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-slate-700/50 border border-slate-600'}`}>
          <span className={`text-base font-mono font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
            {(order as any).order_type === 'MILLING'
              ? ((order as any).target || (order as any).expected_weight || order.quantity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              : ((order as any).target || order.quantity || 0).toLocaleString()
            }
          </span>
        </div>
      </td>
      <td className="px-2 py-1.5 w-12 text-center">
        <span className={`px-2 py-1 rounded text-xs font-bold ${(order as any).order_type === 'MILLING'
            ? theme === 'light' ? 'bg-slate-200 text-slate-700' : 'bg-purple-900/30 text-purple-300'
            : theme === 'light' ? 'bg-slate-200 text-slate-700' : 'bg-cyan-900/30 text-cyan-300'
          }`}>
          {(order as any).order_type === 'MILLING' ? 'TO' : 'BAG'}
        </span>
      </td>
      {/* Confirm Column - Reference Design: Boxed numbers */}
      <td className="px-2 py-1.5 w-24 text-center">
        {(() => {
          const orderType = (order as any).order_type;
          const lastConfirmedQty = (order as any).last_confirmed_qty || 0;

          if (orderType === 'MILLING') {
            const confirmedWeight = lastConfirmedQty > 0 ? lastConfirmedQty.toFixed(2) : '0.00';
            return (
              <div className={`inline-block px-2 py-1 rounded ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-slate-700/50 border border-slate-600'}`}>
                <span className={`text-base font-mono font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  {confirmedWeight}
                </span>
              </div>
            );
          } else {
            const confirmedQuantity = lastConfirmedQty > 0 ? lastConfirmedQty.toFixed(0) : '0';
            return (
              <div className={`inline-block px-2 py-1 rounded ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-slate-700/50 border border-slate-600'}`}>
                <span className={`text-base font-mono font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  {confirmedQuantity}
                </span>
              </div>
            );
          }
        })()}
      </td>
      {/* Current Column - Reference Design: Boxed numbers, green text for running orders */}
      <td className="px-2 py-1.5 w-24 text-center">
        {(() => {
          const orderType = (order as any).order_type;
          const confirmedQty = (order as any).confirmed_qty || 0;

          if (orderType === 'MILLING') {
            const currentWeight = confirmedQty > 0 ? confirmedQty.toFixed(2) : '0.00';
            return (
              <div className={`inline-block px-2 py-1 rounded ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-slate-700/50 border border-slate-600'}`}>
                <span className={`text-base font-mono font-bold ${isRunning ? 'text-green-600' : theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  {currentWeight}
                </span>
              </div>
            );
          } else {
            const currentQuantity = confirmedQty > 0 ? confirmedQty.toFixed(0) : '0';
            return (
              <div className={`inline-block px-2 py-1 rounded ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-slate-700/50 border border-slate-600'}`}>
                <span className={`text-base font-mono font-bold ${isRunning ? 'text-green-600' : theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  {currentQuantity}
                </span>
              </div>
            );
          }
        })()}
      </td>
      {/* Remaining Column */}
      {/* ✅ CRITICAL FIX (Jan 23, 2026): Use backend-provided target (already converted for PACKING) */}
      <td className="px-2 py-1.5 w-24 text-center">
        {(() => {
          const orderType = (order as any).order_type;
          const confirmedQty = (order as any).confirmed_qty || 0;

          // Calculate remaining: target - current (confirmed)
          // ✅ Use backend-provided target (already converted for PACKING orders)
          let target = (order as any).target || 0;
          let remaining = 0;
          let unit = '';

          if (orderType === 'MILLING') {
            // Fallback to expected_weight if target not provided
            if (target <= 0) {
              target = (order as any).expected_weight || order.quantity || 0;
            }
            remaining = Math.max(0, target - confirmedQty);
            unit = 'TO';
          } else {
            // ✅ FIX (Jan 23, 2026): Fallback for PACKING if target not provided
            if (target <= 0) {
              target = order.quantity || 0;
            }
            remaining = Math.max(0, target - confirmedQty);
            unit = 'BAG';
          }

          const remainingDisplay = remaining > 0 ? remaining.toFixed(2) : '0.00';

          return (
            <div className="flex flex-col items-center gap-0.5">
              {/* Remaining - Industrial colors: dark amber for warning */}
              <span className={`text-base font-mono font-bold ${theme === 'light' ? 'text-amber-700' : 'text-orange-400'
                }`}>
                {remainingDisplay}
              </span>
              <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${orderType === 'MILLING'
                  ? theme === 'light' ? 'bg-slate-200 text-slate-700' : 'bg-purple-900/30 text-purple-300'
                  : theme === 'light' ? 'bg-slate-200 text-slate-700' : 'bg-cyan-900/30 text-cyan-300'
                }`}>
                {unit}
              </span>
            </div>
          );
        })()}
      </td>

      {/* Byproducts Columns - Only show values when byproduct scale is configured (scale name is not null) */}
      {showByproducts && (
        <>
          <td className="px-2 py-1.5 text-center text-xs">
            {(order as any).order_type === 'MILLING' && (order as any).scale1 ? (
              <div className="flex flex-col items-center">
                <span className="font-mono font-bold">
                  {((order as any).scale1_qty !== null && (order as any).scale1_qty !== undefined) 
                    ? Number((order as any).scale1_qty).toFixed(2) 
                    : '0.00'}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${theme === 'light' ? 'bg-gray-100 text-gray-600' : 'bg-gray-700 text-gray-400'}`}>
                  {(order as any).scale1}
                </span>
              </div>
            ) : <span className="text-gray-400">-</span>}
          </td>
          <td className="px-2 py-1.5 text-center text-xs">
            {(order as any).order_type === 'MILLING' && (order as any).scale2 ? (
              <div className="flex flex-col items-center">
                <span className="font-mono font-bold">
                  {((order as any).scale2_qty !== null && (order as any).scale2_qty !== undefined) 
                    ? Number((order as any).scale2_qty).toFixed(2) 
                    : '0.00'}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${theme === 'light' ? 'bg-gray-100 text-gray-600' : 'bg-gray-700 text-gray-400'}`}>
                  {(order as any).scale2}
                </span>
              </div>
            ) : <span className="text-gray-400">-</span>}
          </td>
        </>
      )}

      {/* Status Column - RUNNING green, Pending orange, Completed purple, Validated blue */}
      <td className="px-2 py-1.5 w-24 text-center">
        <span 
          className="px-2.5 py-1 rounded-full text-xs font-semibold inline-flex items-center justify-center gap-1.5 shadow-sm"
          style={{
            backgroundColor: isRunning 
              ? (theme === 'light' ? '#dcfce7' : '#166534')  // light green / dark green
              : isValidated 
              ? (theme === 'light' ? '#dbeafe' : '#1e3a8a')  // light blue / dark blue (SAP confirmed)
              : isCompleted 
              ? (theme === 'light' ? '#ede9fe' : '#4c1d95')  // light purple / dark purple (100% complete)
              : isPending 
              ? (theme === 'light' ? '#fed7aa' : '#9a3412')   // light orange / dark orange
              : order.status === 'Rejected' 
              ? (theme === 'light' ? '#fee2e2' : '#991b1b')  // light red / dark red
              : (theme === 'light' ? '#f3f4f6' : '#374151'), // light gray / dark gray
            color: isRunning 
              ? (theme === 'light' ? '#16a34a' : '#86efac')  // darker green / light green
              : isValidated 
              ? (theme === 'light' ? '#2563eb' : '#93c5fd')  // darker blue / light blue (SAP confirmed)
              : isCompleted 
              ? (theme === 'light' ? '#7c3aed' : '#c4b5fd')  // darker purple / light purple (100% complete)
              : isPending 
              ? (theme === 'light' ? '#ea580c' : '#fdba74')  // darker orange / light orange
              : order.status === 'Rejected' 
              ? (theme === 'light' ? '#dc2626' : '#fca5a5')  // darker red / light red
              : (theme === 'light' ? '#6b7280' : '#9ca3af')  // darker gray / light gray
          }}
        >
          <span 
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{
              backgroundColor: isRunning 
                ? (theme === 'light' ? '#22c55e' : '#86efac')  // green dot
                : isValidated 
                ? (theme === 'light' ? '#3b82f6' : '#93c5fd')  // blue dot (SAP confirmed)
                : isCompleted 
                ? (theme === 'light' ? '#8b5cf6' : '#c4b5fd')  // purple dot (100% complete)
                : isPending 
                ? (theme === 'light' ? '#f97316' : '#fdba74')  // orange dot
                : order.status === 'Rejected' 
                ? (theme === 'light' ? '#ef4444' : '#fca5a5')  // red dot
                : (theme === 'light' ? '#6b7280' : '#9ca3af')  // gray dot
            }}
          />
          {order.status === 'InProgress' ? 'RUNNING' : order.status}
        </span>
      </td>
      
      {/* Priority Column - Show SAP Priority ID (priority_id); styling by queue position (isTopPriority) */}
      <td className="px-2 py-1.5 w-16 text-center">
        <span 
          className="px-2 py-1 rounded text-xs font-bold"
          style={{
            backgroundColor: isTopPriority 
              ? '#059669'  // emerald-600 for first in queue (can run)
              : '#f59e0b', // amber-500 for waiting (has conflict)
            color: '#ffffff'
          }}
          title={isTopPriority 
            ? (order as any).has_priority_conflict 
              ? `SAP Priority ID ${priority} - First in queue (can run)`
              : `SAP Priority ID ${priority} - No conflicts (runs immediately)`
            : `SAP Priority ID ${priority} - Waiting for ${(order as any).conflict_waiting_for?.join(', ') || 'higher priority orders'}`
          }
        >
          {priority}
        </span>
      </td>

      <td className="px-2 py-1.5 w-36">
        {/* Enhanced Progress Bar */}
        {(() => {
          const orderId = order.po_number || String(order.id);
          const isCurrentOrder = autoValidatorStatus.current_po === orderId;
          const isCompleted = order.status === 'Validated' || order.status === 'Completed' || order.status === 'Confirmed';
          const isInProgress = order.status === 'InProgress';

          // ✅ FIX: Calculate progress correctly - use progress API data if available, otherwise calculate from order data
          // ✅ CRITICAL FIX (Jan 23, 2026): Use backend-provided target (already converted for PACKING)
          const orderType = (order as any).order_type;
          const confirmedQty = (order as any).confirmed_qty || 0;
          // Use backend-provided target (already converted for PACKING orders)
          let targetQty = (order as any).target || 0;

          if (orderType === 'MILLING' && targetQty <= 0) {
            // Fallback for MILLING if target not provided
            targetQty = (order as any).expected_weight || order.quantity || 0;
          } else if (orderType === 'PACKING' && targetQty <= 0) {
            // ✅ FIX (Jan 23, 2026): Fallback for PACKING if target not provided
            // PACKING quantity is already in bags
            targetQty = order.quantity || 0;
          }

          // ✅ FIX: Use confirmed_qty directly - DO NOT reset it after shift end
          let displayConfirmedQty = confirmedQty;
          if (order.status === 'Pending' && confirmedQty === 0) {
            displayConfirmedQty = 0;
          }

          // Calculate progress percentage from confirmed_qty
          let calculatedProgress = 0;
          if (targetQty > 0) {
            calculatedProgress = (displayConfirmedQty / targetQty) * 100;
            calculatedProgress = Math.min(calculatedProgress, 100);
          }

          // ✅ CRITICAL FIX: Don't use cached progress for Pending orders
          // Pending orders should ALWAYS show 0% progress (fresh from database)
          // This prevents stale cached progress from showing when orders are reset/reloaded
          const isPendingOrder = order.status === 'Pending';
          
          // Use auto-validator progress if available and it's the current order, otherwise use calculated progress
          // For Pending orders: ALWAYS use calculatedProgress (which is 0 if confirmed_qty is 0)
          const progress = isPendingOrder 
            ? calculatedProgress
            : (isCurrentOrder && autoValidatorStatus.progress_pct > 0
            ? autoValidatorStatus.progress_pct
                : (orderProgress[orderId || ''] || calculatedProgress));

          // Determine bar gradient based on state
          const getBarStyle = (): React.CSSProperties => {
            if (isCompleted) {
              return { background: 'linear-gradient(90deg, #10b981, #059669)' }; // green gradient
            }
            if (isCurrentOrder || isInProgress) {
              return { background: 'linear-gradient(90deg, #3b82f6, #1d4ed8)' }; // blue gradient
            }
            if (progress > 0) {
              return { background: 'linear-gradient(90deg, #f59e0b, #d97706)' }; // amber gradient (paused with progress)
            }
            return { background: '#9ca3af' }; // gray for not started
          };

          return (
            <div className="flex flex-col gap-0.5">
              {/* Progress bar container */}
              <div 
                className="relative h-5 rounded-md overflow-hidden"
                style={{
                  backgroundColor: theme === 'light' ? '#e5e7eb' : '#374151',
                  boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.12)'
                }}
              >
                {/* Progress fill */}
                <div
                  className="h-full transition-all duration-500 ease-out"
                  style={{
                    width: `${isCompleted ? 100 : Math.min(progress, 100)}%`,
                    ...getBarStyle(),
                    boxShadow: progress > 0 ? '0 0 8px rgba(59, 130, 246, 0.25)' : 'none',
                    animation: isCurrentOrder ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
                  }}
                />
                {/* Percentage text overlay */}
                <div 
                  className="absolute inset-0 flex items-center justify-center"
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    fontFamily: 'ui-monospace, monospace',
                    color: progress > 40 ? '#ffffff' : (theme === 'light' ? '#374151' : '#e5e7eb'),
                    textShadow: progress > 40 ? '0 1px 2px rgba(0,0,0,0.3)' : 'none'
                  }}
                >
                  {isCompleted ? '100%' : `${progress.toFixed(1)}%`}
                </div>
              </div>
              {/* Show qty context for InProgress orders */}
              {isInProgress && targetQty > 0 && (
                <div 
                  className="text-center"
                  style={{
                    fontSize: '9px',
                    color: theme === 'light' ? '#6b7280' : '#9ca3af',
                    fontFamily: 'ui-monospace, monospace'
                  }}
                >
                  {orderType === 'MILLING' 
                    ? `${displayConfirmedQty.toFixed(2)} / ${targetQty.toFixed(2)} TO`
                    : `${Math.round(displayConfirmedQty)} / ${Math.round(targetQty)} BAG`
                  }
                </div>
              )}
            </div>
          );
        })()}
      </td>
      <td className="px-2 py-1.5 w-80">
        <div className="flex flex-col gap-1">
          {/* Main action buttons */}
          <div className="flex gap-1">
            {/* START BUTTON - Reference Design: Green with Play icon */}
            {order.status === 'Pending' && onStartOrder && (
              (() => {
                const hasConflict = (order as any).has_priority_conflict === true;
                const canRun = (order as any).conflict_can_run !== false;
                const scaleIsLocked = hasConflict && !canRun;
                const waitingFor = (order as any).conflict_waiting_for || [];
                
                // ✅ Jan 30, 2026: Check if this order is currently being started
                const orderPo = order.po_number || String(order.id) || '';
                const isStarting = validatingOrders.has(orderPo);
                
                // ✅ Jan 30, 2026: SCALE-BASED START (not priority-based)
                // Orders with FREE scales can start regardless of priority
                // Priority only matters within same-scale conflict groups
                const isLocked = scaleIsLocked;
                
                // Build tooltip message
                let tooltipMessage = "Start Order - Click to begin validation";
                if (isStarting) {
                  tooltipMessage = "⏳ Starting validation... Please wait";
                } else if (scaleIsLocked) {
                  tooltipMessage = `🔒 Scales locked by: ${waitingFor.join(', ')} - Wait for them to complete`;
                }
                
                return (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isLocked || isStarting) return;
                      onStartOrder(orderPo);
                    }}
                    disabled={isLocked || isStarting}
                    className={`flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 ${
                      isStarting
                        ? 'bg-yellow-500 text-white cursor-wait'
                        : isLocked 
                          ? 'opacity-50 cursor-not-allowed bg-gray-400'
                          : 'bg-green-500 hover:bg-green-600 text-white shadow-sm'
                    }`}
                    title={tooltipMessage}
                  >
                    {isStarting ? (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span>Starting...</span>
                      </>
                    ) : (
                      <>
                        <Play className="h-3 w-3" />
                        <span>Start</span>
                      </>
                    )}
                  </button>
                );
              })()
            )}

            {/* PAUSE BUTTON - Reference Design: Orange with Pause icon */}
            {order.status === 'InProgress' && onStopOrder && isAdmin && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  const orderId = order.po_number || String(order.id) || '';
                  onStopOrder(orderId);
                }}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 bg-orange-500 hover:bg-orange-600 !text-white shadow-sm"
                style={{ color: 'white !important' }}
                title="Pause Order"
              >
                <Square className="h-3 w-3" style={{ color: 'white' }} />
                <span style={{ color: 'white !important' }}>Pause</span>
              </button>
            )}
            
            {/* CONFIRM BUTTON - Reference Design: Blue */}
            {order.status === 'InProgress' && 
             ((order as any).confirmed_qty > 0) && 
             onManualConfirm && (
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  await onManualConfirm(order);
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 bg-blue-500 hover:bg-blue-600 !text-white shadow-sm"
                style={{ color: 'white !important' }}
                title="Manual Confirm - Send current accumulated production to SAP"
              >
                <span style={{ color: 'white !important' }}>Confirm</span>
              </button>
            )}
          </div>

          {/* Secondary action buttons */}
          <div className="flex gap-1">
            {/* PUSH CONFIRMATION BUTTON - Show for Completed orders (need SAP confirmation) and Validated orders */}
            {(order.status === 'Completed' || order.status === 'Validated') && onPushConfirmation && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onPushConfirmation(order);
                }}
                disabled={pushingConfirmation}
                className={`px-2 py-1 text-xs font-medium rounded transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed ${theme === 'light'
                    ? 'bg-green-500 text-white hover:bg-green-600 shadow-md'
                    : 'bg-green-500 text-white hover:bg-green-400 shadow-md'
                  }`}
                title="Push Confirmation to SAP"
                style={{ color: 'white !important' }}
              >
                {pushingConfirmation ? 'Pushing...' : 'Push Confirmation'}
              </button>
            )}
            {onViewValidationDetails && (order.status === 'Validated' || order.status === 'Completed' || order.status === 'Rejected') && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onViewValidationDetails(order);
                }}
                className={`px-2 py-1 text-xs font-medium rounded transition-all duration-200 hover:scale-105 ${theme === 'light'
                    ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                    : 'bg-purple-900/30 text-purple-300 hover:bg-purple-800/40'
                  }`}
                title="View Validation Details"
              >
                Details
              </button>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
};

// Fallback mock 

const statusOptions = ['All', 'Pending', 'InProgress'];

const ProcessOrderValidation = () => {
  // ✅ REMOVED: apiBase variable - now using getApiUrl() from apiConfig.ts
  // All API calls use getApiUrl() which reads from API_BASE_URL in apiConfig.ts

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

  // ✅ Feb 9, 2026: Role-based order access
  // Derive which order types the current user may see from their permissions / roles.
  // admin, manager, and generic operator can see everything.
  // milling_operator  -> MILLING only
  // packing_operator  -> PACKING only
  const userRoles = currentUser?.roles || [];
  const canAccessMilling = isAdmin
    || userRoles.includes('manager')
    || userRoles.includes('operator')
    || userRoles.includes('milling_operator');
  const canAccessPacking = isAdmin
    || userRoles.includes('manager')
    || userRoles.includes('operator')
    || userRoles.includes('packing_operator');
  const canAccessAll = canAccessMilling && canAccessPacking;



  // Helper function to test API connectivity
  const testApiConnectivity = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // Reduced timeout

      // Try multiple endpoints to test connectivity
      const endpoints = [
        '/api/health',
        '/api/orders',
        '/api/sap-sync/orders'
      ];

      for (const endpoint of endpoints) {
        try {
          const response = await apiFetch(getApiUrl(endpoint), {
            method: 'GET',
            signal: controller.signal
          });

          if (response.ok || response.status === 401 || response.status === 403) {
            // Server is responding (even with auth errors)
            clearTimeout(timeoutId);
          
            return true;
          }
        } catch (endpointError) {
         
          continue;
        }
      }

      clearTimeout(timeoutId);
      return false;
    } catch (err) {
     
      return false;
    }
  };

  // VPN Status
  const [vpnStatus, setVpnStatus] = useState<{connected: boolean, lastChecked: Date | null}>({connected: true, lastChecked: null});
  
  const checkVpnStatus = async () => {
    try {
      // Use controller to timeout quickly if network is down
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await apiFetch(getApiUrl('/api/vpn/status'), {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        setVpnStatus({connected: data.connected, lastChecked: new Date()});
      } else {
        setVpnStatus({connected: false, lastChecked: new Date()});
      }
    } catch (err) {
      setVpnStatus({connected: false, lastChecked: new Date()});
    }
  };

  useEffect(() => {
    checkVpnStatus();
    const interval = setInterval(checkVpnStatus, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const [orders, setOrders] = useState<Order[]>([]);
  const [statusFilter, setStatusFilter] = useState('All');
  const [activeOrderTab, setActiveOrderTab] = useState('all');

  // ✅ Feb 9, 2026: Set default tab based on user role when user data loads
  const defaultTabSetRef = React.useRef(false);
  useEffect(() => {
    if (!currentUser || defaultTabSetRef.current) return;
    defaultTabSetRef.current = true;
    if (!canAccessAll) {
      if (canAccessMilling && !canAccessPacking) {
        setActiveOrderTab('milling');
      } else if (canAccessPacking && !canAccessMilling) {
        setActiveOrderTab('packing');
      }
    }
  }, [currentUser, canAccessAll, canAccessMilling, canAccessPacking]);
  const [poSearchTerm, setPoSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validatingOrders, setValidatingOrders] = useState<Set<string>>(new Set());
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showRejectionModal, setShowRejectionModal] = useState(false);
  const [showManualConfirmationModal, setShowManualConfirmationModal] = useState(false);
  const [selectedOrderId, setSelectedOrderId] = useState<number>(0);
  const [selectedOrderForManualConfirm, setSelectedOrderForManualConfirm] = useState<Order | null>(null);
  const [manualConfirmData, setManualConfirmData] = useState({
    scrap: 0,
    confirmed_text: '',
    override_qty: null as number | null, // Allow manual override of quantity
    custom_byproducts: {
      scale1_qty: '' as string | number | null,
      scale2_qty: '' as string | number | null,
      scale3_qty: '' as string | number | null
    }
  });
  
  // Reprocess Modal State
  const [showReprocessModal, setShowReprocessModal] = useState(false);
  const [selectedErrorLog, setSelectedErrorLog] = useState<any>(null);
  const [reprocessData, setReprocessData] = useState({ scrap: 0, confirmed_text: '' });
  const [reprocessing, setReprocessing] = useState(false);
  
  // Resend Modal State (for VPN network errors)
  const [showResendModal, setShowResendModal] = useState(false);
  const [selectedResendLog, setSelectedResendLog] = useState<any>(null);
  const [resendData, setResendData] = useState({ scrap: 0, confirmed_text: '', force_resend: false });
  const [resending, setResending] = useState(false);

  // Payload Viewer Modal State
  const [showPayloadModal, setShowPayloadModal] = useState(false);
  const [selectedPayload, setSelectedPayload] = useState<any>(null);
  const [selectedPayloadPO, setSelectedPayloadPO] = useState<string>('');

  const openReprocessModal = (log: any) => {
    setSelectedErrorLog(log);
    // Initialize with data from payload if available
    const payload = log.payload?.sent_payload || {};
    setReprocessData({
      scrap: payload.scrap || 0,
      confirmed_text: payload.confirmed_text || ''
    });
    setShowReprocessModal(true);
  };

  const handleReprocess = async () => {
    if (!selectedErrorLog) return;
    
    setReprocessing(true);
    try {
      const response = await apiFetch(getApiUrl(`/api/error-log/${selectedErrorLog.id}/reprocess`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reprocessData)
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        showCustomAlert('Success', result.message, 'success');
        setShowReprocessModal(false);
        // Refresh logs if modal is open
        if (modalType === 'errorlog') openOrdersModal('errorlog');
        // Refresh counts
        loadKpiCounts();
      } else {
        showCustomAlert('Error', result.error || 'Reprocess failed', 'error');
      }
    } catch (err) {
      
      showCustomAlert('Error', 'Network error', 'error');
    } finally {
      setReprocessing(false);
    }
  };
  
  const handleResend = async () => {
    if (!selectedResendLog) return;
    
    setResending(true);
    try {
      const response = await apiFetch(getApiUrl(`/api/error-log/${selectedResendLog.id}/resend`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scrap: resendData.scrap,
          confirmed_text: resendData.confirmed_text,
          force_resend: resendData.force_resend
        })
      });
      
      const result = await response.json();
      
      if (result.ok || result.success) {
        addToast(`✅ Confirmation resent successfully for ${selectedResendLog.po_number}`, 'success');
        setShowResendModal(false);
        setResendData({ scrap: 0, confirmed_text: '', force_resend: false }); // Reset state
        // Refresh logs if modal is open
        if (modalType === 'errorlog') openOrdersModal('errorlog');
        // Refresh counts
        loadKpiCounts();
      } else if (result.error === 'duplicate') {
        // Show warning but keep modal open so user can enable force_resend
        addToast(`⚠️ ${result.message}`, 'warning');
        // Don't close modal - let user enable force_resend checkbox
      } else if (result.error === 'vpn_disconnected') {
        addToast(`⚠️ ${result.message}`, 'warning');
      } else {
        addToast(`❌ Failed to resend: ${result.message || result.error}`, 'error');
      }
    } catch (err: any) {
     
      addToast(`❌ Failed to resend: ${err.message}`, 'error');
    } finally {
      setResending(false);
    }
  };

  const [sendingManualConfirm, setSendingManualConfirm] = useState(false);
  const [selectedOrderDetails, setSelectedOrderDetails] = useState<{
    po_number?: string;
    material?: string;
    quantity?: number;
    unit?: string;
  } | null>(null);
  const [modalDefaults, setModalDefaults] = useState<Partial<ValidationRequest & { expected_quantity?: number; unit?: string }> | undefined>(undefined);
  const [showOrdersModal, setShowOrdersModal] = useState(false);
  const [modalOrders, setModalOrders] = useState<Order[]>([]);
  const [modalTitle, setModalTitle] = useState('');
  const [modalType, setModalType] = useState<'confirmed' | 'completed' | 'rejected' | 'inprogress' | 'errorlog' | 'offline'>('confirmed');
  const [searchTerm, setSearchTerm] = useState('');

  // Offline Orders Management State
  const [selectedOfflineOrders, setSelectedOfflineOrders] = useState<Set<number>>(new Set());
  const [offlineEdits, setOfflineEdits] = useState<Record<number, {scrap?: number, confirmed_text?: string}>>({});
  const [sendingOffline, setSendingOffline] = useState(false);

  const handleOfflineSelection = (id: number) => {
    const newSelected = new Set(selectedOfflineOrders);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedOfflineOrders(newSelected);
  };

  const selectAllOffline = () => {
    const allIds = modalOrders.map(o => o.id);
    setSelectedOfflineOrders(new Set(allIds));
  };

  const deselectAllOffline = () => {
    setSelectedOfflineOrders(new Set());
  };

  const handleOfflineEdit = (id: number, field: 'scrap' | 'confirmed_text', value: any) => {
    setOfflineEdits(prev => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: value
      }
    }));
  };

  const saveOfflineChanges = async (id: number) => {
    const edits = offlineEdits[id];
    if (!edits) return;

    try {
      const response = await apiFetch(getApiUrl(`/api/offline-confirmations/${id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(edits)
      });
      
      if (!response.ok) throw new Error('Update failed');
      
      // Update local state
      setModalOrders(prev => prev.map(o => {
        if (o.id === id) {
          return { ...o, ...edits };
        }
        return o;
      }));
      
      // Clear edits for this item
      const newEdits = { ...offlineEdits };
      delete newEdits[id];
      setOfflineEdits(newEdits);
      
    } catch (err) {
      
      showCustomAlert('Error', 'Failed to update order details', 'error');
    }
  };

  const sendOfflineOrders = async (ids: number[]) => {
    if (ids.length === 0) return;
    
    // First save any pending edits for these IDs
    for (const id of ids) {
      if (offlineEdits[id]) {
        await saveOfflineChanges(id);
      }
    }
    
    setSendingOffline(true);
    try {
      // Check VPN first
      await checkVpnStatus();
      if (!vpnStatus.connected) {
        showCustomAlert('Offline Mode', 'Cannot send orders: VPN is disconnected.', 'warning');
        setSendingOffline(false);
        return;
      }

      const response = await apiFetch(getApiUrl('/api/offline-confirmations/send'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_ids: ids })
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        showCustomAlert('Success', result.message, 'success');
        // Refresh list
        openOrdersModal('offline');
        // Clear selection
        setSelectedOfflineOrders(new Set());
        // Refresh KPI counts
        loadKpiCounts();
      } else {
        showCustomAlert('Error', result.error || 'Failed to send orders', 'error');
      }
    } catch (err) {
     
      showCustomAlert('Error', 'Network error occurred', 'error');
    } finally {
      setSendingOffline(false);
    }
  };

  // Send manually confirmed offline order (using scrap/confirmed_text from table)
  const sendManualConfirmedOrder = async (order: any) => {
    setSendingOffline(true);
    try {
      // Get current scrap and confirmed_text from edits or order
      const currentScrap = offlineEdits[order.id]?.scrap ?? order.scrap ?? 0;
      const currentConfirmedText = offlineEdits[order.id]?.confirmed_text ?? order.confirmed_text ?? '';

      // First save any pending edits for this order
      if (offlineEdits[order.id]) {
        await saveOfflineChanges(order.id);
      }

      // Update the offline confirmation with current values (in case they were edited)
      if (currentScrap !== order.scrap || currentConfirmedText !== order.confirmed_text) {
        const updateResponse = await apiFetch(getApiUrl(`/api/offline-confirmations/${order.id}`), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scrap: currentScrap,
            confirmed_text: currentConfirmedText
          })
        });

        if (!updateResponse.ok) {
          throw new Error('Failed to update order details');
        }
      }

      // Check VPN
      await checkVpnStatus();
      if (!vpnStatus.connected) {
        showCustomAlert('Offline Mode', 'Cannot send orders: VPN is disconnected.', 'warning');
        setSendingOffline(false);
        return;
      }

      // Send to SAP
      const sendResponse = await apiFetch(getApiUrl('/api/offline-confirmations/send'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_ids: [order.id] })
      });
      
      const result = await sendResponse.json();
      
      if (sendResponse.ok && result.success) {
        showCustomAlert('Success', 'Order manually confirmed and sent to SAP', 'success');
        // Refresh list
        openOrdersModal('offline');
        // Refresh KPI counts
        loadKpiCounts();
      } else {
        showCustomAlert('Error', result.error || 'Failed to send order', 'error');
      }
    } catch (err) {
      
      showCustomAlert('Error', 'Network error occurred', 'error');
    } finally {
      setSendingOffline(false);
    }
  };

  // Modal pagination state
  const [modalCurrentPage, setModalCurrentPage] = useState(1);
  const [modalItemsPerPage, setModalItemsPerPage] = useState(10);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [totalOrders, setTotalOrders] = useState(0);

  // Progress dialog state
  const [showProgressDialog, setShowProgressDialog] = useState(false);
  const [pushingConfirmation, setPushingConfirmation] = useState(false);
  const [editingScales, setEditingScales] = useState<{
    scale1_qty: number | null;
    scale2_qty: number | null;
    scale3_qty: number | null;
  }>({ scale1_qty: null, scale2_qty: null, scale3_qty: null });
  const [savingScales, setSavingScales] = useState(false);
  const [selectedOrderProgress, setSelectedOrderProgress] = useState<{
    po_number: string;
    material: string;
    version?: string;
    expected_tons: number;
    current_tons: number;
    remaining_tons: number;
    progress_pct: number;
    status: string;
    last_tick: string | null;
    order_type?: string;
    packing_line?: string;
    unit?: string;
    equipment_list?: string[];
    equipment_details?: Record<string, any>;
    scale_lock_status?: {
      scales_locked: boolean;
      locked_scales: Record<string, string>;
      locking_orders: string[];
      message: string | null;
    };
    scale_details?: Array<{
      scale_number: number;
      scale_tag: string;
      baseline: number;
      current_reading: number;
      delta: number;
      description: string;
      is_locked?: boolean;
      locked_by?: string | null;
    }>;
    // ✅ Byproduct scales (editable)
    scale1?: string;
    scale1_qty?: number;
    scale2?: string;
    scale2_qty?: number;
    scale3?: string;
    scale3_qty?: number;
    // ✅ Byproduct details with baseline/current/delta
    byproduct_details?: Record<string, {
      scale_key: string;
      baseline: number;
      current: number;
      delta: number;
    }>;
    // ✅ Shift weight fields for manual confirmation calculation
    weight_shift_a?: number;
    weight_shift_b?: number;
    weight_shift_c?: number;
    confirmed_shift_a?: number;
    confirmed_shift_b?: number;
    confirmed_shift_c?: number;
    current_shift?: string;
    variance?: number;
    variance_pct?: number;
    tolerance_pct?: number;
    lower_limit?: number;
    upper_limit?: number;
    within_tolerance?: boolean;
  } | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const { theme } = useTheme();

  // Auto Validator state
  const [autoValidatorStatus, setAutoValidatorStatus] = useState({
    running: false,
    current_po: null as string | null,
    progress_pct: 0,
    expected_tons: 0,
    delta_tons: 0,
    baseline: null as number | null,
    last_tick: null as string | null
  });

  // Show Start/Stop Auto Validation buttons when enabled in Settings > Demo tab (localStorage)
  const [showAutoValidationButton] = useState(
    () => typeof window !== 'undefined' && localStorage.getItem('show_auto_validation_button') === 'true'
  );

  // ⭐ CRITICAL: Track if auto-validation was manually started by user
  const [autoValidationManuallyStarted, setAutoValidationManuallyStarted] = useState(false);

  // ⭐ SAFETY: Global flag to prevent any accidental auto-starts
  const [autoValidationLocked, setAutoValidationLocked] = useState(false);
  const [isStartingValidation, setIsStartingValidation] = useState(false);
  const [isStoppingValidation, setIsStoppingValidation] = useState(false);
  const [orderProgress, setOrderProgress] = useState<Record<string, number>>({});
  const [toasts, setToasts] = useState<Array<{ id: string, message: string, type: 'success' | 'error' | 'info' | 'warning' }>>([]);
  const [previousStatus, setPreviousStatus] = useState<typeof autoValidatorStatus | null>(null);
  const [completedOrders, setCompletedOrders] = useState<Set<string>>(new Set());
  
  // ✅ PERSISTENT: Use localStorage to prevent duplicate "Order validated!" notifications
  const getStoredCompletedOrders = (): Set<string> => {
    try {
      const stored = localStorage.getItem('hercules_validated_orders_notified');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Only keep entries from last 24 hours
        const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
        const filtered = parsed.filter((item: any) => item.timestamp > oneDayAgo);
        return new Set(filtered.map((item: any) => item.orderId));
      }
    } catch (error) {
     
    }
    return new Set();
  };
  
  const saveValidatedOrderNotification = (orderId: string) => {
    try {
      const stored = localStorage.getItem('hercules_validated_orders_notified');
      const items = stored ? JSON.parse(stored) : [];
      items.push({ orderId, timestamp: Date.now() });
      // Keep only last 100 items
      const recentItems = items.slice(-100);
      localStorage.setItem('hercules_validated_orders_notified', JSON.stringify(recentItems));
    } catch (error) {
      
    }
  };
  
  const validatedOrdersNotifiedRef = useRef<Set<string>>(getStoredCompletedOrders());

  // Custom popup state
  const [showCustomPopup, setShowCustomPopup] = useState(false);
  const [popupData, setPopupData] = useState<{
    title: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    onConfirm?: () => void;
  } | null>(null);

  // Validation details modal state
  const [showValidationDetails, setShowValidationDetails] = useState(false);
  const [validationDetails, setValidationDetails] = useState<any>(null);

  // Classify all orders state
  const [classifying, setClassifying] = useState(false);

  // Priority state management
  const [orderPriorities, setOrderPriorities] = useState<Record<number, number>>({});
  
  // ✅ FIX: Track recent drag operations to skip polling refreshes
  const lastDragTimeRef = useRef<number>(0);
  const DRAG_COOLDOWN_MS = 5000; // Skip polling for 5 seconds after drag
  
  // ✅ FIX: Track validation refresh to prevent multiple refreshes for same validation event
  const lastValidationRefreshTimeRef = useRef<number>(0);
  const validationRefreshingOrdersRef = useRef<Set<string>>(new Set()); // Orders currently being refreshed
  const VALIDATION_COOLDOWN_MS = 5000; // Skip duplicate refreshes for 5 seconds
  
  // ✅ FIX: Track when auto-validator was stopped to prevent UI fluctuation
  const lastStopTimeRef = useRef<number>(0);
  const STOP_COOLDOWN_MS = 15000; // Skip polling for 15 seconds after stop to allow database to stabilize
  
  // ✅ AGGRESSIVE FIX: Completely block ALL order state updates during stop
  const stopLockdownActiveRef = useRef<boolean>(false);
  
  // ✅ NUCLEAR FIX: Track orders that MUST show Pending regardless of state
  // This overrides any state updates at the UI level
  const forcedPendingOrdersRef = useRef<Set<string>>(new Set());
  const [forcedPendingVersion, setForcedPendingVersion] = useState(0); // Triggers re-render when forced set changes
  
  // Helper function to check if orders can be updated
  const canUpdateOrders = useCallback(() => {
    if (stopLockdownActiveRef.current) {
     
      return false;
    }
    const timeSinceStop = Date.now() - lastStopTimeRef.current;
    if (timeSinceStop < STOP_COOLDOWN_MS) {
   
      return false;
    }
    return true;
  }, []);
  
  // ✅ Helper function to get the display status for an order (respects forced pending)
  const getOrderDisplayStatus = useCallback((order: Order): string => {
    const orderId = order.po_number || String(order.id);
    if (forcedPendingOrdersRef.current.has(orderId)) {
      return 'Pending';
    }
    return order.status;
  }, []);

  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Load priority order from database (source of truth)
  const loadPriorityOrder = async () => {
    try {
   
      try {
        const response = await apiFetch(getApiUrl('/api/orders/priority'));
        if (response.ok) {
          const priorities = await response.json();
        

          // Update state with database priorities
          setOrderPriorities(priorities);

          // Sync localStorage with database (database is source of truth)
          localStorage.setItem('orderPriorities', JSON.stringify(priorities));
        } else {
         
          // Fallback to localStorage if API fails
          const savedPriorities = localStorage.getItem('orderPriorities');
          if (savedPriorities) {
            const parsedPriorities = JSON.parse(savedPriorities);
            setOrderPriorities(parsedPriorities);
            
          }
        }
      } catch (apiErr) {
        
        // Fallback to localStorage if API fails
        const savedPriorities = localStorage.getItem('orderPriorities');
        if (savedPriorities) {
          const parsedPriorities = JSON.parse(savedPriorities);
          setOrderPriorities(parsedPriorities);
         
        }
      }
    } catch (err) {
     
    }
  };

  // Save priority order to API and localStorage
  const savePriorityOrder = async (newPriorities: Record<number, number>) => {
    try {
     

      // Save to API FIRST (database is source of truth)
      try {
        const response = await apiFetch(getApiUrl('/api/orders/priority'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(newPriorities),
        });

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          // Response is not JSON (likely HTML error page)
          const textResponse = await response.text();
          console.error('❌ API returned non-JSON response:', {
            status: response.status,
            statusText: response.statusText,
            contentType: contentType,
            preview: textResponse.substring(0, 200)
          });
          throw new Error(`Server error (${response.status}): Expected JSON but received ${contentType || 'unknown'}. The endpoint may not be registered or there's a server error.`);
        }

        if (response.ok) {
          const result = await response.json();
         

          // After successful API save, reload priorities from database
          await loadPriorityOrder();

          // Reload orders to get updated priorities from database
          await loadOrders();

          // Update local state with database priorities (source of truth)
          const dbPriorities = await apiFetch(getApiUrl('/api/orders/priority')).then(r => {
            if (r.ok) {
              const contentType = r.headers.get('content-type');
              if (contentType && contentType.includes('application/json')) {
                return r.json();
              }
            }
            return {};
          });
          if (Object.keys(dbPriorities).length > 0) {
            setOrderPriorities(dbPriorities);
            localStorage.setItem('orderPriorities', JSON.stringify(dbPriorities));
           
          }
        } else {
          // Try to parse JSON error
          try {
            const errorData = await response.json();
            console.error('❌ Failed to save priority order to API:', response.status, errorData);
            throw new Error(errorData.error || `Failed to save priorities: ${response.statusText}`);
          } catch (parseErr) {
            // If JSON parsing fails, use status text
            throw new Error(`Failed to save priorities: HTTP ${response.status} ${response.statusText}`);
          }
        }
      } catch (apiErr: any) {
        console.error('❌ API save failed:', apiErr);
        // Re-throw with a more user-friendly message
        if (apiErr.message) {
          throw apiErr;
        } else {
          throw new Error(`Failed to save priorities: ${apiErr.toString()}`);
        }
      }
    } catch (err) {
      console.error('❌ Failed to save priority order:', err);
      throw err; // Re-throw so caller can handle the error
    }
  };

  // ✅ NEW: Save priorities without reloading orders (for drag-drop optimistic updates)
  const savePriorityOrderWithoutReload = async (newPriorities: Record<number, number>) => {
    

    const response = await apiFetch(getApiUrl('/api/orders/priority'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newPriorities),
    });

    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      throw new Error(`Server error (${response.status}): Expected JSON`);
    }

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Failed to save priorities`);
    }

    
    localStorage.setItem('orderPriorities', JSON.stringify(newPriorities));
  };

  // Handle drag end: update hercules_priority (queue position) only. Display stays SAP priority_id (e.g. 3).
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    lastDragTimeRef.current = Date.now();

    if (!over || active.id === over.id) return;

    const activeOrderType = activeOrderTab === 'milling' ? 'MILLING' : activeOrderTab === 'packing' ? 'PACKING' : null;
    const draggedOrder = orders.find(o => o.id === active.id);
    const targetOrderType = activeOrderType || (draggedOrder as any)?.order_type;

    if (draggedOrder?.status === 'InProgress') {
      addToast('Running orders cannot be moved. Pause the order first.', 'warning');
      return;
    }

    const ordersOfSameType = orders.filter(o => (o as any).order_type === targetOrderType);
    const ordersOfOtherType = orders.filter(o => (o as any).order_type !== targetOrderType);
    const oldIndex = ordersOfSameType.findIndex((item) => item.id === active.id);
    const newIndex = ordersOfSameType.findIndex((item) => item.id === over.id);

    if (oldIndex === -1 || newIndex === -1) {
      addToast('Cannot drag between Milling and Packing orders', 'warning');
      return;
    }

    if (draggedOrder?.status === 'Pending') {
      const hasConflict = (draggedOrder as any).has_priority_conflict === true;
      if (hasConflict) {
        const conflictWaitingFor = (draggedOrder as any).conflict_waiting_for || [];
        const targetOrder = ordersOfSameType[newIndex];
        if (targetOrder?.status === 'InProgress' && newIndex < oldIndex) {
          addToast('Pending orders cannot move above running orders in the same conflict group.', 'warning');
          return;
        }
        const runningOrdersInConflict = ordersOfSameType.filter(o =>
          o.status === 'InProgress' && conflictWaitingFor.includes(o.po_number || (o as any).order_id)
        );
        for (const runningOrder of runningOrdersInConflict) {
          const runningIndex = ordersOfSameType.findIndex(o => o.id === runningOrder.id);
          if (newIndex <= runningIndex) {
            addToast(`Pending orders cannot move above running order ${runningOrder.po_number || (runningOrder as any).order_id}.`, 'warning');
            return;
          }
        }
      }
    }

    // =========================================================
    // VALIDATION RULE 3: PAUSED orders can move anywhere (no restriction)
    // =========================================================
    // (No validation needed for Paused orders - they have full flexibility)

    // ✅ Jan 30, 2026: SEQUENTIAL PRIORITY on drag-and-drop
    // When reordering, assign sequential priorities (1, 2, 3...) based on new position
    // This ensures the database reflects the actual order

    // Reorder for visual update
    const reorderedSameType = arrayMove([...ordersOfSameType], oldIndex, newIndex);

    // ✅ FIX: Assign SEQUENTIAL priorities based on new order position
    // All orders get new priorities: 1, 2, 3, 4...
    const newPriorities: Record<number, number> = {};
    const updatedSameTypeOrders = reorderedSameType.map((item, index) => {
      const newPriority = index + 1;  // 1-based priority
      newPriorities[item.id] = newPriority;
      return { ...item, priority: newPriority };
    });

    // Combine: updated same-type orders + unchanged other-type orders
    const allUpdatedOrders = [...updatedSameTypeOrders, ...ordersOfOtherType];

    // Sort by status first, then by priority within each type
    allUpdatedOrders.sort((a, b) => {
      // ✅ Feb 5, 2026: Completed before Validated (queue UX)
      const statusOrder: Record<string, number> = { 'InProgress': 0, 'Pending': 1, 'Completed': 2, 'Validated': 3 };
      const statusA = statusOrder[a.status] ?? 4;
      const statusB = statusOrder[b.status] ?? 4;

      if (statusA !== statusB) return statusA - statusB;

      // ✅ Sort by database priority (group-wise)
      const priorityA = (a as any).priority ?? 999;
      const priorityB = (b as any).priority ?? 999;

      if (priorityA !== priorityB) return priorityA - priorityB;

      // Within same priority group, sort by id (FIFO)
      return a.id - b.id;
    });

    // ✅ OPTIMISTIC UPDATE: Update local state immediately
    setOrders(allUpdatedOrders);
    setOrderPriorities(prev => ({ ...prev, ...newPriorities }));

    try {
      // Save to database WITHOUT reloading orders
      // ✅ Jan 30, 2026: Sequential priorities assigned based on position
      await savePriorityOrderWithoutReload(newPriorities);
      addToast(`Priorities updated successfully`, "success");

      // ✅ Reload orders to refresh display
      setTimeout(() => loadOrders(), 500);
    } catch (error: any) {
      console.error('❌ Failed to save priorities:', error);
      addToast(`Failed to update priorities: ${error.message || 'Unknown error'}`, "error");
      // Only reload on ERROR to restore correct state from database
      await loadOrders();
    }
  };

  // Helper function to classify order based on MATERIAL code
  const classifyOrderByMaterial = (material: string): { order_type: string; confidence: string } => {
    if (!material || material.length < 2) {
      
      return { order_type: 'Unknown', confidence: '0%' };
    }

    // Remove leading zeros and get the first two significant digits
    const trimmedMaterial = material.replace(/^0+/, '');
    const firstTwoDigits = trimmedMaterial.substring(0, 2);

    

    switch (firstTwoDigits) {
      case '13':
        
        return { order_type: 'MILLING', confidence: '100%' };
      case '14':
      
        return { order_type: 'PACKING', confidence: '100%' };
      default:
       
        return { order_type: 'Unknown', confidence: '0%' };
    }
  };

  // Load orders from process_orders table with priority + FIFO ordering
  const loadOrders = async () => {
    try {
      // ✅ AGGRESSIVE FIX: Skip if stop lockdown is active
      if (stopLockdownActiveRef.current) {
        
        return;
      }
      
      setLoading(true);
      setError(null);

      // Calculate offset for pagination
      const offset = (currentPage - 1) * itemsPerPage;

      // Build status filter for API - include Completed and Validated orders so they remain visible
      const statusFilterParam = statusFilter === 'All' ? 'Pending,InProgress,Completed,Validated' : statusFilter;

      // ✅ Build order_type filter for API - filter by type BEFORE pagination so priority-1 orders show at top
      const orderTypeParam = activeOrderTab === 'milling' ? '&order_type=MILLING' 
                           : activeOrderTab === 'packing' ? '&order_type=PACKING' 
                           : '';

      // Fetch orders for validation using the new SAP sync endpoint with pagination and status filtering
      const response = await apiFetch(getApiUrl(`/api/sap-sync/orders?statuses=${statusFilterParam}&limit=${itemsPerPage}&offset=${offset}${orderTypeParam}`));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const responseData = await response.json();
      const apiOrders = responseData.ok ? responseData.orders : [];
      const totalCount = responseData.total || apiOrders.length;

      

      // ✅ Fetch conflict info from backend
      let conflictInfo: Record<string, any> = {};
      try {
        const conflictResponse = await apiFetch(getApiUrl(`/api/orders/with-conflicts?status=${statusFilterParam}`));
        if (conflictResponse.ok) {
          const conflictData = await conflictResponse.json();
          if (conflictData.success && conflictData.orders) {
            // Build a map of po_number -> conflict info
            conflictData.orders.forEach((order: any) => {
              conflictInfo[order.po_number] = {
                has_priority_conflict: order.has_priority_conflict || false,
                conflict_group_priority: order.conflict_group_priority,
                conflict_can_run: order.conflict_can_run,
                conflict_waiting_for: order.conflict_waiting_for || [],
                conflict_shared_scales: order.conflict_shared_scales || [],
                conflict_shared_with: order.conflict_shared_with || [],
                conflict_group_id: order.conflict_group_id
              };
            });
      
            if (conflictData.conflict_groups?.length > 0) {
              
            }
          }
        }
      } catch (conflictErr) {
        console.warn('⚠️ Could not load conflict info:', conflictErr);
      }

    

      // Update total orders count
      setTotalOrders(totalCount);

      // ✅ FIX: Use API priority directly as source of truth (database values)
      // Do NOT merge with potentially stale orderPriorities state - that causes race conditions
      // Extract priorities from API orders for state sync
      const apiPriorities: Record<number, number> = {};
      apiOrders.forEach((order: any) => {
        if (order.id && order.priority !== undefined && order.priority !== null) {
          apiPriorities[order.id] = order.priority;
        }
      });

      // Update state with priorities from database (for drag-drop functionality)
      setOrderPriorities(apiPriorities);

      // Sync localStorage with database priorities
      localStorage.setItem('orderPriorities', JSON.stringify(apiPriorities));

      // Auto-classify orders based on MATERIAL code if they don't have order_type
      // ✅ Also merge conflict info from backend
      // ✅ FIX: Use order.priority directly from API (database is source of truth)
      const classifiedOrders = apiOrders.map((order: any) => {
        let classifiedOrder = order;
        
        if (!order.order_type || order.order_type === 'Unknown') {
      
          const classification = classifyOrderByMaterial(order.material || '');
          
          classifiedOrder = { ...order, order_type: classification.order_type };
        }
        
        // ✅ FIX: Use priority directly from API response (database is source of truth)
        // Fallback to 999 only if priority is not set in database
        // Ensure priority is always a number for proper sorting
        const rawPriority = order.priority;
        const orderPriority = typeof rawPriority === 'number' ? rawPriority : 
                             (rawPriority !== undefined && rawPriority !== null ? Number(rawPriority) : 999);
        classifiedOrder = { ...classifiedOrder, priority: isNaN(orderPriority) ? 999 : orderPriority };
        
        // ✅ Merge conflict info from backend
        const orderConflict = conflictInfo[order.po_number];
        if (orderConflict) {
          classifiedOrder = {
            ...classifiedOrder,
            has_priority_conflict: orderConflict.has_priority_conflict,
            conflict_group_priority: orderConflict.conflict_group_priority,
            conflict_can_run: orderConflict.conflict_can_run,
            conflict_waiting_for: orderConflict.conflict_waiting_for,
            conflict_shared_scales: orderConflict.conflict_shared_scales,
            conflict_shared_with: orderConflict.conflict_shared_with,
            conflict_group_id: orderConflict.conflict_group_id
          };
        }
        
        return classifiedOrder;
      });

      // ✅ FIX: Sort by STATUS first (InProgress on top), then by database priority
      // This ensures InProgress orders are always visible at the top of the table
      const sortedOrders = classifiedOrders.sort((a: Order, b: Order) => {
        // ✅ Primary sort: by status (InProgress first for visibility)
        const statusOrder: Record<string, number> = { 'InProgress': 0, 'Pending': 1, 'Completed': 2, 'Validated': 3 };
        const statusA = statusOrder[a.status] ?? 4;
        const statusB = statusOrder[b.status] ?? 4;
        
        if (statusA !== statusB) {
          return statusA - statusB;
        }
        
        // ✅ Jan 30, 2026: Sort by database priority (consistent with backend pagination)
        // Lower priority number = higher priority (1 is top priority)
        const priorityA = (a as any).priority ?? 999;
        const priorityB = (b as any).priority ?? 999;
        
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }
        
        // Tiebreaker: sort by id ascending (older orders first)
        return a.id - b.id;
      });

      // Filter out orders where confirmation matches target (final confirmation sent to SAP)
      // ✅ CRITICAL FIX (Jan 23, 2026): Use backend-provided target (already converted for PACKING)
      const filteredOrders = sortedOrders.filter((order: any) => {
        const orderType = order.order_type;
        const lastConfirmedQty = order.last_confirmed_qty || 0;
        // Use backend-provided target (already converted for PACKING orders)
        let targetQty = order.target || 0;

        if (orderType === 'MILLING' && targetQty <= 0) {
          // Fallback for MILLING if target not provided
          targetQty = order.expected_weight || order.quantity || 0;
        } else if (orderType === 'PACKING' && targetQty <= 0) {
          // ✅ FIX (Jan 23, 2026): Fallback for PACKING if target not provided
          targetQty = order.quantity || 0;
        }

        // Hide order if confirmation matches target (final confirmation sent)
        // Use a small tolerance (0.01) for floating point comparison
        const tolerance = 0.01;
        const matchesTarget = Math.abs(lastConfirmedQty - targetQty) < tolerance;

        if (matchesTarget) {
   
          return false;
        }

        return true;
      });

    
      setOrders(filteredOrders);
      // ✅ CRITICAL FIX: Do NOT clear completedOrders on every reload
      // This was causing duplicate "Order validated!" notifications
      // Only clear entries for orders that are no longer validated/completed
      const currentValidatedIds = new Set<string>(
        filteredOrders
          .filter((o: any) => o.status === 'Validated' || o.status === 'Completed' || o.status === 'Confirmed')
          .map((o: any) => String(o.po_number || o.id))
      );
      setCompletedOrders(prev => {
        const cleaned = new Set<string>();
        // Keep entries that are still validated
        prev.forEach(id => {
          if (currentValidatedIds.has(id)) {
            cleaned.add(id);
          }
        });
        // Also add any currently validated orders to prevent future notifications
        currentValidatedIds.forEach(id => cleaned.add(id));
        return cleaned;
      });
      
      // ✅ CRITICAL FIX: Clear stale orderProgress entries to prevent showing old cached progress
      // Only keep progress for orders that:
      // 1. Actually exist in the current list
      // 2. Are NOT in Pending status (Pending orders should always show fresh 0% progress)
      const currentOrderIds = new Set(filteredOrders.map((o: any) => o.po_number || String(o.id)));
      const pendingOrderIds = new Set(
        filteredOrders
          .filter((o: any) => o.status === 'Pending')
          .map((o: any) => o.po_number || String(o.id))
      );
      
      setOrderProgress(prev => {
        const cleaned: Record<string, number> = {};
        // Only keep entries for orders that still exist AND are not Pending
        for (const [orderId, progress] of Object.entries(prev)) {
          if (currentOrderIds.has(orderId) && !pendingOrderIds.has(orderId)) {
            cleaned[orderId] = progress;
          }
        }
        // Log if any stale entries were removed
        const removedCount = Object.keys(prev).length - Object.keys(cleaned).length;
        if (removedCount > 0) {
          
        }
        return cleaned;
      });
    } catch (err) {
      console.error('Failed to load orders:', err);
      setError('Failed to load orders from server.');
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  // Load priorities on component mount (database is source of truth)
  useEffect(() => {
    loadPriorityOrder();
  }, []);

  // Load orders when filter changes
  useEffect(() => {
    setCurrentPage(1); // Reset to first page when filter changes
    loadOrders();
  }, [statusFilter]);

  // Load orders when order type tab changes (Milling/Packing/All)
  useEffect(() => {
    setCurrentPage(1); // Reset to first page when tab changes
    loadOrders();
  }, [activeOrderTab]);

  // Load orders when pagination parameters change
  useEffect(() => {
    loadOrders();
  }, [currentPage, itemsPerPage]);

  // Dev helper: Seed demo order
  const seedDemoOrder = async () => {
    try {
      const response = await apiFetch(getApiUrl('/api/dev/seed-order'), {
        method: 'POST'
      });
      const data = await response.json();
      if (data.ok) {
        await loadOrders();
        setSelectedOrderId(data.order_id);
      }
    } catch (err) {
      console.error('Failed to seed demo order:', err);
      setError('Failed to seed demo order');
    }
  };

  // Dev helper: Load demo receipts
  const loadDemoReceipts = async (pass = true) => {
    try {
      const response = await apiFetch(getApiUrl(`/api/dev/demo-receipts/${pass ? 'pass' : 'fail'}`));
      const data = await response.json();
      setModalDefaults(data);
      setShowValidationModal(true);
    } catch (err) {
      console.error('Failed to load demo receipts:', err);
      setError('Failed to load demo receipts');
    }
  };

  // Open validation modal
  const openValidationModal = (orderId: number, preset?: typeof modalDefaults) => {
    setSelectedOrderId(orderId);

    // Find the order data to pre-populate the modal
    const order = orders.find(o => o.id === orderId);
    if (order) {
      setModalDefaults({
        po_number: order.po_number,
        material_code: order.material,
        expected_quantity: order.quantity || 0, // Add expected quantity
        expected_weight: (order as any).expected_weight || 0, // Add expected weight from table
        confirmed_quantity: (order as any).confirmed_qty || 0, // Add confirmed quantity
        unit: order.unit || 'TO', // Add unit
        confirmed_text: (order as any).confirmed_text || '', // Add confirmed text
        scrap: (order as any).scrap || 0, // Add scrap quantity
        ...preset // Override with any preset data
      });
    } else if (preset) {
      setModalDefaults(preset);
    }

    setShowValidationModal(true);
  };

  // Close validation modal
  const closeValidationModal = () => {
    setShowValidationModal(false);
    setSelectedOrderId(0);
    setModalDefaults(undefined);
  };

  const classifyOrder = async (poNumber: string) => {
    try {
      

      // Find the order in the current orders list
      const order = orders.find(o => o.po_number === poNumber);
      if (!order) {
        throw new Error(`Order ${poNumber} not found`);
      }

      // Classify based on MATERIAL code
      const classification = classifyOrderByMaterial(order.material || '');

  

      // Show classification result
      addToast(`Order ${poNumber} classified as ${classification.order_type} (${classification.confidence} confidence)`, 'success');

      // Update the order in the local state
      setOrders(prevOrders =>
        prevOrders.map(o =>
          o.po_number === poNumber
            ? { ...o, order_type: classification.order_type } as any
            : o
        )
      );

      return classification;
    } catch (err: any) {
      console.error('❌ Failed to classify order:', err);
      addToast(`Failed to classify order: ${err.message}`, 'error');
      return null;
    }
  };

  // Manual start order function
  // const startOrderManually = async (poNumber: string) => {
  //   try {
  //     console.log(`🔄 Starting order ${poNumber}...`);

  //     const response = await fetch(`${apiBase}/api/orders/${poNumber}/start`, {
  //       method: 'POST',
  //       headers: { 'Content-Type': 'application/json' }
  //     });

  //     console.log(`📡 Start order response status: ${response.status}`);

  //     if (!response.ok) {
  //       let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

  //       // Try to parse JSON error response
  //       try {
  //         const contentType = response.headers.get('content-type');
  //         if (contentType && contentType.includes('application/json')) {
  //       const errorData = await response.json();
  //           errorMessage = errorData.message || errorData.error || errorMessage;
  //         } else {
  //           // If not JSON, it might be HTML error page
  //           const textResponse = await response.text();
  //           console.log('⚠️ Non-JSON error response:', textResponse.substring(0, 200));
  //           errorMessage = `Server error (${response.status}): ${response.statusText}`;
  //         }
  //       } catch (parseError) {
  //         console.log('⚠️ Could not parse error response:', parseError);
  //         errorMessage = `Server error (${response.status}): ${response.statusText}`;
  //       }

  //       throw new Error(errorMessage);
  //     }

  //     // Parse successful response
  //     const contentType = response.headers.get('content-type');
  //     if (contentType && contentType.includes('application/json')) {
  //     const data = await response.json();
  //       console.log('✅ Start order success:', data);

  //     addToast(
  //         `✅ Order ${poNumber} started! Type: ${data.order_type || 'Unknown'}, Equipment: ${data.equipment ? data.equipment.join(', ') : 'N/A'}`,
  //       'success'
  //     );
  //     } else {
  //       console.log('⚠️ Non-JSON success response');
  //       addToast(`✅ Order ${poNumber} started successfully!`, 'success');
  //     }

  //     await loadOrders();

  //   } catch (err: any) {
  //     console.error('❌ Failed to start order:', err);
  //     addToast(`Failed to start order: ${err.message}`, 'error');
  //   }
  // };

  // Manual start order function with SCADA baseline capture
  const startOrderManually = async (poNumber: string) => {
    try {
      

      // ✅ FIX: Add to Set instead of setting single value
      setValidatingOrders(prev => new Set(Array.from(prev).concat([poNumber])));

      const response = await apiFetch(getApiUrl(`/api/orders/${poNumber}/start`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        const responseStatus = response.status; // ✅ Store status for later use

        try {
          // ✅ Try to get the response text first
          const responseText = await response.text();
         
          
          // ✅ Try to parse as JSON
          try {
            const errorData = JSON.parse(responseText);
            // ✅ Check multiple possible fields for error message
            errorMessage = errorData.message || 
                          errorData.error || 
                          errorData.detail || 
                          errorData.description ||
                          (errorData.errors && errorData.errors[0] && errorData.errors[0].message) ||
                          errorMessage;
           
          } catch (jsonError) {
            // ✅ If not JSON, use the text directly if it's not empty and not HTML
            if (responseText && responseText.trim() && !responseText.includes('<!DOCTYPE') && !responseText.startsWith('<html')) {
              errorMessage = responseText.trim();
              
            }
          }
        } catch (parseError) {
          
        }

        // ✅ Attach status to error for later use
        const error = new Error(errorMessage);
        (error as any).status = responseStatus;
        throw error;
      }

      const data = await response.json();
      

      // Show detailed success message with equipment and baselines
      if (data.success) {
        const equipmentList = data.equipment ? data.equipment.join(', ') : 'N/A';
        const baselinesCount = data.baselines ? Object.keys(data.baselines).length : 0;

        addToast(
          `✅ Order ${poNumber} started!\n` +
          `Type: ${data.order_type || 'Unknown'}\n` +
          `Version: ${data.version || 'N/A'}\n` +
          `Equipment: ${equipmentList}\n` +
          `Baselines captured: ${baselinesCount} devices`,
          'success'
        );

        // Auto-open progress dialog for this order
        setTimeout(() => {
          const order = orders.find(o => o.po_number === poNumber);
          if (order) {
            openProgressDialog(order);
          }
        }, 500);
      } else {
        addToast(`✅ Order ${poNumber} started successfully!`, 'success');
      }

      // ✅ FIX: Remove from validatingOrders on success
      setValidatingOrders(prev => {
        const updated = new Set(prev);
        updated.delete(poNumber);
        return updated;
      });

      await loadOrders();
      await loadKpiCounts();

    } catch (err: any) {
      console.error('❌ Failed to start order:', err);
      console.error('❌ Error message:', err.message);
      console.error('❌ Error string:', String(err));
      
      // ✅ Check if this is a 409 Conflict (scales locked)
      if ((err as any).status === 409) {
        addToast(
          `🔒 Cannot start order ${poNumber}\n` +
          `Scales are locked by another order.\n` +
          `Please wait for higher priority orders to complete.`,
          'warning'
        );
        // Refresh orders to get updated conflict info
        await loadOrders();
        return;
      }
      
      // ✅ Get order information to determine order type
      const order = orders.find(o => o.po_number === poNumber);
      const orderType = order ? (order as any).order_type : null;
      
      
      // ✅ Parse error message to extract version and mapping type
      const errorMessage = err.message || String(err);
      const errorLower = errorMessage.toLowerCase();
     
      
      // ✅ Check if this is a classification/mapping error
      const isPalletizerError = errorLower.includes('palletizer') || 
                               (orderType === 'PACKING' && errorLower.includes('mapping'));
      const isMillingError = errorLower.includes('milling') || 
                            (orderType === 'MILLING' && errorLower.includes('mapping') && !errorLower.includes('palletizer'));
      
     
      
      // ✅ Extract version from error message (e.g., "version BKL2", "for version BKL2", or just "BKL2")
      let version = '';
      const versionMatch = errorMessage.match(/version\s+([A-Z0-9]+)/i) || 
                          errorMessage.match(/for\s+version\s+([A-Z0-9]+)/i) ||
                          errorMessage.match(/\b([A-Z][A-Z0-9]{2,})\b/);
      if (versionMatch && versionMatch[1]) {
        version = versionMatch[1];
        
      } else if (order) {
        version = order.version || '';
       
      }
      
      // ✅ Build user-friendly message based on order type and error
      let toastType: 'warning' | 'error' = 'error';
      let toastMessage = '';
      
      if (isPalletizerError) {
        // PACKING order - palletizer mapping issue
        toastType = 'warning';
        if (version) {
          toastMessage = `⚠️ We don't have palletizer version ${version} in palletizer mapping`;
        } else {
          toastMessage = `⚠️ We don't have palletizer version in palletizer mapping`;
        }
      } else if (isMillingError) {
        // MILLING order - milling mapping issue
        toastType = 'warning';
        if (version) {
          toastMessage = `⚠️ We don't have version ${version} in milling mapping`;
        } else {
          toastMessage = `⚠️ We don't have version in milling mapping`;
        }
      } else if (errorLower.includes('classification failed') || 
                 errorLower.includes('classification') ||
                 errorLower.includes('mapping')) {
        // Generic classification/mapping error - try to determine from order type
        toastType = 'warning';
        if (orderType === 'PACKING') {
          toastMessage = version 
            ? `⚠️ We don't have palletizer version ${version} in palletizer mapping`
            : `⚠️ We don't have palletizer version in palletizer mapping`;
        } else if (orderType === 'MILLING') {
          toastMessage = version
            ? `⚠️ We don't have version ${version} in milling mapping`
            : `⚠️ We don't have version in milling mapping`;
        } else {
          toastMessage = `⚠️ Classification issue: ${errorMessage}`;
        }
      } else if ((err as any).status === 400 || errorLower.includes('400') || errorLower.includes('bad request')) {
        // ✅ HTTP 400 error - likely a mapping/classification issue if we have order type
        if (orderType === 'PACKING') {
          toastType = 'warning';
          toastMessage = version 
            ? `⚠️ We don't have palletizer version ${version} in palletizer mapping`
            : `⚠️ We don't have palletizer version in palletizer mapping`;
        } else if (orderType === 'MILLING') {
          toastType = 'warning';
          toastMessage = version
            ? `⚠️ We don't have version ${version} in milling mapping`
            : `⚠️ We don't have version in milling mapping`;
        } else {
          // Unknown order type, show generic error
          toastType = 'error';
          toastMessage = `Failed to start order: ${errorMessage}`;
        }
      } else {
        // Other errors - show as error
        toastType = 'error';
        toastMessage = `Failed to start order: ${errorMessage}`;
      }
      
      addToast(toastMessage, toastType);

      // ✅ FIX: Remove from Set on error
      setValidatingOrders(prev => {
        const updated = new Set(prev);
        updated.delete(poNumber);
        return updated;
      });

    } finally {
      // ✅ FIX: Don't clear validatingOrders here
      // Order will be removed from Set when it completes (status changes to Validated)
      // or on error in catch block
    }
  };



  // View validation details function
  const viewValidationDetails = async (order: Order) => {
    try {
      // Fetch full order details including overflow_weight and progress data
      const [progressResponse, orderResponse] = await Promise.all([
        apiFetch(getApiUrl(`/api/orders/${order.po_number}/progress`)),
        apiFetch(getApiUrl('/api/sap-sync/orders?statuses=Completed,Validated,InProgress,Pending&limit=1000'))
      ]);

      let overflowWeight = 0;
      let fullOrderData: any = null;
      let progressData: any = null;
      let scaleDetails: any[] = [];

      // Get overflow and scale details from progress endpoint
      if (progressResponse.ok) {
        progressData = await progressResponse.json();
        overflowWeight = progressData.overflow || 0;
        scaleDetails = progressData.scale_details || [];
      }

      // Get full order data from sap-sync endpoint
      if (orderResponse.ok) {
        const orderData = await orderResponse.json();
        const orders = orderData.ok ? orderData.orders : [];
        fullOrderData = orders.find((o: any) => o.po_number === order.po_number || o.order_id === order.po_number);
      }

      // If we don't have full order data, try to get it from the current orders list
      if (!fullOrderData) {
        fullOrderData = orders.find(o => o.po_number === order.po_number);
      }

      // Extract scale values - PRIORITY: progressData (from database via progress endpoint)
      // progressData.scale1/scale2/scale3 are the CORRECT byproduct scales from the database
      // DO NOT use equipment_list or scale_details as fallback - those are FORMULA equipment, not byproduct scales
      let scale1 = "";
      let scale1_qty = 0;
      let scale2 = "";
      let scale2_qty = 0;
      let scale3 = "";
      let scale3_qty = 0;

      // HIGHEST PRIORITY: Use progressData which has correct byproduct scales from database
      if (progressData) {
        scale1 = progressData.scale1 || "";
        scale1_qty = progressData.scale1_qty || 0;
        scale2 = progressData.scale2 || "";
        scale2_qty = progressData.scale2_qty || 0;
        scale3 = progressData.scale3 || "";
        scale3_qty = progressData.scale3_qty || 0;
      }
      
      // Fallback to current orders list if progressData doesn't have scales
      if (!scale1) {
        const currentOrder = orders.find(o => o.po_number === order.po_number);
        if (currentOrder && (currentOrder as any).scale1) {
          scale1 = (currentOrder as any).scale1 || "";
          scale1_qty = (currentOrder as any).scale1_qty || 0;
          scale2 = (currentOrder as any).scale2 || "";
          scale2_qty = (currentOrder as any).scale2_qty || 0;
          scale3 = (currentOrder as any).scale3 || "";
          scale3_qty = (currentOrder as any).scale3_qty || 0;
        }
        // Last fallback to fullOrderData from API
        else if (fullOrderData) {
          scale1 = fullOrderData.scale1 || "";
          scale1_qty = fullOrderData.scale1_qty || 0;
          scale2 = fullOrderData.scale2 || "";
          scale2_qty = fullOrderData.scale2_qty || 0;
          scale3 = fullOrderData.scale3 || "";
          scale3_qty = fullOrderData.scale3_qty || 0;
        }
      }
      
      // NOTE: Removed fallback to equipment_list and scale_details
      // Those contain FORMULA equipment scales (WG201, WG301, DM201...), NOT byproduct scales (WG501, WG502, WG503)
      // Using them as fallback was causing wrong scale values to be displayed

      // Get shift from progress data or order data
      const currentShift = progressData?.order_current_shift || fullOrderData?.current_shift || fullOrderData?.shift || "";

      // Construct SAP payload in the exact format sent to SAP (uppercase field names)
      // Helper function to format date as YYYYMMDD
      const formatDateForSAP = (dateStr: string | null | undefined): string => {
        if (!dateStr) return "";
        try {
          const date = new Date(dateStr);
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          return `${year}${month}${day}`;
        } catch {
          return "";
        }
      };

      // Helper function to format time as HHMMSS
      const formatTimeForSAP = (dateStr: string | null | undefined): string => {
        if (!dateStr) return "";
        try {
          const date = new Date(dateStr);
          const hours = String(date.getHours()).padStart(2, '0');
          const minutes = String(date.getMinutes()).padStart(2, '0');
          const seconds = String(date.getSeconds()).padStart(2, '0');
          return `${hours}${minutes}${seconds}`;
        } catch {
          return "";
        }
      };

      const sapPayload = fullOrderData ? {
        UOM: fullOrderData.unit || fullOrderData.uom || "TO",
        BATCH: fullOrderData.batch || "",
        PLANT: fullOrderData.plant || "3130",
        SHIFT: currentShift,
        SCALE1: scale1,
        SCALE2: scale2,
        SCALE3: scale3,
        STATUS: "Confirmed",
        VERSION: fullOrderData.version || order.version || "",
        MATERIAL: fullOrderData.material || order.material || "",
        TOTAL_QTY: String(fullOrderData.expected_weight || fullOrderData.quantity || 0),
        CREATED_ON: formatDateForSAP(fullOrderData.created_at || fullOrderData.sap_created_on),
        SCALE1_QTY: String(scale1_qty || 0),
        SCALE2_QTY: String(scale2_qty || 0),
        SCALE3_QTY: String(scale3_qty || 0),
        CONFIRMED_AT: formatTimeForSAP(fullOrderData.confirmed_at || fullOrderData.updated_at),
        MATERIAL_DESC: fullOrderData.material_desc || "",
        PROCESS_ORDER: fullOrderData.po_number || fullOrderData.order_id || order.po_number || "",
        CONFIRMED_WEIGHT: String(fullOrderData.confirmed_qty || 0),
        FINAL_CONFIRMATION: (fullOrderData.is_final_sent || fullOrderData.status === 'Validated' || fullOrderData.status === 'Completed') ? "X" : ""
      } : null;

      // Try to get validation result if order is validated
      let validationResult = null;
      try {
        const validateResponse = await apiFetch(getApiUrl(`/api/orders/${order.po_number}/validate`), {
        method: 'POST'
      });
        if (validateResponse.ok) {
          const validateData = await validateResponse.json();
          validationResult = validateData.validation_result || null;
        }
      } catch (e) {
        // If validate endpoint fails (e.g., order already validated), that's okay
        
      }

      setValidationDetails({
        order_type: fullOrderData?.order_type || (order as any).order_type || "",
        overflow_weight: overflowWeight,
        sap_payload: sapPayload,
        full_order_data: fullOrderData,
        ...(validationResult || {})
      });
      setShowValidationDetails(true);

    } catch (err) {
      console.error('Failed to fetch validation details:', err);
      addToast('Failed to load validation details', 'error');
    }
  };

  // Classify all orders function
  const classifyAllOrders = async () => {
    setClassifying(true);

    try {
      

      // Get all orders that need classification (Unknown or no order_type)
      const unclassifiedOrders = orders.filter(order => {
        const extendedOrder = order as Order & { order_type?: string };
        return !extendedOrder.order_type || extendedOrder.order_type === 'Unknown';
      });

      

      if (unclassifiedOrders.length === 0) {
        addToast('No orders need classification', 'info');
        return;
      }

      // Classify each order based on MATERIAL code
      let millingCount = 0;
      let packingCount = 0;
      let unknownCount = 0;
      const classificationResults = [];

      for (const order of unclassifiedOrders) {
        
        const classification = classifyOrderByMaterial(order.material || '');
        classificationResults.push({
          po_number: order.po_number,
          material: order.material,
          order_type: classification.order_type,
          confidence: classification.confidence
        });

        if (classification.order_type === 'MILLING') {
          millingCount++;
        } else if (classification.order_type === 'PACKING') {
          packingCount++;
        } else {
          unknownCount++;
        }
      }

    

      // Update all orders in the local state
      setOrders(prevOrders =>
        prevOrders.map(order => {
          const classification = classifyOrderByMaterial(order.material || '');
          return { ...order, order_type: classification.order_type } as any;
        })
      );

      // Show success message
      addToast(
        `✅ Classified ${unclassifiedOrders.length} orders: ${millingCount} MILLING, ${packingCount} PACKING${unknownCount > 0 ? `, ${unknownCount} Unknown` : ''}`,
        'success'
      );

      // Reload KPI counts to reflect changes
      await loadKpiCounts();

    } catch (err: any) {
      console.error('❌ Classification failed:', err);
      addToast(`Failed to classify orders: ${err.message}`, 'error');
    } finally {
      setClassifying(false);
    }
  };

  // Mock validation function for testing when API is not available
  const mockValidation = async (poNumber: string) => {
    

    // Show loading message
    addToast(`🔄 Validating order ${poNumber} (Mock Mode)...`, 'info');

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    const order = orders.find(o => o.po_number === poNumber);
    if (!order) {
      throw new Error(`Order ${poNumber} not found`);
    }

    // Mock validation result
    const mockResult = {
      success: true,
      validation_result: {
        validated: true,
        total_actual: order.quantity || 100,
        unit: (order as any).order_type === 'MILLING' ? 'TO' : 'BAG',
        variance_pct: Math.random() * 5 - 2.5, // Random variance between -2.5% and +2.5%
        errors: []
      }
    };

    addToast(
      `✅ Order ${poNumber} validated (Mock Mode)! Actual: ${mockResult.validation_result.total_actual} ${mockResult.validation_result.unit} (${mockResult.validation_result.variance_pct > 0 ? '+' : ''}${mockResult.validation_result.variance_pct.toFixed(1)}% variance)`,
      'success'
    );

    // Update order status locally
    // ✅ Feb 5, 2026: Set to Completed (100% tracking), Validated only after SAP confirmation
    setOrders(prev => prev.map(o =>
      o.po_number === poNumber ? { ...o, status: 'Completed' } : o
    ));

    await loadKpiCounts();
    return mockResult;
  };

  // Enhanced validateOrder function that integrates with backend validation
  const validateOrderManually = async (poNumber: string) => {
    try {
      setValidatingOrders(prev => new Set(Array.from(prev).concat([poNumber])));

      

      // First, try to test basic API connectivity
      let isApiAvailable = false;
      try {
        isApiAvailable = await testApiConnectivity();
       
      } catch (connectivityError) {
        console.warn('⚠️ API connectivity test failed:', connectivityError);
        isApiAvailable = false;
      }

      // If API is not available, use mock validation
      if (!isApiAvailable) {
        console.warn('⚠️ API not available, using mock validation');
        return await mockValidation(poNumber);
      }

      // Try the backend validation endpoint
      try {
        const url = getApiUrl(`/api/orders/${poNumber}/validate`);
        

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // Increased timeout for validation

        const response = await apiFetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal
        });

        clearTimeout(timeoutId);
        

        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

          // Try to parse JSON error response
          try {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
              const errorData = await response.json();
              errorMessage = errorData.message || errorData.error || errorMessage;
            }
          } catch (parseError) {
            
          }

          throw new Error(errorMessage);
        }

        const validationResult = await response.json();
        

        // Handle successful validation
        if (validationResult.success) {
          addToast(
            `✅ Order ${poNumber} validated successfully! ${validationResult.message || ''}`,
            'success'
          );

          // ✅ Feb 5, 2026: Set to Completed (100% tracking), Validated only after SAP confirmation
          setOrders(prev => prev.map(o =>
            o.po_number === poNumber ? { ...o, status: 'Completed' } : o
          ));

          await loadOrders();
          await loadKpiCounts();

          return validationResult;
        } else {
          throw new Error(validationResult.message || 'Validation failed');
        }

      } catch (validationError: any) {
        console.error('❌ Backend validation failed:', validationError);

        // If validation fails, try to get current progress instead
        try {
          
          const progressUrl = getApiUrl(`/api/orders/${poNumber}/progress`);
          const progressResponse = await apiFetch(progressUrl);

          if (progressResponse.ok) {
            const progressData = await progressResponse.json();
           

            // Show progress dialog with current status
            // Convert TON to TO if present, or use TO for MILLING orders
            const unit = progressData.unit === 'TON' || progressData.unit === 'ton'
              ? 'TO'
              : (progressData.unit || (progressData.order_type === 'MILLING' ? 'TO' : 'BAG'));

            setSelectedOrderProgress({
              po_number: poNumber,
              material: progressData.material || '',
              expected_tons: progressData.target || 0,
              current_tons: progressData.current || 0,
              remaining_tons: progressData.remaining || 0,
              progress_pct: progressData.progress_pct || 0,
              status: progressData.status || progressData.order_status || 'Pending',
              last_tick: progressData.timestamp || null,
              order_type: progressData.order_type,
              equipment_list: progressData.equipment_list || [],
              equipment_details: progressData.equipment_details || {},
              scale_details: progressData.scale_details || [],
              scale_lock_status: progressData.scale_lock_status,
              version: progressData.version,
              // ✅ Byproduct scales (editable)
              scale1: progressData.scale1 || '',
              scale1_qty: progressData.scale1_qty || 0,
              scale2: progressData.scale2 || '',
              scale2_qty: progressData.scale2_qty || 0,
              scale3: progressData.scale3 || '',
              scale3_qty: progressData.scale3_qty || 0,
              byproduct_details: progressData.byproduct_details || {},
              unit: unit
            });
            setShowProgressDialog(true);

            addToast(
              `📊 Order ${poNumber} is in progress (${progressData.progress_pct?.toFixed(1)}% complete)`,
              'info'
            );

            return progressData;
          }
        } catch (progressError) {
          console.error('❌ Could not get progress data:', progressError);
        }

        // If all else fails, show error
        addToast(`Failed to validate order ${poNumber}: ${validationError.message}`, 'error');
        throw validationError;
      }

    } catch (err: any) {
      console.error('❌ Validation failed:', err);
      addToast(`Failed to validate order: ${err.message}`, 'error');
      throw err;
    } finally {
      setValidatingOrders(prev => {
        const updated = new Set(prev);
        updated.delete(poNumber);
        return updated;
      });
    }
  };

  // Manual stop order function
  const stopOrderManually = async (poNumber: string) => {
    try {
      
      
      // ✅ AGGRESSIVE FIX: Enable lockdown to block ALL order updates
      stopLockdownActiveRef.current = true;
      
      // ✅ FIX: Set stop cooldown to prevent UI fluctuation during stop process
      lastStopTimeRef.current = Date.now();
      
      // ✅ NUCLEAR FIX: Add order to forced pending list to override any state updates at UI level
      // This prevents the 2-3 second flicker where polling shows stale InProgress status
      forcedPendingOrdersRef.current.add(poNumber);
      setForcedPendingVersion(v => v + 1); // Trigger re-render with forced Pending status
      
      
      // ✅ Immediately set this order to Pending AND clear byproduct values to prevent flickering
      setOrders(prevOrders => prevOrders.map(order => 
        order.po_number === poNumber 
          ? { 
              ...order, 
              status: 'Pending',
              // Clear byproduct values to prevent fluctuation during stop
              scale1_qty: (order as any).scale1_qty || 0,
              scale2_qty: (order as any).scale2_qty || 0,
              scale3_qty: (order as any).scale3_qty || 0
            } 
          : order
      ));

      const response = await apiFetch(getApiUrl(`/api/orders/${poNumber}/stop`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const textResponse = await response.text();
        console.error('❌ API returned non-JSON response:', {
          status: response.status,
          statusText: response.statusText,
          contentType: contentType,
          preview: textResponse.substring(0, 200)
        });
        throw new Error(`Server error (${response.status}): Expected JSON but received ${contentType || 'unknown'}`);
      }

      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.message || errorData.error || 'Failed to stop order');
        } catch (parseErr) {
          throw new Error(`Failed to stop order: HTTP ${response.status} ${response.statusText}`);
        }
      }

      const data = await response.json();
      

      // Show success message
      if (autoValidatorStatus.running) {
        addToast(`Order ${poNumber} stopped. Auto-validator will move to next priority order.`, 'success');
      } else {
        addToast(`Order ${poNumber} stopped successfully.`, 'success');
      }

      // ✅ FIX: Clear progress state for this order to prevent stale data
      setOrderProgress(prev => {
        const updated = { ...prev };
        delete updated[poNumber];
        return updated;
      });
      
      // ✅ FIX: Close progress dialog if it's showing this order
      if (selectedOrderProgress?.po_number === poNumber) {
        setShowProgressDialog(false);
        setSelectedOrderProgress(null);
      }
      
      // ✅ Clear progress state for this order
      setOrderProgress(prev => {
        const updated = { ...prev };
        delete updated[poNumber];
        return updated;
      });

      // Refresh KPI counts only (orders are already updated locally)
      await loadKpiCounts();
      
      // ✅ Release lockdown after a delay, then reset cooldown for extra protection
      setTimeout(async () => {
        stopLockdownActiveRef.current = false;
       
        
        // ✅ CRITICAL: Reset cooldown timer to prevent immediate polling
        lastStopTimeRef.current = Date.now();
        
        
        // ✅ Clear forced pending status for this order BEFORE refresh
        forcedPendingOrdersRef.current.delete(poNumber);
        setForcedPendingVersion(v => v + 1); // Trigger re-render to show real status from DB
        
        
        await loadOrders(); // Refresh with real data
        
      }, STOP_COOLDOWN_MS);

    } catch (err: any) {
      console.error('❌ Failed to stop order:', err);
      addToast(`Failed to stop order: ${err.message || 'Unknown error'}`, 'error');
      // Release lockdown on error
      stopLockdownActiveRef.current = false;
      // Also clear forced pending on error
      forcedPendingOrdersRef.current.delete(poNumber);
      setForcedPendingVersion(v => v + 1);
    }
  };

  // Open rejection modal
  const openRejectionModal = (orderId: number) => {
    const order = orders.find(o => o.id === orderId);
    if (order) {
      setSelectedOrderId(orderId);
      setSelectedOrderDetails({
        po_number: order.po_number,
        material: order.material,
        quantity: order.quantity,
        unit: order.unit
      });
      setShowRejectionModal(true);
    }
  };

  // Open manual confirmation modal - fetch fresh data first
  const openManualConfirmationModal = async (order: Order) => {
    
    
    try {
      // ✅ CRITICAL: Fetch fresh order data from backend to get latest confirmed_shift values
      
      const response = await apiFetch(getApiUrl(`/api/orders/${order.po_number}/progress`));
      
      if (!response.ok) {
        console.error('Failed to fetch fresh order data');
        addToast('Failed to fetch order data. Please try again.', 'error');
        return;
      }
      
      const freshData = await response.json();
    
      
      // Merge fresh data with existing order data
      const updatedOrder = {
        ...order,
        confirmed_qty: freshData.confirmed_qty || freshData.current || 0,
        confirmed_shift_a: freshData.confirmed_shift_a || 0,
        confirmed_shift_b: freshData.confirmed_shift_b || 0,
        confirmed_shift_c: freshData.confirmed_shift_c || 0,
        last_confirmed_qty: freshData.last_confirmed_qty || 0,
        scale1_qty: freshData.scale1_qty || 0,
        scale2_qty: freshData.scale2_qty || 0,
        scale3_qty: freshData.scale3_qty || 0,
        current_shift: freshData.current_shift || 'A'
      };
      
     
      
      // ✅ Check if there's available production (not already sent to SAP)
      const totalProduction = updatedOrder.confirmed_qty || 0;
      const confirmedShiftA = updatedOrder.confirmed_shift_a || 0;
      const confirmedShiftB = updatedOrder.confirmed_shift_b || 0;
      const confirmedShiftC = updatedOrder.confirmed_shift_c || 0;
      const alreadySent = confirmedShiftA + confirmedShiftB + confirmedShiftC;
      const available = Math.max(0, totalProduction - alreadySent);
      
   
      
      if (available <= 0) {
        addToast('⚠️ No production available to confirm. All production has already been sent to SAP.', 'warning');
        console.error('❌ Cannot open modal: no available production');
        return;
      }
      
      setSelectedOrderForManualConfirm(updatedOrder as Order);
      setManualConfirmData({ 
        scrap: 0, 
        confirmed_text: '',
        override_qty: null,
        custom_byproducts: {
          scale1_qty: updatedOrder.scale1_qty ? String(updatedOrder.scale1_qty) : '',
          scale2_qty: updatedOrder.scale2_qty ? String(updatedOrder.scale2_qty) : '',
          scale3_qty: updatedOrder.scale3_qty ? String(updatedOrder.scale3_qty) : ''
        }
      });
      setShowManualConfirmationModal(true);
    } catch (err: any) {
      console.error('❌ Error opening manual confirmation modal:', err);
      addToast(`Failed to open confirmation dialog: ${err.message}`, 'error');
    }
  };

  // Close rejection modal
  const closeRejectionModal = () => {
    setShowRejectionModal(false);
    setSelectedOrderId(0);
    setSelectedOrderDetails(null);
  };

  // Reject order function
  const rejectOrder = async (rejectionData: RejectionData) => {
    // Get po_number from order details or find the order
    const order = orders.find(o => o.id === rejectionData.order_id);
    const poNumber = order?.po_number || String(rejectionData.order_id);

    try {
      
      setValidatingOrders(prev => new Set(Array.from(prev).concat([poNumber])));

      // Build remarks from rejection data
      const remarks = `${rejectionData.category}: ${rejectionData.reason} - ${rejectionData.description}`;

      // Call the dedicated reject endpoint with database ID
      const response = await apiFetch(getApiUrl(`/api/orders/${rejectionData.order_id}/reject`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          remarks: remarks,
          rejected_by: rejectionData.rejected_by || 'Unknown'
        })
      });

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const textResponse = await response.text();
        console.error('❌ API returned non-JSON response:', {
          status: response.status,
          statusText: response.statusText,
          contentType: contentType,
          preview: textResponse.substring(0, 200)
        });
        throw new Error(`Server error (${response.status}): Expected JSON but received ${contentType || 'unknown'}`);
      }

      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.message || errorData.error || `Rejection failed: ${response.statusText}`);
        } catch (parseErr) {
          throw new Error(`Failed to reject order: HTTP ${response.status} ${response.statusText}`);
        }
      }

      const result = await response.json();
      

      // Update local state
      setOrders(prev =>
        prev.map(o => o.id === rejectionData.order_id ? { ...o, status: 'Rejected' } : o)
      );

      // Refresh KPI counts to show updated rejected count
      await loadKpiCounts();

      // Reload orders to get updated status from database
      await loadOrders();

      // If auto-validator is running, refresh its status to see the next order
      if (autoValidatorStatus.running) {
        await fetchAutoValidatorStatus();
      }

      // Show success message
      if (autoValidatorStatus.running) {
        addToast(`Order ${result.po_number || rejectionData.order_details?.po_number || rejectionData.order_id} rejected. Auto-validator will move to next priority order.`, 'success');
      } else {
        addToast(`Order ${result.po_number || rejectionData.order_details?.po_number || rejectionData.order_id} rejected successfully.`, 'success');
      }

     
    } catch (err: any) {
      console.error('❌ Rejection failed:', err);
      throw new Error(`Failed to reject order: ${err.message || 'Unknown error'}`);
    } finally {
      setValidatingOrders(prev => {
        const updated = new Set(prev);
        updated.delete(poNumber);
        return updated;
      });
    }
  };

  // Manual confirmation function - sends accumulated production to SAP and resets values
  const sendManualConfirmation = async () => {
    if (!selectedOrderForManualConfirm) {
      addToast('No order selected for manual confirmation', 'error');
      return;
    }

    const order = selectedOrderForManualConfirm as any;
    const orderId = order.po_number || String(order.id);
    
  
    
    // ✅ CRITICAL FIX: Calculate available for confirmation
    // Available = Total production - Already sent to SAP
    const totalProduction = order.confirmed_qty || 0;
    const confirmedShiftA = order.confirmed_shift_a || 0;
    const confirmedShiftB = order.confirmed_shift_b || 0;
    const confirmedShiftC = order.confirmed_shift_c || 0;
    const alreadySentToSAP = confirmedShiftA + confirmedShiftB + confirmedShiftC;
    const availableForConfirm = Math.max(0, totalProduction - alreadySentToSAP);
    
   
    
    if (availableForConfirm <= 0) {
      addToast('⚠️ No production available to confirm. All production has already been sent to SAP.', 'warning');
      return;
    }

    try {
      setSendingManualConfirm(true);
      setValidatingOrders(prev => new Set(Array.from(prev).concat([orderId])));



      const payload = {
        po_number: orderId,
        confirmed_qty: availableForConfirm,
        scale1_qty: order.scale1_qty || 0,
        scale2_qty: order.scale2_qty || 0,
        scale3_qty: order.scale3_qty || 0,
        scrap: manualConfirmData.scrap || 0,
        confirmed_text: manualConfirmData.confirmed_text || '',
        shift: order.current_shift || 'A',
        operator: 'manual'
      };
      
      

      // Use the new manual-confirm endpoint that sends to SAP and resets values
      const response = await apiFetch(getApiUrl('/api/process_orders/manual-confirm'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const textResponse = await response.text();
        console.error('❌ API returned non-JSON response:', {
          status: response.status,
          statusText: response.statusText,
          contentType: contentType,
          preview: textResponse.substring(0, 200)
        });
        throw new Error(`Server error (${response.status}): Expected JSON but received ${contentType || 'unknown'}`);
      }

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Backend error response:', errorData);
        const errorMessage = errorData.error || errorData.message || `Manual confirmation failed: ${response.statusText}`;
        throw new Error(errorMessage);
      }

      const result = await response.json();
      

      // Close modal and reset data
      setShowManualConfirmationModal(false);
      setSelectedOrderForManualConfirm(null);
      setManualConfirmData({ 
        scrap: 0, 
        confirmed_text: '',
        override_qty: null,
        custom_byproducts: { scale1_qty: '', scale2_qty: '', scale3_qty: '' }
      });

      // Reload orders to get updated status (confirmed_qty should be 0 now)
      await loadOrders();
      await loadKpiCounts();

      // Show success message with details
      const lastConfirmed = result.last_confirmed_qty || 0;
      const confirmedAmount = result.confirmed_qty_sent || availableForConfirm;
      if (result.offline_mode || result.offline_queued) {
        addToast(
          `✅ Confirmation queued: ${confirmedAmount.toFixed(2)} TO (offline mode - will sync automatically)`,
          'success'
        );
      } else {
        addToast(
          `✅ Confirmation sent to SAP: ${confirmedAmount.toFixed(2)} TO (Total confirmed: ${lastConfirmed.toFixed(2)} TO)`,
          'success'
        );
      }

    } catch (err: any) {
      console.error('❌ Manual confirmation failed:', err);
      addToast(`Failed to send manual confirmation: ${err.message || 'Unknown error'}`, 'error');
    } finally {
      setSendingManualConfirm(false);
      setValidatingOrders(prev => {
        const updated = new Set(prev);
        updated.delete(orderId);
        return updated;
      });
    }
  };

  // Close manual confirmation modal
  const closeManualConfirmationModal = () => {
    setShowManualConfirmationModal(false);
    setSelectedOrderForManualConfirm(null);
    setManualConfirmData({ 
      scrap: 0, 
      confirmed_text: '',
      override_qty: null,
      custom_byproducts: { scale1_qty: null, scale2_qty: null, scale3_qty: null }
    });
  };

  // KPI state for database counts (totalMilling/totalPacking = Pending + InProgress by type)
  const [kpiCounts, setKpiCounts] = useState({
    total: 0,
    totalMilling: 0,
    totalPacking: 0,
    inProgress: 0,
    confirmed: 0,   // Confirmed status only (partial confirmations)
    completed: 0,   // Completed, Validated, CNF (fully done)
    rejected: 0,
    errorLog: 0,
    offlineOrders: 0
  });

  // Load KPI counts from database using existing endpoints
  const loadKpiCounts = async () => {
    try {
      // Offline count: filter by order_type for operators (packing sees only packing, milling only milling)
      let offlineCountUrl = getApiUrl('/api/offline-confirmations/count');
      if (canAccessPacking && !canAccessMilling) offlineCountUrl += '?order_type=PACKING';
      else if (canAccessMilling && !canAccessPacking) offlineCountUrl += '?order_type=MILLING';

      const [pendingResponse, inProgressResponse, confirmedResponse, completedResponse, rejectedResponse, errorLogResponse, offlineResponse] = await Promise.all([
        apiFetch(getApiUrl('/api/orders?status=Pending&limit=1000')), // Pending orders
        apiFetch(getApiUrl('/api/orders?status=InProgress&limit=1000')), // InProgress orders
        apiFetch(getApiUrl('/api/orders?status=Confirmed&limit=1000')), // Confirmed status only
        apiFetch(getApiUrl('/api/orders?statuses=Completed,Validated,CNF,COMP&limit=1000')), // Completed, Validated, CNF, COMP
        apiFetch(getApiUrl('/api/orders?status=Rejected&limit=1000')), // Rejected orders
        apiFetch(getApiUrl('/api/error-log/')), // Error log entries
        apiFetch(offlineCountUrl) // Offline orders (filtered by role when operator)
      ]);

      const [pendingOrders, inProgressOrders, confirmedOrders, completedOrders, rejectedOrders, errorLogs, offlineData] = await Promise.all([
        pendingResponse.ok ? pendingResponse.json() : [],
        inProgressResponse.ok ? inProgressResponse.json() : [],
        confirmedResponse.ok ? confirmedResponse.json() : [],
        completedResponse.ok ? completedResponse.json() : [],
        rejectedResponse.ok ? rejectedResponse.json() : [],
        errorLogResponse.ok ? errorLogResponse.json() : [],
        offlineResponse.ok ? offlineResponse.json() : { count: 0 }
      ]);

      const toOrders = (r: any) => Array.isArray(r) ? r : (r?.orders ?? []);
      const pending = toOrders(pendingOrders);
      const inProgress = toOrders(inProgressOrders);
      const allForTotal = [...pending, ...inProgress];
      const isMilling = (o: any) => o?.order_type === 'MILLING' || String(o?.material || '').replace(/^0+/, '').startsWith('13');
      const isPacking = (o: any) => o?.order_type === 'PACKING' || String(o?.material || '').replace(/^0+/, '').startsWith('14');
      const totalMilling = allForTotal.filter((o: any) => isMilling(o)).length;
      const totalPacking = allForTotal.filter((o: any) => isPacking(o)).length;

      setKpiCounts({
        total: pending.length + inProgress.length,
        totalMilling,
        totalPacking,
        inProgress: inProgress.length,
        confirmed: toOrders(confirmedOrders).length,
        completed: toOrders(completedOrders).length,
        rejected: toOrders(rejectedOrders).length,
        errorLog: Array.isArray(errorLogs) ? errorLogs.length : 0,
        offlineOrders: offlineData?.count ?? 0
      });
    } catch (err) {
      console.error('Failed to load KPI counts:', err);
    }
  };

  /// Push confirmation handler with mid-shift support
  const handlePushConfirmation = async () => {
    if (pushingConfirmation) return;

    setPushingConfirmation(true);

    try {
      // Get order IDs from the modal orders - support Completed, Validated, CNF, and InProgress
      const orderIdsToPush = modalOrders
        .filter(order => order.status === 'Completed' || order.status === 'Validated' || order.status === 'CNF' || order.status === 'COMP' || order.status === 'InProgress')
        .map(order => order.id);

      if (orderIdsToPush.length === 0) {
        showCustomAlert(
          "No Orders",
          "No orders available to push. Orders must be in 'Completed', 'Validated', 'CNF', 'COMP', or 'InProgress' status.",
          "info"
        );
        return;
      }

      // ✅ NEW: Determine if this is mid-shift confirmation
      // If modal shows InProgress orders, it's mid-shift
      const isMidShift = modalType === 'inprogress';

      // ✅ UPDATED: Send with confirm_current_shift flag
      const result = await orderApi.pushConfirmation({
        order_ids: orderIdsToPush,
        confirm_current_shift: isMidShift,  // ✅ NEW: Mid-shift flag
        operator: 'manual',
      });

      // ✅ FIX: Handle offline mode response first - silently store without showing VPN error
      if (result.offline_mode === true) {
        const storedCount = result.stored_count || 0;
        
        if (storedCount > 0) {
          showCustomAlert(
            'Queued for Confirmation',
            `✅ ${storedCount} order(s) queued for confirmation (offline mode). Will sync automatically when connection is restored.`,
            'success',
            () => {
              loadOrders();
              loadKpiCounts();
              setShowOrdersModal(false);
            }
          );
        } else {
          showCustomAlert(
            'Offline Mode',
            `Orders will be confirmed when connection is restored.`,
            'info'
          );
        }
        return; // Exit early for offline mode
      }

      // Parse API response for detailed error handling
      const successfulCount = result.successful_count || 0;
      const failedCount = result.failed_count || 0;
      const failedOrders = result.failed_orders || [];
      const results = result.results || [];

      // Extract error messages and payloads from results
      const errorMessages: string[] = [];
      const payloadMessages: string[] = [];

      results.forEach((orderResult: any) => {
        const poNumber = orderResult.process_order || orderResult.po_number || 'Unknown';

        // Extract and format SAP payload if available
        if (orderResult.sap_payload && Object.keys(orderResult.sap_payload).length > 0) {
          try {
            const formattedPayload = JSON.stringify(orderResult.sap_payload, null, 2);
            payloadMessages.push(`\n📦 SAP Payload for Order ${poNumber}:\n${formattedPayload}`);
          } catch (e) {
            payloadMessages.push(`\n📦 SAP Payload for Order ${poNumber}:\n${JSON.stringify(orderResult.sap_payload)}`);
          }
        }

        if (orderResult.status === 'Error' || orderResult.status === 'Failed') {
          const errorMsg = orderResult.message || 'Order not confirmed in SAP';
          errorMessages.push(`Order ${poNumber}: ${errorMsg}`);
        }
      });

      // If all orders failed
      if (successfulCount === 0 && failedCount > 0) {
        let errorMessage = `Failed to push ${failedCount} order(s) to SAP:\n\n`;
        if (errorMessages.length > 0) {
          errorMessage += errorMessages.join('\n');
        } else if (failedOrders.length > 0) {
          errorMessage += `Failed orders: ${failedOrders.join(', ')}\n`;
          errorMessage += `Reason: Order not confirmed in SAP`;
        } else {
          errorMessage += result.message || 'Unknown error occurred';
        }

        // Add payload information
        if (payloadMessages.length > 0) {
          errorMessage += '\n\n' + payloadMessages.join('\n\n');
        }

        showCustomAlert(
          'Error',
          errorMessage,
          'error'
        );
        return;
      }

      // If some succeeded and some failed (partial success)
      if (successfulCount > 0 && failedCount > 0) {
        let message = `Successfully pushed ${successfulCount} order(s) to SAP.\n\n`;
        message += `Failed to push ${failedCount} order(s):\n\n`;
        if (errorMessages.length > 0) {
          message += errorMessages.join('\n');
        } else if (failedOrders.length > 0) {
          message += `Failed orders: ${failedOrders.join(', ')}\n`;
          message += `Reason: Order not confirmed in SAP`;
        }

        // Add payload information for failed orders
        const failedPayloads = results
          .filter((r: any) => r.status === 'Error' || r.status === 'Failed')
          .map((r: any) => {
            const po = r.process_order || r.po_number || 'Unknown';
            if (r.sap_payload && Object.keys(r.sap_payload).length > 0) {
              try {
                return `\n📦 SAP Payload for Order ${po}:\n${JSON.stringify(r.sap_payload, null, 2)}`;
              } catch (e) {
                return `\n📦 SAP Payload for Order ${po}:\n${JSON.stringify(r.sap_payload)}`;
              }
            }
            return null;
          })
          .filter((p: any) => p !== null);

        if (failedPayloads.length > 0) {
          message += '\n\n' + failedPayloads.join('\n\n');
        }

        showCustomAlert(
          'Partial Success',
          message,
          'warning',
          () => {
            // Refresh the orders and KPI counts
            loadOrders();
            loadKpiCounts();
          }
        );
        return;
      }

      // If all succeeded
      if (successfulCount > 0 && failedCount === 0) {
        let successMessage = `Successfully pushed ${successfulCount} order(s) to SAP`;

        // Add payload information for successful orders
        const successPayloads = results
          .filter((r: any) => r.status === 'Confirmed' || r.status === 'Success')
          .map((r: any) => {
            const po = r.process_order || r.po_number || 'Unknown';
            if (r.sap_payload && Object.keys(r.sap_payload).length > 0) {
              try {
                return `\n📦 SAP Payload for Order ${po}:\n${JSON.stringify(r.sap_payload, null, 2)}`;
              } catch (e) {
                return `\n📦 SAP Payload for Order ${po}:\n${JSON.stringify(r.sap_payload)}`;
              }
            }
            return null;
          })
          .filter((p: any) => p !== null);

        if (successPayloads.length > 0) {
          successMessage += '\n\n' + successPayloads.join('\n\n');
        }

        showCustomAlert(
          'Success!',
          successMessage,
          'success',
          () => {
            // Refresh the orders and KPI counts
            loadOrders();
            loadKpiCounts();
            // Close the modal
            setShowOrdersModal(false);
          }
        );
        return;
      }

      // If no orders were processed (edge case)
      showCustomAlert(
        'Warning',
        'No orders were processed. Please check the order status.',
        'warning'
      );
    } catch (error: any) {
      console.error('Push confirmation failed:', error);
      showCustomAlert(
        'Error',
        `Push confirmation failed: ${error.message || 'Unknown error'}`,
        'error'
      );
    } finally {
      setPushingConfirmation(false);
    }
  };

  // Push confirmation handler for a single order
  const handlePushSingleOrderConfirmation = async (order: Order) => {
    if (pushingConfirmation) return;

    setPushingConfirmation(true);
    const poNumber = order.po_number || String(order.id);
    
    

    try {
      // Push confirmation for this single order
      
      const result: any = await orderApi.pushConfirmation({
        order_ids: [order.id],
        confirm_current_shift: false, // Validated orders are final confirmations
        operator: 'manual',
      });

     

      // ✅ CRITICAL: Handle offline mode response first - silently store without showing VPN error
      if (result.offline_mode === true) {
        const storedCount = result.stored_count || 0;
        const storedOrders = result.stored_orders || [];
        
        if (storedCount > 0) {
          // ✅ FIX: Show success message instead of VPN disconnect warning
          addToast(`✅ Order ${poNumber} queued for confirmation (offline mode)`, 'success');
          // Refresh orders to update status
          await loadOrders();
          await loadKpiCounts();
        } else {
          // Try to store the order manually if backend didn't store it
          
          // Still show a neutral message - the order will be retried
          addToast(`ℹ️ Order ${poNumber} will be confirmed when connection is restored`, 'info');
        }
        return; // Exit early for offline mode
      }

      // Parse API response for online mode
      const successfulCount = result.successful_count || 0;
      const failedCount = result.failed_count || 0;
      const skippedCount = result.skipped_count || 0;
      const results = result.results || [];

      if (successfulCount > 0 && failedCount === 0) {
        // Success
        let successMessage = `✅ Successfully pushed order ${poNumber} to SAP`;

        // Add payload information if available
        const successPayload = results.find((r: any) => r.status === 'Confirmed' || r.status === 'Success');
        if (successPayload?.sap_payload && Object.keys(successPayload.sap_payload).length > 0) {
          try {
            successMessage += `\n\n📦 SAP Payload:\n${JSON.stringify(successPayload.sap_payload, null, 2)}`;
          } catch (e) {
            successMessage += `\n\n📦 SAP Payload:\n${JSON.stringify(successPayload.sap_payload)}`;
          }
        }

        addToast(successMessage, 'success');
        // Refresh orders and KPI counts
        await loadOrders();
        await loadKpiCounts();
      } else if (failedCount > 0) {
        // Failed
        const failedResult = results.find((r: any) => r.status === 'Error' || r.status === 'Failed');
        const errorMsg = failedResult?.message || 'Order not confirmed in SAP';
        
        let errorMessage = `❌ Failed to push order ${poNumber} to SAP:\n${errorMsg}`;
        
        // Add payload information if available
        if (failedResult?.sap_payload && Object.keys(failedResult.sap_payload).length > 0) {
          try {
            errorMessage += `\n\n📦 SAP Payload:\n${JSON.stringify(failedResult.sap_payload, null, 2)}`;
          } catch (e) {
            errorMessage += `\n\n📦 SAP Payload:\n${JSON.stringify(failedResult.sap_payload)}`;
          }
        }

        addToast(errorMessage, 'error');
      } else if (skippedCount > 0 || results.some((r: any) => r.status === 'Skipped')) {
        // Skipped - no production to confirm
        const skippedResult = results.find((r: any) => r.status === 'Skipped');
        const skipReason = skippedResult?.message || result.message || 'No production to confirm';
        addToast(`⚠️ Order ${poNumber} skipped: ${skipReason}`, 'warning');
      } else {
        // No success, no fail, no skip - show message from API
        const message = result.message || 'No response from push confirmation';
        addToast(`ℹ️ Order ${poNumber}: ${message}`, 'info');
      }
    } catch (error: any) {
      console.error('Push confirmation failed:', error);
      addToast(`Push confirmation failed: ${error.message || 'Unknown error'}`, 'error');
    } finally {
      setPushingConfirmation(false);
    }
  };

  // Load KPI counts on component mount
  useEffect(() => {
    loadKpiCounts();
  }, []);

  // // One-time check for auto-validator status on component mount (without starting it)
  // useEffect(() => {
  //   const checkInitialAutoValidatorStatus = async () => {
  //     try {
  //       const response = await apiFetch(getApiUrl('/api/orders/auto-validator/status'));
  //       if (response.ok) {
  //         const data = await response.json();
  //         console.log("🔍 Initial auto-validator status check:", data);

  //         // Only update status if auto-validator is already running
  //         if (data.is_running) {
  //           setAutoValidatorStatus(prev => ({
  //             ...prev,
  //             running: true
  //           }));
  //           console.log("⚠️ Auto-validator was already running on backend");
  //           // ⭐ SAFETY: Do NOT set autoValidationManuallyStarted to true automatically
  //           // User must explicitly click start button to begin monitoring
  //         }
  //       }
  //     } catch (err) {
  //       console.log("🔍 Initial auto-validator status check failed (this is normal if backend is not running):", err);
  //     }
  //   };

  //   checkInitialAutoValidatorStatus();

  //   // Cleanup on unmount - ensure auto-validation is stopped
  //   return () => {
  //     console.log("🧹 Component unmounting - ensuring auto-validation is stopped");
  //     setAutoValidationManuallyStarted(false);
  //     setAutoValidationLocked(false);
  //   };
  // }, []); // Run only once on mount
  // ================================================================
  // ✅ STEP 1: Load auto-validation state from localStorage on mount
  // ================================================================
  useEffect(() => {
    // Load saved state from localStorage
    const savedAutoValidationState = localStorage.getItem('autoValidationRunning');

    if (savedAutoValidationState === 'true') {
      
      setAutoValidationManuallyStarted(true);
    }

    // Also check backend status
    const checkInitialAutoValidatorStatus = async () => {
      try {
        const response = await apiFetch(getApiUrl('/api/orders/auto-validator/status'));
        if (response.ok) {
          const data = await response.json();
         

          // If backend is running AND localStorage says it should be running
          if (data.is_running && savedAutoValidationState === 'true') {
            setAutoValidatorStatus(prev => ({
              ...prev,
              running: true
            }));
           
          } else if (data.is_running && savedAutoValidationState !== 'true') {
            // Backend is running but user didn't start it from this session
           
          }
        }
      } catch (err) {
        
      }
    };

    checkInitialAutoValidatorStatus();
  }, []); // Run only once on mount

  // ================================================================
  // ✅ STEP 2: Save auto-validation state to localStorage whenever it changes
  // ================================================================
  useEffect(() => {
    localStorage.setItem('autoValidationRunning', autoValidationManuallyStarted.toString());
    
  }, [autoValidationManuallyStarted]); // Run whenever autoValidationManuallyStarted changes

  // ================================================================
  // ✅ STEP 3: Cleanup on unmount - DON'T stop auto-validation
  // ================================================================
  useEffect(() => {
    return () => {
      
      // ✅ DON'T reset flags - state persists via localStorage
    };
  }, []); // Run cleanup only on unmount


  // SAP Sync function - Updated to support order type filtering (Jan 30, 2026)
  // orderType: 'all' | 'milling' | 'packing'
  const syncSapOrders = async (orderType: 'all' | 'milling' | 'packing' = 'all') => {
    try {
      // Build URL with optional order_type filter
      const url = orderType && orderType !== 'all'
        ? getApiUrl(`/api/sap-sync/seed-orders?order_type=${orderType.toUpperCase()}`)
        : getApiUrl('/api/sap-sync/seed-orders');
      
      const orderTypeLabel = orderType === 'all' ? 'All' : orderType.toUpperCase();
      
      // Step 1: Call POST /api/sap-sync/seed-orders to fetch from SAP
      const syncResponse = await apiFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (syncResponse.ok) {
        const syncData = await syncResponse.json();
        

        // Step 2: Reload orders with current filters
        await loadOrders();

        // ⭐ Step 3: Apply priorities to newly synced orders
        if (syncData.inserted_orders && syncData.inserted_orders.length > 0) {
          // Get current priorities
          const savedPriorities = localStorage.getItem('orderPriorities');
          let userPriorities: Record<number, number> = {};

          if (savedPriorities) {
            try {
              userPriorities = JSON.parse(savedPriorities);
            } catch (e) {
              console.error('Failed to parse priorities:', e);
            }
          }

          // Assign priorities to new orders
          const maxPriority = Math.max(0, ...Object.values(userPriorities));
          syncData.inserted_orders.forEach((order: any, index: number) => {
            if (!userPriorities[order.id]) {
              userPriorities[order.id] = maxPriority + index + 1;
            }
          });

          // Save updated priorities
          await savePriorityOrder(userPriorities);
        }

        const insertedCount = syncData.inserted_orders?.length || 0;
        const updatedCount = syncData.updated_orders?.length || 0;
        addToast(`${orderTypeLabel} SAP Orders synced! ${insertedCount} added, ${updatedCount} updated ✅`, 'success');

        // Refresh KPI counts
        await loadKpiCounts();
      } else {
        const errorData = await syncResponse.json();
        addToast(`Failed to sync ${orderTypeLabel} Orders: ${errorData.message}`, 'error');
      }
    } catch (err) {
      console.error('Failed to sync SAP orders:', err);
      addToast(`Failed to sync SAP Orders ❌`, 'error');
    }
  };

  // Fetch detailed progress for a specific order
  const fetchOrderProgress = async (poNumber: string) => {
    try {
      const response = await apiFetch(getApiUrl(`/api/orders/${poNumber}/progress`));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const progressData = await response.json();
      
      return progressData;
    } catch (err) {
      console.error('Failed to fetch order progress:', err);
      return null;
    }
  };

  // Open progress dialog for InProgress order
  // const openProgressDialog = async (order: Order) => {
  //   if (order.status === 'InProgress' && order.po_number) {
  //     const progressData = await fetchOrderProgress(order.po_number);
  //     if (progressData) {
  //       setSelectedOrderProgress({
  //         po_number: order.po_number,
  //         material: order.material || '',
  //         expected_tons: progressData.target || progressData.expected_tons || 0,
  //         current_tons: progressData.current || progressData.current_tons || 0,
  //         remaining_tons: progressData.remaining || progressData.remaining_tons || 0,
  //         progress_pct: progressData.progress_pct || 0,
  //         status: progressData.status || progressData.order_status || 'InProgress',
  //         last_tick: progressData.timestamp || progressData.last_tick || null,
  //         order_type: progressData.order_type,
  //         equipment_list: progressData.equipment_list,
  //         unit: progressData.unit
  //       });
  //       setShowProgressDialog(true);
  //     }
  //   }
  // };
  // Open progress dialog with real-time SCADA data
  const openProgressDialog = async (order: Order) => {
    if (order.status === 'InProgress' && order.po_number) {
      try {
       

        const response = await apiFetch(getApiUrl(`/api/orders/${order.po_number}/progress`));

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const progressData = await response.json();
       

        // Enhanced progress data with backend validation details
        // Convert TON to TO if present, or use TO for MILLING orders
        const orderType = progressData.order_type || (order as any).order_type;
        const unit = progressData.unit === 'TON' || progressData.unit === 'ton'
          ? 'TO'
          : (progressData.unit || (orderType === 'MILLING' ? 'TO' : 'BAG'));

        // ✅ FIX: Use confirmed_qty from backend if available, otherwise use current
        // confirmed_qty is the preserved cumulative production (doesn't reset after shift end)
        // current might be 0 after shift end if using shift_weight, so prefer confirmed_qty
        const currentDisplay = progressData.confirmed_qty !== undefined && progressData.confirmed_qty !== null
          ? progressData.confirmed_qty
          : (progressData.current || 0);

      

        setSelectedOrderProgress({
          po_number: order.po_number,
          material: order.material || '',
          version: order.version || '',
          expected_tons: progressData.target || 0,
          current_tons: currentDisplay,
          remaining_tons: progressData.remaining || 0,
          progress_pct: progressData.progress_pct || 0,
          status: progressData.status || progressData.order_status || 'Pending',
          last_tick: progressData.timestamp || null,
          order_type: orderType,
          equipment_list: progressData.equipment_list || [],
          unit: unit,
          // Enhanced equipment details from backend
          equipment_details: progressData.equipment_details || {},
          // Scale lock status from backend
          scale_lock_status: progressData.scale_lock_status || {
            scales_locked: false,
            locked_scales: {},
            locking_orders: [],
            message: null
          },
          scale_details: progressData.scale_details || [],
          // ✅ Byproduct scales (editable)
          scale1: progressData.scale1 || '',
          scale1_qty: progressData.scale1_qty || 0,
          scale2: progressData.scale2 || '',
          scale2_qty: progressData.scale2_qty || 0,
          scale3: progressData.scale3 || '',
          scale3_qty: progressData.scale3_qty || 0,
          byproduct_details: progressData.byproduct_details || {},
          // ✅ Add shift weight fields for manual confirmation calculation
          weight_shift_a: progressData.weight_shift_a || 0,
          weight_shift_b: progressData.weight_shift_b || 0,
          weight_shift_c: progressData.weight_shift_c || 0,
          confirmed_shift_a: progressData.confirmed_shift_a || 0,
          confirmed_shift_b: progressData.confirmed_shift_b || 0,
          confirmed_shift_c: progressData.confirmed_shift_c || 0,
          current_shift: progressData.current_shift || 'A',
          // Add validation-specific data
          variance: progressData.variance || 0,
          variance_pct: progressData.variance_pct || 0,
          tolerance_pct: progressData.tolerance_pct || 5.0,
          lower_limit: progressData.lower_limit || 0,
          upper_limit: progressData.upper_limit || 0,
          within_tolerance: progressData.within_tolerance || false
        });

        // ✅ REAL-TIME FIX: Use delta from byproduct_details for real-time values
        // This ensures byproduct quantities match the Delta values shown in Byproduct Scale Readings
        const byproductDetails = progressData.byproduct_details || {};
        const scale1Key = progressData.scale1 || '';
        const scale2Key = progressData.scale2 || '';
        const scale3Key = progressData.scale3 || '';
        
        setManualConfirmData({
          scrap: 0,
          confirmed_text: '',
          override_qty: null,
          custom_byproducts: {
            scale1_qty: byproductDetails[scale1Key]?.delta !== undefined 
              ? String(byproductDetails[scale1Key].delta.toFixed(3)) 
              : (progressData.scale1_qty ? String(progressData.scale1_qty) : ''),
            scale2_qty: byproductDetails[scale2Key]?.delta !== undefined 
              ? String(byproductDetails[scale2Key].delta.toFixed(3)) 
              : (progressData.scale2_qty ? String(progressData.scale2_qty) : ''),
            scale3_qty: byproductDetails[scale3Key]?.delta !== undefined 
              ? String(byproductDetails[scale3Key].delta.toFixed(3)) 
              : (progressData.scale3_qty ? String(progressData.scale3_qty) : '')
          }
        });

        setShowProgressDialog(true);

        // Show progress notification
        addToast(
          `📊 Order ${order.po_number} progress: ${progressData.progress_pct?.toFixed(1)}% complete (${progressData.current}/${progressData.target} ${progressData.unit})`,
          'info'
        );

      } catch (err) {
        console.error('Failed to fetch progress:', err);
        addToast('Failed to load progress data', 'error');
      }
    }
  };

  // Auto Validator functions
  const startAllValidation = async () => {
    try {
      

      // ⭐ SAFETY CHECK: Ensure we're not already running or locked
      if (autoValidationManuallyStarted) {
        
        addToast("Auto Validation is already running ✅", "info");
        return;
      }

      if (autoValidationLocked || isStartingValidation) {
        
        addToast("Auto Validation is busy - please wait ⚠️", "error");
        return;
      }

      setIsStartingValidation(true);

      // ✅ REMOVED: Auto-resetting priorities was causing issues when orders are filtered
      // The filtered orders array may not contain all orders, leading to incorrect priorities
      // Users can manually reset priorities using the "Reset Priorities" button if needed
      

      // ⭐ ENHANCED: Use the new start endpoint with timeout
      // 90 second timeout - allow time for SCADA baseline capture from SQL Server + multiple order starts
      // Each order start can take 1-2 seconds, so 90s allows for many orders
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);

      try {
        const response = await apiFetch(getApiUrl('/api/orders/auto-validator/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
         
          
          // Show count of orders started
          const startedCount = data.count || data.orders?.length || 0;
          const waitingCount = data.waiting_orders?.length || 0;
          let message = `Auto Validation started! ${startedCount} order(s) running`;
          if (waitingCount > 0) {
            message += `, ${waitingCount} waiting`;
          }
          addToast(`${message} ✅`, "success");

          // ⭐ CRITICAL: Set flag to indicate auto-validation was manually started
          setAutoValidationManuallyStarted(true);

          await fetchAutoValidatorStatus();
          await loadOrders();
          await loadKpiCounts();
        } else {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorMessage = errorData.message || errorMessage;

            // Handle "already running" case gracefully
            if (errorMessage.toLowerCase().includes('already running') ||
              errorMessage.toLowerCase().includes('already started')) {
              
              addToast("Auto Validation was already running - now monitoring status ✅", "info");

              // Set flag to start monitoring the existing process
              setAutoValidationManuallyStarted(true);
              await fetchAutoValidatorStatus();
              await loadOrders();
              await loadKpiCounts();
              return; // Exit early since we handled this case
            }
          } catch (parseError) {
            console.warn("Could not parse error response:", parseError);
          }

          addToast(`Failed to start Auto Validation: ${errorMessage}`, "error");
        }
      } catch (fetchError: any) {
        clearTimeout(timeoutId);

        if (fetchError.name === 'AbortError') {
          
          
          // ⭐ GRACEFUL TIMEOUT HANDLING: Orders may have started even if response timed out
          // Check the status and refresh the UI
          setAutoValidationManuallyStarted(true);
          await fetchAutoValidatorStatus();
          await loadOrders();
          await loadKpiCounts();
          
          // Check if any orders are actually InProgress
          const hasInProgressOrders = orders.some(o => o.status === 'InProgress');
          if (hasInProgressOrders) {
            addToast("Auto Validation started (response delayed) - orders are running ✅", "info");
          } else {
            addToast("Auto Validation start request timed out - please try again ⚠️", "warning");
          }
        } else {
          
          addToast(`Failed to start Auto Validation: ${fetchError.message}`, "error");
        }
      }

    } catch (err) {
      console.error("Failed to start auto validator:", err);
      addToast("Failed to start Auto Validation ❌", "error");
    } finally {
      setIsStartingValidation(false);
    }
  };

  const stopAllValidation = async () => {
    try {
      

      if (isStoppingValidation) {
       
        addToast("Auto Validation is already stopping - please wait ⚠️", "error");
        return;
      }

      setIsStoppingValidation(true);
      
      // ✅ AGGRESSIVE FIX: Enable lockdown FIRST to block ALL order updates
      stopLockdownActiveRef.current = true;
      
      // ✅ FIX: Set stop cooldown to prevent UI fluctuation during stop process
      lastStopTimeRef.current = Date.now();

      // ⭐ CRITICAL: Clear flag FIRST to stop polling immediately
      setAutoValidationManuallyStarted(false);

      // ⭐ SAFETY: Unlock auto-validation when stopping
      setAutoValidationLocked(false);

      // ⭐ CRITICAL: Update status locally immediately - NO DELAYS
      setAutoValidatorStatus(prev => ({
        ...prev,
        running: false,
        current_po: null,
        progress_pct: 0,
        expected_tons: 0,
        delta_tons: 0,
        baseline: null,
        last_tick: null
      }));
      
      // ✅ NUCLEAR FIX: Capture ALL InProgress order IDs and force them to show Pending
      // This overrides any state updates at the UI render level
      const inProgressOrderIds = orders
        .filter(o => o.status === 'InProgress')
        .map(o => o.po_number || String(o.id));
      forcedPendingOrdersRef.current = new Set(inProgressOrderIds);
      setForcedPendingVersion(v => v + 1); // Trigger re-render with forced Pending status

      
      // ✅ CRITICAL FIX: Immediately update ALL InProgress orders to Pending locally
      setOrders(prevOrders => prevOrders.map(order => 
        order.status === 'InProgress' 
          ? { ...order, status: 'Pending' } 
          : order
      ));
      
      // ✅ FIX: Only clear progress for orders being stopped (not all orders)
      // This preserves progress for manually started orders or orders from other validators
      setOrderProgress(prev => {
        const updated = { ...prev };
        inProgressOrderIds.forEach(id => delete updated[id]);
        return updated;
      });

      // ⭐ ENHANCED: Use the new stop endpoint with timeout
      // 30 second timeout - allow time for graceful shutdown and data persistence
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      try {
        const response = await apiFetch(getApiUrl('/api/orders/auto-validator/stop'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          

          // Show detailed success message
          const stoppedCount = data.stopped_count || 0;
          const dbUpdatedCount = data.db_updated_count || 0;
          let successMessage = `✅ Auto Validation stopped successfully`;
          if (stoppedCount > 0 || dbUpdatedCount > 0) {
            successMessage += `\n- Stopped ${stoppedCount} worker(s)\n- Updated ${dbUpdatedCount} order(s) to Pending`;
          }
          if (data.warning) {
            addToast(`${successMessage}\n⚠️ Warning: ${data.warning}`, "warning");
          } else {
            addToast(successMessage, "success");
          }

          // Verify the stop was successful by checking status
          try {
            const statusResponse = await apiFetch(getApiUrl('/api/orders/auto-validator/status'));
            if (statusResponse.ok) {
              const statusData = await statusResponse.json();
              if (!statusData.is_running) {
                
              } else {
                addToast("❌ Auto Validation stop failed - Backend still running", "error");
                
              }
            }
          } catch (statusError) {
            
          }
        } else {
          // Even if backend says it failed, we've already stopped locally
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorMessage = errorData.message || errorMessage;
          } catch (parseError) {
            console.warn("Could not parse error response:", parseError);
          }

          
          addToast("⚠️ Auto Validation stopped locally - Backend stop failed", "warning");
        }
      } catch (fetchError: any) {
        clearTimeout(timeoutId);

        if (fetchError.name === 'AbortError') {
          
          addToast("⚠️ Auto Validation stopped locally - Request timed out", "warning");
        } else {
          
          addToast("⚠️ Auto Validation stopped locally - Backend unreachable", "warning");
        }
      }

      // ⭐ FIX: Clear progress only for orders that were stopped (preserve others)
      // This preserves progress for manually started orders or orders from other validators
      setOrderProgress(prev => {
        const updated = { ...prev };
        forcedPendingOrdersRef.current.forEach(id => delete updated[id]);
        return updated;
      });
      setShowProgressDialog(false);
      setSelectedOrderProgress(null);
      
      // ✅ FORCE UPDATE: Set all orders to Pending AGAIN to make sure it sticks
      setOrders(prevOrders => {
        const updatedOrders = prevOrders.map(order => 
          order.status === 'InProgress' 
            ? { ...order, status: 'Pending' as const } 
            : order
        );
        
        return updatedOrders;
      });
      
      // ⭐ FIX: Don't refresh orders during stop - use the immediate state update
      // Only refresh KPI counts (they don't cause fluctuation)
      await loadKpiCounts();

      // ⭐ ADDITIONAL SAFETY: Double-check that polling is stopped

      
      // ✅ Release lockdown after a delay, then reset cooldown timer to prevent immediate polling
      // NOTE: Keep isStoppingValidation=true until this completes (button stays loading)
      setTimeout(async () => {
        try {
          stopLockdownActiveRef.current = false;
          
          
          // ✅ CRITICAL: Reset the cooldown timer NOW to get another full cooldown period
          lastStopTimeRef.current = Date.now();
         
          
          // ✅ Clear forced pending list BEFORE refresh so we get real status from DB
          forcedPendingOrdersRef.current = new Set();
          setForcedPendingVersion(v => v + 1); // Trigger re-render to show real status
          
          
          // Now do a final refresh to get accurate data from database
          await loadOrders();
          
        } finally {
          // NOW we can clear the loading state - button becomes clickable again
          setIsStoppingValidation(false);
          
        }
      }, STOP_COOLDOWN_MS);

    } catch (err) {
      console.error("Failed to stop auto validator:", err);
      addToast("Failed to stop Auto Validation ❌", "error");
      // Release lockdown and loading state on error
      stopLockdownActiveRef.current = false;
      setIsStoppingValidation(false);
    }
    // NOTE: No finally block - isStoppingValidation is managed inside the timeout
  };

  const resetPriorities = async () => {
    try {
      

      // Create new priorities based on current order in the table (1-based indexing)
      const newPriorities: Record<number, number> = {};
      orders.forEach((order, index) => {
        newPriorities[order.id] = index + 1;
      });

      

      // Save the reset priorities to backend
      await savePriorityOrder(newPriorities);

      addToast(`Priorities reset to proper sequence (1, 2, 3, etc.) ✅`, "success");
      await loadOrders(); // Refresh to show updated priorities
    } catch (err) {
      console.error("Failed to reset priorities:", err);
      addToast("Failed to reset priorities ❌", "error");
    }
  };

  const fetchAutoValidatorStatus = async () => {
    try {
      // ✅ AGGRESSIVE FIX: Skip if stop lockdown is active
      if (stopLockdownActiveRef.current) {
        
        return;
      }
      
      // ✅ FIX: Skip if stop cooldown is active (prevents UI fluctuation after stop)
      const timeSinceLastStop = Date.now() - lastStopTimeRef.current;
      if (timeSinceLastStop < STOP_COOLDOWN_MS) {
        
        return;
      }
      
      // Get auto-validator status
      const response = await apiFetch(getApiUrl('/api/orders/auto-validator/status'));
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      

      // Update auto-validator status
      setAutoValidatorStatus(prev => {
        // ⭐ CRITICAL: Don't override local stop state with backend status
        // If we manually stopped it locally, keep it stopped regardless of backend
        if (!autoValidationManuallyStarted && prev.running === false) {
          
          return prev;
        }

        // Only update state if there's an actual change
        if (prev.running === data.is_running) {
          return prev; // Don't update if nothing changed
        }

        const newStatus = {
          running: data.is_running,
          current_po: null,  // Will be updated from orders
          progress_pct: 0,
          expected_tons: 0,
          delta_tons: 0,
          baseline: null,
          last_tick: null
        };

        
        return newStatus;
      });

      // ✅ OPTIMIZED: Progress fetching moved to updateDataSilently to reduce API calls
      // Only clear auto-validator status if no InProgress orders exist
      if (data.is_running) {
        const inProgressOrders = orders.filter(order => order.status === 'InProgress');
        if (inProgressOrders.length === 0) {
          setAutoValidatorStatus(prev => {
            if (prev.current_po) {
              return {
                ...prev,
                current_po: null,
                progress_pct: 0,
                expected_tons: 0,
                delta_tons: 0,
                last_tick: null
              };
            }
            return prev;
          });
        }
      }

    } catch (err) {
      console.error("Failed to fetch validator status:", err);
    }
  };

  // Poll auto validator status every 5 seconds - ONLY when manually started
  // ✅ REDUCED FREQUENCY: Changed from 3 seconds to 5 seconds to reduce refresh rate
  useEffect(() => {
    // ⭐ CRITICAL: Only start polling if auto-validation was manually started by user
    if (!autoValidationManuallyStarted) {
     
      return;
    }

    

    // Initial fetch
    fetchAutoValidatorStatus();

    const interval = setInterval(async () => {
      // ⭐ ENHANCED: Triple-check the flag before each poll
      if (autoValidationManuallyStarted) {
        await fetchAutoValidatorStatus();
      } else {
        
        clearInterval(interval);
      }
    }, 5000); // Reduced to 5 seconds to prevent server overload

    return () => {
     
      clearInterval(interval);
    };
  }, [autoValidationManuallyStarted]); // ⭐ Only poll when manually started

  // ✅ BACKGROUND DATA UPDATE: Silently update orders list and KPI counts without page refresh
  // Updates data every 15 seconds to show latest values (current, confirmed, remaining, status, progress)
  // This ensures data stays current without causing visible page refreshes
  useEffect(() => {
    let isMounted = true;

    // Background update function that doesn't show loading spinner
    const updateDataSilently = async () => {
      if (!isMounted) return;
      
      // ✅ AGGRESSIVE FIX: Skip if stop lockdown is active (blocks ALL updates)
      if (stopLockdownActiveRef.current) {
        
        return;
      }
      
      // ✅ FIX: Skip polling if drag operation happened recently (prevents double refresh)
      const timeSinceLastDrag = Date.now() - lastDragTimeRef.current;
      if (timeSinceLastDrag < DRAG_COOLDOWN_MS) {
      
        return;
      }
      
      // ✅ FIX: Skip polling if validation refresh happened recently (prevents double refresh)
      const timeSinceLastValidation = Date.now() - lastValidationRefreshTimeRef.current;
      if (timeSinceLastValidation < VALIDATION_COOLDOWN_MS) {
        
        return;
      }
      
      // ✅ FIX: Skip polling if auto-validator was stopped recently (prevents UI fluctuation)
      const timeSinceLastStop = Date.now() - lastStopTimeRef.current;
      if (timeSinceLastStop < STOP_COOLDOWN_MS) {
        
        return;
      }

      try {
        // ✅ Silently update orders list - fetch fresh data without showing loading spinner
        const offset = (currentPage - 1) * itemsPerPage;
        // Include Completed and Validated orders so they remain visible
        const statusFilterParam = statusFilter === 'All' ? 'Pending,InProgress,Completed,Validated' : statusFilter;
        // ✅ Build order_type filter for API - filter by type BEFORE pagination
        const orderTypeParam = activeOrderTab === 'milling' ? '&order_type=MILLING' 
                             : activeOrderTab === 'packing' ? '&order_type=PACKING' 
                             : '';

        const response = await apiFetch(getApiUrl(`/api/sap-sync/orders?statuses=${statusFilterParam}&limit=${itemsPerPage}&offset=${offset}${orderTypeParam}`));
        if (response.ok && isMounted) {
          const responseData = await response.json();
          const apiOrders = responseData.ok ? responseData.orders : [];
          const totalCount = responseData.total || apiOrders.length;

          // ✅ Fetch conflict info from backend (same as loadOrders)
          let conflictInfo: Record<string, any> = {};
          try {
            const conflictResponse = await apiFetch(getApiUrl(`/api/orders/with-conflicts?status=${statusFilterParam}`));
            if (conflictResponse.ok) {
              const conflictData = await conflictResponse.json();
              if (conflictData.success && conflictData.orders) {
                conflictData.orders.forEach((order: any) => {
                  const key = order.po_number || order.id?.toString();
                  if (key) {
                    conflictInfo[key] = {
                      has_priority_conflict: order.has_priority_conflict || false,
                      conflict_group_priority: order.conflict_group_priority,
                      conflict_can_run: order.conflict_can_run,
                      conflict_waiting_for: order.conflict_waiting_for || [],
                      conflict_shared_scales: order.conflict_shared_scales || [],
                      conflict_shared_with: order.conflict_shared_with || [],
                      conflict_group_id: order.conflict_group_id,
                      detected_scales: order.detected_scales || []
                    };
                  }
                });
              }
            }
          } catch (conflictError) {
            console.error('⚠️ Background conflict info fetch failed:', conflictError);
          }

          // ✅ FIX: Use API priority directly as source of truth (database values)
          const apiPriorities: Record<number, number> = {};
          apiOrders.forEach((order: any) => {
            if (order.id && order.priority !== undefined && order.priority !== null) {
              apiPriorities[order.id] = order.priority;
            }
          });

          // Update state with priorities from database
          setOrderPriorities(apiPriorities);
          // Sync localStorage
          localStorage.setItem('orderPriorities', JSON.stringify(apiPriorities));

          // Auto-classify orders if needed AND merge conflict info
          // ✅ FIX: Use order.priority directly from API (database is source of truth)
          const classifiedOrders = apiOrders.map((order: any) => {
            let enrichedOrder = order;
            if (!order.order_type || order.order_type === 'Unknown') {
              const classification = classifyOrderByMaterial(order.material || '');
              enrichedOrder = { ...order, order_type: classification.order_type };
            }
            
            // ✅ FIX: Use priority directly from API response (database is source of truth)
            // Ensure priority is always a number for proper sorting
            const rawPriority = order.priority;
            const orderPriority = typeof rawPriority === 'number' ? rawPriority : 
                                 (rawPriority !== undefined && rawPriority !== null ? Number(rawPriority) : 999);
            enrichedOrder = { ...enrichedOrder, priority: isNaN(orderPriority) ? 999 : orderPriority };
            
            // ✅ Merge conflict info from backend
            const key = order.po_number || order.id?.toString();
            const conflict = conflictInfo[key];
            if (conflict) {
              enrichedOrder = {
                ...enrichedOrder,
                has_priority_conflict: conflict.has_priority_conflict,
                conflict_group_priority: conflict.conflict_group_priority,
                conflict_can_run: conflict.conflict_can_run,
                conflict_waiting_for: conflict.conflict_waiting_for,
                conflict_shared_scales: conflict.conflict_shared_scales,
                conflict_shared_with: conflict.conflict_shared_with,
                conflict_group_id: conflict.conflict_group_id,
                detected_scales: conflict.detected_scales
              };
            }
            
            return enrichedOrder;
          });

          // ✅ OPTIMIZED: Fetch real-time byproduct values using BATCH endpoint (reduces N calls to 1)
          // This ensures the order list shows accumulated totals (stored + current delta)
          const inProgressMillingOrders = classifiedOrders.filter(
            (order: any) => 
              order.order_type === 'MILLING' && 
              order.po_number && 
              order.status === 'InProgress' &&
              !forcedPendingOrdersRef.current.has(order.po_number)
          );

          // ✅ Use batch endpoint instead of N individual calls
          if (inProgressMillingOrders.length > 0) {
            try {
              const orderIds = inProgressMillingOrders.map((order: any) => order.po_number);
              console.log(`📊 Fetching progress for ${orderIds.length} orders via batch endpoint`);
              
              const batchResponse = await apiFetch(getApiUrl('/api/orders/progress-batch'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_ids: orderIds })
              });

              if (batchResponse.ok) {
                const batchData = await batchResponse.json();
                
                if (batchData.success && batchData.data) {
                  // Merge byproduct values into orders from batch response
                  classifiedOrders.forEach((order: any) => {
                    if (forcedPendingOrdersRef.current.has(order.po_number)) return;
                    
                    const progressData = batchData.data[order.po_number];
                    if (progressData) {
                      order.scale1_qty = progressData.scale1_qty ?? 0;
                      order.scale2_qty = progressData.scale2_qty ?? 0;
                      order.scale3_qty = progressData.scale3_qty ?? 0;
                    }
                  });
                  
                  console.log(`✅ Batch progress fetched: ${batchData.summary?.success || 0} orders`);
                }
              } else {
                console.warn('Batch progress endpoint returned error:', batchResponse.status);
              }
            } catch (err) {
              console.warn('Failed to fetch batch progress:', err);
            }
          }

          // ✅ FIX: Preserve existing byproduct values for non-InProgress MILLING orders
          // when API returns null/undefined (prevents values from being lost during refresh)
          classifiedOrders.forEach((newOrder: any) => {
            // Only preserve for MILLING orders that are NOT InProgress
            if (newOrder.order_type === 'MILLING' && newOrder.status !== 'InProgress') {
              // Find existing order in current state
              const existingOrder = orders.find(o => o.po_number === newOrder.po_number);
              if (existingOrder) {
                // Preserve scale names if new ones are null/undefined (needed for display condition)
                if (!newOrder.scale1 && (existingOrder as any).scale1) {
                  newOrder.scale1 = (existingOrder as any).scale1;
                }
                if (!newOrder.scale2 && (existingOrder as any).scale2) {
                  newOrder.scale2 = (existingOrder as any).scale2;
                }
                if (!newOrder.scale3 && (existingOrder as any).scale3) {
                  newOrder.scale3 = (existingOrder as any).scale3;
                }
                // Preserve byproduct quantities if new ones are null/undefined
                if (newOrder.scale1_qty === null || newOrder.scale1_qty === undefined) {
                  newOrder.scale1_qty = (existingOrder as any).scale1_qty ?? 0;
                }
                if (newOrder.scale2_qty === null || newOrder.scale2_qty === undefined) {
                  newOrder.scale2_qty = (existingOrder as any).scale2_qty ?? 0;
                }
                if (newOrder.scale3_qty === null || newOrder.scale3_qty === undefined) {
                  newOrder.scale3_qty = (existingOrder as any).scale3_qty ?? 0;
                }
              }
            }
          });

          // ✅ FIX: Sort by STATUS first (InProgress on top), then by database priority
          // This ensures InProgress orders are always visible at the top of the table
          const sortedOrders = classifiedOrders.sort((a: Order, b: Order) => {
            // ✅ Primary sort: by status (InProgress first for visibility)
            const statusOrder: Record<string, number> = { 'InProgress': 0, 'Pending': 1, 'Completed': 2, 'Validated': 3 };
            const statusA = statusOrder[a.status] ?? 4;
            const statusB = statusOrder[b.status] ?? 4;
            
            if (statusA !== statusB) {
              return statusA - statusB;
            }
            
            // ✅ Jan 30, 2026: Sort by database priority (consistent with backend pagination)
            // Lower priority number = higher priority (1 is top priority)
            const priorityA = (a as any).priority ?? 999;
            const priorityB = (b as any).priority ?? 999;
            
            if (priorityA !== priorityB) {
              return priorityA - priorityB;
            }
            
            // Tiebreaker: sort by id ascending (older orders first)
            return a.id - b.id;
          });

          // Filter out orders where confirmation matches target (final confirmation sent to SAP)
          // Hide orders only when last_confirmed_qty matches the target (expected_weight for MILLING, quantity for PACKING)
          const filteredOrders = sortedOrders.filter((order: any) => {
            const orderType = order.order_type;
            const lastConfirmedQty = order.last_confirmed_qty || 0;
            let targetQty = 0;

            if (orderType === 'MILLING') {
              targetQty = order.expected_weight || order.quantity || 0;
            } else {
              // PACKING
              targetQty = order.quantity || 0;
            }

            // Hide order if confirmation matches target (final confirmation sent)
            // Use a small tolerance (0.01) for floating point comparison
            const tolerance = 0.01;
            const matchesTarget = Math.abs(lastConfirmedQty - targetQty) < tolerance;

            if (matchesTarget) {
              return false;
            }

            return true;
          });

          // Update orders and total count
          if (isMounted) {
            // ✅ CRITICAL: Check lockdown again RIGHT BEFORE setting state
            // This catches race conditions where the fetch started before lockdown but completes after
            if (stopLockdownActiveRef.current) {
              
              return;
            }
            
            // ✅ CRITICAL: Override status for any orders in forcedPendingOrdersRef
            // This ensures stopped orders always show Pending regardless of API data
            const ordersWithForcedPending = filteredOrders.map((order: any) => {
              const orderId = order.po_number || String(order.id);
              if (forcedPendingOrdersRef.current.has(orderId)) {
               
                return { ...order, status: 'Pending' };
              }
              return order;
            });
            
            // ✅ FIX: Save scroll position before state update to prevent jump to top
            const scrollY = window.scrollY || window.pageYOffset;
            
            setOrders(ordersWithForcedPending);
            setTotalOrders(totalCount);
            
            // ✅ FIX: Restore scroll position after React re-renders
            requestAnimationFrame(() => {
              window.scrollTo(0, scrollY);
            });
          }
        }

        // ✅ Silently update KPI counts
        if (isMounted) {
          await loadKpiCounts();
        }
      } catch (error) {
        console.error("⚠️ Background data update failed:", error);
        // Don't show error to user - silent background update
      }
    };

    // Initial load with loading indicator (only on mount)
    loadOrders();
    loadKpiCounts();

    // Update data in background every 5 seconds (reduced from 2s to prevent server overload)
    const interval = setInterval(updateDataSilently, 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [statusFilter, currentPage, itemsPerPage, activeOrderTab]); // ✅ Re-run when filters change

  // Poll for shift-end auto confirmation notifications
  // ✅ Use localStorage to persist shownNotifications across page refreshes
  const getStoredNotifications = (): Set<string> => {
    try {
      const stored = localStorage.getItem('hercules_shown_shift_confirmations');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Only keep notifications from last 24 hours to prevent localStorage from growing too large
        const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
        const filtered = parsed.filter((item: any) => {
          if (item.timestamp) {
            const itemTime = new Date(item.timestamp).getTime();
            return itemTime > oneDayAgo;
          }
          return false;
        });
        return new Set(filtered.map((item: any) => item.key));
      }
    } catch (error) {
      console.error('Error loading stored notifications:', error);
    }
    return new Set();
  };

  const saveNotification = (key: string, timestamp: string) => {
    try {
      const stored = localStorage.getItem('hercules_shown_shift_confirmations');
      const items = stored ? JSON.parse(stored) : [];
      items.push({ key, timestamp });
      // Keep only last 100 items to prevent localStorage from growing too large
      const recentItems = items.slice(-100);
      localStorage.setItem('hercules_shown_shift_confirmations', JSON.stringify(recentItems));
    } catch (error) {
      console.error('Error saving notification:', error);
    }
  };

  const shownNotificationsRef = useRef<Set<string>>(getStoredNotifications());

  useEffect(() => {
    const checkShiftConfirmations = async () => {
      try {
        const response = await apiFetch(getApiUrl('/api/process_orders/shift-confirmations'));
        if (!response.ok) return;

        const data = await response.json();
        if (data.success && data.confirmations && data.confirmations.length > 0) {
          // ✅ Filter to only process confirmations that haven't been shown
          const newConfirmations = data.confirmations.filter((c: any) => {
            // Create unique key: id + timestamp + successful_shifts
            const timestamp = c.timestamp || '';
            const shifts = (c.successful_shifts || []).join(',');
            const uniqueKey = `${c.id}_${timestamp}_${shifts}`;
            
            // ✅ Check if notification is recent (within last 2 minutes) to prevent showing old ones
            let isRecent = false;
            if (timestamp) {
              try {
                const notificationTime = new Date(timestamp).getTime();
                const now = Date.now();
                const ageMinutes = (now - notificationTime) / (1000 * 60);
                isRecent = ageMinutes >= 0 && ageMinutes <= 2; // Only show if 0-2 minutes old
                
                if (!isRecent) {
                  
                  return false;
                }
              } catch (e) {
                console.error('Error parsing timestamp:', e);
                return false;
              }
            }
            
            // Only show if we haven't seen this exact notification before
            if (shownNotificationsRef.current.has(uniqueKey)) {
            
              return false;
            }
            
            // Mark as shown (both in memory and localStorage)
            shownNotificationsRef.current.add(uniqueKey);
            saveNotification(uniqueKey, timestamp);
           
            return true;
          });

          if (newConfirmations.length > 0) {
            

            // Show notification for each new confirmation (only once)
            newConfirmations.forEach((conf: any) => {
              const details = conf.successful_details || [];
              const detailText = details.length > 0
                ? `\n\nConfirmed:\n${details.join('\n')}`
                : '';

              const message = `Shift-end confirmation sent to SAP successfully.\n\n${conf.successful_count} order(s) confirmed${conf.failed_count > 0 ? `, ${conf.failed_count} failed` : ''}${detailText}`;

              showCustomAlert(
                '✅ Shift-End Confirmation',
                message,
                'success'
              );
            });
          } else {
            
          }
        }
      } catch (error) {
        console.error('Error checking shift confirmations:', error);
      }
    };

    // ✅ Check every 60 seconds (reduced frequency to prevent duplicate checks)
    const interval = setInterval(checkShiftConfirmations, 60000);

    // Initial check after 10 seconds (give backend time to process shift end)
    setTimeout(checkShiftConfirmations, 10000);

    return () => clearInterval(interval);
  }, []); // Empty dependency array - this effect should only run once on mount

  // Periodic refresh of progress dialog when open
  // ✅ INCREASED FREQUENCY: Changed to 2 seconds for faster real-time updates
  // Note: Delta updates from SCADA are immediate, but confirmed_qty is updated by worker (1s cycle)
  // 2 second polling ensures responsive UI while not overloading the server
  useEffect(() => {
    if (!showProgressDialog || !selectedOrderProgress) return;

    const interval = setInterval(async () => {
      // ✅ AGGRESSIVE FIX: Skip if stop lockdown is active
      if (stopLockdownActiveRef.current) {
        
        setShowProgressDialog(false);
        setSelectedOrderProgress(null);
        return;
      }
      
      // ✅ FIX: Skip polling if stop cooldown is active (prevents UI fluctuation)
      const timeSinceLastStop = Date.now() - lastStopTimeRef.current;
      if (timeSinceLastStop < STOP_COOLDOWN_MS) {
        
        // Close dialog during stop to prevent stale data
        setShowProgressDialog(false);
        setSelectedOrderProgress(null);
        return;
      }
      
      const progressData = await fetchOrderProgress(selectedOrderProgress.po_number);
      if (progressData) {
        // ✅ FIX: If order status changed to Pending (stopped), close the dialog
        const newStatus = progressData.status || progressData.order_status;
        if (newStatus === 'Pending') {
        
          setShowProgressDialog(false);
          setSelectedOrderProgress(null);
          return;
        }
        
        setSelectedOrderProgress(prev => {
          if (!prev) return null;

          // Convert TON to TO if present
          const unit = progressData.unit === 'TON' || progressData.unit === 'ton'
            ? 'TO'
            : (progressData.unit || prev.unit || 'TO');

          // ✅ FIX: Use confirmed_qty from backend if available, otherwise use current
          // confirmed_qty is the preserved cumulative production (doesn't reset after shift end)
          const currentDisplay = progressData.confirmed_qty !== undefined && progressData.confirmed_qty !== null
            ? progressData.confirmed_qty
            : (progressData.current || progressData.current_tons || 0);

          return {
            ...prev,
            current_tons: currentDisplay,
            remaining_tons: progressData.remaining || progressData.remaining_tons || 0,
            progress_pct: progressData.progress_pct || 0,
            status: progressData.status || progressData.order_status || prev.status || 'Pending',
            last_tick: progressData.timestamp || progressData.last_tick || null,
            equipment_list: progressData.equipment_list || prev.equipment_list,
            unit: unit,
            equipment_details: progressData.equipment_details || prev.equipment_details || {},
            scale_details: progressData.scale_details || prev.scale_details || [],
            scale_lock_status: progressData.scale_lock_status || prev.scale_lock_status,
            // ✅ Byproduct scales (editable) - update if provided in progressData
            scale1: progressData.scale1 !== undefined ? progressData.scale1 : prev.scale1,
            scale1_qty: progressData.scale1_qty !== undefined ? progressData.scale1_qty : prev.scale1_qty,
            scale2: progressData.scale2 !== undefined ? progressData.scale2 : prev.scale2,
            scale2_qty: progressData.scale2_qty !== undefined ? progressData.scale2_qty : prev.scale2_qty,
            scale3: progressData.scale3 !== undefined ? progressData.scale3 : prev.scale3,
            scale3_qty: progressData.scale3_qty !== undefined ? progressData.scale3_qty : prev.scale3_qty,
            byproduct_details: progressData.byproduct_details !== undefined ? progressData.byproduct_details : prev.byproduct_details,
          };
        });
        
        // ✅ REAL-TIME FIX: Also update byproduct quantities in manualConfirmData
        if (progressData.byproduct_details) {
          const byproductDetails = progressData.byproduct_details;
          const scale1Key = progressData.scale1 || '';
          const scale2Key = progressData.scale2 || '';
          const scale3Key = progressData.scale3 || '';
          
          setManualConfirmData(prev => ({
            ...prev,
            custom_byproducts: {
              scale1_qty: byproductDetails[scale1Key]?.delta !== undefined 
                ? String(byproductDetails[scale1Key].delta.toFixed(3)) 
                : prev.custom_byproducts.scale1_qty,
              scale2_qty: byproductDetails[scale2Key]?.delta !== undefined 
                ? String(byproductDetails[scale2Key].delta.toFixed(3)) 
                : prev.custom_byproducts.scale2_qty,
              scale3_qty: byproductDetails[scale3Key]?.delta !== undefined 
                ? String(byproductDetails[scale3Key].delta.toFixed(3)) 
                : prev.custom_byproducts.scale3_qty,
            }
          }));
        }
      }
    }, 1000); // ✅ Changed to 1000ms (1 second) for real-time updates

    return () => clearInterval(interval);
  }, [showProgressDialog, selectedOrderProgress]);

  // Note: Order validation detection is now handled in fetchAutoValidatorStatus function

  // Helper function to add toast notifications
  const addToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    const id = Date.now().toString();
    const newToast = { id, message, type };
    setToasts(prev => [...prev, newToast]);

    // Auto remove toast after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 5000);

   
  };

  // Helper function to show custom popup
  const showCustomAlert = (title: string, message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', onConfirm?: () => void) => {
    setPopupData({ title, message, type, onConfirm });
    setShowCustomPopup(true);
  };

  // Close custom popup
  const closeCustomPopup = () => {
    setShowCustomPopup(false);
    setPopupData(null);
  };





  // Open orders modal for validated, rejected, inprogress orders, error logs, or offline orders
  const openOrdersModal = async (type: 'confirmed' | 'completed' | 'rejected' | 'inprogress' | 'errorlog' | 'offline') => {
    try {
      setModalType(type);

      // Set modal title based on type
      let title = '';
      let statusFilter = '';
      if (type === 'confirmed') {
        title = 'Confirmed Orders';
        statusFilter = 'Confirmed';
      } else if (type === 'completed') {
        title = 'Completed Orders';
        statusFilter = 'Completed,Validated,CNF,COMP';
      } else if (type === 'rejected') {
        title = 'Rejected Orders';
        statusFilter = 'Rejected';
      } else if (type === 'inprogress') {
        title = 'In Progress Orders';
        statusFilter = 'InProgress';
      } else if (type === 'errorlog') {
        title = 'Error Log';
        statusFilter = '';
      } else if (type === 'offline') {
        title = 'Offline Orders (Pending)';
        statusFilter = '';
      }

      setModalTitle(title);

      // Fetch offline orders (filter by order_type for operators: packing sees only packing, milling only milling)
      if (type === 'offline') {
        let offlineUrl = getApiUrl('/api/offline-confirmations?status=pending');
        if (canAccessPacking && !canAccessMilling) offlineUrl += '&order_type=PACKING';
        else if (canAccessMilling && !canAccessPacking) offlineUrl += '&order_type=MILLING';
        const response = await apiFetch(offlineUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        const data = await response.json();
        
        // Convert to order-like format
        const formattedOrders = (data.offline_confirmations || []).map((item: any) => ({
          id: item.id,
          po_number: item.order_id,
          material: item.material,
          version: item.version,
          quantity: item.total_qty,
          confirmed_qty: item.confirmed_weight,
          unit: item.uom || 'KG',  // Map uom to unit for display
          status: item.status,
          created_at: item.created_at,
          updated_at: item.updated_at,
          scrap: item.scrap || 0,
          confirmed_text: item.confirmed_text || '',
          shift: item.shift || '',
          plant: item.plant || '',
          batch: item.batch || '',
          retry_count: item.retry_count,
          validation_method: item.validation_method,
          is_offline: true, // Flag to identify offline orders in UI
          sap_payload: item.sap_payload
        }));
        
        setModalOrders(formattedOrders);
        setShowOrdersModal(true);
        return;
      }

      // Fetch error logs from error log API
      if (type === 'errorlog') {
        const response = await apiFetch(getApiUrl('/api/error-log/'));
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }

        const errorLogs = await response.json();
        // Convert error log entries to order-like format for display
        const formattedOrders = Array.isArray(errorLogs) ? errorLogs.map((log: any) => {
          // Extract material from payload since error_log table doesn't have material column
          let material = 'N/A';
          try {
            const payload = typeof log.payload === 'string' ? JSON.parse(log.payload) : log.payload;
            material = payload?.sent_payload?.material || payload?.material || 'N/A';
          } catch (e) {
            // Keep default N/A if parsing fails
          }
          
          return {
            id: log.id || 0,
            po_number: log.po_number || 'N/A',
            material: material,
            order_type: log.order_type || 'Unknown',
            quantity: log.quantity || 0,
            expected_weight: log.expected_weight || 0,
            confirmed_qty: log.confirmed_qty || 0,
            status: log.status || 'Error',
            created_at: log.created_at,
            updated_at: log.updated_at || log.created_at,
            error_message: log.error_message || log.message || 'Unknown error',
            error_type: log.error_type || '',
            source: log.source || '',
            payload: log.payload,
            resolved_at: log.resolved_at
          };
        }) : [];
        setModalOrders(formattedOrders);
        setShowOrdersModal(true);
        return;
      }

      // Fetch orders with the specific status using SAP sync endpoint to get updated_at
      const response = await apiFetch(getApiUrl(`/api/sap-sync/orders?statuses=${statusFilter}&limit=1000`));
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const responseData = await response.json();
      const orders = responseData.ok ? responseData.orders : [];
      setModalOrders(orders);
      setShowOrdersModal(true);
    } catch (err) {
      console.error(`Failed to load ${type} orders:`, err);
      setError(`Failed to load ${type} orders from server.`);
    }
  };

  // Close orders modal
  const closeOrdersModal = () => {
    setShowOrdersModal(false);
    setModalOrders([]);
    setModalTitle('');
    setSearchTerm('');
    setStartDate('');
    setEndDate('');
    setModalCurrentPage(1); // Reset pagination
  };

  // Filter and sort orders for modal display
  const getFilteredAndSortedOrders = () => {
    let filtered = modalOrders.filter(order => {
      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch = (
          order.id.toString().includes(searchLower) ||
          (order.po_number && order.po_number.toLowerCase().includes(searchLower)) ||
          (order.material && order.material.toLowerCase().includes(searchLower)) ||
          (order.batch && order.batch.toLowerCase().includes(searchLower))
        );
        if (!matchesSearch) return false;
      }

      // Date filter
      if (startDate || endDate) {
        const orderDate = new Date((order as any).updated_at || order.created_at || 0);
        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;

        if (start && orderDate < start) return false;
        if (end && orderDate > end) return false;
      }

      return true;
    });

    // Sort by updated date (newest first)
    filtered.sort((a, b) => {
      const aDate = new Date((a as any).updated_at || a.created_at || 0).getTime();
      const bDate = new Date((b as any).updated_at || b.created_at || 0).getTime();
      return bDate - aDate; // Descending order (newest first)
    });

    return filtered;
  };

  // Get paginated orders for modal
  const getPaginatedModalOrders = () => {
    const filtered = getFilteredAndSortedOrders();
    const startIndex = (modalCurrentPage - 1) * modalItemsPerPage;
    const endIndex = startIndex + modalItemsPerPage;
    return filtered.slice(startIndex, endIndex);
  };

  // Modal pagination handlers
  const handleModalPageChange = (page: number) => {
    setModalCurrentPage(page);
  };

  const handleModalItemsPerPageChange = (newItemsPerPage: number) => {
    setModalItemsPerPage(newItemsPerPage);
    setModalCurrentPage(1); // Reset to first page when changing items per page
  };

  // Calculate KPI totals for validated orders
  const calculateValidatedKPIs = () => {
    const filteredOrders = getFilteredAndSortedOrders();

    const totalExpectedWeight = filteredOrders.reduce((sum, order) => {
      const expectedWeight = (order as any).expected_weight ? parseFloat((order as any).expected_weight) : 0;
      return sum + expectedWeight;
    }, 0);

    const totalConfirmedWeight = filteredOrders.reduce((sum, order) => {
      const confirmedQty = (order as any).confirmed_qty ? parseFloat((order as any).confirmed_qty) : 0;
      return sum + confirmedQty;
    }, 0);

    return {
      totalExpectedWeight: parseFloat(totalExpectedWeight.toFixed(2)),
      totalConfirmedWeight: parseFloat(totalConfirmedWeight.toFixed(2))
    };
  };

  // Function to determine shift based on validation time
  const getShiftFromTime = (dateTime: string | Date, operation: 'milling' | 'packing' = 'milling') => {
    const date = new Date(dateTime);
    const hour = date.getHours();
    const minute = date.getMinutes();
    const timeInMinutes = hour * 60 + minute;

  

    if (operation === 'milling') {
      // Milling shifts: 7am-3pm (A), 3pm-11pm (B), 11pm-7am (C)
      if (timeInMinutes >= 7 * 60 && timeInMinutes < 15 * 60) {
       
        return 'A';
      } else if (timeInMinutes >= 15 * 60 && timeInMinutes < 23 * 60) {
        
        return 'B';
      } else {
       
        return 'C';
      }
    } else {
      // Packing shifts: 7:30am-3:30pm (A), 3:30pm-11:30pm (B)
      if (timeInMinutes >= 7 * 60 + 30 && timeInMinutes < 15 * 60 + 30) {
       
        return 'A';
      } else {
       
        return 'B';
      }
    }
  };

  // Function to determine operation type based on material or other criteria
  const getOperationType = (order: any): 'milling' | 'packing' => {
    // For now, we'll use milling as default since most orders are milling operations
    // In the future, this could be determined by material type, plant, or other criteria
    return 'milling';
  };

  // Pagination handlers
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1); // Reset to first page when changing items per page
  };

  // Calculate total pages
  const totalPages = Math.ceil(totalOrders / itemsPerPage);

  // KPI calculations - use database counts
  const totalOrdersForKPI = kpiCounts.total;
  const inProgressOrders = kpiCounts.inProgress;
  const rejectedOrders = kpiCounts.rejected;
  const errorLogCount = kpiCounts.errorLog;

  // Orders for table - filter by PO number search term and active tab
  // ✅ PERFORMANCE FIX: Memoize to prevent recalculation on every render
  // Only recalculates when orders, activeOrderTab, or poSearchTerm changes
  const filteredOrders = useMemo(() => {
    // First filter by tab and search term
    const filtered = orders.filter(order => {
      // Tab filter
      if (activeOrderTab === 'milling' && (order as any).order_type !== 'MILLING') return false;
      if (activeOrderTab === 'packing' && (order as any).order_type !== 'PACKING') return false;

      if (!poSearchTerm.trim()) {
        return true; // Show all orders if search is empty
      }
      const searchLower = poSearchTerm.toLowerCase().trim();
      const poNumber = order.po_number?.toLowerCase() || '';
      const material = (order as any).material?.toLowerCase() || '';
      const batch = (order as any).batch?.toLowerCase() || '';
      const orderIdStr = order.id?.toString().toLowerCase() || '';
      return (
        poNumber.includes(searchLower) ||
        material.includes(searchLower) ||
        batch.includes(searchLower) ||
        orderIdStr.includes(searchLower)
      );
    });

    // Then sort: Primary by STATUS, Secondary by CAN_RUN (green buttons first), Tertiary by PRIORITY
    const sorted = [...filtered].sort((a, b) => {
      // ✅ Feb 5, 2026: Updated status order - Completed before Validated
      const statusOrder: Record<string, number> = { 'InProgress': 0, 'Pending': 1, 'Completed': 2, 'Validated': 3 };
      const statusA = statusOrder[a.status] ?? 4;
      const statusB = statusOrder[b.status] ?? 4;
      
      if (statusA !== statusB) {
        return statusA - statusB;
      }

      // ✅ Jan 30, 2026: GROUP-WISE - Unlocked orders (green Start) come FIRST as a group
      const hasConflictA = (a as any).has_priority_conflict === true;
      const canRunA = (a as any).conflict_can_run !== false;
      const isLockedA = hasConflictA && !canRunA;
      
      const hasConflictB = (b as any).has_priority_conflict === true;
      const canRunB = (b as any).conflict_can_run !== false;
      const isLockedB = hasConflictB && !canRunB;
      
      // Unlocked orders (can run) come first as Priority 1 group
      if (isLockedA !== isLockedB) {
        return isLockedA ? 1 : -1;
      }
      
      // Within same group, sort by database priority
      const priorityA = (a as any).priority === 0 ? 999 : ((a as any).priority ?? 999);
      const priorityB = (b as any).priority === 0 ? 999 : ((b as any).priority ?? 999);
      
      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }
      
      // Tiebreaker: sort by id ascending (older orders first)
      return a.id - b.id;
    });
    
    return sorted;
  }, [orders, activeOrderTab, poSearchTerm]);

  // ✅ Jan 30, 2026: GROUP-WISE PRIORITY DISPLAY
  // All orders that CAN START (green button) = Priority 1 (same group)
  // Locked orders = Sequential 2, 3, 4...
  const displayPriorities = useMemo(() => {
    const priorityMap: Record<number, number> = {};
    
    // Separate orders into unlocked (can run) and locked groups
    const unlockedOrders: typeof filteredOrders = [];
    const lockedOrders: typeof filteredOrders = [];
    
    filteredOrders.forEach((order) => {
      // InProgress orders are always "can run"
      if (order.status === 'InProgress') {
        unlockedOrders.push(order);
        return;
      }
      
      const hasConflict = (order as any).has_priority_conflict === true;
      const canRun = (order as any).conflict_can_run !== false;
      const isLocked = hasConflict && !canRun;
      
      if (isLocked) {
        lockedOrders.push(order);
      } else {
        unlockedOrders.push(order);
      }
    });
    
    // All unlocked orders get Priority 1 (same group)
    unlockedOrders.forEach((order) => {
      priorityMap[order.id] = 1;
    });
    
    // Locked orders get sequential priorities starting from 2
    lockedOrders.forEach((order, index) => {
      priorityMap[order.id] = index + 2;
    });
    
    return priorityMap;
  }, [filteredOrders]);
  
  // ✅ Jan 30, 2026: Calculate minimum priority among ALL ACTIVE orders (Pending + InProgress)
  // NOTE: Priority enforcement is now SCALE-BASED, not global
  // Orders with FREE scales can start regardless of priority
  // Priority only matters within same-scale conflict groups
  const minPendingPriority = useMemo(() => {
    let minPriority = 999;
    filteredOrders.forEach(order => {
      // Include both Pending AND InProgress orders (not Validated/Completed)
      if (order.status === 'Pending' || order.status === 'InProgress') {
        const dbPriority = (order as any).priority;
        const effectivePriority = (dbPriority && dbPriority > 0 && dbPriority < 999) ? dbPriority : 999;
        if (effectivePriority < minPriority) {
          minPriority = effectivePriority;
        }
      }
    });
    return minPriority;
  }, [filteredOrders]);

  const tableBg = theme === 'light'
    ? 'bg-white border border-blue-200 text-[#222]'
    : 'bg-[#1e293b] border border-cyan-500 text-cyan-200';
  // ✅ Industrial color palette for light mode (enterprise/SAP-style)
  const tableHeader = theme === 'light'
    ? 'bg-slate-100 text-slate-800 border-b-2 border-slate-300'
    : 'bg-[#0f172a] text-cyan-300 border-b border-cyan-500';
  const tableRowEven = theme === 'light' ? 'bg-slate-50' : 'bg-[#22304a]/60';
  const tableRowOdd = theme === 'light' ? 'bg-white' : 'bg-[#1a2532]';
  const borderRow = theme === 'light' ? 'border-slate-200' : 'border-slate-700';
  const filterSelect = theme === 'light'
    ? 'bg-white text-slate-800 border border-slate-300 focus:ring-slate-400'
    : 'bg-[#0f172a] text-cyan-200 border border-cyan-500 focus:ring-cyan-400';

  return (
    <WaterSystemLayout
      title="Process Order Validation"
      subtitle="Process Order Validation & Approval"
    >
      <style>{`
        /* Force white text for buttons in light mode */
        .validation-refresh-light {
          color: white !important;
        }
        
        .validation-refresh-light span {
          color: white !important;
        }
        
        .validation-validate-light {
          color: white !important;
        }
        
        .validation-validate-light span {
          color: white !important;
        }
        
        /* Force white text for push confirmation button */
        .push-confirmation-btn {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
          -webkit-text-stroke-color: transparent !important;
        }
        
        .push-confirmation-btn:hover {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }
        
        .push-confirmation-btn:disabled {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }
        
        .validation-reject-light {
          color: white !important;
        }
        
        .validation-reject-light span {
          color: white !important;
        }
        
        /* Ensure custom popup is always on top */
        .custom-popup-overlay {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          z-index: 9999 !important;
          display: flex !important;
          align-items: flex-start !important;
          justify-content: center !important;
          padding-top: 5vh !important;
        }
        
        .custom-popup-content {
          position: relative !important;
          z-index: 10000 !important;
          margin-top: 0 !important;
          transform: translateY(0) !important;
        }
      `}</style>
      <div className="w-full space-y-6 px-4 lg:px-6">
        <div className="flex items-center justify-between mb-4">
          <h1
            className={
              theme === 'light'
                ? 'text-xl font-bold text-[#222]'
                : 'text-xl font-bold text-cyan-400'
            }
          >
            Process Order Validation
          </h1>

          {/* Shift Indicators - show only the one(s) the user may access */}
          <div className="flex items-center gap-3">
            {canAccessMilling && <ShiftIndicator operation="milling" />}
            {canAccessPacking && <ShiftIndicator operation="packing" />}
          </div>
        </div>


        {/* Error Message */}
        {error && (
          <div className={`p-2 rounded-lg backdrop-blur-md border transition-all duration-300 text-sm ${theme === 'light'
              ? 'bg-red-50/80 border-red-200/50 text-red-800'
              : 'bg-red-900/20 border-red-400/30 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
            }`}>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span className="text-xs font-medium">{error}</span>
              <button
                onClick={() => setError(null)}
                className={`ml-auto p-1 rounded-full transition-colors ${theme === 'light'
                    ? 'hover:bg-red-100 text-red-600'
                    : 'hover:bg-red-800/30 text-red-400'
                  }`}
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* KPI Cards - Reference Design */}
        <div className="grid grid-cols-6 gap-4 w-full mb-6">
          <KpiCard
            title="Total Orders"
            value={canAccessMilling && canAccessPacking ? totalOrdersForKPI : (canAccessPacking ? kpiCounts.totalPacking : kpiCounts.totalMilling)}
            unit=""
            Icon={ListOrdered}
            color="#2563eb"
            showViewButton={false}
            valueNode={
              canAccessMilling && canAccessPacking ? (
                <span className={`text-sm font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  <span className="text-emerald-600 dark:text-emerald-400">Mill </span>
                  <span style={{ color: '#2563eb' }}>{kpiCounts.totalMilling}</span>
                  <span className={`mx-1 ${theme === 'light' ? 'text-gray-400' : 'text-slate-400'}`}>|</span>
                  <span className="text-amber-600 dark:text-amber-400">Pack </span>
                  <span style={{ color: '#2563eb' }}>{kpiCounts.totalPacking}</span>
                </span>
              ) : canAccessPacking ? (
                <span className={`text-sm font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  <span className="text-amber-600 dark:text-amber-400">Pack </span>
                  <span style={{ color: '#2563eb' }}>{kpiCounts.totalPacking}</span>
                </span>
              ) : (
                <span className={`text-sm font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  <span className="text-emerald-600 dark:text-emerald-400">Mill </span>
                  <span style={{ color: '#2563eb' }}>{kpiCounts.totalMilling}</span>
                </span>
              )
            }
          />
          <KpiCard
            title="In Progress"
            value={inProgressOrders}
            unit=""
            Icon={Clock3}
            color="#10b981"
            showViewButton={true}
            onViewClick={() => openOrdersModal('inprogress')}
          />
          <KpiCard
            title="Confirmed"
            value={kpiCounts.confirmed}
            unit=""
            Icon={CheckCircle}
            color="#2563eb"
            showViewButton={true}
            onViewClick={() => openOrdersModal('confirmed')}
          />
          <KpiCard
            title="Completed"
            value={kpiCounts.completed}
            unit=""
            Icon={CheckCircle}
            color="#059669"
            showViewButton={true}
            onViewClick={() => openOrdersModal('completed')}
          />
          <KpiCard
            title="Error Log"
            value={errorLogCount}
            unit=""
            Icon={AlertCircle}
            color="#f59e0b"
            showViewButton={true}
            onViewClick={() => openOrdersModal('errorlog')}
          />
          <KpiCard
            title="Offline Orders"
            value={kpiCounts.offlineOrders}
            unit=""
            Icon={WifiOff}
            color="#a855f7"
            showViewButton={true}
            onViewClick={() => openOrdersModal('offline')}
          />
        </div>

        {/* Auto Validation Control Panel - Compact Version */}
        <div className={`w-full mb-3 p-3 rounded-lg backdrop-blur-md border transition-all duration-300 ${theme === 'light'
            ? 'bg-white/20 border-slate-200/30 hover:border-slate-300/50 hover:bg-white/30'
            : 'bg-slate-900/20 border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
          }`}>
          <div className="flex flex-row items-center justify-between gap-4">
            <div className="flex-1 flex flex-row items-center gap-4">
              <h3 className={`text-sm font-bold whitespace-nowrap ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                }`}>
                Search Order
              </h3>
              <div className="flex-1 max-w-xs min-w-[160px]">
                <div className={`relative flex items-center rounded-md border ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600'}`}>
                  <Search className={`absolute left-2 h-3.5 w-3.5 shrink-0 ${theme === 'light' ? 'text-gray-400' : 'text-slate-400'}`} />
                  <input
                    type="text"
                    value={poSearchTerm}
                    onChange={(e) => setPoSearchTerm(e.target.value)}
                    placeholder="Search orders (PO, ID, material…)"
                    className={`w-full py-1.5 pl-8 pr-2 text-xs rounded-md focus:outline-none focus:ring-2 ${theme === 'light'
                      ? 'bg-white text-gray-900 placeholder-gray-400 focus:ring-blue-500 focus:border-blue-500 border-transparent'
                      : 'bg-slate-700 text-slate-100 placeholder-slate-400 focus:ring-cyan-500 focus:border-cyan-500 border-transparent'
                    }`}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              {/* Sync SAP Buttons - ✅ Feb 9, 2026: Only show buttons matching user's role */}
              {canAccessMilling && (
              <button
                onClick={() => syncSapOrders('milling')}
                className={`relative group flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 overflow-hidden ${theme === 'light'
                    ? 'bg-gradient-to-r from-emerald-500 to-green-600 shadow-md shadow-green-500/30 border border-green-400/30 hover:shadow-lg hover:shadow-green-500/50'
                    : 'bg-gradient-to-r from-emerald-500 to-green-600 shadow-md shadow-green-500/20 border border-green-400/30 hover:shadow-lg hover:shadow-green-500/40'
                  }`}
                title="Sync MILLING Orders from SAP"
                style={{ color: 'white' }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 to-green-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <BarChart3 className="h-3 w-3 relative z-10" style={{ color: 'white' }} />
                <span className="font-semibold relative z-10" style={{ color: 'white' }}>Sync Milling</span>
              </button>
              )}
              {canAccessPacking && (
              <button
                onClick={() => syncSapOrders('packing')}
                className={`relative group flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 overflow-hidden ${theme === 'light'
                    ? 'bg-gradient-to-r from-orange-500 to-amber-600 shadow-md shadow-orange-500/30 border border-orange-400/30 hover:shadow-lg hover:shadow-orange-500/50'
                    : 'bg-gradient-to-r from-orange-500 to-amber-600 shadow-md shadow-orange-500/20 border border-orange-400/30 hover:shadow-lg hover:shadow-orange-500/40'
                  }`}
                title="Sync PACKING Orders from SAP"
                style={{ color: 'white' }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-orange-400/20 to-amber-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <BarChart3 className="h-3 w-3 relative z-10" style={{ color: 'white' }} />
                <span className="font-semibold relative z-10" style={{ color: 'white' }}>Sync Packing</span>
              </button>
              )}


{/* Auto Validation buttons: visible when enabled in Settings > Demo tab (localStorage: show_auto_validation_button) */}
              {showAutoValidationButton && (
                !autoValidationManuallyStarted ? (
                  <button
                    onClick={startAllValidation}
                    disabled={isStartingValidation}
                    className={`relative group flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 overflow-hidden ${isStartingValidation
                        ? 'opacity-50 cursor-not-allowed'
                        : theme === 'light'
                          ? 'bg-gradient-to-r from-emerald-500 via-green-500 to-teal-600 shadow-lg shadow-green-500/40 border border-emerald-400/30 hover:shadow-xl hover:shadow-green-500/60 hover:border-emerald-300/50'
                          : 'bg-gradient-to-r from-emerald-500 via-green-500 to-teal-600 shadow-lg shadow-green-500/30 border border-emerald-400/40 hover:shadow-xl hover:shadow-green-500/50 hover:border-emerald-300/60'
                      }`}
                    title={isStartingValidation ? "Starting Auto Validation..." : "Start Auto Validation"}
                    style={{ color: 'white' }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 via-green-400/20 to-teal-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                    {isStartingValidation ? (
                      <div className="h-3 w-3 relative z-10 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    ) : (
                      <Play className="h-3 w-3 relative z-10" style={{ color: 'white' }} />
                    )}
                    <span className="font-semibold relative z-10" style={{ color: 'white' }}>
                      {isStartingValidation ? 'Starting...' : 'Start'}
                    </span>
                  </button>
                ) : (
                  <div className="flex gap-2">
                    {isAdmin && (
                    <button
                      onClick={stopAllValidation}
                      disabled={isStoppingValidation}
                      className={`relative group flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-xs transition-all duration-300 hover:scale-105 overflow-hidden ${isStoppingValidation
                          ? 'opacity-50 cursor-not-allowed'
                          : theme === 'light'
                            ? 'bg-gradient-to-r from-rose-500 via-red-500 to-pink-600 shadow-lg shadow-red-500/40 border border-rose-400/30 hover:shadow-xl hover:shadow-red-500/60 hover:border-rose-300/50'
                            : 'bg-gradient-to-r from-rose-500 via-red-500 to-pink-600 shadow-lg shadow-red-500/30 border border-rose-400/40 hover:shadow-xl hover:shadow-red-500/50 hover:border-rose-300/60'
                        }`}
                      title={isStoppingValidation ? "Stopping Auto Validation..." : "Stop Auto Validation"}
                      style={{ color: 'white' }}
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-rose-400/20 via-red-400/20 to-pink-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                      {isStoppingValidation ? (
                        <div className="h-3 w-3 relative z-10 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      ) : (
                        <Square className="h-3 w-3 relative z-10" style={{ color: 'white' }} />
                      )}
                      <span className="font-semibold relative z-10" style={{ color: 'white' }}>
                        {isStoppingValidation ? 'Stopping...' : 'Stop'}
                      </span>
                    </button>
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* Filter Bar - Reference Design */}
        <div className={`w-full mb-6 ${theme === 'light' ? 'bg-white' : 'bg-slate-800'} rounded-lg border ${theme === 'light' ? 'border-gray-200' : 'border-slate-700'} p-4`}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {/* Tab Buttons – ✅ Feb 9, 2026: Only show tabs the user's role allows */}
            <div className="flex gap-2">
              {canAccessAll && (
                <button
                  onClick={() => setActiveOrderTab('all')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeOrderTab === 'all'
                      ? theme === 'light' ? 'bg-blue-500 !text-white' : 'bg-blue-600 !text-white'
                      : theme === 'light' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                  }`}
                  style={activeOrderTab === 'all' ? { color: '#ffffff' } : undefined}
                >
                  ALL ORDERS
                </button>
              )}
              {canAccessMilling && (
                <button
                  onClick={() => setActiveOrderTab('milling')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeOrderTab === 'milling'
                      ? theme === 'light' ? 'bg-blue-500 !text-white' : 'bg-blue-600 !text-white'
                      : theme === 'light' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                  }`}
                  style={activeOrderTab === 'milling' ? { color: '#ffffff' } : undefined}
                >
                  MILLING
                </button>
              )}
              {canAccessPacking && (
                <button
                  onClick={() => setActiveOrderTab('packing')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeOrderTab === 'packing'
                      ? theme === 'light' ? 'bg-blue-500 !text-white' : 'bg-blue-600 !text-white'
                      : theme === 'light' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                  }`}
                  style={activeOrderTab === 'packing' ? { color: '#ffffff' } : undefined}
                >
                  PACKING
                </button>
              )}
            </div>

            {/* Status Dropdown and Offline Mode Indicator */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label htmlFor="statusFilter" className={`text-sm font-medium whitespace-nowrap ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                  STATUS:
                </label>
                <select
                  id="statusFilter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className={`px-3 py-1.5 rounded-md border text-sm focus:outline-none focus:ring-2 ${theme === 'light'
                      ? 'bg-white text-gray-900 border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                      : 'bg-slate-700 text-gray-100 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500'
                    }`}
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </div>

              {/* Offline Mode Indicator */}
              {!vpnStatus.connected && (
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md ${theme === 'light' ? 'bg-yellow-100 border border-yellow-300' : 'bg-yellow-900/30 border border-yellow-700'}`}>
                  <AlertTriangle className={`h-4 w-4 ${theme === 'light' ? 'text-yellow-700' : 'text-yellow-400'}`} />
                  <span className={`text-sm font-medium ${theme === 'light' ? 'text-yellow-800' : 'text-yellow-300'}`}>
                    OFFLINE MODE ACTIVE
                  </span>
                  <button
                    onClick={checkVpnStatus}
                    className={`ml-2 text-xs font-medium underline ${theme === 'light' ? 'text-yellow-700 hover:text-yellow-800' : 'text-yellow-400 hover:text-yellow-300'}`}
                  >
                    RECONNECT
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Orders Table with Drag and Drop */}
        <div className={`w-full overflow-x-auto rounded-lg backdrop-blur-md shadow transition-all duration-300 ${theme === 'light'
            ? 'bg-white/20 border border-slate-200/30 hover:shadow-md hover:bg-white/30'
            : 'bg-slate-900/20 border border-cyan-400/30 shadow-[0_0_20px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.15)]'
          }`}>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <table className={`min-w-full table-fixed text-xs text-left font-mono ${theme === 'light' ? 'text-slate-800' : 'text-cyan-200'}`}>
              {/* Table Header - Reference Design */}
              <thead className={`${tableHeader} uppercase text-xs tracking-wider sticky top-0 z-10`}>
                <tr>
                  <th className="px-2 py-1.5 w-8">Drag</th>
                  <th className="px-2 py-1.5 w-16">ORDER ID</th>
                  <th className="px-2 py-1.5 w-28">PO NUMBER</th>
                  <th className="px-2 py-1.5 w-32">MATERIAL</th>
                  <th className="px-2 py-1.5 w-12">VERSION</th>
                  <th className="px-2 py-1.5 w-20">TYPE</th>
                  <th className="px-2 py-1.5 w-24 text-center">TARGET</th>
                  <th className="px-2 py-1.5 w-12 text-center">UNIT</th>
                  <th className="px-2 py-1.5 w-24 text-center">CONFIRM</th>
                  <th className="px-2 py-1.5 w-24 text-center">CURRENT</th>
                  <th className="px-2 py-1.5 w-24 text-center">REMAINING</th>
                  {/* Byproduct Scale Columns - MILLING Orders Only (hide on Packing tab) */}
                  {activeOrderTab !== 'packing' && (
                    <>
                      <th className="px-2 py-1.5 w-24 text-center">BYPROD 1</th>
                      <th className="px-2 py-1.5 w-24 text-center">BYPROD 2</th>
                    </>
                  )}
                  <th className="px-2 py-1.5 w-24 text-center">STATUS</th>
                  <th className="px-2 py-1.5 w-16 text-center">PRIORITY</th>
                  <th className="px-2 py-1.5 w-36 text-center">PROGRESS</th>
                  <th className="px-2 py-1.5 w-80 text-center">ACTIONS</th>
                </tr>
              </thead>
              <SortableContext items={filteredOrders.map(order => order.id)} strategy={verticalListSortingStrategy}>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={activeOrderTab !== 'packing' ? 17 : 15} className="px-3 py-4 text-center text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                          Loading orders...
                        </div>
                      </td>
                    </tr>
                  ) : filteredOrders.length === 0 ? (
                    <tr>
                      <td colSpan={activeOrderTab !== 'packing' ? 17 : 15} className="px-3 py-4 text-center opacity-70 text-sm">
                        No orders found
                      </td>
                    </tr>
                  ) : (
                    filteredOrders.map((order, index) => {
                      // ✅ NUCLEAR FIX: Override status if order is in forced pending list
                      const orderId = order.po_number || String(order.id);
                      const displayOrder = forcedPendingOrdersRef.current.has(orderId)
                        ? { ...order, status: 'Pending' as const }
                        : order;
                      
                      return (
                        <SortableRow
                          key={order.id}
                          order={displayOrder}
                          index={index}
                          theme={theme}
                          validatingOrders={validatingOrders}
                          autoValidatorStatus={autoValidatorStatus}
                          orderProgress={orderProgress}
                          tableRowEven={tableRowEven}
                          tableRowOdd={tableRowOdd}
                          borderRow={borderRow}
                          onValidate={validateOrderManually}
                          onReject={openRejectionModal}
                          onProgressClick={openProgressDialog}
                          isAdmin={isAdmin}
                          onViewValidationDetails={viewValidationDetails}
                          onStartOrder={startOrderManually}
                          onStopOrder={stopOrderManually}
                          onManualConfirm={openManualConfirmationModal}
                          onPushConfirmation={handlePushSingleOrderConfirmation}
                          pushingConfirmation={pushingConfirmation}
                          priority={
                            // Group-wise display when set; else SAP priority_id / hercules priority
                            displayPriorities[order.id] ??
                            (order as any).priority_id ??
                            (order as any).priority ??
                            0
                          }
                          showByproducts={activeOrderTab !== 'packing'}
                          isTopPriority={
                            // ✅ Jan 30, 2026: Only orders with minimum priority can start
                            // Strict priority enforcement - higher priority must run first
                            ((order as any).priority || 999) <= minPendingPriority
                          }
                          minPendingPriority={minPendingPriority}
                        />
                      );
                    })
                  )}
                </tbody>
              </SortableContext>
            </table>
          </DndContext>
        </div>

        {/* Footer - Reference Design: Queue info and Pagination */}
        <div className={`w-full flex flex-col sm:flex-row items-center justify-between gap-4 mt-6 p-4 rounded-lg ${theme === 'light' ? 'bg-white border border-gray-200' : 'bg-slate-800 border border-slate-700'}`}>
          {/* Queue Info */}
          <div className="flex items-center gap-4">
            <span className={`text-sm font-medium ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
              QUEUE: {totalOrders} ORDERS
            </span>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <span className={`text-xs ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>ACTIVE</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${theme === 'light' ? 'bg-gray-400' : 'bg-gray-500'}`}></div>
                <span className={`text-xs ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>PENDING</span>
              </div>
            </div>
          </div>

          {/* Pagination - Reference Design: Previous and Next Page */}
          {totalOrders > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  currentPage === 1
                    ? 'opacity-50 cursor-not-allowed'
                    : theme === 'light'
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                }`}
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  currentPage === totalPages
                    ? 'opacity-50 cursor-not-allowed'
                    : theme === 'light'
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                }`}
              >
                Next Page
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Validation Modal */}
      <OrderValidationModal
        isOpen={showValidationModal}
        onClose={closeValidationModal}
        orderId={selectedOrderId}
        defaults={modalDefaults}
        onValidate={async (validationData: ValidationRequest) => {
          // Find the order and call the new validation function
          const order = orders.find(o => o.id === selectedOrderId);
          if (order) {
            return await validateOrderManually(order.po_number || '');
          }
          throw new Error('Order not found');
        }}
      />

      {/* Rejection Modal */}
      <OrderRejectionModal
        isOpen={showRejectionModal}
        onClose={closeRejectionModal}
        orderId={selectedOrderId}
        orderDetails={selectedOrderDetails || undefined}
        onReject={rejectOrder}
      />

      {/* Manual Confirmation Modal */}
      {showManualConfirmationModal && selectedOrderForManualConfirm && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={closeManualConfirmationModal}
          />
          <div className={`relative w-full max-w-md rounded-lg shadow-xl ${theme === 'light' ? 'bg-white' : 'bg-gray-800'
            }`}>
            {/* Header */}
            <div className={`px-4 py-3 border-b ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'
              }`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold flex items-center gap-2 ${theme === 'light' ? 'text-gray-900' : 'text-white'
                  }`}>
                  📤 Send Confirmation to SAP
                </h3>
                <button
                  onClick={closeManualConfirmationModal}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light'
                      ? 'text-gray-500 hover:bg-gray-200'
                      : 'text-gray-400 hover:bg-gray-700'
                    }`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <p className={`text-sm mt-1 ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                }`}>
                Order: {selectedOrderForManualConfirm.po_number}
              </p>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* Current Values Summary */}
              <div className={`p-3 rounded-lg ${theme === 'light' ? 'bg-blue-50 border border-blue-200' : 'bg-blue-900/20 border border-blue-700'}`}>
                <h4 className={`text-sm font-semibold mb-2 ${theme === 'light' ? 'text-blue-800' : 'text-blue-300'}`}>
                  Confirmation Details:
                </h4>
                {(() => {
                  const totalProduction = (selectedOrderForManualConfirm as any)?.confirmed_qty || 0;
                  const confirmedShiftA = (selectedOrderForManualConfirm as any)?.confirmed_shift_a || 0;
                  const confirmedShiftB = (selectedOrderForManualConfirm as any)?.confirmed_shift_b || 0;
                  const confirmedShiftC = (selectedOrderForManualConfirm as any)?.confirmed_shift_c || 0;
                  const alreadySent = confirmedShiftA + confirmedShiftB + confirmedShiftC;
                  const available = Math.max(0, totalProduction - alreadySent);
                  
                  return (
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        <span className="font-medium">Total Production:</span>{' '}
                        <span className="font-bold">{totalProduction.toFixed(2)} TO</span>
                      </div>
                      <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        <span className="font-medium">Already Sent to SAP:</span>{' '}
                        <span className="font-bold">{alreadySent.toFixed(2)} TO</span>
                      </div>
                      <div className={`col-span-2 ${theme === 'light' ? 'text-green-700 bg-green-100' : 'text-green-300 bg-green-900/30'} p-2 rounded`}>
                        <span className="font-medium">Available to Confirm:</span>{' '}
                        <span className="font-bold text-lg">{available.toFixed(2)} TO</span>
                      </div>
                      <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        <span className="font-medium">Total Confirmed (SAP):</span>{' '}
                        <span className="font-bold">{((selectedOrderForManualConfirm as any)?.last_confirmed_qty || 0).toFixed(2)} TO</span>
                      </div>
                      {(selectedOrderForManualConfirm as any)?.order_type === 'MILLING' && (
                        <>
                          {(selectedOrderForManualConfirm as any)?.scale1 && (
                            <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                              <span className="font-medium">{(selectedOrderForManualConfirm as any)?.scale1}:</span>{' '}
                              <span className="font-bold">{((selectedOrderForManualConfirm as any)?.scale1_qty || 0).toFixed(2)}</span>
                            </div>
                          )}
                          {(selectedOrderForManualConfirm as any)?.scale2 && (
                            <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                              <span className="font-medium">{(selectedOrderForManualConfirm as any)?.scale2}:</span>{' '}
                              <span className="font-bold">{((selectedOrderForManualConfirm as any)?.scale2_qty || 0).toFixed(2)}</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  );
                })()}
                <p className={`text-xs mt-2 ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`}>
                  ℹ️ Confirmation will be sent to SAP immediately if VPN is connected, or queued for offline send if VPN is disconnected.
                </p>
              </div>

              {/* Scrap Field */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                  }`}>
                  Scrap (TO)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={manualConfirmData.scrap || ''}
                  onChange={(e) => setManualConfirmData({
                    ...manualConfirmData,
                    scrap: parseFloat(e.target.value) || 0
                  })}
                  className={`w-full px-3 py-2 rounded-md border text-sm focus:outline-none focus:ring-2 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield] ${theme === 'light'
                      ? 'bg-white border-gray-300 focus:ring-blue-500 focus:border-blue-500 text-gray-900'
                      : 'bg-gray-700 border-gray-600 focus:ring-cyan-500 focus:border-cyan-500 text-white'
                  }`}
                  placeholder="Optional (default: 0)"
                />
              </div>

              {/* Confirmed Text Field */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                  }`}>
                  Confirmed Text (Optional)
                </label>
                <textarea
                  value={manualConfirmData.confirmed_text}
                  onChange={(e) => setManualConfirmData({
                    ...manualConfirmData,
                    confirmed_text: e.target.value
                  })}
                  className={`w-full px-3 py-2 rounded-md border text-sm focus:outline-none focus:ring-2 ${theme === 'light'
                      ? 'bg-white border-gray-300 focus:ring-blue-500 focus:border-blue-500 text-gray-900'
                      : 'bg-gray-700 border-gray-600 focus:ring-cyan-500 focus:border-cyan-500 text-white'
                    }`}
                  placeholder="Enter confirmation notes (optional)"
                  rows={2}
                />
              </div>
            </div>

            {/* Footer */}
            <div className={`px-4 py-3 border-t flex justify-end gap-2 ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'
              }`}>
              <button
                onClick={closeManualConfirmationModal}
                disabled={sendingManualConfirm}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${theme === 'light'
                    ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                    : 'bg-gray-600 text-white hover:bg-gray-500'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await sendManualConfirmation();
                }}
                disabled={sendingManualConfirm}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${theme === 'light'
                    ? 'bg-green-600 text-white hover:bg-green-700 shadow-md'
                    : 'bg-green-500 text-white hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {sendingManualConfirm ? 'Sending...' : 'Send to Confirmation to SAP'}
              </button>
            </div>
          </div>
        </div>
        ,
        document.body
      )}

      {/* Reprocess Modal */}
      {showReprocessModal && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowReprocessModal(false)}
          />
          <div className={`relative w-full max-w-md rounded-lg shadow-xl ${theme === 'light' ? 'bg-white' : 'bg-gray-800'}`}>
            <div className={`px-4 py-3 border-b ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'}`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  Reprocess Order
                </h3>
                <button
                  onClick={() => setShowReprocessModal(false)}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light' ? 'text-gray-500 hover:bg-gray-200' : 'text-gray-400 hover:bg-gray-700'}`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>Scrap (TO)</label>
                <input
                  type="number"
                  step="0.01"
                  value={reprocessData.scrap}
                  onChange={(e) => setReprocessData({ ...reprocessData, scrap: parseFloat(e.target.value) || 0 })}
                  className={`w-full px-3 py-2 rounded border ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-gray-700 border-gray-600 text-white'}`}
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>Confirmed Text</label>
                <textarea
                  value={reprocessData.confirmed_text}
                  onChange={(e) => setReprocessData({ ...reprocessData, confirmed_text: e.target.value })}
                  className={`w-full px-3 py-2 rounded border ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-gray-700 border-gray-600 text-white'}`}
                  rows={3}
                />
              </div>
            </div>
            <div className={`px-4 py-3 border-t flex justify-end gap-2 ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'}`}>
              <button
                onClick={() => setShowReprocessModal(false)}
                className="px-4 py-2 rounded font-medium bg-gray-200 text-gray-800 hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleReprocess}
                disabled={reprocessing}
                className="px-4 py-2 rounded font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {reprocessing ? 'Processing...' : 'Reprocess'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Resend Modal (for VPN network errors) */}
      {showResendModal && selectedResendLog && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowResendModal(false)}
          />
          <div className={`relative w-full max-w-md rounded-lg shadow-xl ${theme === 'light' ? 'bg-white' : 'bg-gray-800'}`}>
            <div className={`px-4 py-3 border-b ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'}`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  📤 Resend Confirmation to SAP
                </h3>
                <button
                  onClick={() => setShowResendModal(false)}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light' ? 'text-gray-500 hover:bg-gray-200' : 'text-gray-400 hover:bg-gray-700'}`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <p className={`text-sm mt-1 ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                Order: {selectedResendLog.po_number}
              </p>
            </div>
            
            {/* Display payload info */}
            <div className="p-4 space-y-4">
              {(() => {
                try {
                  const payload = typeof selectedResendLog.payload === 'string' 
                    ? JSON.parse(selectedResendLog.payload) 
                    : selectedResendLog.payload;
                  const sentPayload = payload?.sent_payload;
                  
                  if (sentPayload) {
                    return (
                      <div className={`p-3 rounded-lg ${theme === 'light' ? 'bg-blue-50 border border-blue-200' : 'bg-blue-900/20 border border-blue-700'}`}>
                        <h4 className={`text-sm font-semibold mb-2 ${theme === 'light' ? 'text-blue-800' : 'text-blue-300'}`}>
                          Original Confirmation Details:
                        </h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                            <span className="font-medium">Shift:</span> {sentPayload.shift || 'N/A'}
                          </div>
                          <div className={`${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                            <span className="font-medium">Weight:</span> {(sentPayload.confirmed_weight || 0).toFixed(2)} {sentPayload.uom || 'KG'}
                          </div>
                        </div>
                        <p className={`text-xs mt-2 ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`}>
                          ℹ️ This will resend the exact same quantity with your scrap and confirmed text values.
                        </p>
                      </div>
                    );
                  }
                } catch (e) {
                  return null;
                }
                return null;
              })()}
              
              <div>
                <label className={`block text-sm font-medium mb-1 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                  Scrap (TO) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={resendData.scrap}
                  onChange={(e) => setResendData({ ...resendData, scrap: parseFloat(e.target.value) || 0 })}
                  className={`w-full px-3 py-2 rounded border ${
                    !resendData.scrap || resendData.scrap <= 0
                      ? theme === 'light'
                        ? 'bg-white border-red-300 focus:ring-red-500 focus:border-red-500'
                        : 'bg-gray-700 border-red-500 focus:ring-red-400 focus:border-red-400 text-white'
                      : theme === 'light' 
                        ? 'bg-white border-gray-300' 
                        : 'bg-gray-700 border-gray-600 text-white'
                  }`}
                  placeholder="Required"
                  required
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                  Confirmed Text (Optional)
                </label>
                <textarea
                  value={resendData.confirmed_text}
                  onChange={(e) => setResendData({ ...resendData, confirmed_text: e.target.value })}
                  className={`w-full px-3 py-2 rounded border ${theme === 'light' ? 'bg-white border-gray-300' : 'bg-gray-700 border-gray-600 text-white'}`}
                  rows={3}
                  placeholder="Enter confirmation notes (optional)"
                />
              </div>
              
              {/* Force Resend Checkbox */}
              <div className={`p-3 rounded-lg ${theme === 'light' ? 'bg-amber-50 border border-amber-200' : 'bg-amber-900/20 border border-amber-700'}`}>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={resendData.force_resend}
                    onChange={(e) => setResendData({ ...resendData, force_resend: e.target.checked })}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                  />
                  <div>
                    <span className={`text-sm font-medium ${theme === 'light' ? 'text-amber-800' : 'text-amber-300'}`}>
                      Force Resend (bypass duplicate check)
                    </span>
                    <p className={`text-xs mt-1 ${theme === 'light' ? 'text-amber-700' : 'text-amber-400'}`}>
                      Use this if the confirmation failed due to network issues and appears as "already confirmed" in local database but SAP never received it.
                    </p>
                  </div>
                </label>
              </div>
            </div>
            
            <div className={`px-4 py-3 border-t flex justify-end gap-2 ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'}`}>
              <button
                onClick={() => setShowResendModal(false)}
                disabled={resending}
                className={`px-4 py-2 rounded font-medium transition-colors ${theme === 'light' ? 'bg-gray-200 text-gray-800 hover:bg-gray-300' : 'bg-gray-600 text-white hover:bg-gray-500'} disabled:opacity-50`}
              >
                Cancel
              </button>
              <button
                onClick={handleResend}
                disabled={resending || !resendData.scrap || resendData.scrap <= 0}
                className={`px-4 py-2 rounded font-medium transition-colors ${theme === 'light' ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-blue-500 text-white hover:bg-blue-600'} disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {resending ? '📤 Resending...' : '📤 Resend to SAP'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Payload Viewer Modal */}
      {showPayloadModal && selectedPayload && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowPayloadModal(false)}
          />
          <div className={`relative w-full max-w-2xl max-h-[80vh] rounded-lg shadow-xl overflow-hidden ${theme === 'light' ? 'bg-white' : 'bg-gray-800'}`}>
            <div className={`px-4 py-3 border-b ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'}`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                  📦 Confirmation Payload - {selectedPayloadPO}
                </h3>
                <button
                  onClick={() => setShowPayloadModal(false)}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light' ? 'text-gray-500 hover:bg-gray-200' : 'text-gray-400 hover:bg-gray-700'}`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              <div className={`text-xs mb-2 ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                Click on the payload to understand what was sent to SAP:
              </div>
              <pre className={`text-xs font-mono whitespace-pre-wrap p-3 rounded border ${theme === 'light' ? 'bg-gray-50 border-gray-200 text-gray-800' : 'bg-gray-900 border-gray-700 text-gray-200'}`}>
                {JSON.stringify(selectedPayload, null, 2)}
              </pre>
            </div>
            <div className={`px-4 py-3 border-t ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'}`}>
              <button
                onClick={() => setShowPayloadModal(false)}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${theme === 'light'
                    ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                    : 'bg-gray-600 text-white hover:bg-gray-500'
                  }`}
              >
                Close
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Progress Dialog */}
      {showProgressDialog && selectedOrderProgress && createPortal(
        <div className={`fixed inset-0 backdrop-blur-lg flex items-center justify-center z-[9999] ${theme === 'light'
            ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30'
            : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
          }`} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}>
          <div className={`w-full max-w-4xl mx-4 rounded-lg shadow-xl ${theme === 'light'
              ? 'bg-white border border-gray-200'
              : 'bg-gray-800 border border-gray-600'
            }`}>
            {/* Header */}
            <div className={`px-4 py-3 border-b ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'
              }`}>
              <div className="flex items-center justify-between">
                <h3 className={`text-lg font-semibold ${theme === 'light' ? 'text-gray-900' : 'text-white'
                  }`}>
                  Order Progress Details
                </h3>
                <button
                  onClick={() => setShowProgressDialog(false)}
                  className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light'
                      ? 'text-gray-500 hover:bg-gray-200'
                      : 'text-gray-400 hover:bg-gray-700'
                    }`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content - Scrollable area */}
            <div className="px-4 py-3 max-h-[70vh] overflow-y-auto">
              {/* Order Header - Compact single row */}
              <div className={`flex items-center justify-between p-3 rounded-lg mb-4 ${
                selectedOrderProgress.order_type === 'MILLING'
                  ? theme === 'light' ? 'bg-purple-50 border border-purple-200' : 'bg-purple-900/20 border border-purple-700'
                  : theme === 'light' ? 'bg-cyan-50 border border-cyan-200' : 'bg-cyan-900/20 border border-cyan-700'
              }`}>
                <div className="flex items-center gap-4">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                    selectedOrderProgress.order_type === 'MILLING'
                      ? theme === 'light' ? 'bg-purple-200 text-purple-800' : 'bg-purple-800 text-purple-200'
                      : theme === 'light' ? 'bg-cyan-200 text-cyan-800' : 'bg-cyan-800 text-cyan-200'
                  }`}>
                    {selectedOrderProgress.order_type}
                  </span>
                  <div className="flex items-center gap-3 text-sm">
                    <span className={`font-mono font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                      {selectedOrderProgress.po_number}
                    </span>
                    <span className={`${theme === 'light' ? 'text-gray-400' : 'text-gray-500'}`}>|</span>
                    <span className={`font-mono ${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                      {selectedOrderProgress.material}
                    </span>
                    <span className={`${theme === 'light' ? 'text-gray-400' : 'text-gray-500'}`}>|</span>
                    <span className={`font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'}`}>
                      v{selectedOrderProgress.version || 'N/A'}
                    </span>
                  </div>
                </div>
                {/* Equipment badges */}
                {Array.isArray(selectedOrderProgress?.equipment_list) && selectedOrderProgress.equipment_list.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {selectedOrderProgress.equipment_list.map((equipment: string) => (
                      <span
                        key={equipment}
                        className={`px-2 py-0.5 rounded text-xs font-mono ${theme === 'light'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-blue-900/40 text-blue-300'
                          }`}
                      >
                        {equipment}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Scale Lock Warning */}
              {selectedOrderProgress.scale_lock_status?.scales_locked && (
                <div className={`mb-4 p-3 rounded-lg border-2 ${theme === 'light'
                    ? 'bg-orange-50 border-orange-300'
                    : 'bg-orange-900/20 border-orange-600'
                  }`}>
                  <div className="flex items-start gap-2">
                    <div className={`flex-shrink-0 mt-0.5 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'
                      }`}>
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-semibold mb-1 ${theme === 'light' ? 'text-orange-800' : 'text-orange-300'
                        }`}>
                        🔒 Scales Locked
                      </div>
                      <div className={`text-xs ${theme === 'light' ? 'text-orange-700' : 'text-orange-400'
                        }`}>
                        {selectedOrderProgress.scale_lock_status.message ||
                          `Some scales are currently in use by another order. Validation will start automatically when scales are available.`}
                      </div>
                      {selectedOrderProgress.scale_lock_status.locking_orders.length > 0 && (
                        <div className={`mt-2 text-xs ${theme === 'light' ? 'text-orange-600' : 'text-orange-500'
                          }`}>
                          <span className="font-medium">Locked by order(s): </span>
                          <span className="font-mono">
                            {selectedOrderProgress.scale_lock_status.locking_orders.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Progress Section - Combined bar and stats */}
              <div className={`p-3 rounded-lg mb-4 ${theme === 'light' ? 'bg-gray-50 border border-gray-200' : 'bg-gray-800/50 border border-gray-700'}`}>
                {/* Progress bar with percentage */}
                <div className="flex items-center gap-3 mb-2">
                  <div className={`flex-1 rounded-full h-3 ${theme === 'light' ? 'bg-slate-200' : 'bg-gray-700'}`}>
                    <div
                      className={`h-3 rounded-full transition-all duration-500 ${
                        theme === 'light' 
                          ? 'bg-gradient-to-r from-slate-500 to-teal-600' 
                          : 'bg-gradient-to-r from-blue-500 to-green-500'
                      }`}
                      style={{ width: `${Math.min(selectedOrderProgress.progress_pct, 100)}%` }}
                    />
                  </div>
                  <span className={`text-lg font-bold min-w-[60px] text-right ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                    {selectedOrderProgress.progress_pct.toFixed(1)}%
                  </span>
                </div>
                {/* Stats row */}
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-1">
                    <span className={theme === 'light' ? 'text-gray-500' : 'text-gray-400'}>Target:</span>
                    <span className={`font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'}`}>
                      {selectedOrderProgress.expected_tons.toFixed(2)} {selectedOrderProgress.unit}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={theme === 'light' ? 'text-gray-500' : 'text-gray-400'}>Current:</span>
                    <span className="font-bold text-blue-500">
                      {selectedOrderProgress.current_tons.toFixed(2)} {selectedOrderProgress.unit}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={theme === 'light' ? 'text-gray-500' : 'text-gray-400'}>Remaining:</span>
                    <span className="font-bold text-orange-500">
                      {selectedOrderProgress.remaining_tons.toFixed(2)} {selectedOrderProgress.unit}
                    </span>
                  </div>
                </div>
              </div>

              {/* Enhanced Equipment Breakdown with Backend Data */}
              {Array.isArray(selectedOrderProgress.equipment_list) && selectedOrderProgress.equipment_list.length > 0 && (
                <div className={`mt-4 p-3 rounded-lg border ${theme === 'light' ? 'bg-gray-50 border-gray-200' : 'bg-gray-700/30 border-gray-600'
                  }`}>
                  <h4 className={`text-sm font-semibold mb-2 ${theme === 'light' ? 'text-gray-900' : 'text-white'
                    }`}>
                    Real-time Equipment Readings
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {selectedOrderProgress.equipment_list.map((equipment: string) => {
                      const equipmentDetails = (selectedOrderProgress as any).equipment_details || {};
                      const equipmentData = equipmentDetails[equipment];
                     
                      // Check if this scale is locked
                      const scaleDetail = selectedOrderProgress.scale_details?.find(
                        (sd: any) => sd.scale_tag === equipment
                      );
                      const isScaleLocked = scaleDetail?.is_locked || false;
                      const lockedByOrder = scaleDetail?.locked_by || null;

                      return (
                        <div key={equipment} className={`p-2 rounded border ${isScaleLocked
                            ? theme === 'light' ? 'bg-orange-50 border-orange-300' : 'bg-orange-900/20 border-orange-600'
                            : theme === 'light' ? 'bg-white border-gray-200' : 'bg-gray-800 border-gray-600'
                          }`}>
                          <div className="flex justify-between items-center mb-1">
                            <div className="flex items-center gap-2">
                              <div className={`text-sm font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                                }`}>
                                {equipment}
                              </div>
                              {isScaleLocked && (
                                <div className={`text-xs px-1.5 py-0.5 rounded ${theme === 'light' ? 'bg-orange-200 text-orange-800' : 'bg-orange-800 text-orange-200'
                                  }`} title={`Locked by order ${lockedByOrder}`}>
                                  🔒
                                </div>
                              )}
                            </div>
                            <div className={`text-xs px-2 py-1 rounded ${isScaleLocked
                                ? theme === 'light' ? 'bg-orange-100 text-orange-700' : 'bg-orange-900/30 text-orange-300'
                                : equipmentData?.delta > 0
                                  ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                                  : theme === 'light' ? 'bg-gray-100 text-gray-600' : 'bg-gray-700 text-gray-400'
                              }`}>
                              {isScaleLocked ? 'Locked' : (equipmentData?.delta > 0 ? 'Active' : 'Standby')}
                            </div>
                          </div>
                          {isScaleLocked && lockedByOrder && (
                            <div className={`text-xs mb-1 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'
                              }`}>
                              Locked by: <span className="font-mono">{lockedByOrder}</span>
                            </div>
                          )}

                          {equipmentData ? (
                            <>
                              {/* For DM scales, only show Delta (accumulated value) */}
                              {equipment.startsWith('DM') ? (
                                <div className="text-xs">
                                  <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                    Delta (Accumulated)
                                  </div>
                                  <div className={`font-mono font-bold text-lg ${equipmentData.delta > 0
                                      ? theme === 'light' ? 'text-green-600' : 'text-green-400'
                                      : theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                                    }`}>
                                    {equipmentData.delta?.toFixed(2) || '0.00'}
                                  </div>
                                </div>
                              ) : (
                                <div className="grid grid-cols-3 gap-2 text-xs">
                                  <div>
                                    <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                      Baseline
                                    </div>
                                    <div className={`font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                                      }`}>
                                      {equipmentData.baseline?.toFixed(2) || '0.00'}
                                    </div>
                                  </div>
                                  <div>
                                    <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                      Current
                                    </div>
                                    <div className={`font-mono font-bold ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                                      }`}>
                                      {equipmentData.current?.toFixed(2) || '0.00'}
                                    </div>
                                  </div>
                                  <div>
                                    <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                      Delta
                                    </div>
                                    <div className={`font-mono font-bold ${equipmentData.delta > 0
                                        ? theme === 'light' ? 'text-green-600' : 'text-green-400'
                                        : theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                                      }`}>
                                      {equipmentData.delta?.toFixed(2) || '0.00'}
                                    </div>
                                  </div>
                                </div>
                              )}
                              {/* ✅ NEW: Show HI/LO values for WG scales */}
                              {/* Always show for WG scales if baseline_hi exists OR if it's a WG scale (we'll show baseline even if current is missing) */}
                              {(equipment.startsWith('WG') && ('baseline_hi' in equipmentData || equipmentData.baseline_hi !== undefined)) || 
                               ('hi' in equipmentData && equipmentData.hi !== undefined && 'lo' in equipmentData && equipmentData.lo !== undefined) ? (
                                <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600">
                                  {/* Baseline HI/LO - Always show for WG scales */}
                                  {equipment.startsWith('WG') && ('baseline_hi' in equipmentData || equipmentData.baseline_hi !== undefined) && (
                                    <div className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                                      <div className="text-xs font-semibold mb-1" style={{color: theme === 'light' ? '#6b7280' : '#9ca3af'}}>Baseline</div>
                                      <div className="grid grid-cols-3 gap-2 text-xs">
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            HI
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                                            {equipmentData.baseline_hi?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            LO
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-indigo-600' : 'text-indigo-400'}`}>
                                            {equipmentData.baseline_lo?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            Combined
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-teal-600' : 'text-teal-400'}`}>
                                            {equipmentData.baseline?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                      </div>
                                      <div className={`mt-1 text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                                        "{equipmentData.baseline_hi ?? 0}" + "{equipmentData.baseline_lo ?? 0}" = "{String(equipmentData.baseline_hi ?? 0) + String(equipmentData.baseline_lo ?? 0)}"
                                      </div>
                                    </div>
                                  )}
                                  
                                  {/* Current HI/LO - Only show if both hi and lo are available */}
                                  {'hi' in equipmentData && equipmentData.hi !== undefined && 'lo' in equipmentData && equipmentData.lo !== undefined && (
                                    <>
                                      <div className="text-xs font-semibold mb-1" style={{color: theme === 'light' ? '#6b7280' : '#9ca3af'}}>Current</div>
                                      <div className="grid grid-cols-3 gap-2 text-xs">
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            HI
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                                            {equipmentData.hi?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            LO
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-indigo-600' : 'text-indigo-400'}`}>
                                            {equipmentData.lo?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            Combined
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-teal-600' : 'text-teal-400'}`}>
                                            {(() => {
                                              const hiStr = String(equipmentData.hi ?? 0);
                                              const loStr = String(equipmentData.lo ?? 0);
                                              const combined = hiStr + loStr;
                                              return parseFloat(combined).toFixed(2);
                                            })()}
                                          </div>
                                        </div>
                                      </div>
                                      <div className={`mt-1 text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                                        "{equipmentData.hi ?? 0}" + "{equipmentData.lo ?? 0}" = "{String(equipmentData.hi ?? 0) + String(equipmentData.lo ?? 0)}"
                                      </div>
                                    </>
                                  )}
                                </div>
                              ) : null}
                            </>
                          ) : (
                            <div className={`text-sm ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                              No data available
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Byproduct Scale Readings (MILLING orders only) - Similar to Equipment Readings */}
              {selectedOrderProgress.order_type === 'MILLING' && 
               ((selectedOrderProgress as any).scale1 || (selectedOrderProgress as any).scale2 || (selectedOrderProgress as any).scale3) && (
                <div className={`mt-4 p-3 rounded-lg border ${theme === 'light' ? 'bg-amber-50 border-amber-200' : 'bg-amber-900/20 border-amber-600'
                  }`}>
                  <h4 className={`text-sm font-semibold mb-2 ${theme === 'light' ? 'text-gray-900' : 'text-white'
                    }`}>
                    Byproduct Scale Readings
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {['scale1', 'scale2', 'scale3'].map((scaleKey) => {
                      const scaleTag = (selectedOrderProgress as any)[scaleKey];
                      if (!scaleTag) return null;
                      
                      // Get byproduct details from backend (baseline/current/delta)
                      const byproductDetails = (selectedOrderProgress as any).byproduct_details || {};
                      const byproductData = byproductDetails[scaleTag];
                      const scaleQty = (selectedOrderProgress as any)[`${scaleKey}_qty`] || 0;
                      
                      return (
                        <div key={scaleKey} className={`p-2 rounded border ${theme === 'light' ? 'bg-white border-amber-200' : 'bg-gray-800 border-amber-600'
                          }`}>
                          <div className="flex justify-between items-center mb-1">
                            <div className={`text-sm font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                              }`}>
                              {scaleTag}
                            </div>
                            <div className={`text-xs px-2 py-1 rounded ${
                              (byproductData?.delta || scaleQty) > 0
                                ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                                : theme === 'light' ? 'bg-gray-100 text-gray-600' : 'bg-gray-700 text-gray-400'
                              }`}>
                              {(byproductData?.delta || scaleQty) > 0 ? 'Active' : 'Standby'}
                            </div>
                          </div>

                          {byproductData ? (
                            <>
                              <div className="grid grid-cols-3 gap-2 text-xs">
                                <div>
                                  <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                    Baseline
                                  </div>
                                  <div className={`font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                                    }`}>
                                    {byproductData.baseline?.toFixed(2) || '0.00'}
                                  </div>
                                </div>
                                <div>
                                  <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                    Current
                                  </div>
                                  <div className={`font-mono font-bold ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                                    }`}>
                                    {byproductData.current?.toFixed(2) || '0.00'}
                                  </div>
                                </div>
                                <div>
                                  <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                    Delta
                                  </div>
                                  <div className={`font-mono font-bold ${byproductData.delta > 0
                                      ? theme === 'light' ? 'text-green-600' : 'text-green-400'
                                      : theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                                    }`}>
                                    {byproductData.delta?.toFixed(2) || '0.00'}
                                  </div>
                                </div>
                              </div>
                              {/* ✅ NEW: Show HI/LO values for WG scales */}
                              {/* Always show for WG scales if baseline_hi exists OR if it's a WG scale (we'll show baseline even if current is missing) */}
                              {(scaleTag.startsWith('WG') && ('baseline_hi' in byproductData || byproductData.baseline_hi !== undefined)) || 
                               ('hi' in byproductData && byproductData.hi !== undefined && 'lo' in byproductData && byproductData.lo !== undefined) ? (
                                <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600">
                                  {/* Baseline HI/LO - Always show for WG scales */}
                                  {scaleTag.startsWith('WG') && ('baseline_hi' in byproductData || byproductData.baseline_hi !== undefined) && (
                                    <div className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                                      <div className="text-xs font-semibold mb-1" style={{color: theme === 'light' ? '#6b7280' : '#9ca3af'}}>Baseline</div>
                                      <div className="grid grid-cols-3 gap-2 text-xs">
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            HI
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                                            {byproductData.baseline_hi?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            LO
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-indigo-600' : 'text-indigo-400'}`}>
                                            {byproductData.baseline_lo?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            Combined
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-teal-600' : 'text-teal-400'}`}>
                                            {byproductData.baseline?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                      </div>
                                      <div className={`mt-1 text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                                        "{byproductData.baseline_hi ?? 0}" + "{byproductData.baseline_lo ?? 0}" = "{String(byproductData.baseline_hi ?? 0) + String(byproductData.baseline_lo ?? 0)}"
                                      </div>
                                    </div>
                                  )}
                                  
                                  {/* Current HI/LO - Only show if both hi and lo are available */}
                                  {'hi' in byproductData && byproductData.hi !== undefined && 'lo' in byproductData && byproductData.lo !== undefined && (
                                    <>
                                      <div className="text-xs font-semibold mb-1" style={{color: theme === 'light' ? '#6b7280' : '#9ca3af'}}>Current</div>
                                      <div className="grid grid-cols-3 gap-2 text-xs">
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            HI
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-purple-600' : 'text-purple-400'}`}>
                                            {byproductData.hi?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            LO
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-indigo-600' : 'text-indigo-400'}`}>
                                            {byproductData.lo?.toFixed(2) ?? '0.00'}
                                          </div>
                                        </div>
                                        <div>
                                          <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                            Combined
                                          </div>
                                          <div className={`font-mono font-bold ${theme === 'light' ? 'text-teal-600' : 'text-teal-400'}`}>
                                            {(() => {
                                              const hiStr = String(byproductData.hi ?? 0);
                                              const loStr = String(byproductData.lo ?? 0);
                                              const combined = hiStr + loStr;
                                              return parseFloat(combined).toFixed(2);
                                            })()}
                                          </div>
                                        </div>
                                      </div>
                                      <div className={`mt-1 text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                                        "{byproductData.hi ?? 0}" + "{byproductData.lo ?? 0}" = "{String(byproductData.hi ?? 0) + String(byproductData.lo ?? 0)}"
                                      </div>
                                    </>
                                  )}
                                </div>
                              ) : null}
                            </>
                          ) : (
                            <div className="grid grid-cols-1 gap-1 text-xs">
                              <div>
                                <div className={`${theme === 'light' ? 'text-gray-600' : 'text-gray-400'}`}>
                                  Qty
                                </div>
                                <div className={`font-mono font-bold ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                                  }`}>
                                  {scaleQty?.toFixed(2) || '0.00'}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Manual Confirmation Section - Always show for InProgress orders */}
              {selectedOrderProgress.status === 'InProgress' && (
                <div className={`mt-4 p-4 rounded-lg border-2 ${theme === 'light' ? 'bg-green-50 border-green-300' : 'bg-green-900/20 border-green-600'
                  }`}>
                  <h4 className={`text-base font-semibold mb-4 flex items-center gap-2 ${theme === 'light' ? 'text-gray-900' : 'text-white'
                    }`}>
                    📤 Send Confirmation to SAP
                  </h4>
                  
                  {/* Production Summary - Compact horizontal layout */}
                  {/* Production Summary - Show Available for Confirmation */}
                  {(() => {
                    // ✅ CRITICAL FIX: Use weight_shift_total for accurate calculation
                    const weightShiftA = (selectedOrderProgress as any).weight_shift_a || 0;
                    const weightShiftB = (selectedOrderProgress as any).weight_shift_b || 0;
                    const weightShiftC = (selectedOrderProgress as any).weight_shift_c || 0;
                    const weightShiftTotal = weightShiftA + weightShiftB + weightShiftC;
                    
                    const confirmedShiftA = (selectedOrderProgress as any).confirmed_shift_a || 0;
                    const confirmedShiftB = (selectedOrderProgress as any).confirmed_shift_b || 0;
                    const confirmedShiftC = (selectedOrderProgress as any).confirmed_shift_c || 0;
                    const alreadySentToSAP = confirmedShiftA + confirmedShiftB + confirmedShiftC;
                    
                    // ✅ REAL-TIME FIX: Always use current_tons for real-time display
                    // This ensures Total Production matches the Current value shown at top
                    const currentTons = selectedOrderProgress.current_tons || 0;
                    const availableForConfirm = Math.max(0, currentTons - alreadySentToSAP);
                    
                    return (
                      <div className={`flex items-center gap-4 mb-4 p-2 rounded ${theme === 'light' ? 'bg-white border border-gray-200' : 'bg-gray-800 border border-gray-600'}`}>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>Total Production:</span>
                          <span className="font-bold text-blue-600">{currentTons.toFixed(2)} {selectedOrderProgress.unit}</span>
                        </div>
                        <div className={`w-px h-4 ${theme === 'light' ? 'bg-gray-300' : 'bg-gray-600'}`}></div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>Available to Confirm:</span>
                          <span className="font-bold text-green-600">{availableForConfirm.toFixed(2)} {selectedOrderProgress.unit}</span>
                        </div>
                        <div className={`w-px h-4 ${theme === 'light' ? 'bg-gray-300' : 'bg-gray-600'}`}></div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>Already Sent to SAP:</span>
                          <span className="font-bold">{alreadySentToSAP.toFixed(2)} {selectedOrderProgress.unit}</span>
                        </div>
                      </div>
                    );
                  })()}
                  
                  {/* Override Quantity - Partial Confirmation Support */}
                  {(() => {
                    // ✅ FIX: Calculate available for confirmation
                    // Available = weight_shift_total - confirmed_shift_total (what's been sent to SAP)
                    // This allows partial confirmations: send some now, keep rest for later
                    const weightShiftA = (selectedOrderProgress as any).weight_shift_a || 0;
                    const weightShiftB = (selectedOrderProgress as any).weight_shift_b || 0;
                    const weightShiftC = (selectedOrderProgress as any).weight_shift_c || 0;
                    const weightShiftTotal = weightShiftA + weightShiftB + weightShiftC;
                    
                    const confirmedShiftA = (selectedOrderProgress as any).confirmed_shift_a || 0;
                    const confirmedShiftB = (selectedOrderProgress as any).confirmed_shift_b || 0;
                    const confirmedShiftC = (selectedOrderProgress as any).confirmed_shift_c || 0;
                    const confirmedShiftTotal = confirmedShiftA + confirmedShiftB + confirmedShiftC;
                    
                    // ✅ REAL-TIME FIX: Always use current_tons for real-time display
                    // This ensures Total Production matches the Current value shown at top
                    const totalProduction = selectedOrderProgress.current_tons || 0;
                    const maxConfirmable = Math.max(0, totalProduction - confirmedShiftTotal);
                    
                    return (
                      <div className="mb-3">
                        <label className={`text-xs font-medium mb-1 block ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                          Confirmation Quantity ({selectedOrderProgress.unit}) 
                          <span className={`ml-1 font-normal ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                            (Max: {maxConfirmable.toFixed(2)} - Remainder kept for next confirmation)
                          </span>
                        </label>
                        <input
                          type="number"
                          min="0"
                          max={maxConfirmable}
                          step="0.01"
                          value={manualConfirmData.override_qty ?? ''}
                          onChange={(e) => {
                            const val = e.target.value ? parseFloat(e.target.value) : null;
                            // Validate: cannot exceed max confirmable
                            if (val !== null && val > maxConfirmable) {
                              addToast(`Override quantity cannot exceed accumulated production (${maxConfirmable.toFixed(2)})`, 'warning');
                              return;
                            }
                            setManualConfirmData({
                              ...manualConfirmData,
                              override_qty: val
                            });
                          }}
                          className={`w-full px-2 py-1.5 text-sm rounded border [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield] ${theme === 'light'
                              ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500 focus:ring-1 focus:ring-green-500'
                              : 'bg-gray-700 border-gray-600 text-white focus:border-green-400 focus:ring-1 focus:ring-green-400'
                            }`}
                          placeholder={`Leave empty to confirm all ${maxConfirmable.toFixed(2)}`}
                        />
                        {manualConfirmData.override_qty !== null && manualConfirmData.override_qty < maxConfirmable && (
                          <p className={`text-xs mt-1 ${theme === 'light' ? 'text-amber-600' : 'text-amber-400'}`}>
                            ⚡ Partial confirmation: {(maxConfirmable - manualConfirmData.override_qty).toFixed(2)} {selectedOrderProgress.unit} will remain for next confirmation
                          </p>
                        )}
                      </div>
                    );
                  })()}

                  {/* Byproduct Overrides (for milling orders) */}
                  {selectedOrderProgress.order_type === 'MILLING' && ((selectedOrderProgress as any).scale1 || (selectedOrderProgress as any).scale2 || (selectedOrderProgress as any).scale3) && (
                    <div className="mb-3">
                      <label className={`text-xs font-medium mb-1 block ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        Byproduct Quantities (Optional Overrides)
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {(selectedOrderProgress as any).scale1 && (
                          <div>
                            <label className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                              {(selectedOrderProgress as any).scale1}
                            </label>
                            <input
                              type="text"
                              value={manualConfirmData.custom_byproducts.scale1_qty}
                              onChange={(e) => setManualConfirmData({
                                ...manualConfirmData,
                                custom_byproducts: {
                                  ...manualConfirmData.custom_byproducts,
                                  scale1_qty: e.target.value
                                }
                              })}
                              className={`w-full px-2 py-1 text-sm font-mono rounded border ${theme === 'light'
                                  ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500'
                                  : 'bg-gray-700 border-gray-600 text-white focus:border-green-400'
                                }`}
                              placeholder={(selectedOrderProgress as any).scale1_qty?.toFixed(4) || '0.0000'}
                            />
                          </div>
                        )}
                        {(selectedOrderProgress as any).scale2 && (
                          <div>
                            <label className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                              {(selectedOrderProgress as any).scale2}
                            </label>
                            <input
                              type="text"
                              value={manualConfirmData.custom_byproducts.scale2_qty}
                              onChange={(e) => setManualConfirmData({
                                ...manualConfirmData,
                                custom_byproducts: {
                                  ...manualConfirmData.custom_byproducts,
                                  scale2_qty: e.target.value
                                }
                              })}
                              className={`w-full px-2 py-1 text-sm font-mono rounded border ${theme === 'light'
                                  ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500'
                                  : 'bg-gray-700 border-gray-600 text-white focus:border-green-400'
                                }`}
                              placeholder={(selectedOrderProgress as any).scale2_qty?.toFixed(4) || '0.0000'}
                            />
                          </div>
                        )}
                        {(selectedOrderProgress as any).scale3 && (
                          <div>
                            <label className={`text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                              {(selectedOrderProgress as any).scale3}
                            </label>
                            <input
                              type="text"
                              value={manualConfirmData.custom_byproducts.scale3_qty}
                              onChange={(e) => setManualConfirmData({
                                ...manualConfirmData,
                                custom_byproducts: {
                                  ...manualConfirmData.custom_byproducts,
                                  scale3_qty: e.target.value
                                }
                              })}
                              className={`w-full px-2 py-1 text-sm font-mono rounded border ${theme === 'light'
                                  ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500'
                                  : 'bg-gray-700 border-gray-600 text-white focus:border-green-400'
                                }`}
                              placeholder={(selectedOrderProgress as any).scale3_qty?.toFixed(4) || '0.0000'}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Scrap and Confirmed Text Fields */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className={`text-xs font-medium mb-1 block ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        Scrap ({selectedOrderProgress.unit})
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={manualConfirmData.scrap || ''}
                        onChange={(e) => setManualConfirmData({
                          ...manualConfirmData,
                          scrap: parseFloat(e.target.value) || 0
                        })}
                        className={`w-full px-2 py-1.5 text-sm rounded border [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield] ${theme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500 focus:ring-1 focus:ring-green-500'
                            : 'bg-gray-700 border-gray-600 text-white focus:border-green-400 focus:ring-1 focus:ring-green-400'
                          }`}
                        placeholder="Optional (default: 0)"
                      />
                    </div>
                    <div>
                      <label className={`text-xs font-medium mb-1 block ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'}`}>
                        Confirmed Text (Optional)
                      </label>
                      <input
                        type="text"
                        value={manualConfirmData.confirmed_text}
                        onChange={(e) => setManualConfirmData({
                          ...manualConfirmData,
                          confirmed_text: e.target.value
                        })}
                        className={`w-full px-2 py-1.5 text-sm rounded border ${theme === 'light'
                            ? 'bg-white border-gray-300 text-gray-900 focus:border-green-500 focus:ring-1 focus:ring-green-500'
                            : 'bg-gray-700 border-gray-600 text-white focus:border-green-400 focus:ring-1 focus:ring-green-400'
                          }`}
                        placeholder="Optional notes"
                      />
                    </div>
                  </div>
                  
                  {/* Send Confirmation Button */}
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        // Reset form fields
                        setManualConfirmData({
                          scrap: 0,
                          confirmed_text: '',
                          override_qty: null,
                          custom_byproducts: { scale1_qty: null, scale2_qty: null, scale3_qty: null }
                        });
                      }}
                      disabled={sendingManualConfirm}
                      className={`px-3 py-2 rounded-md font-medium text-sm transition-colors ${theme === 'light'
                          ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                          : 'bg-gray-600 text-white hover:bg-gray-500'
                        } disabled:opacity-50`}
                    >
                      Reset
                    </button>
                    <button
                      onClick={async () => {
                        setSendingManualConfirm(true);
                        try {
                          // ✅ FIX: Calculate available for confirmation
                          // Available = total SCADA production - what's already sent to SAP
                          const weightShiftA = (selectedOrderProgress as any).weight_shift_a || 0;
                          const weightShiftB = (selectedOrderProgress as any).weight_shift_b || 0;
                          const weightShiftC = (selectedOrderProgress as any).weight_shift_c || 0;
                          const weightShiftTotal = weightShiftA + weightShiftB + weightShiftC;
                          
                          const confirmedShiftA = (selectedOrderProgress as any).confirmed_shift_a || 0;
                          const confirmedShiftB = (selectedOrderProgress as any).confirmed_shift_b || 0;
                          const confirmedShiftC = (selectedOrderProgress as any).confirmed_shift_c || 0;
                          const confirmedShiftTotal = confirmedShiftA + confirmedShiftB + confirmedShiftC;
                          
                          // ✅ REAL-TIME FIX: Always use current_tons for real-time display
                          // This ensures Total Production matches the Current value shown at top
                          const totalProduction = selectedOrderProgress.current_tons || 0;
                          const maxConfirmable = Math.max(0, totalProduction - confirmedShiftTotal);
                          
   
                          
                          const confirmQty = manualConfirmData.override_qty !== null 
                            ? manualConfirmData.override_qty 
                            : maxConfirmable;

                          // Build the confirmation payload
                          const payload: any = {
                            scrap: manualConfirmData.scrap,
                            confirmed_text: manualConfirmData.confirmed_text || '',
                            yield: confirmQty,
                            shift: (selectedOrderProgress as any).current_shift || 'A',
                            operator: 'manual'
                          };

                          // Add byproduct quantities (convert string to number)
                          if (manualConfirmData.custom_byproducts.scale1_qty !== '') {
                            const val = typeof manualConfirmData.custom_byproducts.scale1_qty === 'string' 
                              ? parseFloat(manualConfirmData.custom_byproducts.scale1_qty) 
                              : manualConfirmData.custom_byproducts.scale1_qty;
                            if (!isNaN(val)) {
                              payload.scale1_qty = val;
                            }
                          }
                          
                          if (manualConfirmData.custom_byproducts.scale2_qty !== '') {
                            const val = typeof manualConfirmData.custom_byproducts.scale2_qty === 'string' 
                              ? parseFloat(manualConfirmData.custom_byproducts.scale2_qty) 
                              : manualConfirmData.custom_byproducts.scale2_qty;
                            if (!isNaN(val)) {
                              payload.scale2_qty = val;
                            }
                          }
                          
                          if (manualConfirmData.custom_byproducts.scale3_qty !== '') {
                            const val = typeof manualConfirmData.custom_byproducts.scale3_qty === 'string' 
                              ? parseFloat(manualConfirmData.custom_byproducts.scale3_qty) 
                              : manualConfirmData.custom_byproducts.scale3_qty;
                            if (!isNaN(val)) {
                              payload.scale3_qty = val;
                            }
                          }

                          

                          // Use the process_orders endpoint which handles SAP confirmation properly
                          const response = await apiFetch(getApiUrl('/api/process_orders/manual-confirm'), {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              po_number: selectedOrderProgress.po_number,
                              confirmed_qty: payload.yield || 0,
                              scale1_qty: payload.scale1_qty || 0,
                              scale2_qty: payload.scale2_qty || 0,
                              scale3_qty: payload.scale3_qty || 0,
                              scrap: payload.scrap,
                              confirmed_text: payload.confirmed_text,
                              shift: payload.shift,
                              operator: payload.operator
                            }),
                          });

                          const result = await response.json();

                          if (response.ok && result.success) {
                            const offlineMsg = result.offline_mode ? ' (offline mode)' : '';
                            const remainderMsg = result.remainder_qty > 0 ? ` | Remainder: ${result.remainder_qty.toFixed(2)} kept for next confirmation` : '';
                            addToast(`✅ Confirmed ${result.confirmed_qty_sent?.toFixed(2) || payload.yield} for ${selectedOrderProgress.po_number}${offlineMsg}${remainderMsg}`, 'success');
                            
                            // Reset confirmation data (clear the form fields)
                            setManualConfirmData({
                              scrap: 0,
                              confirmed_text: '',
                              override_qty: null,
                              custom_byproducts: { scale1_qty: null, scale2_qty: null, scale3_qty: null }
                            });
                            
                            // ✅ Refresh the order data to update the "Available to Confirm" display
                            // Keep the dialog open so user can send multiple partial confirmations
                            try {
                              
                              const refreshResponse = await apiFetch(getApiUrl(`/api/orders/${selectedOrderProgress.po_number}/progress`));
                              if (refreshResponse.ok) {
                                const progressData = await refreshResponse.json();
                                
                                // Convert unit (same logic as openProgressDialog)
                                const orderType = progressData.order_type || selectedOrderProgress.order_type;
                                const unit = progressData.unit === 'TON' || progressData.unit === 'ton'
                                  ? 'TO'
                                  : (progressData.unit || (orderType === 'MILLING' ? 'TO' : 'BAG'));
                                
                                const currentDisplay = progressData.confirmed_qty !== undefined && progressData.confirmed_qty !== null
                                  ? progressData.confirmed_qty
                                  : (progressData.current || 0);
                                
                                // Update selectedOrderProgress with fresh data (including confirmed_shift_a/b/c)
                                setSelectedOrderProgress({
                                  ...selectedOrderProgress,
                                  current_tons: currentDisplay,
                                  remaining_tons: progressData.remaining || 0,
                                  progress_pct: progressData.progress_pct || 0,
                                  // ✅ Update shift weight fields (critical for "Available to Confirm" calculation)
                                  weight_shift_a: progressData.weight_shift_a || 0,
                                  weight_shift_b: progressData.weight_shift_b || 0,
                                  weight_shift_c: progressData.weight_shift_c || 0,
                                  confirmed_shift_a: progressData.confirmed_shift_a || 0,
                                  confirmed_shift_b: progressData.confirmed_shift_b || 0,
                                  confirmed_shift_c: progressData.confirmed_shift_c || 0,
                                  current_shift: progressData.current_shift || 'A',
                                  // Also update byproduct scales
                                  scale1_qty: progressData.scale1_qty || 0,
                                  scale2_qty: progressData.scale2_qty || 0,
                                  scale3_qty: progressData.scale3_qty || 0,
                                  byproduct_details: progressData.byproduct_details || {},
                                });
                               
                              }
                            } catch (err) {
                              console.error('Failed to refresh order data:', err);
                            }
                            
                            // Refresh orders list
                            loadOrders();
                            loadKpiCounts();
                          } else {
                            addToast(`❌ Failed: ${result.error || 'Unknown error'}`, 'error');
                          }
                        } catch (err: any) {
                          console.error('Failed to send confirmation:', err);
                          addToast(`❌ Error: ${err.message}`, 'error');
                        } finally {
                          setSendingManualConfirm(false);
                        }
                      }}
                      disabled={sendingManualConfirm}
                      className={`px-4 py-2 rounded-md font-medium text-sm transition-colors ${theme === 'light'
                          ? 'bg-green-600 text-white hover:bg-green-700 shadow-md'
                          : 'bg-green-500 text-white hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                      title="Send confirmation to SAP"
                    >
                      {sendingManualConfirm ? '📤 Sending...' : '📤 Send Confirmation to SAP'}
                    </button>
                  </div>
                  
                  <p className={`text-xs mt-2 ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`}>
                    ℹ️ This will send a manual confirmation to SAP with the specified values. Current production will reset after confirmation.
                  </p>
                </div>
              )}

              {/* Status Footer - Compact inline */}
              <div className={`mt-4 flex items-center justify-between text-xs ${theme === 'light' ? 'text-gray-500' : 'text-gray-400'}`}>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${selectedOrderProgress.status === 'InProgress'
                      ? theme === 'light' ? 'bg-blue-200 text-blue-800' : 'bg-blue-700 text-blue-200'
                      : theme === 'light' ? 'bg-gray-200 text-gray-700' : 'bg-gray-600 text-gray-300'
                    }`}>
                    {selectedOrderProgress.status}
                  </span>
                  {(selectedOrderProgress as any).formula && (
                    <span className="font-mono">{(selectedOrderProgress as any).formula}</span>
                  )}
                </div>
                <span>
                  Last update: {selectedOrderProgress.last_tick
                    ? new Date(selectedOrderProgress.last_tick).toLocaleString()
                    : 'N/A'
                  }
                </span>
              </div>
            </div>

            {/* Footer */}
            <div className={`px-4 py-3 border-t ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'
              }`}>
              <div className="flex justify-end">
                <button
                  onClick={() => setShowProgressDialog(false)}
                  className={`px-4 py-2 rounded-md font-medium transition-colors ${theme === 'light'
                      ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                      : 'bg-gray-600 text-white hover:bg-gray-500'
                    }`}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Enhanced Orders View Modal */}
      {showOrdersModal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-8 animate-in fade-in duration-300">
          {/* Enhanced Backdrop */}
          <div
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${theme === 'light'
                ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30'
                : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
              }`}
            onClick={closeOrdersModal}
          />

          {/* Enhanced Modal Content */}
          <div className={`relative w-full max-w-5xl max-h-[85vh] rounded-xl border shadow-2xl transition-all duration-300 backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${theme === 'light'
              ? 'bg-white/98 border-slate-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]'
              : 'bg-slate-900/95 border-cyan-400/40 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]'
            }`}>
            {/* Compact Header */}
            <div className={`flex items-center justify-between p-3 border-b ${theme === 'light' ? 'bg-blue-100 border-slate-200' : 'bg-slate-800/50 border-cyan-400/30'
              }`}>
              <div className="flex items-center gap-2">
                <div className={`p-1.5 rounded-md ${(modalType === 'confirmed' || modalType === 'completed')
                    ? theme === 'light' ? 'bg-green-100' : 'bg-green-900/30'
                    : modalType === 'rejected'
                      ? theme === 'light' ? 'bg-red-100' : 'bg-red-900/30'
                      : modalType === 'errorlog'
                        ? theme === 'light' ? 'bg-red-100' : 'bg-red-900/30'
                        : theme === 'light' ? 'bg-orange-100' : 'bg-orange-900/30'
                  }`}>
                  {(modalType === 'confirmed' || modalType === 'completed') ? (
                    <CheckCircle className={`h-4 w-4 ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`} />
                  ) : modalType === 'rejected' ? (
                    <XCircle className={`h-4 w-4 ${theme === 'light' ? 'text-red-600' : 'text-red-400'}`} />
                  ) : modalType === 'errorlog' ? (
                    <AlertCircle className={`h-4 w-4 ${theme === 'light' ? 'text-red-600' : 'text-red-400'}`} />
                  ) : (
                    <Clock3 className={`h-4 w-4 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'}`} />
                  )}
                </div>
                <div>
                  <h2 className={`text-base font-bold ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                    }`}>
                    {modalTitle}
                  </h2>
                  <p className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
                    }`}>
                    {modalOrders.length} {modalType === 'errorlog' 
                      ? (modalOrders.length === 1 ? 'entry' : 'entries')
                      : (modalOrders.length === 1 ? 'order' : 'orders')
                    } found
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Push confirm to SAP for all orders - shown in Completed (and In Progress) modal when orders exist */}
                {(modalType === 'completed' || modalType === 'inprogress') && modalOrders.length > 0 && (
                  <button
                    onClick={handlePushConfirmation}
                    disabled={pushingConfirmation}
                    className={`px-4 py-2 rounded-lg text-sm font-bold transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed push-confirmation-btn ${theme === 'light'
                        ? 'bg-green-500 hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)] border border-green-400'
                        : 'bg-green-500 hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)] border border-green-400'
                      }`}
                    style={{
                      color: '#ffffff !important',
                      WebkitTextFillColor: '#ffffff !important',
                      WebkitTextStrokeColor: 'transparent !important'
                    }}
                    title="Push confirm to SAP for all orders"
                  >
                    {pushingConfirmation ? 'Pushing...' : 'Push confirm to SAP for all'}
                  </button>
                )}
                <button
                  onClick={closeOrdersModal}
                  className={`p-1.5 rounded-lg transition-all duration-200 hover:scale-110 ${theme === 'light'
                      ? 'hover:bg-slate-100 text-slate-600'
                      : 'hover:bg-slate-700/50 text-cyan-300'
                    }`}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* KPI Cards for Confirmed Orders */}
            {(modalType === 'confirmed' || modalType === 'completed') && modalOrders.length > 0 && (
              <div className="p-3 border-b border-slate-200 dark:border-slate-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className={`p-4 rounded-lg border transition-all duration-200 ${theme === 'light'
                      ? 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                      : 'bg-blue-900/20 border-blue-700/50 hover:bg-blue-900/30'
                    }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`p-2 rounded-md ${theme === 'light' ? 'bg-blue-100' : 'bg-blue-800/50'
                          }`}>
                          <Weight className={`h-4 w-4 ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                            }`} />
                        </div>
                        <div>
                          <h4 className={`text-xs font-medium ${theme === 'light' ? 'text-blue-700' : 'text-blue-300'
                            }`}>
                            Expected Weight
                          </h4>
                          <p className={`text-xs ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                            }`}>
                            Total from confirmed orders
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${theme === 'light' ? 'text-blue-800' : 'text-blue-200'
                          }`}>
                          {calculateValidatedKPIs().totalExpectedWeight.toLocaleString()}
                        </div>
                        <div className={`text-xs ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'
                          }`}>
                          kg
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className={`p-4 rounded-lg border transition-all duration-200 ${theme === 'light'
                      ? 'bg-green-50 border-green-200 hover:bg-green-100'
                      : 'bg-green-900/20 border-green-700/50 hover:bg-green-900/30'
                    }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`p-2 rounded-md ${theme === 'light' ? 'bg-green-100' : 'bg-green-800/50'
                          }`}>
                          <Scale className={`h-4 w-4 ${theme === 'light' ? 'text-green-600' : 'text-green-400'
                            }`} />
                        </div>
                        <div>
                          <h4 className={`text-xs font-medium ${theme === 'light' ? 'text-green-700' : 'text-green-300'
                            }`}>
                            Confirmed Weight
                          </h4>
                          <p className={`text-xs ${theme === 'light' ? 'text-green-600' : 'text-green-400'
                            }`}>
                            Actual validated quantity
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${theme === 'light' ? 'text-green-800' : 'text-green-200'
                          }`}>
                          {calculateValidatedKPIs().totalConfirmedWeight.toLocaleString()}
                        </div>
                        <div className={`text-xs ${theme === 'light' ? 'text-green-600' : 'text-green-400'
                          }`}>
                          kg
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Compact Search and Date Filters */}
            <div className={`p-4 border-b ${theme === 'light' ? 'bg-slate-50/50 border-slate-200' : 'bg-slate-800/30 border-cyan-400/30'
              }`}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Search */}
                <div className="relative">
                  <Search className={`absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 ${theme === 'light' ? 'text-slate-400' : 'text-slate-500'
                    }`} />
                  <input
                    type="text"
                    placeholder="Search orders..."
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setModalCurrentPage(1); // Reset to first page when searching
                    }}
                    className={`w-full pl-8 pr-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
                        ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                        : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
                      }`}
                  />
                </div>

                {/* Start Date */}
                <div>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      setModalCurrentPage(1); // Reset to first page when filtering
                    }}
                    className={`w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
                        ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                        : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
                      }`}
                  />
                </div>

                {/* End Date */}
                <div>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      setModalCurrentPage(1); // Reset to first page when filtering
                    }}
                    className={`w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 ${theme === 'light'
                        ? 'bg-white border-slate-300 focus:ring-blue-500 focus:border-blue-500 text-slate-800'
                        : 'bg-slate-800 border-slate-600 focus:ring-cyan-500 focus:border-cyan-500 text-cyan-100'
                      }`}
                  />
                </div>
              </div>
            </div>

            {/* Compact Content */}
            <div className="p-4 overflow-x-auto">
              {/* Offline Bulk Actions */}
              {modalType === 'offline' && (
                <div className="flex items-center gap-2 mb-3 px-1">
                  <button
                    onClick={selectAllOffline}
                    className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                      theme === 'light' ? 'bg-gray-200 hover:bg-gray-300 text-gray-800' : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                    }`}
                  >
                    Select All
                  </button>
                  <button
                    onClick={deselectAllOffline}
                    className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                      theme === 'light' ? 'bg-gray-200 hover:bg-gray-300 text-gray-800' : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                    }`}
                  >
                    Deselect All
                  </button>
                  <div className="flex-1"></div>
                  <button
                    onClick={() => sendOfflineOrders(Array.from(selectedOfflineOrders))}
                    disabled={selectedOfflineOrders.size === 0 || sendingOffline}
                    className="px-4 py-1.5 text-xs font-bold rounded bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 transition-colors shadow-sm flex items-center gap-2"
                  >
                    {sendingOffline && <div className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin"></div>}
                    {sendingOffline ? 'Sending...' : `Send Selected (${selectedOfflineOrders.size})`}
                  </button>
                </div>
              )}
              {modalOrders.length === 0 ? (
                <div className={`text-center py-8 ${theme === 'light' ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                  <div className="text-4xl mb-2">📋</div>
                  <p className="text-sm">No {modalType === 'errorlog' ? 'error log entries' : `${modalType} orders`} found</p>
                </div>
              ) : (
                <div className={`overflow-x-auto rounded-lg border transition-all duration-300 ${theme === 'light'
                    ? 'bg-white border-slate-200'
                    : 'bg-slate-800 border-slate-600'
                  }`}>
                  <table className={`min-w-full text-xs ${theme === 'light' ? 'text-slate-800' : 'text-slate-200'
                    }`}>
                    <thead className={`${theme === 'light'
                        ? 'bg-blue-100 text-slate-700 border-b border-slate-200'
                        : 'bg-slate-700 text-slate-200 border-b border-slate-500'
                      }`}>
                      <tr>
                        {modalType === 'errorlog' ? (
                          <>
                            <th className="px-3 py-2 text-left font-medium">Log ID</th>
                            <th className="px-3 py-2 text-left font-medium">PO Number</th>
                            <th className="px-3 py-2 text-left font-medium">Material</th>
                            <th className="px-3 py-2 text-left font-medium">Error Message</th>
                            <th className="px-3 py-2 text-left font-medium">Status</th>
                            <th className="px-3 py-2 text-left font-medium">Created At</th>
                            <th className="px-3 py-2 text-left font-medium">Resolved At</th>
                            <th className="px-3 py-2 text-left font-medium">Actions</th>
                          </>
                        ) : modalType === 'offline' ? (
                          <>
                            <th className="px-3 py-2 text-left font-medium w-10">
                              <input 
                                type="checkbox" 
                                checked={modalOrders.length > 0 && selectedOfflineOrders.size === modalOrders.length}
                                onChange={(e) => e.target.checked ? selectAllOffline() : deselectAllOffline()}
                                className="rounded cursor-pointer"
                              />
                            </th>
                            <th className="px-3 py-2 text-left font-medium">PO Number</th>
                            <th className="px-3 py-2 text-left font-medium">Material</th>
                            <th className="px-3 py-2 text-left font-medium">Version</th>
                            <th className="px-3 py-2 text-left font-medium">Shift</th>
                            <th className="px-3 py-2 text-left font-medium">
                              <div className="flex items-center gap-1">
                                <Weight className="w-3.5 h-3.5" />
                                Confirmed
                              </div>
                            </th>
                            <th className="px-3 py-2 text-left font-medium w-20">Scrap</th>
                            <th className="px-3 py-2 text-left font-medium w-40">Confirmed Text</th>
                            <th className="px-3 py-2 text-left font-medium">Date</th>
                            <th className="px-3 py-2 text-left font-medium">Actions</th>
                          </>
                        ) : (
                          <>
                            <th className="px-3 py-2 text-left font-medium">Order ID</th>
                            <th className="px-3 py-2 text-left font-medium">PO Number</th>
                            <th className="px-3 py-2 text-left font-medium">Material</th>
                            <th className="px-3 py-2 text-left font-medium">Order Type</th>
                            <th className="px-3 py-2 text-left font-medium">
                              <div className="flex items-center gap-1">
                                <Weight className="w-3.5 h-3.5" />
                                TARGET
                              </div>
                            </th>
                            <th className="px-3 py-2 text-left font-medium">Confirm Weight</th>
                            <th className="px-3 py-2 text-left font-medium">UNIT</th>
                            <th className="px-3 py-2 text-left font-medium">Status</th>
                            <th className="px-3 py-2 text-left font-medium">Shift</th>
                            <th className="px-3 py-2 text-left font-medium">Confirmation Date</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {getPaginatedModalOrders().map((order, index) => {
                        if (modalType === 'offline') {
                          return (
                            <tr
                              key={order.id}
                              className={`border-b transition-colors ${
                                theme === 'light' ? 'border-slate-100' : 'border-slate-600'
                              } ${
                                selectedOfflineOrders.has(order.id)
                                  ? theme === 'light' ? 'bg-blue-50' : 'bg-blue-900/20'
                                  : index % 2 === 0
                                    ? theme === 'light' ? 'bg-white' : 'bg-slate-800'
                                    : theme === 'light' ? 'bg-slate-50' : 'bg-slate-700'
                              }`}
                            >
                              <td className="px-3 py-2">
                                <input 
                                  type="checkbox"
                                  checked={selectedOfflineOrders.has(order.id)}
                                  onChange={() => handleOfflineSelection(order.id)}
                                  className="rounded cursor-pointer w-4 h-4"
                                />
                              </td>
                              <td className="px-3 py-2 font-mono text-xs">{order.po_number || 'N/A'}</td>
                              <td className="px-3 py-2 font-mono text-xs">{order.material || 'N/A'}</td>
                              <td className="px-3 py-2 font-mono text-xs">{(order as any).version || '-'}</td>
                              <td className="px-3 py-2 font-mono text-xs font-bold">
                                <span className={`px-1.5 py-0.5 rounded text-white ${
                                  (order as any).shift === 'A' ? 'bg-blue-500' :
                                  (order as any).shift === 'B' ? 'bg-green-500' :
                                  (order as any).shift === 'C' ? 'bg-purple-500' : 'bg-gray-500'
                                }`}>
                                  {(order as any).shift || '-'}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-mono text-xs font-bold text-blue-500">
                                {((order as any).confirmed_qty || 0).toFixed(2)} {(order as any).unit || 'KG'}
                              </td>
                              <td className="px-3 py-2">
                                <input 
                                  type="number"
                                  min="0"
                                  step="0.1"
                                  className={`w-16 px-2 py-1 text-xs border rounded outline-none focus:ring-1 focus:ring-blue-500 ${
                                    theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600 text-white'
                                  }`}
                                  value={offlineEdits[order.id]?.scrap ?? (order as any).scrap ?? 0}
                                  onChange={(e) => handleOfflineEdit(order.id, 'scrap', parseFloat(e.target.value) || 0)}
                                  onClick={(e) => e.stopPropagation()}
                                  placeholder="0"
                                />
                              </td>
                              <td className="px-3 py-2">
                                <input 
                                  type="text"
                                  className={`w-full px-2 py-1 text-xs border rounded outline-none focus:ring-1 focus:ring-blue-500 ${
                                    theme === 'light' ? 'bg-white border-gray-300' : 'bg-slate-700 border-slate-600 text-white'
                                  }`}
                                  value={offlineEdits[order.id]?.confirmed_text ?? (order as any).confirmed_text ?? ''}
                                  onChange={(e) => handleOfflineEdit(order.id, 'confirmed_text', e.target.value)}
                                  onClick={(e) => e.stopPropagation()}
                                  placeholder="Enter confirmation text..."
                                  maxLength={500}
                                />
                              </td>
                              <td className="px-3 py-2 text-xs opacity-70">
                                {order.created_at ? new Date(order.created_at).toLocaleString('en-US', {
                                  month: '2-digit',
                                  day: '2-digit',
                                  year: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                }) : 'N/A'}
                              </td>
                              <td className="px-3 py-2">
                                <div className="flex gap-2">
                                  {offlineEdits[order.id] && (
                                    <button
                                      onClick={(e) => { e.stopPropagation(); saveOfflineChanges(order.id); }}
                                      className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 font-medium"
                                    >
                                      Save
                                    </button>
                                  )}
                                  <button
                                    onClick={(e) => { e.stopPropagation(); sendOfflineOrders([order.id]); }}
                                    className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 font-medium"
                                    disabled={sendingOffline}
                                  >
                                    {sendingOffline ? 'Sending...' : 'Send'}
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        }

                        if (modalType === 'errorlog') {
                          // Render error log entry
                          const log = order as any;
                          return (
                            <tr
                              key={log.id}
                              onClick={() => {
                                // Parse and show payload when row is clicked
                                try {
                                  const payload = typeof log.payload === 'string' ? JSON.parse(log.payload) : log.payload;
                                  setSelectedPayload(payload);
                                  setSelectedPayloadPO(log.po_number || 'N/A');
                                  setShowPayloadModal(true);
                                } catch (e) {
                                  console.error('Failed to parse payload:', e);
                                }
                              }}
                              className={`border-b cursor-pointer transition-colors ${theme === 'light' ? 'border-slate-100 hover:bg-blue-50' : 'border-slate-600 hover:bg-slate-600'
                                } ${index % 2 === 0
                                  ? theme === 'light' ? 'bg-white' : 'bg-slate-800'
                                  : theme === 'light' ? 'bg-slate-50' : 'bg-slate-700'
                                }`}
                            >
                              <td className="px-3 py-2 font-mono text-xs font-semibold">{log.id}</td>
                              <td className="px-3 py-2 font-mono text-xs">{log.po_number || 'N/A'}</td>
                              <td className="px-3 py-2 font-mono text-xs">{log.material || 'N/A'}</td>
                              <td className="px-3 py-2 text-xs">
                                <div className="max-w-xs" title={log.error_message || 'No error message'}>
                                  <div className="truncate">{log.error_message || 'No error message'}</div>
                                  {/* Show payload details for VPN errors */}
                                  {log.error_type === 'sap_network_error' && log.payload && (() => {
                                    try {
                                      const payload = typeof log.payload === 'string' ? JSON.parse(log.payload) : log.payload;
                                      const sentPayload = payload?.sent_payload;
                                      if (sentPayload) {
                                        const shift = sentPayload.shift || 'N/A';
                                        const weight = sentPayload.confirmed_weight || 0;
                                        const uom = sentPayload.uom || 'KG';
                                        return (
                                          <div className={`mt-1 text-xs font-mono ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`}>
                                            📦 Shift {shift}: {Number(weight).toFixed(2)} {uom}
                                          </div>
                                        );
                                      }
                                    } catch (e) {
                                      return null;
                                    }
                                    return null;
                                  })()}
                                </div>
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${log.status === 'Resolved'
                                    ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                                    : theme === 'light' ? 'bg-red-100 text-red-700' : 'bg-red-900/30 text-red-300'
                                  }`}>
                                  {log.status || 'Unresolved'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-xs">
                                {log.created_at ? new Date(log.created_at).toLocaleString('en-US', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                  hour12: true
                                }) : 'N/A'}
                              </td>
                              <td className="px-3 py-2 text-xs">
                                {log.resolved_at ? new Date(log.resolved_at).toLocaleString('en-US', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                  hour12: true
                                }) : '-'}
                              </td>
                              <td className="px-3 py-2">
                                <div className="flex gap-1">
                                  {log.status !== 'Resolved' && (() => {
                                    // Check if this is a VPN network error (partial confirmation failed)
                                    const isVpnError = log.error_type === 'sap_network_error';
                                    
                                    // Check if this is a confirmation order error (sap_failed) or rejected order error
                                    const isConfirmationError = log.error_type === 'sap_failed' || 
                                                               (log.source && (log.source.includes('sap') || log.source.includes('confirmation')));
                                    
                                    // Check if this is a confirmation error from push_confirmation (orders with no production to confirm)
                                    // These are logged with error_type="validation_rejected" but are actually confirmation errors
                                    const errorMsg = (log.error_message || '').toLowerCase();
                                    const isNoProductionError = errorMsg.includes('no remaining production') || 
                                                               errorMsg.includes('no production to confirm') ||
                                                               errorMsg.includes('inprogress order has no') ||
                                                               errorMsg.includes('validated order has no');
                                    
                                    // Only show Revalidate button for actual rejected orders (error_type="validation_rejected")
                                    // Exclude confirmation errors (sap_failed, no production errors, etc.)
                                    const isRejectedOrder = log.error_type === 'validation_rejected' && !isNoProductionError;
                                    
                                     // VPN network errors: show Resend button
                                    if (isVpnError) {
                                      return (
                                        <button
                                          onClick={() => {
                                            // Open modal to enter scrap and confirmed_text
                                            setSelectedResendLog(log);
                                            // Try to get default values from payload
                                            try {
                                              const payload = typeof log.payload === 'string' ? JSON.parse(log.payload) : log.payload;
                                              const sentPayload = payload?.sent_payload;
                                              setResendData({
                                                scrap: sentPayload?.scrap || 0,
                                                confirmed_text: sentPayload?.confirmed_text || '',
                                                force_resend: false
                                              });
                                            } catch (e) {
                                              setResendData({ scrap: 0, confirmed_text: '', force_resend: false });
                                            }
                                            setShowResendModal(true);
                                          }}
                                          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${theme === 'light'
                                              ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                                              : 'bg-blue-900/30 text-blue-300 hover:bg-blue-800/40'
                                            }`}
                                          title="Resend to SAP - enter scrap and confirmed text"
                                        >
                                          📤 Resend
                                        </button>
                                      );
                                    }
                                    
                                    // SAP confirmation errors: show Resend button so user can retry
                                    if (isConfirmationError) {
                                      return (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation(); // Prevent row click from opening payload modal
                                            setSelectedResendLog(log);
                                            try {
                                              const payload = typeof log.payload === 'string' ? JSON.parse(log.payload) : log.payload;
                                              const sentPayload = payload?.sent_payload;
                                              setResendData({
                                                scrap: sentPayload?.scrap || 0,
                                                confirmed_text: sentPayload?.confirmed_text || '',
                                                force_resend: false
                                              });
                                            } catch (err) {
                                              setResendData({ scrap: 0, confirmed_text: '', force_resend: false });
                                            }
                                            setShowResendModal(true);
                                          }}
                                          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${theme === 'light'
                                              ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                                              : 'bg-orange-900/30 text-orange-300 hover:bg-orange-800/40'
                                            }`}
                                          title="Resend to SAP - retry failed confirmation"
                                        >
                                          🔄 Resend
                                        </button>
                                      );
                                    }
                                    
                                    // No production errors: show no buttons (order has no data to send)
                                    if (isNoProductionError) {
                                      return null;
                                    }
                                    
                                    // Rejected order errors: show only Revalidate button
                                    if (isRejectedOrder) {
                                      return (
                                        <button
                                          onClick={async () => {
                                            try {
                                              const response = await apiFetch(getApiUrl(`/api/error-log/${log.id}/revalidate`), {
                                                method: 'POST'
                                              });
                                              const result = await response.json();
                                              if (result.ok) {
                                                addToast(`Revalidation started for ${log.po_number}`, 'success');
                                                await openOrdersModal('errorlog'); // Refresh
                                              } else {
                                                addToast(`Failed to revalidate: ${result.message}`, 'error');
                                              }
                                            } catch (err: any) {
                                              addToast(`Failed to revalidate: ${err.message}`, 'error');
                                            }
                                          }}
                                          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${theme === 'light'
                                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                              : 'bg-green-900/30 text-green-300 hover:bg-green-800/40'
                                            }`}
                                          title="Revalidate Order"
                                        >
                                          Revalidate
                                        </button>
                                      );
                                    }
                                    
                                    // Default: show no buttons for other error types
                                    return null;
                                  })()}
                                </div>
                              </td>
                            </tr>
                          );
                        }

                        // Render order entry (existing logic)
                        const expectedQty = order.quantity || 0;
                        const confirmedQty = (order as any).confirmed_qty || 0;

                        // Get expected weight directly from database
                        const expectedWeight = (order as any).expected_weight ?
                          parseFloat((order as any).expected_weight).toFixed(2) :
                          '0.00';

                        return (
                          <tr
                            key={order.id}
                            className={`border-b ${theme === 'light' ? 'border-slate-100' : 'border-slate-600'
                              } ${index % 2 === 0
                                ? theme === 'light' ? 'bg-white' : 'bg-slate-800'
                                : theme === 'light' ? 'bg-slate-50' : 'bg-slate-700'
                              }`}
                          >
                            <td className="px-3 py-2 font-mono text-xs font-semibold">{order.id}</td>
                            <td className="px-3 py-2 font-mono text-xs">{order.po_number}</td>
                            <td className="px-3 py-2 font-mono text-xs">{order.material}</td>
                            <td className="px-3 py-2">
                              <span className={`px-2 py-1 rounded-full text-xs font-bold ${(order as any).order_type === 'MILLING'
                                  ? theme === 'light'
                                    ? 'bg-purple-100 text-purple-700'
                                    : 'bg-purple-900/30 text-purple-300'
                                  : (order as any).order_type === 'PACKING'
                                    ? theme === 'light'
                                      ? 'bg-cyan-100 text-cyan-700'
                                      : 'bg-cyan-900/30 text-cyan-300'
                                    : 'bg-gray-100 text-gray-700'
                                }`}>
                                {(order as any).order_type || 'Unknown'}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-center">
                              <div className="flex flex-col items-center gap-0.5">
                                {/* Show the appropriate target based on order type */}
                                <span className="text-sm font-mono font-bold">
                                  {(order as any).order_type === 'MILLING'
                                    ? ((order as any).expected_weight || order.quantity || 0).toFixed(2)
                                    : (order.quantity || 0).toLocaleString()
                                  }
                                </span>
                                {/* Show unit badge */}
                                <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${(order as any).order_type === 'MILLING'
                                    ? theme === 'light' ? 'bg-purple-100 text-purple-700' : 'bg-purple-900/30 text-purple-300'
                                    : theme === 'light' ? 'bg-cyan-100 text-cyan-700' : 'bg-cyan-900/30 text-cyan-300'
                                  }`}>
                                  {(order as any).order_type === 'MILLING' ? 'TO' : 'BAG'}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-2 font-mono text-xs font-bold">{confirmedQty} TO</td>
                            <td className="px-3 py-2 text-center">
                              <span className={`px-2 py-1 rounded-full text-xs font-bold ${(order as any).order_type === 'MILLING'
                                  ? theme === 'light' ? 'bg-purple-100 text-purple-700' : 'bg-purple-900/30 text-purple-300'
                                  : theme === 'light' ? 'bg-cyan-100 text-cyan-700' : 'bg-cyan-900/30 text-cyan-300'
                                }`}>
                                {(order as any).order_type === 'MILLING' ? 'TO' : 'BAG'}
                              </span>
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex flex-col gap-1">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${order.status === 'Validated'
                                    ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                                    : theme === 'light' ? 'bg-red-100 text-red-700' : 'bg-red-900/30 text-red-300'
                                  }`}>
{order.status}
                                </span>

                              </div>
                            </td>
                            <td className="px-3 py-2">
                              {(() => {
                                // Determine shift based on validation time
                                const validationTime = order.updated_at || (order as any).created_at;
                                if (validationTime && (order.status === 'Validated' || order.status === 'Rejected')) {
                                  const operationType = getOperationType(order);
                                  const shift = getShiftFromTime(validationTime, operationType);

                                  // Debug logging
                                  

                                  return (
                                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${shift === 'A'
                                        ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                                        : shift === 'B'
                                          ? theme === 'light' ? 'bg-blue-100 text-blue-700' : 'bg-blue-900/30 text-blue-300'
                                          : theme === 'light' ? 'bg-purple-100 text-purple-700' : 'bg-purple-900/30 text-purple-300'
                                      }`}>
                                      {shift}
                                    </span>
                                  );
                                }
                                return <span className="text-xs text-slate-400">-</span>;
                              })()}
                            </td>
                            <td className="px-3 py-2 text-xs">
                              {(order.status === 'Validated' || order.status === 'Rejected') && order.updated_at ?
                                new Date(order.updated_at).toLocaleString('en-US', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                  hour12: true
                                }) :
                                (order.status === 'Validated' || order.status === 'Rejected') && (order as any).created_at ?
                                  new Date((order as any).created_at).toLocaleString('en-US', {
                                    year: 'numeric',
                                    month: '2-digit',
                                    day: '2-digit',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    second: '2-digit',
                                    hour12: true
                                  }) :
                                  'N/A'
                              }
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Compact Footer with Pagination */}
            <div className={`p-4 border-t ${theme === 'light' ? 'border-slate-200/60' : 'border-cyan-400/30'
              }`}>
              {/* Pagination Controls */}
              {getFilteredAndSortedOrders().length > 0 && (
                <div className="mb-4">
                  <Pagination
                    currentPage={modalCurrentPage}
                    totalPages={Math.ceil(getFilteredAndSortedOrders().length / modalItemsPerPage)}
                    totalItems={getFilteredAndSortedOrders().length}
                    itemsPerPage={modalItemsPerPage}
                    onPageChange={handleModalPageChange}
                    onItemsPerPageChange={handleModalItemsPerPageChange}
                    theme={theme}
                  />
                </div>
              )}

              {/* Footer Info and Close Button */}
              <div className="flex items-center justify-between">
                <div className={`text-xs ${theme === 'light' ? 'text-slate-600' : 'text-slate-400'
                  }`}>
                  {getFilteredAndSortedOrders().length} of {modalOrders.length} {modalType === 'errorlog' ? 'entries' : 'orders'}
                  {searchTerm && (
                    <span className="ml-1">
                      (filtered by "{searchTerm}")
                    </span>
                  )}
                </div>
                <button
                  onClick={closeOrdersModal}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105 ${theme === 'light'
                      ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      : 'bg-slate-700 text-cyan-300 hover:bg-slate-600'
                    }`}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`max-w-sm p-4 rounded-lg shadow-lg border backdrop-blur-md transition-all duration-300 transform ${toast.type === 'success'
                ? theme === 'light'
                  ? 'bg-green-50/90 border-green-200 text-green-800'
                  : 'bg-green-900/90 border-green-400 text-green-200'
                : toast.type === 'error'
                  ? theme === 'light'
                    ? 'bg-red-50/90 border-red-200 text-red-800'
                    : 'bg-red-900/90 border-red-400 text-red-200'
                  : theme === 'light'
                    ? 'bg-blue-50/90 border-blue-200 text-blue-800'
                    : 'bg-blue-900/90 border-blue-400 text-blue-200'
              }`}
          >
            <div className="flex items-center gap-2">
              {toast.type === 'success' && <CheckCircle className="h-5 w-5 flex-shrink-0" />}
              {toast.type === 'error' && <XCircle className="h-5 w-5 flex-shrink-0" />}
              {toast.type === 'info' && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
              <span className="text-sm font-medium">{toast.message}</span>
              <button
                onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
                className={`ml-auto p-1 rounded-full transition-colors ${toast.type === 'success'
                    ? theme === 'light'
                      ? 'hover:bg-green-100 text-green-600'
                      : 'hover:bg-green-800/30 text-green-400'
                    : toast.type === 'error'
                      ? theme === 'light'
                        ? 'hover:bg-red-100 text-red-600'
                        : 'hover:bg-red-800/30 text-red-400'
                      : theme === 'light'
                        ? 'hover:bg-blue-100 text-blue-600'
                        : 'hover:bg-blue-800/30 text-blue-400'
                  }`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Custom Modern Popup */}
      {showCustomPopup && popupData && (
        <div className="custom-popup-overlay animate-in fade-in duration-300">
          {/* Backdrop */}
          <div
            className={`absolute inset-0 backdrop-blur-lg transition-all duration-300 ${theme === 'light'
                ? 'bg-gradient-to-br from-slate-200/30 via-slate-100/40 to-slate-200/30'
                : 'bg-gradient-to-br from-slate-900/20 via-slate-800/30 to-slate-900/20'
              }`}
            onClick={closeCustomPopup}
            style={{ top: 0, left: 0, right: 0, bottom: 0 }}
          />

          {/* Popup Content */}
          <div className={`custom-popup-content w-full max-w-2xl rounded-xl border shadow-2xl transition-all duration-300 transform backdrop-blur-xl animate-in slide-in-from-top-4 fade-in duration-300 ${theme === 'light'
              ? 'bg-white/98 border-slate-200 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)]'
              : 'bg-slate-900/95 border-cyan-400/40 shadow-[0_25px_50px_-12px_rgba(0,255,255,0.25)]'
            }`}>
            {/* Header */}
            <div className={`flex items-center gap-3 p-4 border-b ${theme === 'light' ? 'border-slate-200' : 'border-cyan-400/30'
              }`}>
              <div className={`p-2 rounded-lg ${popupData.type === 'success'
                  ? theme === 'light' ? 'bg-green-100' : 'bg-green-900/30'
                  : popupData.type === 'error'
                    ? theme === 'light' ? 'bg-red-100' : 'bg-red-900/30'
                    : popupData.type === 'warning'
                      ? theme === 'light' ? 'bg-orange-100' : 'bg-orange-900/30'
                      : theme === 'light' ? 'bg-blue-100' : 'bg-blue-900/30'
                }`}>
                {popupData.type === 'success' && (
                  <CheckCircle className={`h-6 w-6 ${theme === 'light' ? 'text-green-600' : 'text-green-400'}`} />
                )}
                {popupData.type === 'error' && (
                  <XCircle className={`h-6 w-6 ${theme === 'light' ? 'text-red-600' : 'text-red-400'}`} />
                )}
                {popupData.type === 'warning' && (
                  <AlertCircle className={`h-6 w-6 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'}`} />
                )}
                {popupData.type === 'info' && (
                  <AlertCircle className={`h-6 w-6 ${theme === 'light' ? 'text-blue-600' : 'text-blue-400'}`} />
                )}
              </div>
              <div className="flex-1">
                <h3 className={`text-lg font-bold ${theme === 'light' ? 'text-slate-800' : 'text-cyan-300'
                  }`}>
                  {popupData.title}
                </h3>
              </div>
              <button
                onClick={closeCustomPopup}
                className={`p-2 rounded-lg transition-all duration-200 hover:scale-110 ${theme === 'light'
                    ? 'hover:bg-slate-100 text-slate-600'
                    : 'hover:bg-slate-700/50 text-cyan-300'
                  }`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              <div className={`text-sm leading-relaxed whitespace-pre-wrap font-mono ${theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                }`}>
                {popupData.message}
              </div>
            </div>

            {/* Footer */}
            <div className={`flex justify-end gap-3 p-4 border-t ${theme === 'light' ? 'border-slate-200 bg-slate-50' : 'border-cyan-400/30 bg-slate-800/50'
              }`}>
              <button
                onClick={() => {
                  if (popupData.onConfirm) {
                    popupData.onConfirm();
                  }
                  closeCustomPopup();
                }}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 hover:scale-105 ${popupData.type === 'success'
                    ? theme === 'light'
                      ? 'bg-green-600 text-white hover:bg-green-700 shadow-md'
                      : 'bg-green-500 text-white hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                    : popupData.type === 'error'
                      ? theme === 'light'
                        ? 'bg-red-600 text-white hover:bg-red-700 shadow-md'
                        : 'bg-red-500 text-white hover:bg-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                      : popupData.type === 'warning'
                        ? theme === 'light'
                          ? 'bg-orange-600 text-white hover:bg-orange-700 shadow-md'
                          : 'bg-orange-500 text-white hover:bg-orange-400 shadow-[0_0_15px_rgba(249,115,22,0.3)]'
                        : theme === 'light'
                          ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md'
                          : 'bg-blue-500 text-white hover:bg-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]'
                  }`}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Details Modal */}
      {showValidationDetails && validationDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowValidationDetails(false)} />
          <div className={`relative w-full max-w-4xl max-h-[90vh] rounded-lg shadow-xl overflow-hidden flex flex-col ${theme === 'light' ? 'bg-white' : 'bg-gray-800'
            }`}>
            {/* Header */}
            <div className={`flex items-center justify-between p-4 border-b flex-shrink-0 ${theme === 'light' ? 'border-gray-200' : 'border-gray-600'
              }`}>
              <h3 className={`text-lg font-bold ${theme === 'light' ? 'text-gray-900' : 'text-white'
                }`}>
                Validation Details
              </h3>
              <button
                onClick={() => setShowValidationDetails(false)}
                className={`p-2 rounded-full hover:bg-opacity-20 ${theme === 'light'
                    ? 'text-gray-500 hover:bg-gray-200'
                    : 'text-gray-400 hover:bg-gray-700'
                  }`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content - Scrollable */}
            <div className="p-4 overflow-y-auto flex-1">
              {/* Overflow Weight Section */}
              {validationDetails.overflow_weight !== undefined && validationDetails.overflow_weight !== null && (
                <div className={`mb-4 p-3 rounded-lg border ${validationDetails.overflow_weight > 0
                    ? theme === 'light' ? 'bg-orange-50 border-orange-200' : 'bg-orange-900/20 border-orange-700'
                    : theme === 'light' ? 'bg-gray-50 border-gray-200' : 'bg-gray-700/30 border-gray-600'
                  }`}>
                  <div className="flex justify-between items-center">
                    <span className={`text-sm font-semibold ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                      }`}>
                      Overflow Weight:
                    </span>
                    <span className={`font-mono text-lg font-bold ${validationDetails.overflow_weight > 0
                        ? theme === 'light' ? 'text-orange-700' : 'text-orange-400'
                        : theme === 'light' ? 'text-gray-600' : 'text-gray-400'
                      }`}>
                      {validationDetails.overflow_weight.toFixed(2)} {validationDetails.order_type === 'MILLING' ? 'TO' : 'BAG'}
                    </span>
                  </div>
                  {validationDetails.overflow_weight > 0 && (
                    <p className={`text-xs mt-1 ${theme === 'light' ? 'text-orange-600' : 'text-orange-400'
                      }`}>
                      ⚠️ Production exceeded target by {validationDetails.overflow_weight.toFixed(2)} {validationDetails.order_type === 'MILLING' ? 'TO' : 'BAG'}
                    </p>
                  )}
                </div>
              )}

              {/* Validation Results Section */}
              {validationDetails.order_type && (
                <div className="mb-4">
                  <h4 className={`text-sm font-semibold mb-3 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                    }`}>
                    Validation Results
                  </h4>
              {validationDetails.order_type === 'MILLING' ? (
                <div className="space-y-3">
                      {validationDetails.f1_production !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>F1 Production:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.f1_production} kg</span>
                  </div>
                      )}
                      {validationDetails.f2_production !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>F2 Production:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.f2_production} kg</span>
                  </div>
                      )}
                      {validationDetails.bran_production !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>Bran Production:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.bran_production} kg</span>
                  </div>
                      )}
                      {validationDetails.total_output !== undefined && (
                  <div className="flex justify-between items-center font-bold border-t pt-2">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-700' : 'text-gray-200'
                      }`}>Total Output:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.total_output} kg</span>
                  </div>
                      )}
                      {validationDetails.input_wheat !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>Input Wheat:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.input_wheat} kg</span>
                  </div>
                      )}
                      {validationDetails.extraction_rate !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-green-600' : 'text-green-400'
                      }`}>Extraction Rate:</span>
                    <span className={`font-mono text-sm font-bold ${theme === 'light' ? 'text-green-700' : 'text-green-300'
                      }`}>{validationDetails.extraction_rate}%</span>
                  </div>
                      )}
                </div>
              ) : (
                <div className="space-y-3">
                      {validationDetails.gross_production !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>Gross Production:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.gross_production} bags</span>
                  </div>
                      )}
                      {validationDetails.damaged_bags !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-red-600' : 'text-red-400'
                      }`}>Damaged Bags:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-red-700' : 'text-red-300'
                      }`}>{validationDetails.damaged_bags} bags</span>
                  </div>
                      )}
                      {validationDetails.net_production !== undefined && (
                  <div className="flex justify-between items-center font-bold border-t pt-2">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-700' : 'text-gray-200'
                      }`}>Net Production:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.net_production} bags</span>
                  </div>
                      )}
                      {validationDetails.quality_rate !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-green-600' : 'text-green-400'
                      }`}>Quality Rate:</span>
                    <span className={`font-mono text-sm font-bold ${theme === 'light' ? 'text-green-700' : 'text-green-300'
                      }`}>{validationDetails.quality_rate}%</span>
                  </div>
                      )}
                      {validationDetails.packing_line !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${theme === 'light' ? 'text-gray-600' : 'text-gray-300'
                      }`}>Packing Line:</span>
                    <span className={`font-mono text-sm ${theme === 'light' ? 'text-gray-900' : 'text-white'
                      }`}>{validationDetails.packing_line}</span>
                  </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* SAP Payload Section */}
              {validationDetails.sap_payload && (
                <div className="mt-6">
                  <h4 className={`text-sm font-semibold mb-3 ${theme === 'light' ? 'text-gray-700' : 'text-gray-300'
                    }`}>
                    SAP Confirmation Payload
                  </h4>
                  <div className={`p-4 rounded-lg border overflow-x-auto ${theme === 'light' ? 'bg-gray-50 border-gray-200' : 'bg-gray-900/50 border-gray-600'
                    }`}>
                    <pre className={`text-xs font-mono whitespace-pre-wrap ${theme === 'light' ? 'text-gray-800' : 'text-gray-200'
                      }`}>
                      {JSON.stringify(validationDetails.sap_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className={`flex justify-end p-4 border-t flex-shrink-0 ${theme === 'light' ? 'border-gray-200 bg-gray-50' : 'border-gray-600 bg-gray-700'
              }`}>
              <button
                onClick={() => setShowValidationDetails(false)}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${theme === 'light'
                    ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                    : 'bg-gray-600 text-white hover:bg-gray-500'
                  }`}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </WaterSystemLayout>
  );
};

export default ProcessOrderValidation;
