// Bridge to the Python Api class exposed by pywebview as window.pywebview.api.

import type { CaseData, DesignData, Position, Weights } from './types'

export interface BackendApi {
  ping(): Promise<string>
  list_cases(): Promise<string[]>
  load_case(fileName: string): Promise<CaseData>
  open_case(): Promise<CaseData | null>
  design(weights: Weights): Promise<DesignData>
  save_layout(positions: Position[]): Promise<void>
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
