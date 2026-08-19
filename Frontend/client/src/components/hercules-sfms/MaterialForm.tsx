import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { insertMaterialSchema, type InsertMaterial, type Material } from '../../types/material'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'

interface MaterialFormProps {
  material?: Material
  onSubmit: (data: InsertMaterial) => void
  onCancel: () => void
  isLoading?: boolean
}

const materialTypes = [
  'Raw Material',
  'Treated Material',
  'Finished Product',
  'Chemical',
  'Equipment'
]

const units = [
  'KG',
  'L',
  'Units',
  'Tons',
  'ML',
  'Pieces',
  'Meters'
]

export function MaterialForm({ material, onSubmit, onCancel, isLoading }: MaterialFormProps) {
  const form = useForm<InsertMaterial>({
    resolver: zodResolver(insertMaterialSchema),
    defaultValues: {
      name: material?.name || '',
      code: material?.code || '',
      type: material?.type || 'Raw Material',
      stock: material?.stock || 0,
      unit: material?.unit || 'KG',
      cost: material?.cost || 0,
      reorderLevel: material?.reorderLevel || 0,
      status: material?.status || 'In Stock',
      supplier: material?.supplier || '',
      description: material?.description || '',
    }
  })

  const handleSubmit = (data: InsertMaterial) => {
    onSubmit(data)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Material Name</FormLabel>
                <FormControl>
                  <Input 
                    placeholder="Enter material name" 
                    {...field}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Material Code</FormLabel>
                <FormControl>
                  <Input 
                    placeholder="Enter material code" 
                    {...field}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Material Type</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white">
                      <SelectValue placeholder="Select material type" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {materialTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="unit"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Unit</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="bg-slate-800/50 border-slate-600 text-white">
                      <SelectValue placeholder="Select unit" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {units.map((unit) => (
                      <SelectItem key={unit} value={unit}>
                        {unit}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <FormField
            control={form.control}
            name="stock"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Current Stock</FormLabel>
                <FormControl>
                  <Input 
                    type="number"
                    step="0.01"
                    placeholder="0"
                    {...field}
                    onChange={e => field.onChange(parseFloat(e.target.value) || 0)}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="cost"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Unit Cost ($)</FormLabel>
                <FormControl>
                  <Input 
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    {...field}
                    onChange={e => field.onChange(parseFloat(e.target.value) || 0)}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="reorderLevel"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Reorder Level</FormLabel>
                <FormControl>
                  <Input 
                    type="number"
                    step="0.01"
                    placeholder="0"
                    {...field}
                    onChange={e => field.onChange(parseFloat(e.target.value) || 0)}
                    className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="supplier"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Supplier</FormLabel>
              <FormControl>
                <Input 
                  placeholder="Enter supplier name" 
                  {...field}
                  className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea 
                  placeholder="Enter material description" 
                  {...field}
                  className="bg-slate-800/50 border-slate-600 text-white placeholder:text-slate-400 min-h-[80px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end space-x-3 pt-4">
          <Button 
            type="button" 
            variant="outline" 
            onClick={onCancel}
            disabled={isLoading}
            className="border-slate-600 text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </Button>
          <Button 
            type="submit" 
            disabled={isLoading}
            className="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 dark:from-cyan-600 dark:to-blue-600 dark:hover:from-cyan-700 dark:hover:to-blue-700"
          >
            {isLoading ? 'Saving...' : material ? 'Update Material' : 'Create Material'}
          </Button>
        </div>
      </form>
    </Form>
  )
}