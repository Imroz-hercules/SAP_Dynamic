import React, { useState } from 'react';
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
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Plus, Settings as SettingsIcon, Grid3x3, LayoutGrid, Filter, Search } from 'lucide-react';
import { ChartWidget } from './ChartWidget';
import { WidgetConfigModal } from './WidgetConfigModal';
import { AdminSettingsModal } from './AdminSettingsModal';
import { DashboardWidget, Facility } from '@shared/schema';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';

interface SortableWidgetProps {
  widget: DashboardWidget;
  onEdit: (widget: DashboardWidget) => void;
  onDelete: (widgetId: number) => void;
}

function SortableWidget({ widget, onEdit, onDelete }: SortableWidgetProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <ChartWidget
        widget={widget}
        onEdit={onEdit}
        onDelete={onDelete}
        isDragging={isDragging}
        dragHandleProps={listeners}
      />
    </div>
  );
}

interface EnhancedWidgetDashboardProps {
  facilities: Facility[];
}

export function EnhancedWidgetDashboard({ facilities }: EnhancedWidgetDashboardProps) {
  const [widgetConfigOpen, setWidgetConfigOpen] = useState(false);
  const [adminSettingsOpen, setAdminSettingsOpen] = useState(false);
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [chartTypeFilter, setChartTypeFilter] = useState('all');
  const [layoutType, setLayoutType] = useState('grid'); // 'grid' or 'masonry'
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch widgets
  const { data: widgets = [], isLoading } = useQuery<DashboardWidget[]>({
    queryKey: ['/api/widgets'],
    queryFn: () => fetch('/api/widgets').then(res => res.json()),
  });

  // Filter widgets based on search and filters
  const filteredWidgets = widgets.filter(widget => {
    const matchesSearch = widget.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         widget.metricType.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = chartTypeFilter === 'all' || widget.chartType === chartTypeFilter;
    return matchesSearch && matchesFilter;
  });

  // Widget mutations
  const createWidgetMutation = useMutation({
    mutationFn: (data: any) => apiRequest('POST', '/api/widgets', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/widgets'] });
      toast({ title: "Widget added successfully" });
    },
    onError: (error) => {
      console.error('Failed to add widget:', error);
      toast({ title: "Failed to add widget", variant: "destructive" });
    }
  });

  const updateWidgetMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: number } & any) =>
      apiRequest('PATCH', `/api/widgets/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/widgets'] });
      toast({ title: "Widget updated successfully" });
    },
    onError: () => {
      toast({ title: "Failed to update widget", variant: "destructive" });
    }
  });

  const updatePositionsMutation = useMutation({
    mutationFn: (widgets: { id: number; position: number }[]) =>
      apiRequest('PUT', '/api/widgets/positions', { widgets }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/widgets'] });
    },
    onError: () => {
      toast({ title: "Failed to update widget positions", variant: "destructive" });
    }
  });

  const deleteWidgetMutation = useMutation({
    mutationFn: (id: number) => apiRequest('DELETE', `/api/widgets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/widgets'] });
      toast({ title: "Widget deleted successfully" });
    },
    onError: () => {
      toast({ title: "Failed to delete widget", variant: "destructive" });
    }
  });

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = filteredWidgets.findIndex((widget) => widget.id === active.id);
      const newIndex = filteredWidgets.findIndex((widget) => widget.id === over?.id);

      const newWidgets = arrayMove(filteredWidgets, oldIndex, newIndex);
      
      // Update positions
      const positionUpdates = newWidgets.map((widget, index) => ({
        id: widget.id,
        position: index
      }));
      
      updatePositionsMutation.mutate(positionUpdates);
    }
  };

  const handleAddWidget = () => {
    setEditingWidget(null);
    setWidgetConfigOpen(true);
  };

  const handleEditWidget = (widget: DashboardWidget) => {
    setEditingWidget(widget);
    setWidgetConfigOpen(true);
  };

  const handleSaveWidget = async (config: any) => {
    const widgetData = {
      ...config,
      position: editingWidget?.position ?? widgets.length,
    };

    try {
      if (editingWidget) {
        await updateWidgetMutation.mutateAsync({ id: editingWidget.id, ...widgetData });
      } else {
        await createWidgetMutation.mutateAsync(widgetData);
      }
      setWidgetConfigOpen(false);
    } catch (error) {
      console.error('Failed to save widget:', error);
    }
  };

  const handleDeleteWidget = (widgetId: number) => {
    deleteWidgetMutation.mutate(widgetId);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Enhanced Dashboard Header */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Dashboard Widgets</h2>
            <p className="text-slate-400">Drag and drop widgets to customize your dashboard</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleAddWidget}
              className="bg-cyan-600 hover:bg-cyan-700 text-white"
            >
              <Plus size={16} className="mr-2" />
              Add Widget
            </Button>
            <Button
              onClick={() => setAdminSettingsOpen(true)}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              <SettingsIcon size={16} className="mr-2" />
              Admin Settings
            </Button>
          </div>
        </div>

        {/* Filters and Controls */}
        <div className="bg-slate-800/50 rounded-lg p-4 flex gap-4 items-center">
          <div className="flex-1">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search widgets by title or metric..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Filter size={16} className="text-slate-400" />
            <Select value={chartTypeFilter} onValueChange={setChartTypeFilter}>
              <SelectTrigger className="w-40 bg-slate-700 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                <SelectItem value="all">All Charts</SelectItem>
                <SelectItem value="line">Line Charts</SelectItem>
                <SelectItem value="bar">Bar Charts</SelectItem>
                <SelectItem value="pie">Pie Charts</SelectItem>
                <SelectItem value="donut">Donut Charts</SelectItem>
                <SelectItem value="gauge">Gauges</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-1 border border-slate-600 rounded-md">
            <Button
              variant={layoutType === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setLayoutType('grid')}
              className="border-none"
            >
              <Grid3x3 size={16} />
            </Button>
            <Button
              variant={layoutType === 'masonry' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setLayoutType('masonry')}
              className="border-none"
            >
              <LayoutGrid size={16} />
            </Button>
          </div>

          <div className="text-sm text-slate-400">
            {filteredWidgets.length} of {widgets.length} widgets
          </div>
        </div>
      </div>

      {/* Widgets Grid */}
      {filteredWidgets.length === 0 ? (
        <div className="text-center py-12">
          {widgets.length === 0 ? (
            <>
              <div className="text-slate-400 mb-4">No widgets configured yet</div>
              <Button
                onClick={handleAddWidget}
                className="bg-cyan-600 hover:bg-cyan-700 text-white"
              >
                <Plus size={16} className="mr-2" />
                Add Your First Widget
              </Button>
            </>
          ) : (
            <div className="text-slate-400 mb-4">
              No widgets match your current filters
            </div>
          )}
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={filteredWidgets.map(w => w.id)} strategy={rectSortingStrategy}>
            <div
              className={`grid gap-4 ${
                layoutType === 'grid' 
                  ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4' 
                  : 'columns-1 sm:columns-2 lg:columns-3 xl:columns-4'
              }`}
            >
              {filteredWidgets.map((widget) => (
                <SortableWidget
                  key={widget.id}
                  widget={widget}
                  onEdit={handleEditWidget}
                  onDelete={handleDeleteWidget}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {/* Modals */}
      <WidgetConfigModal
        isOpen={widgetConfigOpen}
        onClose={() => setWidgetConfigOpen(false)}
        onSave={handleSaveWidget}
        widget={editingWidget || undefined}
        facilities={facilities}
      />

      <AdminSettingsModal
        isOpen={adminSettingsOpen}
        onClose={() => setAdminSettingsOpen(false)}
      />
    </div>
  );
}