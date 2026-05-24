export const API_BASE =
  import.meta.env.VITE_API_BASE ??
  (import.meta.env.DEV ? '' : 'https://inkbook-4tlr.onrender.com')

export function artistApiPath(slug: string, action: 'intake' | 'confirm-date' | 'intakes' | 'approve') {
  return `${API_BASE}/api/artists/${slug}/${action}`
}

export function artistProfilePath(slug: string) {
  return `${API_BASE}/api/artists/${slug}`
}

export function createArtistPath() {
  return `${API_BASE}/api/artists`
}

export function checkSlugPath(slug: string) {
  return `${API_BASE}/api/artists/check-slug/${slug}`
}

export function onboardPath() {
  return `${API_BASE}/api/artists/onboard`
}
