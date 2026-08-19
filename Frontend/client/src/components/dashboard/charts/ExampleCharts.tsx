import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart,
  RadialBarChart,
  RadialBar,
  ComposedChart
} from 'recharts';
import { useTheme } from '../../../contexts/ThemeContext';

// Sample data for different chart types
const pieData = [
  { name: 'Flour', value: 45, color: '#22c55e' },
  { name: 'Bran', value: 25, color: '#f59e0b' },
  { name: 'Semolina', value: 20, color: '#3b82f6' },
  { name: 'Other', value: 10, color: '#8b5cf6' }
];

const barData = [
  { name: 'Line 1', value: 27, target: 30 },
  { name: 'Line 2', value: 26, target: 30 },
  { name: 'Line 3', value: 27, target: 30 },
  { name: 'Line 4', value: 24, target: 30 },
  { name: 'Line 5', value: 26, target: 30 }
];

const lineData = [
  { time: '00:00', throughput: 10, efficiency: 30 },
  { time: '04:00', throughput: 12, efficiency: 32 },
  { time: '08:00', throughput: 15, efficiency: 35 },
  { time: '12:00', throughput: 14, efficiency: 33 },
  { time: '16:00', throughput: 13, efficiency: 31 },
  { time: '20:00', throughput: 11, efficiency: 29 }
];

const trendData = [
  { month: 'Jan', production: 2400, target: 2500 },
  { month: 'Feb', production: 1398, target: 2500 },
  { month: 'Mar', production: 9800, target: 2500 },
  { month: 'Apr', production: 3908, target: 2500 },
  { month: 'May', production: 4800, target: 2500 },
  { month: 'Jun', production: 3800, target: 2500 }
];

const gaugeData = [
  { name: 'Utilization', value: 75, fill: '#22c55e' },
  { name: 'Efficiency', value: 85, fill: '#3b82f6' },
  { name: 'Quality', value: 92, fill: '#8b5cf6' }
];

const donutData = [
  { name: 'Active', value: 33, fill: '#22c55e' },
  { name: 'Idle', value: 65, fill: '#f59e0b' },
  { name: 'Maintenance', value: 2, fill: '#ef4444' }
];

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: any) => {
  const { theme } = useTheme();
  
  if (active && payload && payload.length) {
    return (
      <div className={`p-3 rounded-lg border backdrop-blur-md ${
        theme === 'light' 
          ? 'bg-white/90 border-slate-300 text-slate-800' 
          : 'bg-slate-800/90 border-slate-600 text-slate-200'
      }`}>
        <p className="font-medium">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Pie Chart Component
export const PieChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={pieData}
          cx="50%"
          cy="50%"
          innerRadius={40}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {pieData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

// Bar Chart Component
export const BarChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e5e7eb' : '#374151'} />
        <XAxis 
          dataKey="name" 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <YAxis 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
        <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="target" fill="#22c55e" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};

// Line Chart Component
export const LineChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={lineData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e5e7eb' : '#374151'} />
        <XAxis 
          dataKey="time" 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <YAxis 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
        <Line 
          type="monotone" 
          dataKey="throughput" 
          stroke="#3b82f6" 
          strokeWidth={3}
          dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
        />
        <Line 
          type="monotone" 
          dataKey="efficiency" 
          stroke="#8b5cf6" 
          strokeWidth={3}
          dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: '#8b5cf6', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

// Area Chart Component (Trend)
export const TrendChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <defs>
          <linearGradient id="colorProduction" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
          </linearGradient>
          <linearGradient id="colorTarget" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e5e7eb' : '#374151'} />
        <XAxis 
          dataKey="month" 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <YAxis 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
        <Area 
          type="monotone" 
          dataKey="production" 
          stroke="#3b82f6" 
          fillOpacity={1} 
          fill="url(#colorProduction)" 
          strokeWidth={2}
        />
        <Area 
          type="monotone" 
          dataKey="target" 
          stroke="#22c55e" 
          fillOpacity={1} 
          fill="url(#colorTarget)" 
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// Gauge Chart Component (Radial Bar)
export const GaugeChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="80%" data={gaugeData}>
        <RadialBar 
          dataKey="value" 
          cornerRadius={10} 
          fill="#3b82f6"
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
      </RadialBarChart>
    </ResponsiveContainer>
  );
};

// Doughnut Chart Component
export const DoughnutChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={donutData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {donutData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

// Composed Chart (Bar + Line)
export const ComposedChartExample: React.FC = () => {
  const { theme } = useTheme();
  
  const composedData = [
    { name: 'Jan', production: 2400, efficiency: 85 },
    { name: 'Feb', production: 1398, efficiency: 78 },
    { name: 'Mar', production: 9800, efficiency: 92 },
    { name: 'Apr', production: 3908, efficiency: 88 },
    { name: 'May', production: 4800, efficiency: 90 },
    { name: 'Jun', production: 3800, efficiency: 87 }
  ];
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={composedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme === 'light' ? '#e5e7eb' : '#374151'} />
        <XAxis 
          dataKey="name" 
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <YAxis 
          yAxisId="left"
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <YAxis 
          yAxisId="right" 
          orientation="right"
          tick={{ fontSize: 10, fill: theme === 'light' ? '#374151' : '#e5e7eb' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend 
          wrapperStyle={{
            color: theme === 'light' ? '#374151' : '#e5e7eb',
            fontSize: '10px',
            lineHeight: '12px'
          }}
        />
        <Bar yAxisId="left" dataKey="production" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        <Line yAxisId="right" type="monotone" dataKey="efficiency" stroke="#22c55e" strokeWidth={3} />
      </ComposedChart>
    </ResponsiveContainer>
  );
};
