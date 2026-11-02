// Bridge to the Python Api class exposed by pywebview as window.pywebview.api.

export interface BackendApi {
  ping(): Promise<string>
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
