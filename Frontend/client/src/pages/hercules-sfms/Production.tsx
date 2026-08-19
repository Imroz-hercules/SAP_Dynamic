import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { WaterSystemLayout } from '../../components/water-system/WaterSystemLayout'
import { KPICard } from '../../components/water-system/KPICard'
import { Search, Filter, Play, Pause, Square, StopCircle, RotateCcw, Activity, Factory, Target, Timer, TrendingUp, Zap, AlertTriangle, CheckCircle, Clock, BookOpen, Settings, Plus, ChevronUp, ChevronDown, CircuitBoard, Power, Wrench, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Separator } from '@/components/ui/separator'
import { useToast } from '@/hooks/use-toast'
import { apiRequest } from '@/lib/queryClient'

// Production Order interface
interface ProductionOrder {
  id: number;
  orderNumber: string;
  productionLineId: number;
  recipeId: number;
  recipeName: string;
  recipeCode: string;
  targetQuantity: number;
  unit: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'unreleased' | 'released' | 'running' | 'paused' | 'held' | 'stopped' | 'completed' | 'aborted';
  progress: number;
  currentQuantity: number;
  startTime?: string;
  estimatedCompletion?: string;
  queuePosition: number;
  createdAt: string;
}

// Production Line interface
interface ProductionLine {
  id: number;
  name: string;
  zone: string;
  equipmentStatus: 'idle' | 'running' | 'paused' | 'maintenance' | 'offline' | 'fault';
  operatingMode: 'auto' | 'manual' | 'maintenance';
  feedingEnabled: boolean;
  safetyInterlocks: boolean;
  currentOrder?: ProductionOrder;
  queuedOrders: ProductionOrder[];
  efficiency: number;
  uptime: number;
  totalProduced: number;
  currentSpeed: number;
  targetSpeed: number;
  alarms: number;
  warnings: number;
  lastMaintenance: string;
}

// Recipe interface  
interface Recipe {
  id: number;
  name: string;
  code: string;
  category: string;
  batchSize: number;
  duration: number;
  ingredients: number;
  version: string;
  status: 'active' | 'inactive' | 'draft';
}

// Form schema for new orders
const newOrderSchema = z.object({
  orderNumber: z.string().min(1, "Order number is required"),
  recipeId: z.number().min(1, "Recipe selection is required"),
  targetQuantity: z.number().min(0.1, "Target quantity must be positive"),
  unit: z.string().default('kg'),
  priority: z.enum(['low', 'normal', 'high', 'urgent']).default('normal'),
})

type NewOrderFormData = z.infer<typeof newOrderSchema>

// Mock data for available recipes
const availableRecipes: Recipe[] = [
  { id: 1, name: 'Premium Widget Mix', code: 'RCP-001', category: 'Widget', batchSize: 5000, duration: 120, ingredients: 8, version: '1.2', status: 'active' },
  { id: 2, name: 'Standard Component Mix', code: 'RCP-002', category: 'Component', batchSize: 8000, duration: 180, ingredients: 12, version: '2.1', status: 'active' },
  { id: 3, name: 'Specialty Blend Alpha', code: 'RCP-003', category: 'Specialty', batchSize: 3000, duration: 90, ingredients: 6, version: '1.0', status: 'active' },
  { id: 4, name: 'Economy Grade Basic', code: 'RCP-004', category: 'Basic', batchSize: 10000, duration: 240, ingredients: 5, version: '3.0', status: 'active' },
  { id: 5, name: 'High-Performance Pro', code: 'RCP-005', category: 'Pro', batchSize: 2000, duration: 60, ingredients: 15, version: '1.5', status: 'active' },
];

// Mock data for production lines with industrial control
const productionLines: ProductionLine[] = [
  {
    id: 1,
    name: 'Production Line A',
    zone: 'Manufacturing Zone 1',
    equipmentStatus: 'running',
    operatingMode: 'auto',
    feedingEnabled: true,
    safetyInterlocks: true,
    currentOrder: {
      id: 101,
      orderNumber: 'WO-2025-001',
      productionLineId: 1,
      recipeId: 1,
      recipeName: 'Premium Widget Mix',
      recipeCode: 'RCP-001',
      targetQuantity: 5000,
      unit: 'kg',
      priority: 'high',
      status: 'running',
      progress: 65,
      currentQuantity: 3250,
      startTime: '2025-07-29T07:30:00Z',
      estimatedCompletion: '2025-07-29T11:30:00Z',
      queuePosition: 0,
      createdAt: '2025-07-29T07:00:00Z'
    },
    queuedOrders: [
      {
        id: 104,
        orderNumber: 'WO-2025-004',
        productionLineId: 1,
        recipeId: 2,
        recipeName: 'Standard Component Mix',
        recipeCode: 'RCP-002',
        targetQuantity: 8000,
        unit: 'kg',
        priority: 'normal',
        status: 'released',
        progress: 0,
        currentQuantity: 0,
        queuePosition: 1,
        createdAt: '2025-07-29T08:00:00Z'
      }
    ],
    efficiency: 94,
    uptime: 98.5,
    totalProduced: 125000,
    currentSpeed: 85,
    targetSpeed: 90,
    alarms: 0,
    warnings: 1,
    lastMaintenance: '2025-07-20'
  },
  {
    id: 2,
    name: 'Production Line B',
    zone: 'Manufacturing Zone 2',
    equipmentStatus: 'running',
    operatingMode: 'auto',
    feedingEnabled: true,
    safetyInterlocks: true,
    currentOrder: {
      id: 102,
      orderNumber: 'WO-2025-002',
      productionLineId: 2,
      recipeId: 2,
      recipeName: 'Standard Component Mix',
      recipeCode: 'RCP-002',
      targetQuantity: 8000,
      unit: 'kg',
      priority: 'normal',
      status: 'running',
      progress: 35,
      currentQuantity: 2800,
      startTime: '2025-07-29T06:00:00Z',
      estimatedCompletion: '2025-07-29T12:00:00Z',
      queuePosition: 0,
      createdAt: '2025-07-29T05:30:00Z'
    },
    queuedOrders: [],
    efficiency: 89,
    uptime: 96.2,
    totalProduced: 98000,
    currentSpeed: 78,
    targetSpeed: 85,
    alarms: 0,
    warnings: 0,
    lastMaintenance: '2025-07-18'
  },
  {
    id: 3,
    name: 'Production Line C',
    zone: 'Manufacturing Zone 3',
    equipmentStatus: 'held',
    operatingMode: 'auto',
    feedingEnabled: false,
    safetyInterlocks: true,
    currentOrder: {
      id: 103,
      orderNumber: 'WO-2025-003',
      productionLineId: 3,
      recipeId: 3,
      recipeName: 'Specialty Blend Alpha',
      recipeCode: 'RCP-003',
      targetQuantity: 3000,
      unit: 'kg',
      priority: 'urgent',
      status: 'held',
      progress: 78,
      currentQuantity: 2340,
      startTime: '2025-07-29T08:15:00Z',
      queuePosition: 0,
      createdAt: '2025-07-29T08:00:00Z'
    },
    queuedOrders: [],
    efficiency: 92,
    uptime: 94.8,
    totalProduced: 87500,
    currentSpeed: 0,
    targetSpeed: 75,
    alarms: 1,
    warnings: 2,
    lastMaintenance: '2025-07-22'
  },
  {
    id: 4,
    name: 'Production Line D',
    zone: 'Manufacturing Zone 4',
    equipmentStatus: 'idle',
    operatingMode: 'auto',
    feedingEnabled: false,
    safetyInterlocks: true,
    queuedOrders: [
      {
        id: 105,
        orderNumber: 'WO-2025-005',
        productionLineId: 4,
        recipeId: 4,
        recipeName: 'Economy Grade Basic',
        recipeCode: 'RCP-004',
        targetQuantity: 10000,
        unit: 'kg',
        priority: 'low',
        status: 'unreleased',
        progress: 0,
        currentQuantity: 0,
        queuePosition: 1,
        createdAt: '2025-07-29T09:00:00Z'
      }
    ],
    efficiency: 91,
    uptime: 97.1,
    totalProduced: 156000,
    currentSpeed: 0,
    targetSpeed: 95,
    alarms: 0,
    warnings: 0,
    lastMaintenance: '2025-07-25'
  },
  {
    id: 5,
    name: 'Production Line E',
    zone: 'Manufacturing Zone 5',
    equipmentStatus: 'maintenance',
    operatingMode: 'maintenance',
    feedingEnabled: false,
    safetyInterlocks: false,
    queuedOrders: [],
    efficiency: 88,
    uptime: 92.3,
    totalProduced: 76000,
    currentSpeed: 0,
    targetSpeed: 80,
    alarms: 0,
    warnings: 0,
    lastMaintenance: '2025-07-29'
  }
];

const getEquipmentStatusColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'text-green-400 bg-green-500/10 border-green-500/20'
    case 'paused':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
    case 'held':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    case 'idle':
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
    case 'maintenance':
      return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
    case 'offline':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    case 'fault':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    default:
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  }
}

const getEquipmentStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <Play className="h-4 w-4" />
    case 'paused':
      return <Pause className="h-4 w-4" />
    case 'held':
      return <Shield className="h-4 w-4" />
    case 'idle':
      return <Clock className="h-4 w-4" />
    case 'maintenance':
      return <Settings className="h-4 w-4" />
    case 'offline':
      return <AlertTriangle className="h-4 w-4" />
    case 'fault':
      return <AlertTriangle className="h-4 w-4" />
    default:
      return <Clock className="h-4 w-4" />
  }
}

const getOrderStatusColor = (status: string) => {
  switch (status) {
    case 'unreleased':
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
    case 'released':
      return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
    case 'running':
      return 'text-green-400 bg-green-500/10 border-green-500/20'
    case 'paused':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
    case 'held':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    case 'stopped':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    case 'completed':
      return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    case 'aborted':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    default:
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  }
}

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'urgent':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    case 'high':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    case 'normal':
      return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
    case 'low':
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
    default:
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  }
}

export default function Production() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('All')
  const [filterZone, setFilterZone] = useState('All')
  const [selectedLine, setSelectedLine] = useState<ProductionLine | null>(null)
  const [showNewOrderDialog, setShowNewOrderDialog] = useState(false)
  const [expandedQueues, setExpandedQueues] = useState<{[key: number]: boolean}>({})

  const { toast } = useToast()

  const form = useForm<NewOrderFormData>({
    resolver: zodResolver(newOrderSchema),
    defaultValues: {
      orderNumber: '',
      recipeId: 0,
      targetQuantity: 0,
      unit: 'kg',
      priority: 'normal',
    },
  })

  // Filter production lines
  const filteredLines = productionLines.filter(line => {
    const matchesSearch = line.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         line.zone.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'All' || line.equipmentStatus === filterStatus
    const matchesZone = filterZone === 'All' || line.zone === filterZone
    return matchesSearch && matchesStatus && matchesZone
  })

  // Calculate KPIs
  const activeLines = productionLines.filter(l => l.equipmentStatus === 'running').length
  const totalLines = productionLines.length
  const avgEfficiency = Math.round(productionLines.reduce((sum, l) => sum + l.efficiency, 0) / totalLines)
  const avgUptime = Math.round(productionLines.reduce((sum, l) => sum + l.uptime, 0) / totalLines * 10) / 10
  const totalOrders = productionLines.reduce((sum, l) => sum + (l.currentOrder ? 1 : 0) + l.queuedOrders.length, 0)
  const releasedOrders = productionLines.reduce((sum, l) => {
    const currentReleased = l.currentOrder && l.currentOrder.status !== 'unreleased' ? 1 : 0
    const queuedReleased = l.queuedOrders.filter(o => o.status !== 'unreleased').length
    return sum + currentReleased + queuedReleased
  }, 0)

  // Toggle queue expansion
  const toggleQueue = (lineId: number) => {
    setExpandedQueues(prev => ({
      ...prev,
      [lineId]: !prev[lineId]
    }))
  }

  // Industrial control functions
  const handleStart = (lineId: number) => {
    toast({
      title: "Production Started",
      description: `Line ${lineId} production started`,
    })
  }

  const handlePause = (lineId: number) => {
    toast({
      title: "Production Paused",
      description: `Line ${lineId} production paused`,
    })
  }

  const handleStop = (lineId: number) => {
    toast({
      title: "Production Stopped",
      description: `Line ${lineId} production stopped`,
    })
  }

  const handleHold = (lineId: number) => {
    toast({
      title: "Production Held",
      description: `Line ${lineId} held for operator intervention`,
    })
  }

  const handleReset = (lineId: number) => {
    toast({
      title: "Equipment Reset",
      description: `Line ${lineId} equipment reset completed`,
    })
  }

  const handleEnableFeeding = (lineId: number) => {
    toast({
      title: "Feeding Enabled",
      description: `Material feeding enabled for line ${lineId}`,
    })
  }

  const handleRelease = (orderId: number) => {
    toast({
      title: "Order Released",
      description: `Order ${orderId} released for production`,
    })
  }

  const handleUnrelease = (orderId: number) => {
    toast({
      title: "Order Unreleased",
      description: `Order ${orderId} unreleased and queued`,
    })
  }

  const handleNewOrder = (data: NewOrderFormData) => {
    if (!selectedLine) return
    
    const newOrderNumber = `WO-2025-${String(Date.now()).slice(-3)}`
    toast({
      title: "Order Created",
      description: `New order ${newOrderNumber} created for ${selectedLine.name}`,
    })
    
    form.reset()
    setShowNewOrderDialog(false)
    setSelectedLine(null)
  }

  return (
    <WaterSystemLayout title="Production Control Center" subtitle="Industrial manufacturing control and order management">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <KPICard
          title="Active Lines"
          value={activeLines.toString()}
          icon="activity"
          trend={2}
          color="green"
        />
        <KPICard
          title="Total Lines"
          value={totalLines.toString()}
          icon="gauge"
          trend={0}
          color="blue"
        />
        <KPICard
          title="Avg Efficiency"
          value={`${avgEfficiency}%`}
          icon="gauge"
          trend={1}
          color="cyan"
        />
        <KPICard
          title="Avg Uptime"
          value={`${avgUptime}%`}
          icon="activity"
          trend={0}
          color="purple"
        />
        <KPICard
          title="Total Orders"
          value={totalOrders.toString()}
          icon="package"
          trend={3}
          color="yellow"
        />
        <KPICard
          title="Released Orders"
          value={releasedOrders.toString()}
          icon="signal"
          trend={1}
          color="orange"
        />
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-6">
        <div className="flex items-center gap-4 flex-1">
          <div className="flex items-center gap-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-lg px-3 py-2 min-w-0 flex-1 max-w-md">
            <Search className="h-4 w-4 text-slate-400 shrink-0" />
            <Input
              placeholder="Search production lines..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="border-0 bg-transparent placeholder-slate-500 text-white focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>
          
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-40 bg-slate-800/50 border-slate-700/50 text-white">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="All">All Status</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="idle">Idle</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
              <SelectItem value="offline">Offline</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterZone} onValueChange={setFilterZone}>
            <SelectTrigger className="w-48 bg-slate-800/50 border-slate-700/50 text-white">
              <SelectValue placeholder="Zone" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="All">All Zones</SelectItem>
              <SelectItem value="Manufacturing Zone 1">Zone 1</SelectItem>
              <SelectItem value="Manufacturing Zone 2">Zone 2</SelectItem>
              <SelectItem value="Manufacturing Zone 3">Zone 3</SelectItem>
              <SelectItem value="Manufacturing Zone 4">Zone 4</SelectItem>
              <SelectItem value="Manufacturing Zone 5">Zone 5</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Production Lines - Compact Layout */}
      <div className="space-y-3">
        {filteredLines.map((line) => (
          <div key={line.id} className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-lg p-4 hover:bg-slate-800/70 transition-all duration-200 hover:border-cyan-500/30">
            {/* Compact Header with Equipment Status */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded border border-blue-500/30">
                  <Factory className="h-4 w-4 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{line.name}</h3>
                  <p className="text-xs text-slate-400">{line.zone}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={`text-xs ${getEquipmentStatusColor(line.equipmentStatus)} border flex items-center gap-1`}>
                  {getEquipmentStatusIcon(line.equipmentStatus)}
                  {line.equipmentStatus.toUpperCase()}
                </Badge>
                <Badge className="text-xs text-blue-400 bg-blue-500/10 border-blue-500/20">
                  {line.operatingMode.toUpperCase()}
                </Badge>
                <div className="flex items-center gap-1 text-xs">
                  <div className={`w-2 h-2 rounded-full ${line.feedingEnabled ? 'bg-green-400' : 'bg-red-400'}`} />
                  <Shield className={`w-3 h-3 ${line.safetyInterlocks ? 'text-green-400' : 'text-red-400'}`} />
                  <span className="text-yellow-400 font-mono">{line.currentSpeed}/{line.targetSpeed}</span>
                  {line.alarms > 0 && <AlertTriangle className="w-3 h-3 text-red-400" />}
                </div>
              </div>
            </div>

            {/* Compact Current Order & Queue Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-3">
              {/* Current Order - Left Column */}
              <div className="bg-slate-900/50 p-3 rounded border border-slate-600/50">
                {line.currentOrder ? (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-cyan-400" />
                        <span className="text-sm font-medium text-white">Active Order</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Badge className={`text-xs ${getOrderStatusColor(line.currentOrder.status)} border`}>
                          {line.currentOrder.status === 'unreleased' ? 'UNREL' : 'REL'}
                        </Badge>
                        <Badge className={`text-xs ${getPriorityColor(line.currentOrder.priority)} border`}>
                          {line.currentOrder.priority.charAt(0).toUpperCase()}
                        </Badge>
                        {line.currentOrder.status === 'unreleased' ? (
                          <Button
                            size="sm"
                            variant="outline"
                            className="bg-green-600/20 border-green-500 text-green-400 hover:bg-green-600/30 h-5 px-1 text-[10px]"
                            onClick={() => handleRelease(line.currentOrder.id)}
                          >
                            REL
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="bg-orange-600/20 border-orange-500 text-orange-400 hover:bg-orange-600/30 h-5 px-1 text-[10px]"
                            onClick={() => handleUnrelease(line.currentOrder.id)}
                          >
                            UNREL
                          </Button>
                        )}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-white font-medium text-sm">{line.currentOrder.orderNumber}</div>
                      <div className="text-xs text-slate-300">{line.currentOrder.recipeName} ({line.currentOrder.recipeCode})</div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400">Progress: {line.currentOrder.currentQuantity.toLocaleString()}/{line.currentOrder.targetQuantity.toLocaleString()} {line.currentOrder.unit}</span>
                        <span className="text-xs text-green-400 font-medium">{line.currentOrder.progress}%</span>
                      </div>
                      <Progress value={line.currentOrder.progress} className="h-1" />
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-2">
                    <Clock className="h-6 w-6 text-slate-500 mx-auto mb-1" />
                    <p className="text-xs text-slate-400 mb-2">No active order</p>
                    <Button 
                      size="sm" 
                      className="bg-cyan-600 hover:bg-cyan-700 text-white h-6 px-3 text-xs"
                      onClick={() => {
                        setSelectedLine(line)
                        setShowNewOrderDialog(true)
                      }}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      New Order
                    </Button>
                  </div>
                )}
              </div>

              {/* Queue - Right Column */}
              <div className="bg-slate-900/50 p-3 rounded border border-slate-600/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Timer className="h-4 w-4 text-purple-400" />
                    <span className="text-sm font-medium text-white">Queue</span>
                    <Badge className="text-xs text-purple-400 bg-purple-500/10 border-purple-500/20">
                      {line.queuedOrders.length}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button 
                      size="sm" 
                      variant="outline"
                      className="bg-cyan-600/20 border-cyan-500 text-cyan-400 hover:bg-cyan-600/30 h-6 px-2 text-xs"
                      onClick={() => {
                        setSelectedLine(line)
                        setShowNewOrderDialog(true)
                      }}
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                    {line.queuedOrders.length > 0 && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="bg-slate-600/20 border-slate-500 text-slate-400 hover:bg-slate-600/30 h-6 px-1 text-xs"
                        onClick={() => toggleQueue(line.id)}
                      >
                        {expandedQueues[line.id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      </Button>
                    )}
                  </div>
                </div>

                {line.queuedOrders.length > 0 ? (
                  <div className="space-y-1">
                    {(expandedQueues[line.id] ? line.queuedOrders : line.queuedOrders.slice(0, 2)).map((order) => (
                      <div key={order.id} className="bg-slate-800/30 p-2 rounded border border-slate-700/30 flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <Badge className="text-xs text-slate-400 bg-slate-500/10 border-slate-500/20 w-6 h-4 text-center p-0 text-[10px]">
                            #{order.queuePosition}
                          </Badge>
                          <div className="min-w-0 flex-1">
                            <div className="text-xs text-white font-medium truncate">{order.orderNumber}</div>
                            <div className="text-[10px] text-slate-400 truncate">{order.recipeName} - {order.targetQuantity.toLocaleString()} {order.unit}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <Badge className={`text-[10px] ${getOrderStatusColor(order.status)} border`}>
                            {order.status === 'unreleased' ? 'UNREL' : 'REL'}
                          </Badge>
                          <Badge className={`text-[10px] ${getPriorityColor(order.priority)} border`}>
                            {order.priority.charAt(0).toUpperCase()}
                          </Badge>
                          {order.status === 'unreleased' ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="bg-green-600/20 border-green-500 text-green-400 hover:bg-green-600/30 h-5 px-1 text-[10px]"
                              onClick={() => handleRelease(order.id)}
                            >
                              REL
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              className="bg-orange-600/20 border-orange-500 text-orange-400 hover:bg-orange-600/30 h-5 px-1 text-[10px]"
                              onClick={() => handleUnrelease(order.id)}
                            >
                              UNREL
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                    {!expandedQueues[line.id] && line.queuedOrders.length > 2 && (
                      <div className="text-center text-[10px] text-slate-500 py-1">
                        +{line.queuedOrders.length - 2} more
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-xs text-slate-500 py-1">
                    No orders queued
                  </div>
                )}
              </div>
            </div>

            {/* Compact Industrial Control Panel */}
            <div className="bg-slate-900/50 p-3 rounded border border-slate-600/50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CircuitBoard className="h-4 w-4 text-blue-400" />
                  <span className="text-sm font-medium text-white">Line Controls</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1">
                    <span className="text-slate-400">Eff:</span>
                    <span className="text-white font-medium">{line.efficiency}%</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-slate-400">Up:</span>
                    <span className="text-white font-medium">{line.uptime}%</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-slate-400">Total:</span>
                    <span className="text-white font-medium">{(line.totalProduced / 1000).toFixed(1)}K</span>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-center items-center gap-2 flex-wrap">
                {/* Primary Controls */}
                {line.equipmentStatus === 'running' ? (
                  <>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-yellow-500/80 to-amber-500/80 border-yellow-400 text-yellow-100 hover:from-yellow-400/90 hover:to-amber-400/90 shadow-lg hover:shadow-yellow-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handlePause(line.id)}
                    >
                      <Pause className="h-3 w-3 mr-1" />
                      PAUSE
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-orange-500/80 to-red-500/80 border-orange-400 text-orange-100 hover:from-orange-400/90 hover:to-red-400/90 shadow-lg hover:shadow-orange-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleHold(line.id)}
                    >
                      <Shield className="h-3 w-3 mr-1" />
                      HOLD
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStop(line.id)}
                    >
                      <StopCircle className="h-3 w-3 mr-1" />
                      STOP
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-slate-500/80 to-slate-600/80 border-slate-400 text-slate-100 hover:from-slate-400/90 hover:to-slate-500/90 shadow-lg hover:shadow-slate-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleReset(line.id)}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      RESET
                    </Button>
                    <Button 
                      size="sm" 
                      className={`${line.feedingEnabled 
                        ? 'bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20' 
                        : 'bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20'
                      } h-8 px-4 text-xs font-medium`}
                      onClick={() => handleEnableFeeding(line.id)}
                    >
                      <Power className="h-3 w-3 mr-1" />
                      {line.feedingEnabled ? 'DISABLE FEED' : 'ENABLE FEED'}
                    </Button>
                  </>
                ) : line.equipmentStatus === 'paused' ? (
                  <>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStart(line.id)}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      RESUME
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-orange-500/80 to-red-500/80 border-orange-400 text-orange-100 hover:from-orange-400/90 hover:to-red-400/90 shadow-lg hover:shadow-orange-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleHold(line.id)}
                    >
                      <Shield className="h-3 w-3 mr-1" />
                      HOLD
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStop(line.id)}
                    >
                      <StopCircle className="h-3 w-3 mr-1" />
                      STOP
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-slate-500/80 to-slate-600/80 border-slate-400 text-slate-100 hover:from-slate-400/90 hover:to-slate-500/90 shadow-lg hover:shadow-slate-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleReset(line.id)}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      RESET
                    </Button>
                    <Button 
                      size="sm" 
                      className={`${line.feedingEnabled 
                        ? 'bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20' 
                        : 'bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20'
                      } h-8 px-4 text-xs font-medium`}
                      onClick={() => handleEnableFeeding(line.id)}
                    >
                      <Power className="h-3 w-3 mr-1" />
                      {line.feedingEnabled ? 'DISABLE FEED' : 'ENABLE FEED'}
                    </Button>
                  </>
                ) : line.equipmentStatus === 'held' ? (
                  <>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStart(line.id)}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      RESUME
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStop(line.id)}
                    >
                      <StopCircle className="h-3 w-3 mr-1" />
                      STOP
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-slate-500/80 to-slate-600/80 border-slate-400 text-slate-100 hover:from-slate-400/90 hover:to-slate-500/90 shadow-lg hover:shadow-slate-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleReset(line.id)}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      RESET
                    </Button>
                    <Button 
                      size="sm" 
                      className={`${line.feedingEnabled 
                        ? 'bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20' 
                        : 'bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20'
                      } h-8 px-4 text-xs font-medium`}
                      onClick={() => handleEnableFeeding(line.id)}
                    >
                      <Power className="h-3 w-3 mr-1" />
                      {line.feedingEnabled ? 'DISABLE FEED' : 'ENABLE FEED'}
                    </Button>
                  </>
                ) : line.equipmentStatus === 'idle' && (line.currentOrder || line.queuedOrders.some(o => o.status === 'released')) ? (
                  <>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleStart(line.id)}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      START
                    </Button>
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-slate-500/80 to-slate-600/80 border-slate-400 text-slate-100 hover:from-slate-400/90 hover:to-slate-500/90 shadow-lg hover:shadow-slate-500/20 h-8 px-4 text-xs font-medium"
                      onClick={() => handleReset(line.id)}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      RESET
                    </Button>
                    <Button 
                      size="sm" 
                      className={`${line.feedingEnabled 
                        ? 'bg-gradient-to-r from-red-600/80 to-red-700/80 border-red-500 text-red-100 hover:from-red-500/90 hover:to-red-600/90 shadow-lg hover:shadow-red-500/20' 
                        : 'bg-gradient-to-r from-emerald-500/80 to-green-600/80 border-emerald-400 text-emerald-100 hover:from-emerald-400/90 hover:to-green-500/90 shadow-lg hover:shadow-emerald-500/20'
                      } h-8 px-4 text-xs font-medium`}
                      onClick={() => handleEnableFeeding(line.id)}
                    >
                      <Power className="h-3 w-3 mr-1" />
                      {line.feedingEnabled ? 'DISABLE FEED' : 'ENABLE FEED'}
                    </Button>
                  </>
                ) : line.equipmentStatus === 'maintenance' ? (
                  <div className="text-center text-xs text-orange-400 py-2 font-medium">
                    <Wrench className="h-4 w-4 inline mr-2" />
                    EQUIPMENT UNDER MAINTENANCE
                  </div>
                ) : (
                  <div className="text-center text-xs text-slate-500 py-2 font-medium">
                    <Clock className="h-4 w-4 inline mr-2" />
                    NO ACTIVE ORDERS - CREATE ORDER TO ENABLE CONTROLS
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* New Order Dialog */}
      <Dialog open={showNewOrderDialog} onOpenChange={setShowNewOrderDialog}>
        <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Production Order - {selectedLine?.name}</DialogTitle>
          </DialogHeader>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleNewOrder)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="orderNumber"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-300">Work Order Number</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="WO-2025-XXX"
                          className="bg-slate-800 border-slate-600 text-white placeholder-slate-500"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-red-400" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="recipeId"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-300">Recipe</FormLabel>
                      <Select onValueChange={(value) => field.onChange(parseInt(value))} value={field.value.toString()}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                            <SelectValue placeholder="Select recipe" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          {availableRecipes.map((recipe) => (
                            <SelectItem key={recipe.id} value={recipe.id.toString()}>
                              {recipe.name} ({recipe.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage className="text-red-400" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="targetQuantity"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-300">Target Quantity</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="5000"
                          className="bg-slate-800 border-slate-600 text-white placeholder-slate-500"
                          {...field}
                          onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                        />
                      </FormControl>
                      <FormMessage className="text-red-400" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="unit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-300">Unit</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="kg">Kilograms (kg)</SelectItem>
                          <SelectItem value="tons">Tons (t)</SelectItem>
                          <SelectItem value="liters">Liters (L)</SelectItem>
                          <SelectItem value="units">Units (pcs)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage className="text-red-400" />
                    </FormItem>
                  )}
                />

                <div className="md:col-span-2">
                  <FormField
                    control={form.control}
                    name="priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-slate-300">Priority Level</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="bg-slate-800 border-slate-700">
                            <SelectItem value="low">Low Priority</SelectItem>
                            <SelectItem value="normal">Normal Priority</SelectItem>
                            <SelectItem value="high">High Priority</SelectItem>
                            <SelectItem value="urgent">Urgent Priority</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage className="text-red-400" />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {/* Recipe Details Preview */}
              {form.watch('recipeId') > 0 && (
                <div className="bg-slate-800/50 p-4 rounded border border-slate-600/50">
                  <h4 className="text-white font-medium mb-3">Recipe Details</h4>
                  {(() => {
                    const selectedRecipe = availableRecipes.find(r => r.id === form.watch('recipeId'))
                    return selectedRecipe ? (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-slate-400">Category</span>
                          <div className="text-white">{selectedRecipe.category}</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Batch Size</span>
                          <div className="text-white">{selectedRecipe.batchSize.toLocaleString()} kg</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Duration</span>
                          <div className="text-white">{selectedRecipe.duration} min</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Ingredients</span>
                          <div className="text-white">{selectedRecipe.ingredients}</div>
                        </div>
                      </div>
                    ) : null
                  })()}
                </div>
              )}

              <div className="flex items-center justify-end gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  className="bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600"
                  onClick={() => {
                    form.reset()
                    setShowNewOrderDialog(false)
                    setSelectedLine(null)
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-cyan-600 hover:bg-cyan-700 text-white"
                >
                  Create Order
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </WaterSystemLayout>
  )
}