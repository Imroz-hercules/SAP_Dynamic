import React, { useState } from 'react'
import { WaterSystemLayout } from '../../components/water-system/WaterSystemLayout'
import { Truck, Package, Calendar, MapPin, CheckCircle, Clock, FileText, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// Mock data for Intake Lines with correct columns
const intakeLine1Data = [
  { id: 1, badgeNo: 'B001', sourceMaterialCode: 'WH-001', declaredQuantityKG: '25000', destinationSilo1: 'SILO-A1', destinationSilo2: 'SILO-A2', rfidBadgeReading: 'RFID-001', activeBadge: 'Yes', activeDestination: 'SILO-A1', statusWord: 'Active' },
  { id: 2, badgeNo: 'B002', sourceMaterialCode: 'CR-002', declaredQuantityKG: '30000', destinationSilo1: 'SILO-B1', destinationSilo2: 'SILO-B2', rfidBadgeReading: 'RFID-002', activeBadge: 'Yes', activeDestination: 'SILO-B1', statusWord: 'Completed' },
  { id: 3, badgeNo: 'B003', sourceMaterialCode: 'RC-003', declaredQuantityKG: '28000', destinationSilo1: 'SILO-C1', destinationSilo2: 'SILO-C2', rfidBadgeReading: 'RFID-003', activeBadge: 'No', activeDestination: 'N/A', statusWord: 'Pending' }
]

const intakeLine2Data = [
  { id: 1, badgeNo: 'B004', sourceMaterialCode: 'BR-004', declaredQuantityKG: '32000', destinationSilo1: 'SILO-D1', destinationSilo2: 'SILO-D2', rfidBadgeReading: 'RFID-004', activeBadge: 'Yes', activeDestination: 'SILO-D1', statusWord: 'Active' },
  { id: 2, badgeNo: 'B005', sourceMaterialCode: 'SB-005', declaredQuantityKG: '27000', destinationSilo1: 'SILO-E1', destinationSilo2: 'SILO-E2', rfidBadgeReading: 'RFID-005', activeBadge: 'Yes', activeDestination: 'SILO-E2', statusWord: 'Completed' },
  { id: 3, badgeNo: 'B006', sourceMaterialCode: 'WH-006', declaredQuantityKG: '35000', destinationSilo1: 'SILO-F1', destinationSilo2: 'SILO-F2', rfidBadgeReading: 'RFID-006', activeBadge: 'Yes', activeDestination: 'SILO-F1', statusWord: 'Processing' }
]

const mineralIntakeData = [
  { id: 1, badgeNo: 'B007', sourceMaterialCode: 'LS-007', declaredQuantityKG: '40000', destinationSilo1: 'SILO-G1', destinationSilo2: 'SILO-G2', rfidBadgeReading: 'RFID-007', activeBadge: 'Yes', activeDestination: 'SILO-G1', statusWord: 'Active' },
  { id: 2, badgeNo: 'B008', sourceMaterialCode: 'SL-008', declaredQuantityKG: '15000', destinationSilo1: 'SILO-H1', destinationSilo2: 'SILO-H2', rfidBadgeReading: 'RFID-008', activeBadge: 'No', activeDestination: 'N/A', statusWord: 'Completed' },
  { id: 3, badgeNo: 'B009', sourceMaterialCode: 'PH-009', declaredQuantityKG: '22000', destinationSilo1: 'SILO-I1', destinationSilo2: 'SILO-I2', rfidBadgeReading: 'RFID-009', activeBadge: 'Yes', activeDestination: 'SILO-I2', statusWord: 'Pending' }
]

const outloading1Data = [
  { id: 1, badgeNo: 'B010', sourceMaterialCode: 'FM-A01', rfidSet: 'SET-001', declaredQuantityKG: '28000', destinationSilo1: 'OUT-S1', destinationSilo2: 'OUT-S2', rfidBadgeReading: 'RFID-010', activeBadge: 'Yes', activeDestination: 'OUT-S1', statusWord: 'Loading', activDestSet: 'SET-A1' },
  { id: 2, badgeNo: 'B011', sourceMaterialCode: 'CF-B02', rfidSet: 'SET-002', declaredQuantityKG: '35000', destinationSilo1: 'OUT-S3', destinationSilo2: 'OUT-S4', rfidBadgeReading: 'RFID-011', activeBadge: 'Yes', activeDestination: 'OUT-S3', statusWord: 'Completed', activDestSet: 'SET-A2' },
  { id: 3, badgeNo: 'B012', sourceMaterialCode: 'CTF-C03', rfidSet: 'SET-003', declaredQuantityKG: '42000', destinationSilo1: 'OUT-S5', destinationSilo2: 'OUT-S6', rfidBadgeReading: 'RFID-012', activeBadge: 'No', activeDestination: 'N/A', statusWord: 'Scheduled', activDestSet: 'N/A' }
]

const outloading2Data = [
  { id: 1, badgeNo: 'B013', sourceMaterialCode: 'PM-D04', rfidSet: 'SET-004', declaredQuantityKG: '38000', destinationSilo1: 'OUT-S7', destinationSilo2: 'OUT-S8', rfidBadgeReading: 'RFID-013', activeBadge: 'Yes', activeDestination: 'OUT-S7', statusWord: 'Loading', activDestSet: 'SET-B1' },
  { id: 2, badgeNo: 'B014', sourceMaterialCode: 'OF-E05', rfidSet: 'SET-005', declaredQuantityKG: '25000', destinationSilo1: 'OUT-S9', destinationSilo2: 'OUT-S10', rfidBadgeReading: 'RFID-014', activeBadge: 'Yes', activeDestination: 'OUT-S9', statusWord: 'Completed', activDestSet: 'SET-B2' },
  { id: 3, badgeNo: 'B015', sourceMaterialCode: 'LF-F06', rfidSet: 'SET-006', declaredQuantityKG: '30000', destinationSilo1: 'OUT-S11', destinationSilo2: 'OUT-S12', rfidBadgeReading: 'RFID-015', activeBadge: 'Yes', activeDestination: 'OUT-S11', statusWord: 'Preparing', activDestSet: 'SET-B3' }
]

const outloading3Data = [
  { id: 1, badgeNo: 'B016', sourceMaterialCode: 'SF-G07', rfidSet: 'SET-007', declaredQuantityKG: '33000', destinationSilo1: 'OUT-S13', destinationSilo2: 'OUT-S14', rfidBadgeReading: 'RFID-016', activeBadge: 'Yes', activeDestination: 'OUT-S13', statusWord: 'Loading', activDestSet: 'SET-C1' },
  { id: 2, badgeNo: 'B017', sourceMaterialCode: 'FF-H08', rfidSet: 'SET-008', declaredQuantityKG: '20000', destinationSilo1: 'OUT-S15', destinationSilo2: 'OUT-S16', rfidBadgeReading: 'RFID-017', activeBadge: 'Yes', activeDestination: 'OUT-S15', statusWord: 'Completed', activDestSet: 'SET-C2' },
  { id: 3, badgeNo: 'B018', sourceMaterialCode: 'TF-I09', rfidSet: 'SET-009', declaredQuantityKG: '36000', destinationSilo1: 'OUT-S17', destinationSilo2: 'OUT-S18', rfidBadgeReading: 'RFID-018', activeBadge: 'No', activeDestination: 'N/A', statusWord: 'Scheduled', activDestSet: 'N/A' }
]

const bulkLineData = [
  { id: 1, badgeNo: 'B019', sourceMaterialCode: 'BG-001', feed: 'Bulk Grain Mix', recipeName: 'BulkRecipe_01', recipeSet: 'R-SET-001', recipeQuantity: '50000', recipeQuantityConsumed: '48500', weightInv: '49200', weightWt: '49800', weightOn: '50100' },
  { id: 2, badgeNo: 'B020', sourceMaterialCode: 'RM-002', feed: 'Raw Material Blend', recipeName: 'BulkRecipe_02', recipeSet: 'R-SET-002', recipeQuantity: '45000', recipeQuantityConsumed: '44200', weightInv: '44800', weightWt: '45200', weightOn: '45500' },
  { id: 3, badgeNo: 'B021', sourceMaterialCode: 'FI-003', feed: 'Feed Ingredient Mix', recipeName: 'BulkRecipe_03', recipeSet: 'R-SET-003', recipeQuantity: '38000', recipeQuantityConsumed: '37100', weightInv: '37600', weightWt: '38200', weightOn: '38400' },
  { id: 4, badgeNo: 'B022', sourceMaterialCode: 'PM-004', feed: 'Premium Mix', recipeName: 'BulkRecipe_04', recipeSet: 'R-SET-004', recipeQuantity: '42000', recipeQuantityConsumed: '41300', weightInv: '41800', weightWt: '42100', weightOn: '42300' },
  { id: 5, badgeNo: 'B023', sourceMaterialCode: 'SM-005', feed: 'Standard Mix', recipeName: 'BulkRecipe_05', recipeSet: 'R-SET-005', recipeQuantity: '35000', recipeQuantityConsumed: '34500', weightInv: '34800', weightWt: '35100', weightOn: '35200' }
]

const ptLineData = [
  { id: 1, badgeNo: 'B024', sourceMaterialCode: 'PT-001A', feed: 'Premium Feed A', recipeName: 'PTRecipe_01', recipeSet: 'PT-SET-001', recipeQuantity: '29000', recipeQuantityConsumed: '28200', weightInv: '28500', weightWt: '28800', weightOn: '29100', productionLine: 'PT-LINE-A', batchNo: 'BATCH-001', qualityGrade: 'Grade-A' },
  { id: 2, badgeNo: 'B025', sourceMaterialCode: 'PT-002B', feed: 'Special Mix B', recipeName: 'PTRecipe_02', recipeSet: 'PT-SET-002', recipeQuantity: '32000', recipeQuantityConsumed: '31400', weightInv: '31700', weightWt: '32100', weightOn: '32300', productionLine: 'PT-LINE-B', batchNo: 'BATCH-002', qualityGrade: 'Grade-B' },
  { id: 3, badgeNo: 'B026', sourceMaterialCode: 'PT-003C', feed: 'Custom Blend C', recipeName: 'PTRecipe_03', recipeSet: 'PT-SET-003', recipeQuantity: '27000', recipeQuantityConsumed: '26300', weightInv: '26600', weightWt: '27200', weightOn: '27400', productionLine: 'PT-LINE-C', batchNo: 'BATCH-003', qualityGrade: 'Grade-A' },
  { id: 4, badgeNo: 'B027', sourceMaterialCode: 'PT-004D', feed: 'Advanced Mix D', recipeName: 'PTRecipe_04', recipeSet: 'PT-SET-004', recipeQuantity: '35000', recipeQuantityConsumed: '34100', weightInv: '34500', weightWt: '34900', weightOn: '35200', productionLine: 'PT-LINE-D', batchNo: 'BATCH-004', qualityGrade: 'Grade-A' },
  { id: 5, badgeNo: 'B028', sourceMaterialCode: 'PT-005E', feed: 'Standard Mix E', recipeName: 'PTRecipe_05', recipeSet: 'PT-SET-005', recipeQuantity: '24000', recipeQuantityConsumed: '23400', weightInv: '23700', weightWt: '24100', weightOn: '24300', productionLine: 'PT-LINE-E', batchNo: 'BATCH-005', qualityGrade: 'Grade-B' }
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Completed':
      return 'text-green-400 light:text-green-600 bg-green-500/10 light:bg-green-100 border-green-500/20 light:border-green-300'
    case 'Active':
    case 'Loading':
      return 'text-blue-400 light:text-blue-600 bg-blue-500/10 light:bg-blue-100 border-blue-500/20 light:border-blue-300'
    case 'Pending':
    case 'Scheduled':
      return 'text-orange-400 light:text-orange-600 bg-orange-500/10 light:bg-orange-100 border-orange-500/20 light:border-orange-300'
    case 'Processing':
    case 'Preparing':
      return 'text-purple-400 light:text-purple-600 bg-purple-500/10 light:bg-purple-100 border-purple-500/20 light:border-purple-300'
    default:
      return 'text-slate-400 light:text-slate-600 bg-slate-500/10 light:bg-slate-100 border-slate-500/20 light:border-slate-300'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'Completed':
      return <CheckCircle className="h-3 w-3" />
    case 'Active':
    case 'Loading':
    case 'Processing':
      return <Clock className="h-3 w-3" />
    case 'Pending':
    case 'Scheduled':
    case 'Preparing':
      return <Clock className="h-3 w-3" />
    default:
      return <Clock className="h-3 w-3" />
  }
}

// Helper function to render table for intake lines
const renderIntakeTable = (data: any[], title: string) => (
  <div className="bg-slate-950/50 light:bg-white border border-slate-700/30 light:border-gray-200 rounded-lg backdrop-blur-sm light:shadow-lg">
    <div className="p-6 border-b border-slate-700/30 light:border-gray-200">
      <h3 className="text-lg font-semibold text-white light:text-gray-900">{title}</h3>
    </div>
    <div className="p-6">
      <div className="rounded-md border border-slate-700/30 light:border-gray-200">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/50 light:hover:bg-gray-50">
              <TableHead className="text-white light:text-gray-900 font-semibold">Badge No</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Source/Line Material Code</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Declared Quantity_KG</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Destination Silo1</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Destination Silo2</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">RFID_Badge Reading</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Active Badge</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Active Destination</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Status Word</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow key={item.id} className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/30 light:hover:bg-gray-50 transition-colors">
                <TableCell className="text-cyan-400 light:text-blue-600 font-medium">{item.badgeNo}</TableCell>
                <TableCell className="text-white light:text-gray-900">{item.sourceMaterialCode}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 light:bg-yellow-100 border border-yellow-500/20 light:border-yellow-300 text-yellow-400 light:text-yellow-600">
                    {item.declaredQuantityKG}
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.destinationSilo1}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.destinationSilo2}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.rfidBadgeReading}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${item.activeBadge === 'Yes' ? 'text-green-400 light:text-green-600 bg-green-500/10 light:bg-green-100 border-green-500/20 light:border-green-300' : 'text-red-400 light:text-red-600 bg-red-500/10 light:bg-red-100 border-red-500/20 light:border-red-300'}`}>
                    {item.activeBadge}
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.activeDestination}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(item.statusWord)}`}>
                    {getStatusIcon(item.statusWord)}
                    <span className="ml-1">{item.statusWord}</span>
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
)

// Helper function to render table for outloading lines
const renderOutloadingTable = (data: any[], title: string) => (
  <div className="bg-slate-950/50 light:bg-white border border-slate-700/30 light:border-gray-200 rounded-lg backdrop-blur-sm light:shadow-lg">
    <div className="p-6 border-b border-slate-700/30 light:border-gray-200">
      <h3 className="text-lg font-semibold text-white light:text-gray-900">{title}</h3>
    </div>
    <div className="p-6">
      <div className="rounded-md border border-slate-700/30 light:border-gray-200">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/50 light:hover:bg-gray-50">
              <TableHead className="text-white light:text-gray-900 font-semibold">Badge No</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Source/Line Material Code</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">RFID_SET</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Declared Quantity_KG</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Destination Silo1</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Destination Silo2</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">RFID_Badge Reading</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Active Badge</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Active Destination</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Status Word</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">ACTIV_DEST_SET</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow key={item.id} className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/30 light:hover:bg-gray-50 transition-colors">
                <TableCell className="text-cyan-400 light:text-blue-600 font-medium">{item.badgeNo}</TableCell>
                <TableCell className="text-white light:text-gray-900">{item.sourceMaterialCode}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.rfidSet}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 light:bg-yellow-100 border border-yellow-500/20 light:border-yellow-300 text-yellow-400 light:text-yellow-600">
                    {item.declaredQuantityKG}
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.destinationSilo1}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.destinationSilo2}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.rfidBadgeReading}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${item.activeBadge === 'Yes' ? 'text-green-400 light:text-green-600 bg-green-500/10 light:bg-green-100 border-green-500/20 light:border-green-300' : 'text-red-400 light:text-red-600 bg-red-500/10 light:bg-red-100 border-red-500/20 light:border-red-300'}`}>
                    {item.activeBadge}
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.activeDestination}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(item.statusWord)}`}>
                    {getStatusIcon(item.statusWord)}
                    <span className="ml-1">{item.statusWord}</span>
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.activDestSet}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
)

// Helper function to render table for bulk line
const renderBulkLineTable = (data: any[], title: string) => (
  <div className="bg-slate-950/50 light:bg-white border border-slate-700/30 light:border-gray-200 rounded-lg backdrop-blur-sm light:shadow-lg">
    <div className="p-6 border-b border-slate-700/30 light:border-gray-200">
      <h3 className="text-lg font-semibold text-white light:text-gray-900">{title}</h3>
    </div>
    <div className="p-6">
      <div className="rounded-md border border-slate-700/30 light:border-gray-200">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/50 light:hover:bg-gray-50">
              <TableHead className="text-white light:text-gray-900 font-semibold">Badge No</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Source Material Code</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Feed</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Name</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Set</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Quantity</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Quantity_CONSUMED</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_INV</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_WT</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_ON</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow key={item.id} className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/30 light:hover:bg-gray-50 transition-colors">
                <TableCell className="text-cyan-400 light:text-blue-600 font-medium">{item.badgeNo}</TableCell>
                <TableCell className="text-white light:text-gray-900">{item.sourceMaterialCode}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.feed}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.recipeName}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.recipeSet}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 light:bg-yellow-100 border border-yellow-500/20 light:border-yellow-300 text-yellow-400 light:text-yellow-600">
                    {item.recipeQuantity}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-500/10 light:bg-orange-100 border border-orange-500/20 light:border-orange-300 text-orange-400 light:text-orange-600">
                    {item.recipeQuantityConsumed}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 light:bg-blue-100 border border-blue-500/20 light:border-blue-300 text-blue-400 light:text-blue-600">
                    {item.weightInv}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 light:bg-purple-100 border border-purple-500/20 light:border-purple-300 text-purple-400 light:text-purple-600">
                    {item.weightWt}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 light:bg-green-100 border border-green-500/20 light:border-green-300 text-green-400 light:text-green-600">
                    {item.weightOn}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
)

// Helper function to render table for PT line
const renderPTLineTable = (data: any[], title: string) => (
  <div className="bg-slate-950/50 light:bg-white border border-slate-700/30 light:border-gray-200 rounded-lg backdrop-blur-sm light:shadow-lg">
    <div className="p-6 border-b border-slate-700/30 light:border-gray-200">
      <h3 className="text-lg font-semibold text-white light:text-gray-900">{title}</h3>
    </div>
    <div className="p-6">
      <div className="rounded-md border border-slate-700/30 light:border-gray-200">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/50 light:hover:bg-gray-50">
              <TableHead className="text-white light:text-gray-900 font-semibold">Badge No</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Source Material Code</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Feed</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Name</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Set</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Quantity</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Recipe_Quantity_CONSUMED</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_INV</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_WT</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Weight_ON</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Production_Line</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Batch_No</TableHead>
              <TableHead className="text-white light:text-gray-900 font-semibold">Quality_Grade</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow key={item.id} className="border-slate-700/30 light:border-gray-200 hover:bg-slate-800/30 light:hover:bg-gray-50 transition-colors">
                <TableCell className="text-cyan-400 light:text-blue-600 font-medium">{item.badgeNo}</TableCell>
                <TableCell className="text-white light:text-gray-900">{item.sourceMaterialCode}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.feed}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.recipeName}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.recipeSet}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 light:bg-yellow-100 border border-yellow-500/20 light:border-yellow-300 text-yellow-400 light:text-yellow-600">
                    {item.recipeQuantity}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-500/10 light:bg-orange-100 border border-orange-500/20 light:border-orange-300 text-orange-400 light:text-orange-600">
                    {item.recipeQuantityConsumed}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 light:bg-blue-100 border border-blue-500/20 light:border-blue-300 text-blue-400 light:text-blue-600">
                    {item.weightInv}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 light:bg-purple-100 border border-purple-500/20 light:border-purple-300 text-purple-400 light:text-purple-600">
                    {item.weightWt}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 light:bg-green-100 border border-green-500/20 light:border-green-300 text-green-400 light:text-green-600">
                    {item.weightOn}
                  </span>
                </TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.productionLine}</TableCell>
                <TableCell className="text-slate-300 light:text-gray-700">{item.batchNo}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${item.qualityGrade === 'Grade-A' ? 'text-green-400 light:text-green-600 bg-green-500/10 light:bg-green-100 border-green-500/20 light:border-green-300' : 'text-yellow-400 light:text-yellow-600 bg-yellow-500/10 light:bg-yellow-100 border-yellow-500/20 light:border-yellow-300'}`}>
                    {item.qualityGrade}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
)

export function Orders() {
  return (
    <WaterSystemLayout 
      title="Orders Management" 
      subtitle="Order processing, bay organization, and fulfillment"
    >
      <div className="space-y-6">
        <Tabs defaultValue="intake-line-1" className="w-full">
          <TabsList className="grid w-full grid-cols-4 lg:grid-cols-8 bg-slate-800/50 light:bg-gray-100">
            <TabsTrigger value="intake-line-1" className="text-xs">INTAKE LINE 1</TabsTrigger>
            <TabsTrigger value="intake-line-2" className="text-xs">INTAKE LINE 2</TabsTrigger>
            <TabsTrigger value="mineral-intake" className="text-xs">Mineral Intake</TabsTrigger>
            <TabsTrigger value="outloading-1" className="text-xs">Outloading 1</TabsTrigger>
            <TabsTrigger value="outloading-2" className="text-xs">Outloading 2</TabsTrigger>
            <TabsTrigger value="outloading-3" className="text-xs">Outloading 3</TabsTrigger>
            <TabsTrigger value="bulk-line" className="text-xs">Bulk Line</TabsTrigger>
            <TabsTrigger value="pt-line" className="text-xs">PT Line</TabsTrigger>
          </TabsList>

          <TabsContent value="intake-line-1" className="space-y-4">
            {renderIntakeTable(intakeLine1Data, "Intake Line 1 Orders")}
          </TabsContent>

          <TabsContent value="intake-line-2" className="space-y-4">
            {renderIntakeTable(intakeLine2Data, "Intake Line 2 Orders")}
          </TabsContent>

          <TabsContent value="mineral-intake" className="space-y-4">
            {renderIntakeTable(mineralIntakeData, "Mineral Intake Orders")}
          </TabsContent>

          <TabsContent value="outloading-1" className="space-y-4">
            {renderOutloadingTable(outloading1Data, "Outloading 1 Orders")}
          </TabsContent>

          <TabsContent value="outloading-2" className="space-y-4">
            {renderOutloadingTable(outloading2Data, "Outloading 2 Orders")}
          </TabsContent>

          <TabsContent value="outloading-3" className="space-y-4">
            {renderOutloadingTable(outloading3Data, "Outloading 3 Orders")}
          </TabsContent>

          <TabsContent value="bulk-line" className="space-y-4">
            {renderBulkLineTable(bulkLineData, "Bulk Line Orders")}
          </TabsContent>

          <TabsContent value="pt-line" className="space-y-4">
            {renderPTLineTable(ptLineData, "PT Line Orders")}
          </TabsContent>
        </Tabs>
      </div>
    </WaterSystemLayout>
  )
}