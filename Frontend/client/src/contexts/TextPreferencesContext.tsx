import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'hercules-text-prefs'

/** Font family option id -> CSS font stack for --app-font-family (professional fonts only) */
export const FONT_FAMILY_OPTIONS: { value: string; label: string; fontStack: string }[] = [
  { value: 'default', label: 'Default (system)', fontStack: 'inherit' },
  { value: 'arial', label: 'Arial', fontStack: 'Arial, Helvetica, "Helvetica Neue", sans-serif' },
  { value: 'segoe', label: 'Segoe UI', fontStack: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif' },
  { value: 'sans', label: 'Sans-serif', fontStack: 'Arial, Helvetica, "Helvetica Neue", sans-serif' },
]

export interface TextPreferences {
  fontSizeScale: number
  fontFamily: string
  bold: boolean
  italic: boolean
  underline: boolean
}

const defaults: TextPreferences = {
  fontSizeScale: 1,
  fontFamily: 'default',
  bold: false,
  italic: false,
  underline: false,
}

function loadPreferences(): TextPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<TextPreferences>
    const validFont = FONT_FAMILY_OPTIONS.some((o) => o.value === parsed.fontFamily)
    return {
      fontSizeScale: typeof parsed.fontSizeScale === 'number' ? Math.max(0.8, Math.min(1.5, parsed.fontSizeScale)) : defaults.fontSizeScale,
      fontFamily: validFont ? parsed.fontFamily! : defaults.fontFamily,
      bold: typeof parsed.bold === 'boolean' ? parsed.bold : defaults.bold,
      italic: typeof parsed.italic === 'boolean' ? parsed.italic : defaults.italic,
      underline: typeof parsed.underline === 'boolean' ? parsed.underline : defaults.underline,
    }
  } catch {
    return { ...defaults }
  }
}

function applyToDocument(prefs: TextPreferences) {
  const root = document.documentElement
  const fontOption = FONT_FAMILY_OPTIONS.find((o) => o.value === prefs.fontFamily)
  const fontStack = fontOption ? fontOption.fontStack : FONT_FAMILY_OPTIONS[0].fontStack
  root.style.setProperty('--app-font-size', `${prefs.fontSizeScale}rem`)
  root.style.setProperty('--app-font-family', fontStack)
  root.style.setProperty('--app-font-weight', prefs.bold ? 'bold' : 'normal')
  root.style.setProperty('--app-font-style', prefs.italic ? 'italic' : 'normal')
  root.style.setProperty('--app-text-decoration', prefs.underline ? 'underline' : 'none')
}

interface TextPreferencesContextType {
  preferences: TextPreferences
  setFontSizeScale: (value: number) => void
  setFontFamily: (value: string) => void
  setBold: (value: boolean) => void
  setItalic: (value: boolean) => void
  setUnderline: (value: boolean) => void
  setPreferences: (prefs: Partial<TextPreferences>) => void
}

const TextPreferencesContext = createContext<TextPreferencesContextType | undefined>(undefined)

export function TextPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferencesState] = useState<TextPreferences>(loadPreferences)

  useEffect(() => {
    applyToDocument(preferences)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
    } catch {
      // ignore storage errors
    }
  }, [preferences])

  const setFontSizeScale = (fontSizeScale: number) => {
    setPreferencesState((prev) => ({ ...prev, fontSizeScale: Math.max(0.8, Math.min(1.5, fontSizeScale)) }))
  }
  const setFontFamily = (fontFamily: string) => setPreferencesState((prev) => ({ ...prev, fontFamily }))
  const setBold = (bold: boolean) => setPreferencesState((prev) => ({ ...prev, bold }))
  const setItalic = (italic: boolean) => setPreferencesState((prev) => ({ ...prev, italic }))
  const setUnderline = (underline: boolean) => setPreferencesState((prev) => ({ ...prev, underline }))
  const setPreferences = (next: Partial<TextPreferences>) => {
    setPreferencesState((prev) => {
      const merged = { ...prev, ...next }
      if (typeof merged.fontSizeScale === 'number') {
        merged.fontSizeScale = Math.max(0.8, Math.min(1.5, merged.fontSizeScale))
      }
      return merged
    })
  }

  return (
    <TextPreferencesContext.Provider
      value={{
        preferences,
        setFontSizeScale,
        setFontFamily,
        setBold,
        setItalic,
        setUnderline,
        setPreferences,
      }}
    >
      {children}
    </TextPreferencesContext.Provider>
  )
}

export function useTextPreferences() {
  const context = useContext(TextPreferencesContext)
  if (context === undefined) {
    throw new Error('useTextPreferences must be used within a TextPreferencesProvider')
  }
  return context
}
