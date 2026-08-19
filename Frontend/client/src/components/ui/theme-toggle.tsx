import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className="relative inline-flex h-6 w-12 items-center rounded-full transition-colors duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-slate-900"
      style={{
        backgroundColor: theme === 'light' ? '#ffffff' : '#0891b2',
        border: theme === 'light' ? '2px solid #67e8f9' : '2px solid #22d3ee'
      }}
    >
      {/* Toggle handle */}
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-lg transition-transform duration-300 ease-in-out ${
          theme === 'light' ? 'translate-x-1' : 'translate-x-6'
        }`}
      >
        {/* Icon inside the handle */}
        <div className="flex h-full w-full items-center justify-center">
          {theme === 'light' ? (
            <Sun className="h-3 w-3 text-yellow-500" />
          ) : (
            <Moon className="h-3 w-3 text-white" />
          )}
        </div>
      </span>
      
      {/* Background icons */}
      <div className="absolute inset-0 flex items-center justify-between px-1.5">
        {/* Sun icon (left side) */}
        <Sun 
          className={`h-3 w-3 transition-opacity duration-300 ${
            theme === 'light' 
              ? 'text-yellow-500 opacity-100' 
              : 'text-slate-400 opacity-30'
          }`} 
        />
        
        {/* Moon icon (right side) */}
        <Moon 
          className={`h-3 w-3 transition-opacity duration-300 ${
            theme === 'dark' 
              ? 'text-white opacity-100' 
              : 'text-slate-400 opacity-30'
          }`} 
        />
      </div>
      
      <span className="sr-only">Toggle theme</span>
    </button>
  )
}