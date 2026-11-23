// Place search with Photon (https://photon.komoot.io), built on OpenStreetMap data.

const PHOTON_URL = 'https://photon.komoot.io/api/'
const MAX_RESULTS = 5
const TIMEOUT_MS = 10000

export type LngLat = [number, number]

export interface Place {
  name: string
  address: string
  center: LngLat
  bounds: [LngLat, LngLat] | null // south-west and north-east corners
  isCase?: boolean // opens the Polish grid instead of a zone
}

const example = (name: string, address: string, lat: number, lon: number): Place => ({
  name,
  address,
  center: [lon, lat],
  bounds: null,
})

export const POLAND: Place = {
  ...example('Polonia', 'case2383wp', 52, 19.3),
  isCase: true,
}

// Shown before typing: zones of very different size.
export const EXAMPLES: Place[] = [
  example('UPC San Miguel', 'Lima', -12.0764, -77.0934),
  example('Miraflores', 'Lima', -12.1211, -77.0297),
  example('Plaza de Armas', 'Cusco', -13.517, -71.9785),
  example('Plaza de Armas', 'Arequipa', -16.3988, -71.5369),
  example('Oxapampa', 'Pasco', -10.5776, -75.4026),
  POLAND,
]

// Networks of the scale view, from the smallest to the largest.
export const SCALE_PLACES: { place: Place; radiusKm: number | null }[] = [
  { place: example('Oxapampa', 'Pasco', -10.5776, -75.4026), radiusKm: 10 },
  { place: example('Cusco', 'Cusco', -13.517, -71.9785), radiusKm: 5 },
  { place: example('UPC San Miguel', 'Lima', -12.0764, -77.0934), radiusKm: 5 },
  { place: example('Arequipa', 'Arequipa', -16.3988, -71.5369), radiusKm: 10 },
  { place: example('UPC San Miguel', 'Lima', -12.0764, -77.0934), radiusKm: 10 },
  { place: POLAND, radiusKm: null },
  { place: example('UPC San Miguel', 'Lima', -12.0764, -77.0934), radiusKm: 20 },
]

interface PhotonFeature {
  geometry: { coordinates: LngLat }
  properties: {
    name?: string
    street?: string
    housenumber?: string
    district?: string
    city?: string
    state?: string
    country?: string
    countrycode?: string
    extent?: [number, number, number, number] // west, north, east, south
  }
}

// Places near `near` rank first, so a common name finds the local one.
export async function searchPlaces(
  query: string,
  near: LngLat,
  signal: AbortSignal,
): Promise<Place[]> {
  const url = new URL(PHOTON_URL)
  url.search = new URLSearchParams({
    q: query,
    lang: 'default', // local names instead of the browser language
    limit: String(MAX_RESULTS),
    lon: String(near[0]),
    lat: String(near[1]),
    zoom: '10',
    location_bias_scale: '0.1',
  }).toString()
  const response = await fetch(url, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(TIMEOUT_MS)]),
  })
  if (!response.ok) throw new Error(`Photon answered ${response.status}`)
  const data: { features: PhotonFeature[] } = await response.json()
  return data.features.map(toPlace)
}

export function toPlace({ geometry, properties: p }: PhotonFeature): Place {
  const street = [p.street, p.housenumber].filter(Boolean).join(' ')
  const name = p.name ?? (street || (p.city ?? p.country ?? ''))
  // Photon repeats names ("San Miguel, San Miguel"), so keep each part once.
  const parts = new Set([street, p.district, p.city, p.state, p.country])
  parts.delete(name)
  return {
    name,
    address: [...parts].filter(Boolean).join(', '),
    center: geometry.coordinates,
    isCase: p.countrycode === 'PL',
    bounds: p.extent
      ? [
          [p.extent[0], p.extent[3]],
          [p.extent[2], p.extent[1]],
        ]
      : null,
  }
}
