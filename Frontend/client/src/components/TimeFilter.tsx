import React, { useState, useEffect, useRef } from 'react';
import { Calendar } from '@/components/ui/calendar';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CalendarIcon, ChevronDown, X, Clock } from 'lucide-react';
import { format, startOfMonth, startOfDay, subDays, subMonths } from 'date-fns';
import { cn } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export interface TimeFilterProps {
  onApply: (filters: {
    mode: 'single' | 'range';
    date?: string;
    startDate?: string;
    endDate?: string;
    shifts?: string[];
    timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
  }) => void;
  initialValues?: {
    mode?: 'single' | 'range';
    date?: string;
    startDate?: string;
    endDate?: string;
    shifts?: string[];
    timeRange?: 'daily' | 'weekly' | 'monthly' | 'range';
  };
  hideShifts?: boolean;
}

const SHIFT_OPTIONS = ['A', 'B', 'C'];

// Custom Checkbox wrapper for light mode visibility
const LightModeCheckbox = ({ 
  id, 
  checked, 
  onCheckedChange, 
  theme 
}: { 
  id: string; 
  checked: boolean; 
  onCheckedChange: (checked: boolean) => void;
  theme: 'light' | 'dark';
}) => {
  return (
    <>
      <Checkbox
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        className={cn(
          'time-filter-checkbox',
          theme === 'light'
            ? checked
              ? '!bg-blue-600 !border-blue-600'
              : 'border-slate-300 bg-white'
            : ''
        )}
        style={
          theme === 'light' && checked
            ? { 
                backgroundColor: '#2563eb', 
                borderColor: '#2563eb',
                color: '#ffffff',
                '--primary': '#2563eb',
                '--primary-foreground': '#ffffff'
              } as React.CSSProperties
            : undefined
        }
      />
      {theme === 'light' && (
        <style>{`
          #${id}[data-state="checked"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
          }
          #${id}[data-state="checked"] > span {
            color: #ffffff !important;
            display: flex !important;
            opacity: 1 !important;
            visibility: visible !important;
          }
          #${id}[data-state="checked"] span {
            color: #ffffff !important;
          }
          #${id}[data-state="checked"] svg {
            stroke: #ffffff !important;
            color: #ffffff !important;
            opacity: 1 !important;
            visibility: visible !important;
            display: block !important;
          }
          #${id}[data-state="checked"] path {
            stroke: #ffffff !important;
            stroke-width: 3 !important;
            opacity: 1 !important;
            visibility: visible !important;
          }
          #${id}[data-state="checked"] * {
            color: #ffffff !important;
          }
        `}</style>
      )}
    </>
  );
};

export function TimeFilter({ onApply, initialValues, hideShifts = false }: TimeFilterProps) {
  const { theme } = useTheme();
  
  // Mode state
  const [mode, setMode] = useState<'single' | 'range'>(
    initialValues?.mode || 'single'
  );

  // Date states
  const [date, setDate] = useState<Date | undefined>(
    initialValues?.date ? new Date(initialValues.date) : new Date()
  );
  const [startDate, setStartDate] = useState<Date | undefined>(
    initialValues?.startDate ? new Date(initialValues.startDate) : undefined
  );
  const [endDate, setEndDate] = useState<Date | undefined>(
    initialValues?.endDate ? new Date(initialValues.endDate) : undefined
  );

  // Time states for start and end dates
  const [startTime, setStartTime] = useState<string>(() => {
    if (initialValues?.startDate) {
      const date = new Date(initialValues.startDate);
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    }
    return '00:00';
  });
  const [endTime, setEndTime] = useState<string>(() => {
    if (initialValues?.endDate) {
      const date = new Date(initialValues.endDate);
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    }
    return '23:59';
  });

  // Time state for daily period
  const [dailyTime, setDailyTime] = useState<string>(() => {
    if (initialValues?.date) {
      const date = new Date(initialValues.date);
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    }
    return '00:00';
  });

  // Shift states
  const [selectedShifts, setSelectedShifts] = useState<string[]>(
    initialValues?.shifts || SHIFT_OPTIONS
  );

  // Period selector (Daily/Weekly/Monthly/Date Range)
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly' | 'range'>(
    initialValues?.timeRange || 'daily'
  );

  // Month selector for Monthly period
  const [selectedMonth, setSelectedMonth] = useState<Date>(
    initialValues?.startDate ? new Date(initialValues.startDate) : new Date()
  );

  // Popover states
  const [datePopoverOpen, setDatePopoverOpen] = useState(false);
  const [shiftPopoverOpen, setShiftPopoverOpen] = useState(false);
  const [monthPopoverOpen, setMonthPopoverOpen] = useState(false);
  const [startDateTimePopoverOpen, setStartDateTimePopoverOpen] = useState(false);
  const [endDateTimePopoverOpen, setEndDateTimePopoverOpen] = useState(false);

  // Initialize dates based on period (only on mount)
  useEffect(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Normalize to start of day (12:00 AM)
    
    // If initial values provided, use them
    if (initialValues?.timeRange) {
      setPeriod(initialValues.timeRange);
      if (initialValues.timeRange === 'monthly' && initialValues.startDate) {
        setSelectedMonth(new Date(initialValues.startDate));
      }
      return; // Don't override with defaults if initial values exist
    }
    
    // Otherwise set defaults based on current period
    if (period === 'daily') {
      // Daily: from 12:00 AM to current time
      setDate(today);
      setDailyTime('00:00');
      setMode('single');
      } else if (period === 'weekly') {
        // Weekly: last 7 days
        const sevenDaysAgo = subDays(today, 6); // Include today, so 6 days ago
        setStartDate(sevenDaysAgo);
        setEndDate(today);
        setMode('range');
        setStartTime('00:00');
        setEndTime('23:59');
      } else if (period === 'monthly') {
        // Monthly: from 1st of current month
        const firstOfMonth = startOfMonth(today);
        setStartDate(firstOfMonth);
        setEndDate(today);
        setSelectedMonth(today);
        setMode('range');
        setStartTime('00:00');
        setEndTime('23:59');
      } else if (period === 'range') {
        // Date Range: user will select
        setMode('range');
        setStartTime('00:00');
        setEndTime('23:59');
      }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update dates when period changes
  useEffect(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (period === 'daily') {
      setMode('single');
      setDate(today);
      setDailyTime('00:00');
      setStartDate(undefined);
      setEndDate(undefined);
    } else if (period === 'weekly') {
      setMode('range');
      const sevenDaysAgo = subDays(today, 6);
      setStartDate(sevenDaysAgo);
      setEndDate(today);
      setDate(undefined);
      setStartTime('00:00');
      setEndTime('23:59');
    } else if (period === 'monthly') {
      setMode('range');
      const firstOfMonth = startOfMonth(selectedMonth);
      setStartDate(firstOfMonth);
      // If selected month is current month, end date is today, otherwise end of that month
      if (selectedMonth.getMonth() === today.getMonth() && selectedMonth.getFullYear() === today.getFullYear()) {
        setEndDate(today);
      } else {
        const endOfMonth = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1, 0);
        setEndDate(endOfMonth);
      }
      setDate(undefined);
      setStartTime('00:00');
      setEndTime('23:59');
    } else if (period === 'range') {
      setMode('range');
      setDate(undefined);
      if (!startDate || !endDate) {
        const sevenDaysAgo = subDays(today, 6);
        setStartDate(sevenDaysAgo);
        setEndDate(today);
        setStartTime('00:00');
        setEndTime('23:59');
      }
    }
  }, [period]);

  // Update monthly dates when selectedMonth changes (only if period is monthly)
  useEffect(() => {
    if (period === 'monthly') {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const firstOfMonth = startOfMonth(selectedMonth);
      setStartDate(firstOfMonth);
      // If selected month is current month, end date is today, otherwise end of that month
      if (selectedMonth.getMonth() === today.getMonth() && selectedMonth.getFullYear() === today.getFullYear()) {
        setEndDate(today);
      } else {
        const endOfMonth = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1, 0);
        setEndDate(endOfMonth);
      }
    }
  }, [selectedMonth, period]);

  // Handle shift toggle
  const toggleShift = (shift: string) => {
    setSelectedShifts((prev) =>
      prev.includes(shift)
        ? prev.filter((s) => s !== shift)
        : [...prev, shift]
    );
  };

  // Handle apply filters
  const handleApply = () => {
    if (!hideShifts && selectedShifts.length === 0) {
      // At least one shift must be selected (only if shifts are shown)
      return;
    }

    if (mode === 'single') {
      if (!date) return;
      // Combine date with time for daily period
      const dateTime = combineDateAndTime(date, dailyTime);
      if (!dateTime) return;
      onApply({
        mode: 'single',
        date: format(dateTime, 'yyyy-MM-dd HH:mm:ss'),
        shifts: hideShifts ? [] : selectedShifts,
        timeRange: period,
      });
    } else {
      if (!startDate || !endDate) return;
      
      // Combine dates with times
      const startDateTime = combineDateAndTime(startDate, startTime);
      const endDateTime = combineDateAndTime(endDate, endTime);
      
      if (!startDateTime || !endDateTime) return;
      
      // Validate end date/time is not before start date/time
      if (endDateTime < startDateTime) {
        return;
      }
      
      onApply({
        mode: 'range',
        startDate: format(startDateTime, 'yyyy-MM-dd HH:mm:ss'),
        endDate: format(endDateTime, 'yyyy-MM-dd HH:mm:ss'),
        shifts: hideShifts ? [] : selectedShifts,
        timeRange: period,
      });
    }
  };

  // Handle clear/reset
  const handleClear = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Reset to default based on period
    if (period === 'daily') {
      setDate(today);
      setDailyTime('00:00');
    } else if (period === 'weekly') {
      const sevenDaysAgo = subDays(today, 6);
      setStartDate(sevenDaysAgo);
      setEndDate(today);
      setStartTime('00:00');
      setEndTime('23:59');
    } else if (period === 'monthly') {
      const firstOfMonth = startOfMonth(today);
      setStartDate(firstOfMonth);
      setEndDate(today);
      setSelectedMonth(today);
      setStartTime('00:00');
      setEndTime('23:59');
    } else if (period === 'range') {
      const sevenDaysAgo = subDays(today, 6);
      setStartDate(sevenDaysAgo);
      setEndDate(today);
      setStartTime('00:00');
      setEndTime('23:59');
    }
    
    setSelectedShifts(SHIFT_OPTIONS);
  };

  // Format date for display (with time if provided)
  const formatDateDisplay = (date: Date | undefined, time?: string): string => {
    if (!date) return 'Select date';
    const dateStr = format(date, 'dd-MM-yyyy');
    if (time) {
      return `${dateStr} ${time}`;
    }
    return dateStr;
  };

  // Helper to combine date and time into a Date object
  const combineDateAndTime = (date: Date | undefined, time: string): Date | undefined => {
    if (!date) return undefined;
    const [hours, minutes] = time.split(':').map(Number);
    const combined = new Date(date);
    combined.setHours(hours, minutes, 0, 0);
    return combined;
  };

  // Helper to format datetime for datetime-local input (YYYY-MM-DDTHH:mm)
  const formatDateTimeLocal = (date: Date | undefined, time: string): string => {
    if (!date) return '';
    const [hours, minutes] = time.split(':').map(Number);
    const combined = new Date(date);
    combined.setHours(hours, minutes, 0, 0);
    const year = combined.getFullYear();
    const month = String(combined.getMonth() + 1).padStart(2, '0');
    const day = String(combined.getDate()).padStart(2, '0');
    const hoursStr = String(combined.getHours()).padStart(2, '0');
    const minutesStr = String(combined.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hoursStr}:${minutesStr}`;
  };

  // Helper to parse datetime-local value back to date and time
  const parseDateTimeLocal = (value: string): { date: Date; time: string } | null => {
    if (!value) return null;
    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) return null;
      const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
      return { date, time };
    } catch {
      return null;
    }
  };

  // Get shift display text
  const getShiftDisplayText = (): string => {
    if (selectedShifts.length === 0) return 'Select shifts';
    if (selectedShifts.length === SHIFT_OPTIONS.length) return 'All Shifts';
    return selectedShifts.sort().join(', ');
  };

  // Format time for display (HH:mm to 12-hour format)
  const formatTimeDisplay = (time: string): string => {
    if (!time) return '00:00';
    const [hours, minutes] = time.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
    return `${String(displayHours).padStart(2, '0')}:${String(minutes).padStart(2, '0')} ${period}`;
  };

  // Parse time from 12-hour format to 24-hour format
  const parseTimeTo24Hour = (hours: number, minutes: number, period: 'AM' | 'PM'): string => {
    let hour24 = hours;
    if (period === 'AM' && hours === 12) {
      hour24 = 0;
    } else if (period === 'PM' && hours !== 12) {
      hour24 = hours + 12;
    }
    return `${String(hour24).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  };

  // Generate time options (30-minute intervals)
  const generateTimeOptions = (): string[] => {
    const options: string[] = [];
    for (let hour = 0; hour < 24; hour++) {
      for (let minute = 0; minute < 60; minute += 30) {
        const time24 = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
        options.push(time24);
      }
    }
    return options;
  };

  // Time Picker Component (detailed picker for custom time)
  const TimePicker = ({ 
    value, 
    onChange, 
    id 
  }: { 
    value: string; 
    onChange: (time: string) => void;
    id: string;
  }) => {
    const hoursRef = useRef<HTMLDivElement>(null);
    const minutesRef = useRef<HTMLDivElement>(null);
    const periodRef = useRef<HTMLDivElement>(null);

    const [hours, minutes] = value.split(':').map(Number);
    const period: 'AM' | 'PM' = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;

    // Scroll to selected values on mount
    useEffect(() => {
      if (hoursRef.current) {
        const selectedHour = hoursRef.current.querySelector(`[data-hour="${displayHours}"]`);
        selectedHour?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
      if (minutesRef.current) {
        const selectedMinute = minutesRef.current.querySelector(`[data-minute="${minutes}"]`);
        selectedMinute?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
      if (periodRef.current) {
        const selectedPeriod = periodRef.current.querySelector(`[data-period="${period}"]`);
        selectedPeriod?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }, [displayHours, minutes, period]);

    const handleHoursChange = (newHours: number) => {
      onChange(parseTimeTo24Hour(newHours, minutes, period));
    };

    const handleMinutesChange = (newMinutes: number) => {
      onChange(parseTimeTo24Hour(displayHours, newMinutes, period));
    };

    const handlePeriodChange = (newPeriod: 'AM' | 'PM') => {
      onChange(parseTimeTo24Hour(displayHours, minutes, newPeriod));
    };

    return (
      <div className={cn(
        'flex flex-col gap-2',
        theme === 'light' ? 'bg-white' : 'bg-slate-800'
      )}>
        <div className={cn(
          'text-xs font-medium mb-1',
          theme === 'light' ? 'text-slate-700' : 'text-slate-300'
        )}>
          Time:
        </div>
        <div className={cn(
          'flex items-center gap-1 px-2 py-1.5 rounded-md border text-xs',
          theme === 'light'
            ? 'bg-white border-slate-300 text-slate-900'
            : 'bg-slate-800 border-slate-700 text-slate-200'
        )}>
          <Clock className={cn(
            'h-3.5 w-3.5 mr-1',
            theme === 'light' ? 'text-slate-600' : 'text-slate-400'
          )} />
          <span className={cn(
            theme === 'light' ? 'text-slate-900' : 'text-slate-200'
          )}>
            {formatTimeDisplay(value)}
          </span>
        </div>
        <div className="flex gap-2">
          {/* Hours */}
          <div className="flex flex-col items-center">
            <div className={cn(
              'text-[10px] font-medium mb-1',
              theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            )}>
              Hours
            </div>
            <div 
              ref={hoursRef}
              className={cn(
                'w-12 h-32 overflow-y-auto rounded-md border',
                theme === 'light'
                  ? 'bg-slate-50 border-slate-300'
                  : 'bg-slate-900 border-slate-700',
                'scrollbar-thin scrollbar-thumb-slate-400 scrollbar-track-transparent'
              )}
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: theme === 'light' ? '#94a3b8 transparent' : '#64748b transparent'
              }}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((hour) => (
                <div
                  key={hour}
                  data-hour={hour}
                  onClick={() => handleHoursChange(hour)}
                  className={cn(
                    'px-2 py-1 text-xs text-center cursor-pointer transition-colors',
                    displayHours === hour
                      ? theme === 'light'
                        ? 'bg-blue-600 !text-white font-semibold'
                        : 'bg-cyan-500 !text-white font-semibold'
                      : theme === 'light'
                        ? 'hover:bg-slate-200 text-slate-900'
                        : 'hover:bg-slate-700 text-slate-200'
                  )}
                  style={displayHours === hour ? { color: '#ffffff' } : undefined}
                >
                  {String(hour).padStart(2, '0')}
                </div>
              ))}
            </div>
          </div>

          {/* Minutes */}
          <div className="flex flex-col items-center">
            <div className={cn(
              'text-[10px] font-medium mb-1',
              theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            )}>
              Minutes
            </div>
            <div 
              ref={minutesRef}
              className={cn(
                'w-12 h-32 overflow-y-auto rounded-md border',
                theme === 'light'
                  ? 'bg-slate-50 border-slate-300'
                  : 'bg-slate-900 border-slate-700',
                'scrollbar-thin scrollbar-thumb-slate-400 scrollbar-track-transparent'
              )}
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: theme === 'light' ? '#94a3b8 transparent' : '#64748b transparent'
              }}
            >
              {Array.from({ length: 60 }, (_, i) => i).map((minute) => (
                <div
                  key={minute}
                  data-minute={minute}
                  onClick={() => handleMinutesChange(minute)}
                  className={cn(
                    'px-2 py-1 text-xs text-center cursor-pointer transition-colors',
                    minutes === minute
                      ? theme === 'light'
                        ? 'bg-blue-600 !text-white font-semibold'
                        : 'bg-cyan-500 !text-white font-semibold'
                      : theme === 'light'
                        ? 'hover:bg-slate-200 text-slate-900'
                        : 'hover:bg-slate-700 text-slate-200'
                  )}
                  style={minutes === minute ? { color: '#ffffff' } : undefined}
                >
                  {String(minute).padStart(2, '0')}
                </div>
              ))}
            </div>
          </div>

          {/* AM/PM */}
          <div className="flex flex-col items-center">
            <div className={cn(
              'text-[10px] font-medium mb-1',
              theme === 'light' ? 'text-slate-600' : 'text-slate-400'
            )}>
              Period
            </div>
            <div 
              ref={periodRef}
              className={cn(
                'w-12 h-32 overflow-y-auto rounded-md border',
                theme === 'light'
                  ? 'bg-slate-50 border-slate-300'
                  : 'bg-slate-900 border-slate-700',
                'scrollbar-thin scrollbar-thumb-slate-400 scrollbar-track-transparent'
              )}
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: theme === 'light' ? '#94a3b8 transparent' : '#64748b transparent'
              }}
            >
              {(['AM', 'PM'] as const).map((p) => (
                <div
                  key={p}
                  data-period={p}
                  onClick={() => handlePeriodChange(p)}
                  className={cn(
                    'px-2 py-1 text-xs text-center cursor-pointer transition-colors',
                    period === p
                      ? theme === 'light'
                        ? 'bg-blue-600 !text-white font-semibold'
                        : 'bg-cyan-500 !text-white font-semibold'
                      : theme === 'light'
                        ? 'hover:bg-slate-200 text-slate-900'
                        : 'hover:bg-slate-700 text-slate-200'
                  )}
                  style={period === p ? { color: '#ffffff' } : undefined}
                >
                  {p}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Teams-style Time Dropdown Component
  const TimeDropdown = ({
    value,
    onChange,
    id,
    label
  }: {
    value: string;
    onChange: (time: string) => void;
    id: string;
    label?: string;
  }) => {
    const [popoverOpen, setPopoverOpen] = useState(false);
    const [showCustomPicker, setShowCustomPicker] = useState(false);
    const timeOptions = generateTimeOptions();
    const currentTimeDisplay = formatTimeDisplay(value);
    const isCustomTime = !timeOptions.includes(value);

    return (
      <Popover open={popoverOpen} onOpenChange={(open) => {
        setPopoverOpen(open);
        if (!open) {
          setShowCustomPicker(false);
        }
      }}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            size="sm"
            className={cn(
              'h-8 w-[120px] justify-between text-left font-normal text-xs',
              theme === 'light'
                ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
            )}
          >
            <div className="flex items-center gap-1.5 flex-1 min-w-0">
              <Clock className={cn(
                'h-3.5 w-3.5 flex-shrink-0',
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              )} />
              <span className={cn(
                'truncate',
                theme === 'light' ? 'text-slate-900' : 'text-slate-200'
              )}>
                {currentTimeDisplay}
              </span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 opacity-50 flex-shrink-0" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className={cn(
            showCustomPicker ? 'w-auto p-3' : 'w-[140px] p-0',
            theme === 'light'
              ? 'bg-white border-slate-300'
              : 'bg-slate-800 border-slate-700'
          )}
          align="start"
        >
          {showCustomPicker ? (
            <TimePicker
              value={value}
              onChange={(time) => {
                onChange(time);
                setPopoverOpen(false);
                setShowCustomPicker(false);
              }}
              id={`${id}-custom`}
            />
          ) : (
            <div 
              className="max-h-[200px] overflow-y-auto time-dropdown-scroll"
            >
              {timeOptions.map((time) => {
                const timeDisplay = formatTimeDisplay(time);
                const isSelected = value === time;
                return (
                  <div
                    key={time}
                    onClick={() => {
                      onChange(time);
                      setPopoverOpen(false);
                    }}
                    className={cn(
                      'px-3 py-2 text-xs cursor-pointer transition-colors',
                      isSelected
                        ? theme === 'light'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'bg-cyan-900/50 text-cyan-300 font-medium'
                        : theme === 'light'
                          ? 'hover:bg-slate-100 text-slate-900'
                          : 'hover:bg-slate-700 text-slate-200'
                    )}
                  >
                    {timeDisplay}
                  </div>
                );
              })}
              <div
                onClick={() => {
                  setShowCustomPicker(true);
                }}
                className={cn(
                  'px-3 py-2 text-xs cursor-pointer transition-colors border-t',
                  theme === 'light'
                    ? 'border-slate-200 hover:bg-slate-100 text-slate-900'
                    : 'border-slate-700 hover:bg-slate-700 text-slate-200'
                )}
              >
                Custom
              </div>
            </div>
          )}
        </PopoverContent>
      </Popover>
    );
  };

  return (
    <>
      {/* Force checkbox checked state visibility in light mode */}
      {theme === 'light' && (
        <style>{`
          .time-filter-checkbox[data-state="checked"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
            --primary: #2563eb !important;
            --primary-foreground: #ffffff !important;
            color: #ffffff !important;
          }
          
          /* Ensure time field text is visible in light mode */
          #start-time, #end-time {
            color: #0f172a !important;
          }
          #start-time span, #end-time span {
            color: #0f172a !important;
          }
          #start-time svg, #end-time svg {
            color: #475569 !important;
          }
          
          /* Ensure selected time picker items have white text in light mode */
          [data-hour][style*="color: rgb(255, 255, 255)"],
          [data-minute][style*="color: rgb(255, 255, 255)"],
          [data-period][style*="color: rgb(255, 255, 255)"] {
            color: #ffffff !important;
          }
          .bg-blue-600.text-white,
          .bg-blue-600 .text-white,
          .bg-blue-600[class*="text-white"] {
            color: #ffffff !important;
          }
          .bg-blue-600 * {
            color: #ffffff !important;
          }
          
          /* Radio button styling for light mode */
          [data-radix-radio-group-item] {
            border-color: #94a3b8 !important;
          }
          
          [data-radix-radio-group-item][data-state="checked"] {
            border-color: #2563eb !important;
          }
          
          [data-radix-radio-group-item][data-state="checked"] [data-radix-radio-group-indicator] {
            background-color: #2563eb !important;
          }
          
          [data-radix-radio-group-item][data-state="checked"] [data-radix-radio-group-indicator] circle {
            fill: #ffffff !important;
          }
          .time-filter-checkbox[data-state="checked"] [data-radix-checkbox-indicator] {
            color: #ffffff !important;
            display: flex !important;
            opacity: 1 !important;
            visibility: visible !important;
          }
          .time-filter-checkbox[data-state="checked"] > span {
            color: #ffffff !important;
            display: flex !important;
            opacity: 1 !important;
            visibility: visible !important;
          }
          .time-filter-checkbox[data-state="checked"] span {
            color: #ffffff !important;
          }
          .time-filter-checkbox[data-state="checked"] svg {
            color: #ffffff !important;
            stroke: #ffffff !important;
            fill: none !important;
            stroke-width: 3 !important;
            display: block !important;
            opacity: 1 !important;
            visibility: visible !important;
            width: 16px !important;
            height: 16px !important;
          }
          .time-filter-checkbox[data-state="checked"] svg path {
            stroke: #ffffff !important;
            fill: none !important;
            stroke-width: 3 !important;
            opacity: 1 !important;
            visibility: visible !important;
            stroke-linecap: round !important;
            stroke-linejoin: round !important;
          }
          .time-filter-checkbox[data-state="checked"] svg * {
            stroke: #ffffff !important;
            fill: none !important;
          }
          .time-filter-checkbox[data-state="checked"] [class*="lucide"] {
            color: #ffffff !important;
            stroke: #ffffff !important;
          }
          .time-filter-checkbox[data-state="checked"] * {
            color: #ffffff !important;
          }
          /* Force white checkmark for all checked checkboxes in light mode */
          :root.light .time-filter-checkbox[data-state="checked"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
          }
          :root.light .time-filter-checkbox[data-state="checked"] svg {
            stroke: #ffffff !important;
            color: #ffffff !important;
          }
          :root.light .time-filter-checkbox[data-state="checked"] path {
            stroke: #ffffff !important;
          }
          
          /* Hide scrollbar for time dropdown */
          .time-dropdown-scroll::-webkit-scrollbar {
            display: none;
          }
          .time-dropdown-scroll {
            -ms-overflow-style: none;
            scrollbar-width: none;
          }
        `}</style>
      )}
      
      {/* Global style for hiding scrollbars in time dropdown */}
      <style>{`
        .time-dropdown-scroll::-webkit-scrollbar {
          display: none;
        }
        .time-dropdown-scroll {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
      
      
      <div className={cn(
        'w-full p-3 rounded-lg backdrop-blur-sm',
        theme === 'light'
          ? 'bg-white border border-slate-200 shadow-sm'
          : 'bg-slate-900/50 border border-slate-700/30'
      )}>
        {/* Single Row Layout */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Period Selector (Radio Buttons) */}
        <div className="flex items-center gap-3">
          <Label className={cn(
            'text-xs font-medium whitespace-nowrap',
            theme === 'light' ? 'text-slate-700' : 'text-slate-300'
          )}>
            Period:
          </Label>
          <RadioGroup
            value={period}
            onValueChange={(value: 'daily' | 'weekly' | 'monthly' | 'range') => setPeriod(value)}
            className="flex items-center gap-3"
          >
            <div className="flex items-center gap-1.5">
              <RadioGroupItem value="daily" id="period-daily" className={cn(
                theme === 'light'
                  ? 'border-slate-400 text-blue-600'
                  : 'border-slate-500 text-cyan-400'
              )} />
              <Label
                htmlFor="period-daily"
                className={cn(
                  'text-xs font-normal cursor-pointer',
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                )}
              >
                Daily
              </Label>
            </div>
            <div className="flex items-center gap-1.5">
              <RadioGroupItem value="weekly" id="period-weekly" className={cn(
                theme === 'light'
                  ? 'border-slate-400 text-blue-600'
                  : 'border-slate-500 text-cyan-400'
              )} />
              <Label
                htmlFor="period-weekly"
                className={cn(
                  'text-xs font-normal cursor-pointer',
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                )}
              >
                Weekly
              </Label>
            </div>
            <div className="flex items-center gap-1.5">
              <RadioGroupItem value="monthly" id="period-monthly" className={cn(
                theme === 'light'
                  ? 'border-slate-400 text-blue-600'
                  : 'border-slate-500 text-cyan-400'
              )} />
              <Label
                htmlFor="period-monthly"
                className={cn(
                  'text-xs font-normal cursor-pointer',
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                )}
              >
                Monthly
              </Label>
            </div>
            <div className="flex items-center gap-1.5">
              <RadioGroupItem value="range" id="period-range" className={cn(
                theme === 'light'
                  ? 'border-slate-400 text-blue-600'
                  : 'border-slate-500 text-cyan-400'
              )} />
              <Label
                htmlFor="period-range"
                className={cn(
                  'text-xs font-normal cursor-pointer',
                  theme === 'light' ? 'text-slate-700' : 'text-slate-300'
                )}
              >
                Date Range
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Date Inputs */}
        {period === 'daily' ? (
          <div className="flex items-center gap-2">
            <Label htmlFor="date" className={cn(
              'text-xs whitespace-nowrap',
              theme === 'light' ? 'text-slate-700' : 'text-slate-300'
            )}>
              Date:
            </Label>
            <Popover open={datePopoverOpen} onOpenChange={setDatePopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  id="date"
                  variant="outline"
                  size="sm"
                  className={cn(
                    'h-9 w-[200px] justify-start text-left font-normal text-xs',
                    theme === 'light'
                      ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                      : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700',
                    !date && 'text-slate-500'
                  )}
                >
                  <CalendarIcon className="mr-2 h-3.5 w-3.5" />
                  {date ? formatDateDisplay(date, dailyTime) : 'Select date & time'}
                </Button>
              </PopoverTrigger>
                <PopoverContent 
                className={cn(
                  'w-auto p-3',
                  theme === 'light'
                    ? 'bg-white border-slate-300 calendar-popover-light'
                    : 'bg-slate-800 border-slate-700'
                )} 
                align="start"
              >
                <div className="flex items-start gap-3">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={(selectedDate) => {
                      if (selectedDate) {
                        setDate(selectedDate);
                        setDatePopoverOpen(false);
                      }
                    }}
                    initialFocus
                    theme={theme}
                    className={theme === 'light' ? 'bg-white' : 'bg-slate-800'}
                  />
                  <div className="flex flex-col items-start gap-2 pt-2 border-l pl-3">
                    <TimeDropdown
                      value={dailyTime}
                      onChange={(time) => {
                        setDailyTime(time);
                      }}
                      id="daily-time"
                      label="Time"
                    />
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        ) : period === 'monthly' ? (
          <>
            <div className="flex items-center gap-2">
              <Label htmlFor="month-selector" className={cn(
                'text-xs whitespace-nowrap',
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              )}>
                Month:
              </Label>
              <Popover open={monthPopoverOpen} onOpenChange={setMonthPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    id="month-selector"
                    variant="outline"
                    size="sm"
                    className={cn(
                      'h-9 w-[160px] justify-start text-left font-normal text-xs',
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                        : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-3.5 w-3.5" />
                    {format(selectedMonth, 'MMMM yyyy')}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className={cn(
                  'w-auto p-0',
                  theme === 'light'
                    ? 'bg-white border-slate-300 calendar-popover-light'
                    : 'bg-slate-800 border-slate-700'
                )} align="start">
                  <Calendar
                    mode="single"
                    selected={selectedMonth}
                    onSelect={(selectedDate) => {
                      if (selectedDate) {
                        setSelectedMonth(selectedDate);
                        const firstOfMonth = startOfMonth(selectedDate);
                        setStartDate(firstOfMonth);
                        const today = new Date();
                        today.setHours(0, 0, 0, 0);
                        // If selected month is current month, end date is today, otherwise end of that month
                        if (selectedDate.getMonth() === today.getMonth() && selectedDate.getFullYear() === today.getFullYear()) {
                          setEndDate(today);
                        } else {
                          const endOfMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1, 0);
                          setEndDate(endOfMonth);
                        }
                        setMonthPopoverOpen(false);
                      }
                    }}
                    initialFocus
                    theme={theme}
                    className={theme === 'light' ? 'bg-white' : 'bg-slate-800'}
                  />
                </PopoverContent>
              </Popover>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-xs',
                theme === 'light' ? 'text-slate-600' : 'text-slate-400'
              )}>
                {startDate && endDate ? `${formatDateDisplay(startDate)} - ${formatDateDisplay(endDate)}` : ''}
              </span>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <Label htmlFor="start-datetime" className={cn(
                'text-xs whitespace-nowrap',
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              )}>
                Start:
              </Label>
              <Popover open={startDateTimePopoverOpen} onOpenChange={setStartDateTimePopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    id="start-datetime"
                    variant="outline"
                    size="sm"
                    className={cn(
                      'h-9 w-[200px] justify-start text-left font-normal text-xs',
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                        : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700',
                      !startDate && 'text-slate-500'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-3.5 w-3.5" />
                    {startDate
                      ? formatDateDisplay(startDate, startTime)
                      : 'Select date & time'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className={cn(
                    'w-auto p-3',
                    theme === 'light'
                      ? 'bg-white border-slate-300 calendar-popover-light'
                      : 'bg-slate-800 border-slate-700'
                  )}
                  align="start"
                >
                  <div className="flex items-start gap-3">
                    <Calendar
                      mode="single"
                      selected={startDate}
                      onSelect={(selectedDate) => {
                        if (selectedDate) {
                          setStartDate(selectedDate);
                          // If end date is before new start date, update end date
                          if (endDate && endDate < selectedDate) {
                            setEndDate(selectedDate);
                          }
                        }
                      }}
                      disabled={(date) => {
                        // Disable dates after end date
                        if (endDate) {
                          return date > endDate;
                        }
                        return false;
                      }}
                      initialFocus
                      theme={theme}
                      className={theme === 'light' ? 'bg-white' : 'bg-slate-800'}
                    />
                    <div className="flex flex-col items-start gap-2 pt-2 border-l pl-3">
                      <TimeDropdown
                        value={startTime}
                        onChange={(time) => {
                          setStartTime(time);
                        }}
                        id="start-time"
                        label="Start time"
                      />
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="end-datetime" className={cn(
                'text-xs whitespace-nowrap',
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              )}>
                End:
              </Label>
              <Popover open={endDateTimePopoverOpen} onOpenChange={setEndDateTimePopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    id="end-datetime"
                    variant="outline"
                    size="sm"
                    className={cn(
                      'h-9 w-[200px] justify-start text-left font-normal text-xs',
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                        : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700',
                      !endDate && 'text-slate-500'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-3.5 w-3.5" />
                    {endDate
                      ? formatDateDisplay(endDate, endTime)
                      : 'Select date & time'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className={cn(
                    'w-auto p-3',
                    theme === 'light'
                      ? 'bg-white border-slate-300 calendar-popover-light'
                      : 'bg-slate-800 border-slate-700'
                  )}
                  align="start"
                >
                  <div className="flex items-start gap-3">
                    <Calendar
                      mode="single"
                      selected={endDate}
                      onSelect={(selectedDate) => {
                        if (selectedDate) {
                          setEndDate(selectedDate);
                          // If start date is after new end date, update start date
                          if (startDate && startDate > selectedDate) {
                            setStartDate(selectedDate);
                          }
                        }
                      }}
                      disabled={(date) => {
                        // Disable dates before start date
                        if (startDate) {
                          return date < startDate;
                        }
                        return false;
                      }}
                      initialFocus
                      theme={theme}
                      className={theme === 'light' ? 'bg-white' : 'bg-slate-800'}
                    />
                    <div className="flex flex-col items-start gap-2 pt-2 border-l pl-3">
                      <TimeDropdown
                        value={endTime}
                        onChange={(time) => {
                          setEndTime(time);
                        }}
                        id="end-time"
                        label="End time"
                      />
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
            {startDate && endDate && (() => {
              const startDateTime = combineDateAndTime(startDate, startTime);
              const endDateTime = combineDateAndTime(endDate, endTime);
              if (startDateTime && endDateTime && endDateTime < startDateTime) {
                return (
                  <div className="text-xs text-red-400 whitespace-nowrap">
                    End date/time cannot be before start date/time
                  </div>
                );
              }
              return null;
            })()}
          </>
        )}

        {/* Shift Multi-Select and Action Buttons - Grouped together */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Shift Multi-Select - Only show if not hidden */}
          {!hideShifts && (
            <div className="flex items-center gap-2">
              <Label htmlFor="shifts" className={cn(
                'text-xs whitespace-nowrap',
                theme === 'light' ? 'text-slate-700' : 'text-slate-300'
              )}>
                Shifts:
              </Label>
              <Popover open={shiftPopoverOpen} onOpenChange={setShiftPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    id="shifts"
                    variant="outline"
                    size="sm"
                    className={cn(
                      'h-9 w-[130px] justify-between text-xs font-normal',
                      theme === 'light'
                        ? 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                        : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                    )}
                  >
                    <span className="font-normal truncate">
                      {getShiftDisplayText()}
                    </span>
                    <ChevronDown className="h-3.5 w-3.5 opacity-50 flex-shrink-0 ml-1" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className={cn(
                    'w-56 p-2',
                    theme === 'light'
                      ? 'bg-white border-slate-300'
                      : 'bg-slate-800 border-slate-700'
                  )}
                  align="start"
                >
                  <div className="space-y-2">
                    {SHIFT_OPTIONS.map((shift) => (
                      <div
                        key={shift}
                        className={cn(
                          'flex items-center space-x-2 p-2 rounded cursor-pointer',
                          theme === 'light'
                            ? 'hover:bg-slate-100'
                            : 'hover:bg-slate-700'
                        )}
                        onClick={() => toggleShift(shift)}
                      >
                        <LightModeCheckbox
                          id={`shift-${shift}`}
                          checked={selectedShifts.includes(shift)}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              if (!selectedShifts.includes(shift)) {
                                setSelectedShifts(prev => [...prev, shift]);
                              }
                            } else {
                              setSelectedShifts(prev => prev.filter(s => s !== shift));
                            }
                          }}
                          theme={theme}
                        />
                        <Label
                          htmlFor={`shift-${shift}`}
                          className={cn(
                            'text-sm cursor-pointer font-normal flex-1',
                            theme === 'light' ? 'text-slate-900' : 'text-slate-200'
                          )}
                        >
                          Shift {shift}
                        </Label>
                      </div>
                    ))}
                  </div>
                  {selectedShifts.length === 0 && (
                    <div className="mt-2 text-xs text-red-400">
                      At least one shift must be selected
                    </div>
                  )}
                </PopoverContent>
              </Popover>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleClear}
              className={cn(
                'h-9 px-3 text-xs',
                theme === 'light'
                  ? 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                  : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
              )}
            >
              <X className="mr-1.5 h-3.5 w-3.5" />
              Clear
            </Button>
            <button
              type="button"
              onClick={handleApply}
              disabled={
                (!hideShifts && selectedShifts.length === 0) ||
                (mode === 'single' && !date) ||
                (mode === 'range' && (!startDate || !endDate || endDate < startDate))
              }
              className="h-9 px-3 !bg-blue-600 hover:!bg-blue-700 !text-white text-xs font-medium rounded-md transition-all duration-200 disabled:!bg-gray-400 disabled:!text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Apply Filters
            </button>
          </div>
        </div>
      </div>
    </div>
    </>
  );
}

