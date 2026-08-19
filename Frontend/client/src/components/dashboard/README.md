# Customizable Dashboard Components

This directory contains the customizable dashboard components for the Hercules SFMS system, allowing users to create personalized chart layouts for Milling and Packing operations.

## Components

### 1. ChartCard (`ChartCard.tsx`)
A reusable card component that wraps individual charts with:
- **Drag handle**: Allows users to drag and reposition charts
- **Remove button**: X icon in top-right corner to remove charts
- **Hover animations**: Smooth scale and glow effects
- **Theme support**: Full dark/light mode compatibility
- **Glassmorphism design**: Modern translucent card styling

### 2. CustomizableDashboard (`CustomizableDashboard.tsx`)
The main dashboard component featuring:
- **Drag-and-drop layout**: Using react-grid-layout for responsive grid positioning
- **Chart management**: Add/remove charts dynamically
- **Layout persistence**: Saves user preferences to localStorage
- **Responsive design**: Adapts to different screen sizes
- **Operation-specific**: Separate layouts for Milling and Packing

### 3. Example Charts (`charts/ExampleCharts.tsx`)
A collection of pre-built chart components using Recharts:
- **PieChart**: Production distribution visualization
- **BarChart**: Line performance comparison
- **LineChart**: Throughput vs efficiency trends
- **AreaChart**: Production trend analysis
- **RadialBarChart**: System metrics gauge
- **DoughnutChart**: Machine status overview
- **ComposedChart**: Combined bar and line charts

## Features

### 🎨 Modern UI/UX
- Clean, modern design with glassmorphism effects
- Smooth animations and micro-interactions
- Hover effects with scale transforms and glow
- Floating particle effects in dark mode

### 🌓 Theme Support
- Full dark/light mode compatibility
- Dynamic color schemes using Tailwind classes
- Theme-aware chart colors and tooltips
- Consistent styling across all components

### 📱 Responsive Design
- Mobile-first approach with responsive breakpoints
- Adaptive grid layouts for different screen sizes
- Touch-friendly drag handles and controls
- Optimized for desktop, tablet, and mobile

### 💾 Data Persistence
- Layout positions saved to localStorage
- Chart configurations preserved between sessions
- Operation-specific storage (separate for Milling/Packing)
- Automatic restoration on page reload

### 🔧 Customization Options
- Add/remove charts dynamically
- Drag-and-drop repositioning
- Resizable chart containers
- Reset to default layout option

## Usage

### Integration with SAPDashboard
The customizable dashboard is integrated into the existing SAPDashboard component with a toggle button:

```tsx
// Toggle between standard and customizable dashboard
const [useCustomizableDashboard, setUseCustomizableDashboard] = useState(false);

// In the render method
{useCustomizableDashboard ? (
  <CustomizableDashboard operation="milling" kpiData={kpiData} />
) : (
  // Standard dashboard charts
)}
```

### Adding New Chart Types
To add new chart types, extend the `chartTypes` array in `CustomizableDashboard.tsx`:

```tsx
const chartTypes: ChartConfig[] = [
  // ... existing charts
  { 
    id: 'new-chart', 
    type: 'new-chart', 
    title: 'New Chart Title', 
    component: NewChartComponent 
  }
];
```

### Customizing Chart Data
Charts use sample data defined in `ExampleCharts.tsx`. To connect with real data:

1. Pass KPI data through props
2. Modify chart components to use real data
3. Update data transformation logic as needed

## Technical Details

### Dependencies
- **react-grid-layout**: Drag-and-drop grid functionality
- **recharts**: Chart rendering and visualization
- **lucide-react**: Icon components
- **Tailwind CSS**: Styling and theming

### Browser Support
- Modern browsers with CSS Grid support
- ES6+ JavaScript features
- LocalStorage API for persistence

### Performance
- Lazy loading of chart components
- Optimized re-renders with React.memo
- Efficient drag-and-drop with react-grid-layout
- Minimal bundle size impact

## File Structure
```
dashboard/
├── ChartCard.tsx              # Reusable chart card component
├── CustomizableDashboard.tsx  # Main dashboard component
├── charts/
│   └── ExampleCharts.tsx      # Pre-built chart components
└── README.md                  # This documentation
```

## Future Enhancements
- Chart data export functionality
- Custom chart creation wizard
- Dashboard sharing capabilities
- Advanced filtering and date range selection
- Real-time data streaming integration
- Chart annotation and notes features
