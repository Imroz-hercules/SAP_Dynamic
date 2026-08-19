import React from 'react'
import { BarChart3, LineChart, PieChart, Activity, TrendingUp, Dot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChartTypeSelectorProps {
  value: 'line' | 'bar' | 'pie' | 'donut' | 'area' | 'scatter'
  onChange: (chartType: 'line' | 'bar' | 'pie' | 'donut' | 'area' | 'scatter') => void
}

const CHART_TYPES = [
  {
    id: 'line' as const,
    label: 'Line Chart',
    description: 'Best for trends over time',
    icon: <LineChart size={16} />
  },
  {
    id: 'bar' as const,
    label: 'Bar Chart',
    description: 'Compare categories',
    icon: <BarChart3 size={16} />
  },
  {
    id: 'area' as const,
    label: 'Area Chart',
    description: 'Filled line chart for volumes',
    icon: <Activity size={16} />
  },
  {
    id: 'pie' as const,
    label: 'Pie Chart',
    description: 'Show parts of a whole',
    icon: <PieChart size={16} />
  },
  {
    id: 'donut' as const,
    label: 'Donut Chart',
    description: 'Pie chart with center space',
    icon: <PieChart size={16} />
  },
  {
    id: 'scatter' as const,
    label: 'Scatter Plot',
    description: 'Show correlation between variables',
    icon: <Dot size={16} />
  }
]

export function ChartTypeSelector({ value, onChange }: ChartTypeSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-3">
        Chart Type
      </label>

      <div className="grid grid-cols-2 gap-2">
        {CHART_TYPES.map((chartType) => (
          <button
            key={chartType.id}
            onClick={() => onChange(chartType.id)}
            className={cn(
              'p-3 rounded-lg border transition-all duration-200 text-left',
              value === chartType.id
                ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400'
                : 'border-slate-700/50 bg-slate-800/30 text-slate-300 hover:border-slate-600/50 hover:bg-slate-700/30'
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={cn(
                'flex-shrink-0',
                value === chartType.id ? 'text-cyan-400' : 'text-slate-400'
              )}>
                {chartType.icon}
              </div>
              <div className="font-medium text-sm">{chartType.label}</div>
            </div>
            <div className="text-xs text-slate-500">{chartType.description}</div>
            {value === chartType.id && (
              <div className="mt-2">
                <div className="w-2 h-2 rounded-full bg-cyan-400"></div>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Chart preview */}
      <div className="mt-4 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
        <div className="text-xs text-slate-400 mb-2">Preview</div>
        <div className="h-16 bg-slate-900/50 rounded flex items-center justify-center">
          <div className={cn(
            'text-2xl',
            value === 'line' ? 'text-cyan-400' : 'text-slate-600'
          )}>
            {CHART_TYPES.find(t => t.id === value)?.icon}
          </div>
        </div>
      </div>
    </div>
  )
}