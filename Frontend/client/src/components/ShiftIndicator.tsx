import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { Clock, Factory, Package } from 'lucide-react';
import { shiftApi, ShiftMaster } from '../lib/api';

interface ShiftIndicatorProps {
  operation: 'milling' | 'packing';
  className?: string;
  plant?: string; // Optional plant code, defaults to '3130' for milling, others for packing
}

const ShiftIndicator: React.FC<ShiftIndicatorProps> = ({ operation, className = '', plant }) => {
  const { theme } = useTheme();
  const [shifts, setShifts] = useState<ShiftMaster[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentShift, setCurrentShift] = useState<{ shift: string; start: string; end: string } | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  // Determine plant and department
  const plantCode = plant || (operation === 'milling' ? '3130' : '3131');
  const department = operation === 'milling' ? 'MILLING' : 'PACKING';

  // Fetch shifts from database
  useEffect(() => {
    const fetchShifts = async () => {
      try {
        setLoading(true);
        const allShifts = await shiftApi.getShifts();
        // Filter shifts by plant and department
        const filteredShifts = allShifts.filter(
          s => s.plant === plantCode && s.department === department
        ).sort((a, b) => a.sort_order - b.sort_order);
        setShifts(filteredShifts);
      } catch (error) {
        console.error('Error fetching shifts:', error);
        setShifts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchShifts();
    // Refresh every minute to update time remaining
    const interval = setInterval(fetchShifts, 60000);
    return () => clearInterval(interval);
  }, [plantCode, department]);

  // Calculate current shift and time remaining - updates every second
  useEffect(() => {
    if (shifts.length === 0) {
      setCurrentShift(null);
      setTimeRemaining('');
      return;
    }

    const calculateShift = () => {
      const now = new Date();
      const currentHour = now.getHours();
      const currentMinute = now.getMinutes();
      const currentTime = currentHour * 60 + currentMinute;

      // Find current shift
      let foundShift: ShiftMaster | null = null;
      for (const shift of shifts) {
        const [startHour, startMin] = shift.start_time.split(':').map(Number);
        const [endHour, endMin] = shift.end_time.split(':').map(Number);
        const startMinutes = startHour * 60 + startMin;
        const endMinutes = endHour * 60 + endMin;

        // Handle same-day shift
        if (startMinutes < endMinutes) {
          if (currentTime >= startMinutes && currentTime < endMinutes) {
            foundShift = shift;
            break;
          }
        } else {
          // Handle overnight shift
          if (currentTime >= startMinutes || currentTime < endMinutes) {
            foundShift = shift;
            break;
          }
        }
      }

      if (foundShift) {
        const [startHour, startMin] = foundShift.start_time.split(':').map(Number);
        const [endHour, endMin] = foundShift.end_time.split(':').map(Number);
        const startMinutes = startHour * 60 + startMin;
        const endMinutes = endHour * 60 + endMin;

        // Format times for display
        const startTime = formatTime(foundShift.start_time);
        const endTime = formatTime(foundShift.end_time);

        setCurrentShift({
          shift: foundShift.shift_code,
          start: startTime,
          end: endTime
        });

        // Calculate time remaining
        let remainingMinutes = 0;
        
        if (endMinutes < startMinutes) {
          // Overnight shift (e.g., 23:00 to 07:00)
          if (currentTime >= startMinutes) {
            // We're in the first part of the shift (before midnight)
            // End time is tomorrow, so add 24 hours
            remainingMinutes = (endMinutes + 24 * 60) - currentTime;
          } else if (currentTime < endMinutes) {
            // We're in the second part of the shift (after midnight, before end time)
            // End time is today, so no need to add 24 hours
            remainingMinutes = endMinutes - currentTime;
          } else {
            // Should not happen if shift detection is correct, but handle gracefully
            remainingMinutes = 0;
          }
        } else {
          // Same-day shift
          remainingMinutes = endMinutes - currentTime;
        }

        // Ensure non-negative
        if (remainingMinutes < 0) {
          remainingMinutes = 0;
        }

        const hours = Math.floor(remainingMinutes / 60);
        const minutes = remainingMinutes % 60;
        setTimeRemaining(`${hours}h ${minutes}m`);
      } else {
        setCurrentShift(null);
        setTimeRemaining('');
      }
    };

    // Calculate immediately
    calculateShift();
    
    // Update every second for real-time countdown
    const interval = setInterval(calculateShift, 1000);
    return () => clearInterval(interval);
  }, [shifts]);

  // Helper to format time (HH:MM) to 12-hour format
  const formatTime = (timeStr: string): string => {
    const [hour, minute] = timeStr.split(':').map(Number);
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}:${minute.toString().padStart(2, '0')} ${period}`;
  };

  // Get all shift details for tooltip
  const getAllShiftDetails = () => {
    return shifts.map(shift => ({
      shift: shift.shift_code,
      start: formatTime(shift.start_time),
      end: formatTime(shift.end_time),
      duration: calculateDuration(shift.start_time, shift.end_time)
    }));
  };

  // Calculate duration between start and end times
  const calculateDuration = (start: string, end: string): string => {
    const [startHour, startMin] = start.split(':').map(Number);
    const [endHour, endMin] = end.split(':').map(Number);
    const startMinutes = startHour * 60 + startMin;
    let endMinutes = endHour * 60 + endMin;
    
    if (endMinutes < startMinutes) {
      endMinutes += 24 * 60; // Overnight shift
    }
    
    const durationMinutes = endMinutes - startMinutes;
    const hours = Math.floor(durationMinutes / 60);
    return `${hours} hours`;
  };

  const allShifts = getAllShiftDetails();
  const Icon = operation === 'milling' ? Factory : Package;

  // Don't render if no shifts found or loading
  if (loading || shifts.length === 0 || !currentShift) {
    return null;
  }

  return (
    <div className="relative group">
      <div className={`inline-flex items-center gap-2.5 px-4 py-2 rounded-full border transition-all duration-300 cursor-help ${className} ${
        theme === 'light' 
          ? 'bg-white/80 border-slate-200/40 hover:bg-white/90' 
          : 'bg-slate-800/80 border-slate-600/40 hover:bg-slate-800/90'
      }`}>
        <Icon className={`h-5 w-5 ${
          theme === 'light' ? 'text-slate-500' : 'text-slate-400'
        }`} />
        
        <span className={`text-sm font-medium ${
          theme === 'light' ? 'text-slate-600' : 'text-slate-300'
        }`}>
          {operation === 'milling' ? 'Mill' : 'Pack'}
        </span>
        
        <span className={`px-2 py-1 rounded-full text-sm font-bold ${
          currentShift.shift === 'A'
            ? theme === 'light' ? 'bg-green-500 text-white' : 'bg-green-400 text-slate-900'
            : currentShift.shift === 'B'
            ? theme === 'light' ? 'bg-cyan-500 text-white' : 'bg-cyan-400 text-slate-900'
            : theme === 'light' ? 'bg-orange-500 text-white' : 'bg-orange-400 text-slate-900'
        }`}>
          {currentShift.shift}
        </span>
        
        <span className={`text-sm font-mono ${
          theme === 'light' ? 'text-slate-500' : 'text-slate-400'
        }`}>
          {timeRemaining}
        </span>
      </div>

      {/* Tooltip */}
      <div className={`absolute top-full left-1/2 transform -translate-x-1/2 mt-2 px-3 py-2 rounded-lg shadow-lg border z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap ${
        theme === 'light' 
          ? 'bg-white border-slate-200 text-slate-800' 
          : 'bg-slate-800 border-slate-600 text-slate-200'
      }`}>
        <div className="text-xs font-semibold mb-1">
          {operation === 'milling' ? 'Milling' : 'Packing'} Shift Schedule
        </div>
        
        <div className="space-y-1">
          {allShifts.map((shift) => (
            <div key={shift.shift} className={`flex items-center gap-2 ${
              shift.shift === currentShift.shift ? 'font-bold' : ''
            }`}>
              <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                shift.shift === 'A'
                  ? theme === 'light' ? 'bg-green-100 text-green-700' : 'bg-green-900/30 text-green-300'
                  : shift.shift === 'B'
                  ? theme === 'light' ? 'bg-cyan-100 text-cyan-700' : 'bg-cyan-900/30 text-cyan-300'
                  : theme === 'light' ? 'bg-orange-100 text-orange-700' : 'bg-orange-900/30 text-orange-300'
              }`}>
                {shift.shift}
              </span>
              <span className="text-xs">
                {shift.start} - {shift.end}
              </span>
            </div>
          ))}
        </div>
        
        <div className={`mt-2 pt-2 border-t ${
          theme === 'light' ? 'border-slate-200' : 'border-slate-600'
        }`}>
          <div className="text-xs font-medium">
            Current: Shift {currentShift.shift} ({timeRemaining} remaining)
          </div>
        </div>
      </div>
    </div>
  );
};

export default ShiftIndicator;
