import { z } from 'zod'

// Material schema for validation
export const insertMaterialSchema = z.object({
  name: z.string().min(1, 'Material name is required'),
  code: z.string().min(1, 'Material code is required'),
  type: z.string().min(1, 'Material type is required'),
  stock: z.number().min(0, 'Stock must be non-negative'),
  unit: z.string().min(1, 'Unit is required'),
  cost: z.number().min(0, 'Cost must be non-negative'),
  reorderLevel: z.number().min(0, 'Reorder level must be non-negative'),
  status: z.string().default('In Stock'),
  supplier: z.string().optional(),
  description: z.string().optional(),
  location: z.string().optional(),
})

export const updateMaterialSchema = insertMaterialSchema.partial()

// Types derived from schemas
export type InsertMaterial = z.infer<typeof insertMaterialSchema>
export type UpdateMaterial = z.infer<typeof updateMaterialSchema>

// Material type with ID for existing materials
export interface Material extends InsertMaterial {
  id: number
  createdAt?: string
  updatedAt?: string
}

