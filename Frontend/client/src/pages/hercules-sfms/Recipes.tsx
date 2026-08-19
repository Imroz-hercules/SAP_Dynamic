import React, { useState } from 'react'
import { WaterSystemLayout } from '../../components/water-system/WaterSystemLayout'
import { KPICard } from '../../components/water-system/KPICard'
import { Search, Filter, Plus, Edit, Trash2, Clock, CheckCircle, AlertTriangle, BookOpen, Beaker, Factory, Package } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
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

// Mock recipe data
const recipes = [
  {
    id: 1,
    name: "Premium Feed Mix A",
    code: "RCP-001",
    category: "Feed",
    batchSize: 5000,
    unit: "kg",
    duration: 45,
    status: "Active",
    ingredients: 8,
    cost: 2850.50,
    lastModified: "2025-01-15",
    description: "High-protein premium feed for livestock with enhanced nutritional profile"
  },
  {
    id: 2,
    name: "Protein Blend Special",
    code: "RCP-002", 
    category: "Protein",
    batchSize: 3200,
    unit: "kg",
    duration: 35,
    status: "Active",
    ingredients: 6,
    cost: 4200.75,
    lastModified: "2025-01-10",
    description: "Specialized protein concentrate for high-performance animal nutrition"
  },
  {
    id: 3,
    name: "Grain Meal Standard",
    code: "RCP-003",
    category: "Grain",
    batchSize: 8000,
    unit: "kg", 
    duration: 55,
    status: "Active",
    ingredients: 12,
    cost: 1950.25,
    lastModified: "2025-01-08",
    description: "Standard grain-based meal with balanced mineral content"
  },
  {
    id: 4,
    name: "Vitamin Supplement Mix",
    code: "RCP-004",
    category: "Supplement",
    batchSize: 1000,
    unit: "kg",
    duration: 25,
    status: "Draft",
    ingredients: 15,
    cost: 8500.00,
    lastModified: "2025-01-05",
    description: "Concentrated vitamin and mineral supplement for enhanced animal health"
  },
  {
    id: 5,
    name: "Feed Mix B Economy",
    code: "RCP-005",
    category: "Feed",
    batchSize: 6500,
    unit: "kg",
    duration: 40,
    status: "Inactive",
    ingredients: 5,
    cost: 1650.80,
    lastModified: "2024-12-28",
    description: "Cost-effective feed mixture for standard livestock requirements"
  }
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Active':
      return 'text-green-400 bg-green-500/10 border-green-500/20'
    case 'Draft':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    case 'Inactive':
      return 'text-red-400 bg-red-500/10 border-red-500/20'
    default:
      return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'Active':
      return <CheckCircle className="h-4 w-4" />
    case 'Draft':
      return <Clock className="h-4 w-4" />
    case 'Inactive':
      return <AlertTriangle className="h-4 w-4" />
    default:
      return <Clock className="h-4 w-4" />
  }
}

export function Recipes() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('All')
  const [filterStatus, setFilterStatus] = useState('All')

  const filteredRecipes = recipes.filter(recipe => {
    const matchesSearch = recipe.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         recipe.code.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = filterCategory === 'All' || recipe.category === filterCategory
    const matchesStatus = filterStatus === 'All' || recipe.status === filterStatus
    return matchesSearch && matchesCategory && matchesStatus
  })

  // Calculate KPIs
  const totalRecipes = recipes.length
  const activeRecipes = recipes.filter(r => r.status === 'Active').length
  const draftRecipes = recipes.filter(r => r.status === 'Draft').length
  const avgIngredients = recipes.reduce((sum, r) => sum + r.ingredients, 0) / recipes.length
  const totalCategories = new Set(recipes.map(r => r.category)).size
  const avgBatchSize = recipes.reduce((sum, r) => sum + r.batchSize, 0) / recipes.length

  return (
    <WaterSystemLayout 
      title="Recipe Management" 
      subtitle="Batch recipes and production formulations"
    >
      <div className="space-y-6">
        
        {/* Recipe KPI Cards */}
        <div className="grid grid-cols-6 gap-4">
          <KPICard
            title="TOTAL RECIPES"
            value={totalRecipes.toString()}
            subtitle="Recipe Library"
            icon="activity"
            color="blue"
            chartType="line"
          />
          <KPICard
            title="ACTIVE RECIPES"
            value={activeRecipes.toString()}
            subtitle="Production Ready"
            icon="gauge"
            color="green"
            chartType="gauge"
          />
          <KPICard
            title="DRAFT RECIPES"
            value={draftRecipes.toString()}
            subtitle="In Development"
            icon="activity"
            color="orange"
            chartType="bar"
          />
          <KPICard
            title="AVG INGREDIENTS"
            value={avgIngredients.toFixed(1)}
            subtitle="Per Recipe"
            icon="gauge"
            color="purple"
            chartType="gauge"
          />
          <KPICard
            title="CATEGORIES"
            value={totalCategories.toString()}
            subtitle="Recipe Types"
            icon="activity"
            color="cyan"
            chartType="circle"
          />
          <KPICard
            title="AVG BATCH SIZE"
            value={`${(avgBatchSize / 1000).toFixed(1)}K`}
            subtitle="kg per batch"
            icon="activity"
            color="purple"
            chartType="line"
          />
        </div>

        {/* Recipe Management Interface */}
        <div className="bg-slate-950/50 border border-slate-700/30 rounded-lg backdrop-blur-sm">
          {/* Header */}
          <div className="p-6 border-b border-slate-700/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                <BookOpen className="h-6 w-6 text-cyan-400" />
                Recipe Library
              </h3>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="bg-green-600 hover:bg-green-700 text-white">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Recipe
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-4xl">
                  <DialogHeader>
                    <DialogTitle className="text-white">Create New Recipe</DialogTitle>
                  </DialogHeader>
                  <div className="p-6">
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Recipe Name</label>
                          <Input placeholder="Enter recipe name..." className="bg-slate-800/50 border-slate-600 text-white" />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Recipe Code</label>
                          <Input placeholder="RCP-XXX" className="bg-slate-800/50 border-slate-600 text-white" />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
                          <Select>
                            <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white">
                              <SelectValue placeholder="Select category" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-800 border-slate-600">
                              <SelectItem value="feed">Feed</SelectItem>
                              <SelectItem value="protein">Protein</SelectItem>
                              <SelectItem value="grain">Grain</SelectItem>
                              <SelectItem value="supplement">Supplement</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Batch Size (kg)</label>
                          <Input type="number" placeholder="5000" className="bg-slate-800/50 border-slate-600 text-white" />
                        </div>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Duration (minutes)</label>
                          <Input type="number" placeholder="45" className="bg-slate-800/50 border-slate-600 text-white" />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                          <textarea 
                            placeholder="Recipe description..."
                            className="w-full p-3 bg-slate-800/50 border border-slate-600 rounded-md text-white placeholder-slate-400 resize-none"
                            rows={4}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6">
                      <Button variant="outline" className="bg-slate-800 text-white border-slate-600">Cancel</Button>
                      <Button className="bg-green-600 hover:bg-green-700 text-white">Create Recipe</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            
            {/* Filters */}
            <div className="grid grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Search Recipes</label>
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
                <label className="block text-sm font-medium text-slate-300 mb-2">Category Filter</label>
                <Select value={filterCategory} onValueChange={setFilterCategory}>
                  <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    <SelectItem value="All">All Categories</SelectItem>
                    <SelectItem value="Feed">Feed</SelectItem>
                    <SelectItem value="Protein">Protein</SelectItem>
                    <SelectItem value="Grain">Grain</SelectItem>
                    <SelectItem value="Supplement">Supplement</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Status Filter</label>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    <SelectItem value="All">All Status</SelectItem>
                    <SelectItem value="Active">Active</SelectItem>
                    <SelectItem value="Draft">Draft</SelectItem>
                    <SelectItem value="Inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button 
                  variant="outline" 
                  className="bg-slate-800/50 border-slate-600 text-white hover:bg-slate-700"
                  onClick={() => {
                    setSearchTerm('')
                    setFilterCategory('All')
                    setFilterStatus('All')
                  }}
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Clear Filters
                </Button>
              </div>
            </div>
          </div>

          {/* Recipes Table */}
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700/30">
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Recipe</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Code</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Category</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Batch Size</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Duration</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Ingredients</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Cost/Batch</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecipes.map((recipe) => (
                    <tr key={recipe.id} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                      <td className="px-4 py-3">
                        <div>
                          <div className="text-white font-medium">{recipe.name}</div>
                          <div className="text-xs text-slate-400 mt-1">{recipe.description.substring(0, 50)}...</div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-cyan-400 font-mono">{recipe.code}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded flex items-center gap-1 w-fit">
                          {recipe.category === 'Feed' && <Package className="h-3 w-3" />}
                          {recipe.category === 'Protein' && <Beaker className="h-3 w-3" />}
                          {recipe.category === 'Grain' && <Factory className="h-3 w-3" />}
                          {recipe.category === 'Supplement' && <Beaker className="h-3 w-3" />}
                          {recipe.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-white">{recipe.batchSize.toLocaleString()} {recipe.unit}</td>
                      <td className="px-4 py-3 text-slate-300">{recipe.duration} min</td>
                      <td className="px-4 py-3 text-white">{recipe.ingredients}</td>
                      <td className="px-4 py-3 text-white">${recipe.cost.toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 w-fit ${getStatusColor(recipe.status)}`}>
                          {getStatusIcon(recipe.status)}
                          {recipe.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-7 w-7 p-0 bg-blue-600/20 border-blue-500 hover:bg-blue-600/30"
                          >
                            <Edit className="h-3 w-3 text-blue-400" />
                          </Button>
                          
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
                                <AlertDialogTitle className="text-white">Delete Recipe</AlertDialogTitle>
                                <AlertDialogDescription className="text-slate-300">
                                  Are you sure you want to delete "{recipe.name}"? This action cannot be undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel className="bg-slate-800 text-white border-slate-600">Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-red-600 hover:bg-red-700">Delete</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredRecipes.length === 0 && (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-slate-400">
                        No recipes found matching your criteria
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