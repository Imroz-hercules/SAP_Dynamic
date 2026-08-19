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
import { Plus, Settings as SettingsIcon } from 'lucide-react';
import { ChartWidget } from './ChartWidget';
import { WidgetConfigModal } from './WidgetConfigModal';
import { AdminSettingsModal } from './AdminSettingsModal';
import { DashboardWidget, Facility } from '@shared/schema';
import { Button } from '@/components/ui/button';
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

interface DraggableDashboardProps {
  facilities: Facility[];
}

export function DraggableDashboard({ facilities }: DraggableDashboardProps) {
  const [widgetConfigOpen, setWidgetConfigOpen] = useState(false);
  const [adminSettingsOpen, setAdminSettingsOpen] = useState(false);
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null);
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

  // Widget mutations
  const createWidgetMutation = useMutation({
    mutationFn: (data: any) => apiRequest('POST', '/api/widgets', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/widgets'] });
      toast({ title: "Widget added successfully" });
    },
    onError: () => {
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
      const oldIndex = widgets.findIndex((widget) => widget.id === active.id);
      const newIndex = widgets.findIndex((widget) => widget.id === over?.id);

      const newWidgets = arrayMove(widgets, oldIndex, newIndex);
      
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

    if (editingWidget) {
      await updateWidgetMutation.mutateAsync({ id: editingWidget.id, ...widgetData });
    } else {
      await createWidgetMutation.mutateAsync(widgetData);
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
      {/* Dashboard Header */}
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

      {/* Widgets Grid */}
      {widgets.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-slate-400 mb-4">No widgets configured yet</div>
          <Button
            onClick={handleAddWidget}
            className="bg-cyan-600 hover:bg-cyan-700 text-white"
          >
            <Plus size={16} className="mr-2" />
            Add Your First Widget
          </Button>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={widgets.map(w => w.id)} strategy={rectSortingStrategy}>
            <div
              className="grid gap-4 auto-rows-min"
              style={{
                gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
                minHeight: '200px',
              }}
            >
              {widgets.map((widget) => (
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