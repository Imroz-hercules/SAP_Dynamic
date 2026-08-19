import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X } from 'lucide-react';
import { DashboardWidget, AdminConfig } from '@shared/schema';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { useQuery } from '@tanstack/react-query';

const widgetConfigSchema = z.object({
  title: z.string().min(1, "Title is required"),
  chartType: z.string().min(1, "Chart type is required"),
  metricType: z.string().min(1, "Metric type is required"),
  facilityId: z.number().optional(),
  width: z.number().min(1).max(4).default(1),
  height: z.number().min(1).max(3).default(1),
});

type WidgetConfigForm = z.infer<typeof widgetConfigSchema>;

interface WidgetConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: WidgetConfigForm) => void;
  widget?: DashboardWidget;
  facilities: Array<{ id: number; name: string; location: string }>;
}

export function WidgetConfigModal({ 
  isOpen, 
  onClose, 
  onSave, 
  widget, 
  facilities 
}: WidgetConfigModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch chart types from admin config
  const { data: chartTypes = [] } = useQuery<AdminConfig[]>({
    queryKey: ['/api/admin/config', 'chart_types'],
    queryFn: () => fetch('/api/admin/config?type=chart_types').then(res => res.json()),
    enabled: isOpen,
  });

  // Fetch metric types from admin config
  const { data: metricTypes = [] } = useQuery<AdminConfig[]>({
    queryKey: ['/api/admin/config', 'metric_types'],
    queryFn: () => fetch('/api/admin/config?type=metric_types').then(res => res.json()),
    enabled: isOpen,
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors }
  } = useForm<WidgetConfigForm>({
    resolver: zodResolver(widgetConfigSchema),
    defaultValues: {
      title: '',
      chartType: '',
      metricType: '',
      facilityId: undefined,
      width: 1,
      height: 1,
    }
  });

  // Reset form when widget changes or modal opens
  useEffect(() => {
    if (isOpen) {
      if (widget) {
        reset({
          title: widget.title,
          chartType: widget.chartType,
          metricType: widget.metricType,
          facilityId: widget.facilityId || undefined,
          width: widget.width,
          height: widget.height,
        });
      } else {
        reset({
          title: '',
          chartType: '',
          metricType: '',
          facilityId: undefined,
          width: 1,
          height: 1,
        });
      }
    }
  }, [isOpen, widget, reset]);

  const onSubmit = async (data: WidgetConfigForm) => {
    setIsSubmitting(true);
    try {
      await onSave(data);
      onClose();
    } catch (error) {
      console.error('Failed to save widget:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const chartTypeValue = watch('chartType');
  const metricTypeValue = watch('metricType');

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border border-slate-700 text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="text-cyan-400">
            {widget ? 'Edit Widget' : 'Add New Widget'}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Configure your widget settings including chart type, metrics, and display options.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title" className="text-slate-300">Widget Title</Label>
            <Input
              id="title"
              {...register('title')}
              placeholder="Enter widget title"
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-400"
            />
            {errors.title && (
              <p className="text-red-400 text-sm">{errors.title.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="chartType" className="text-slate-300">Chart Type</Label>
            <Select
              value={chartTypeValue}
              onValueChange={(value) => setValue('chartType', value)}
            >
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue placeholder="Select chart type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {chartTypes.filter(ct => ct.isEnabled).map((chartType) => (
                  <SelectItem key={chartType.id} value={chartType.configValue}>
                    {chartType.displayName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.chartType && (
              <p className="text-red-400 text-sm">{errors.chartType.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="metricType" className="text-slate-300">Metric Type</Label>
            <Select
              value={metricTypeValue}
              onValueChange={(value) => setValue('metricType', value)}
            >
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue placeholder="Select metric type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {metricTypes.filter(mt => mt.isEnabled).map((metricType) => (
                  <SelectItem key={metricType.id} value={metricType.configValue}>
                    {metricType.displayName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.metricType && (
              <p className="text-red-400 text-sm">{errors.metricType.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="facilityId" className="text-slate-300">Facility (Optional)</Label>
            <Select
              value={watch('facilityId')?.toString() || 'all'}
              onValueChange={(value) => setValue('facilityId', value === 'all' ? undefined : Number(value))}
            >
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue placeholder="All facilities" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                <SelectItem value="all">All Facilities</SelectItem>
                {facilities.map((facility) => (
                  <SelectItem key={facility.id} value={facility.id.toString()}>
                    {facility.name} - {facility.location}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="width" className="text-slate-300">Width</Label>
              <Select
                value={watch('width')?.toString()}
                onValueChange={(value) => setValue('width', Number(value))}
              >
                <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-600">
                  <SelectItem value="1">1 Column</SelectItem>
                  <SelectItem value="2">2 Columns</SelectItem>
                  <SelectItem value="3">3 Columns</SelectItem>
                  <SelectItem value="4">4 Columns</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="height" className="text-slate-300">Height</Label>
              <Select
                value={watch('height')?.toString()}
                onValueChange={(value) => setValue('height', Number(value))}
              >
                <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-600">
                  <SelectItem value="1">1 Row</SelectItem>
                  <SelectItem value="2">2 Rows</SelectItem>
                  <SelectItem value="3">3 Rows</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-cyan-600 hover:bg-cyan-700 text-white"
            >
              {isSubmitting ? 'Saving...' : 'Save Widget'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}