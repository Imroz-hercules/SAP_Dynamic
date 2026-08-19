import React, { useState } from 'react'
import { WaterSystemLayout } from '../../components/hercules-sfms/WaterSystemLayout'
import { KPICard } from '../../components/hercules-sfms/KPICard'
import { Search, Filter, Plus, AlertTriangle, CheckCircle, XCircle, Clock, Edit, Trash2, Package, Settings, MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/lib/queryClient'
import { type Material, type InsertMaterial, type UpdateMaterial } from '../../types/material'
import { MaterialForm } from '../../components/hercules-sfms/MaterialForm'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog'
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/hooks/use-toast'

const getStatusColor = (status: string) => {
  switch (status) {
    case 'In Stock':
      return 'text-green-400 bg-green-500/10 border-green-500/20'
    case 'Low Stock':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    case 'Critical':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    default:
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'In Stock':
      return <CheckCircle className="h-4 w-4" />
    case 'Low Stock':
      return <AlertTriangle className="h-4 w-4" />
    case 'Critical':
      return <XCircle className="h-4 w-4" />
    default:
      return <Clock className="h-4 w-4" />
  }
}

export default function Material() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('All')
  const [editingMaterial, setEditingMaterial] = useState<Material | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Fetch materials
  const { data: materials = [], isLoading } = useQuery<Material[]>({
    queryKey: ['/api/materials'],
  })

  // Create material mutation
  const createMaterial = useMutation({
    mutationFn: (data: InsertMaterial) => apiRequest('POST', '/api/materials', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/materials'] })
      setIsDialogOpen(false)
      toast({
        title: "Success",
        description: "Material created successfully.",
      })
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to create material. Please try again.",
        variant: "destructive",
      })
      console.error('Error creating material:', error)
    }
  })

  // Update material mutation
  const updateMaterial = useMutation({
    mutationFn: ({ id, data }: { id: number, data: UpdateMaterial }) => 
      apiRequest('PATCH', `/api/materials/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/materials'] })
      setEditingMaterial(null)
      setIsDialogOpen(false)
      toast({
        title: "Success",
        description: "Material updated successfully.",
      })
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to update material. Please try again.",
        variant: "destructive",
      })
      console.error('Error updating material:', error)
    }
  })

  // Delete material mutation
  const deleteMaterial = useMutation({
    mutationFn: (id: number) => apiRequest('DELETE', `/api/materials/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/materials'] })
      toast({
        title: "Success",
        description: "Material deleted successfully.",
      })
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to delete material. Please try again.",
        variant: "destructive",
      })
      console.error('Error deleting material:', error)
    }
  })

  const handleSubmit = (data: InsertMaterial | UpdateMaterial) => {
    if (editingMaterial) {
      updateMaterial.mutate({ id: editingMaterial.id, data: data as UpdateMaterial })
    } else {
      createMaterial.mutate(data as InsertMaterial)
    }
  }

  const filteredMaterials = materials.filter(material => {
    const matchesSearch = material.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         material.code.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterType === 'All' || material.type === filterType
    return matchesSearch && matchesFilter
  })

  // Calculate KPIs
  const totalMaterials = materials.length
  const inStockCount = materials.filter(m => m.status === 'In Stock').length
  const lowStockCount = materials.filter(m => m.status === 'Low Stock').length
  const criticalStockCount = materials.filter(m => m.status === 'Critical').length
  const totalValue = materials.reduce((sum, m) => sum + (m.stock * m.cost), 0)

  return (
    <WaterSystemLayout 
      title="Material Management" 
      subtitle="Material inventory, costs, and specifications management"
    >
      <div className="space-y-6">
        
        {/* KPI Cards */}
        <div className="grid grid-cols-6 gap-4">
          <KPICard
            title="TOTAL MATERIALS"
            value={totalMaterials.toString()}
            subtitle="Active Materials"
            icon="activity"
            color="blue"
            chartType="line"
          />
          <KPICard
            title="IN STOCK"
            value={inStockCount.toString()}
            subtitle="Available Items"
            icon="gauge"
            color="green"
            chartType="bar"
          />
          <KPICard
            title="LOW STOCK"
            value={lowStockCount.toString()}
            subtitle="Need Reorder"
            icon="activity"
            color="orange"
            chartType="gauge"
          />
          <KPICard
            title="CRITICAL"
            value={criticalStockCount.toString()}
            subtitle="Urgent Action"
            icon="gauge"
            color="orange"
            chartType="bar"
          />
          <KPICard
            title="TOTAL VALUE"
            value={`$${(totalValue / 1000).toFixed(1)}K`}
            subtitle="Inventory Worth"
            icon="activity"
            color="purple"
            chartType="line"
          />
          <KPICard
            title="EXPIRED ITEMS"
            value="1"
            subtitle="Requires Attention"
            icon="activity"
            color="purple"
            chartType="gauge"
          />
        </div>

        {/* Material Inventory Interface */}
        <div className="bg-slate-950/50 border border-slate-700/30 rounded-lg backdrop-blur-sm">
          {/* Table Header */}
          <div className="p-6 border-b border-slate-700/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Material Inventory</h3>
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button 
                    className="bg-green-600 hover:bg-green-700 text-white"
                    onClick={() => setEditingMaterial(null)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add sMaterial
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl">
                  <DialogHeader>
                    <DialogTitle className="text-white">
                      {editingMaterial ? 'Edit Material' : 'Add New Material'}
                    </DialogTitle>
                  </DialogHeader>
                  <MaterialForm
                    material={editingMaterial || undefined}
                    onSubmit={handleSubmit}
                    onCancel={() => {
                      setIsDialogOpen(false)
                      setEditingMaterial(null)
                    }}
                    isLoading={createMaterial.isPending || updateMaterial.isPending}
                  />
                </DialogContent>
              </Dialog>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Search Materials</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search by name or code..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 bg-slate-800/50 border-slate-600 text-white placeholder-slate-400"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Filter by Type</label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full p-2 bg-slate-800/50 border border-slate-600 rounded-md text-white"
                >
                  <option value="All">All Types</option>
                  <option value="Raw Material">Raw Material</option>
                  <option value="Chemical">Chemical</option>
                  <option value="Additive">Additive</option>
                  <option value="Supplement">Supplement</option>
                </select>
              </div>
              <div className="flex items-end">
                <Button 
                  variant="outline" 
                  className="bg-slate-800/50 border-slate-600 text-white hover:bg-slate-700"
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Clear Filters
                </Button>
              </div>
            </div>
          </div>

          {/* Materials Table */}
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700/30">
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Material</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Code</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Type</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Stock</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Unit</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Cost/Unit</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Location</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-slate-400">
                        Loading materials...
                      </td>
                    </tr>
                  ) : (
                    filteredMaterials.map((material) => (
                      <tr key={material.id} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                        <td className="px-4 py-3 text-white font-medium">{material.name}</td>
                        <td className="px-4 py-3 text-cyan-400 font-mono">{material.code}</td>
                        <td className="px-4 py-3 text-slate-300">{material.type}</td>
                        <td className="px-4 py-3 text-white">{material.stock.toLocaleString()}</td>
                        <td className="px-4 py-3 text-slate-300">{material.unit}</td>
                        <td className="px-4 py-3 text-white">${material.cost.toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 w-fit ${getStatusColor(material.status)}`}>
                            {getStatusIcon(material.status)}
                            {material.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300 flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {material.location}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Dialog open={isDialogOpen && editingMaterial?.id === material.id} onOpenChange={(open) => {
                              if (!open) {
                                setEditingMaterial(null)
                                setIsDialogOpen(false)
                              }
                            }}>
                              <DialogTrigger asChild>
                                <Button 
                                  size="sm" 
                                  variant="outline" 
                                  className="h-7 w-7 p-0 bg-blue-600/20 border-blue-500 hover:bg-blue-600/30"
                                  onClick={() => {
                                    setEditingMaterial(material)
                                    setIsDialogOpen(true)
                                  }}
                                >
                                  <Edit className="h-3 w-3 text-blue-400" />
                                </Button>
                              </DialogTrigger>
                              <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl">
                                <DialogHeader>
                                  <DialogTitle className="text-white">Edit Material</DialogTitle>
                                </DialogHeader>
                                <MaterialForm
                                  material={editingMaterial || undefined}
                                  onSubmit={handleSubmit}
                                  onCancel={() => {
                                    setIsDialogOpen(false)
                                    setEditingMaterial(null)
                                  }}
                                  isLoading={updateMaterial.isPending}
                                />
                              </DialogContent>
                            </Dialog>
                            
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button 
                                  size="sm" 
                                  variant="outline" 
                                  className="h-7 w-7 p-0 bg-red-600/20 border-red-500 hover:bg-red-600/30"
                                >
                                  <Trash2 className="h-3 w-3 text-red-400" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent className="bg-slate-900 border-slate-700">
                                <AlertDialogHeader>
                                  <AlertDialogTitle className="text-white">Delete Material</AlertDialogTitle>
                                  <AlertDialogDescription className="text-slate-300">
                                    Are you sure you want to delete "{material.name}"? This action cannot be undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel className="bg-slate-800 text-white border-slate-600">Cancel</AlertDialogCancel>
                                  <AlertDialogAction 
                                    onClick={() => deleteMaterial.mutate(material.id)}
                                    className="bg-red-600 hover:bg-red-700"
                                    disabled={deleteMaterial.isPending}
                                  >
                                    {deleteMaterial.isPending ? 'Deleting...' : 'Delete'}
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                  {filteredMaterials.length === 0 && !isLoading && (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-slate-400">
                        No materials found matching your criteria
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </WaterSystemLayout>
  )
}