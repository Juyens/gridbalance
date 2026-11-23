// Bridge to the Python Api class exposed by pywebview as window.pywebview.api.

import type { CaseData, DesignData, Measure, Weights } from './types'
import type { Locale } from './i18n'

export interface BackendApi {
  ping(): Promise<string>
  get_theme(): Promise<'light' | 'dark' | null>
  set_theme(theme: 'light' | 'dark'): Promise<void>
  get_language(): Promise<Locale | null>
  set_language(language: Locale): Promise<void>
  load_zone(lat: number, lon: number, radiusKm: number | null): Promise<CaseData | null>
  load_case(): Promise<CaseData>
  measure(place: { lat: number; lon: number; radiusKm: number | null } | null): Promise<Measure>
  design(weights: Weights): Promise<DesignData>
  save_export(kind: 'png' | 'csv', content: string): Promise<boolean>
}

declare global {
  interface Window {
    pywebview?: { api: BackendApi }
  }
}

// pywebview injects the api after the page loads and fires 'pywebviewready'.
export function getApi(): Promise<BackendApi> {
  return new Promise((resolve) => {
    if (window.pywebview?.api) {
      resolve(window.pywebview.api)
      return
    }
    window.addEventListener('pywebviewready', () => resolve(window.pywebview!.api), { once: true })
  })
}

// pywebview rejects with the Python exception; keep only its message.
export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String(error.message)
  }
  return String(error)
}
