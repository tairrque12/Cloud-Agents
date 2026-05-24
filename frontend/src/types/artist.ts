export const MIGUEL_FALLBACK: ArtistProfile = {
  slug: 'miguel',
  name: 'Miguel',
  instagram_handle: 'miguel_tattoos',
  city: 'Austin',
  state: 'TX',
  location: 'Austin, TX',
  bio_short: 'Black and grey realism specialist based in the Austin, TX area.',
  specialties: ['realism', 'blackwork', 'portraits'],
  booking_url: '/book',
  status: 'active',
}

export interface ArtistProfile {
  slug: string
  name: string
  instagram_handle?: string | null
  city?: string | null
  state?: string | null
  location?: string | null
  studio_name?: string | null
  bio_short?: string | null
  bio?: string | null
  specialties?: string[]
  booking_url: string
  status: string
  availability?: ArtistAvailability
  pricing_tiers?: ApiPricingConfig
}

export interface PricingTier {
  min: number
  max: number
  deposit: number
}

export type PricingConfig = Record<
  'small' | 'half_day' | 'full_day' | 'full_sleeve',
  PricingTier
>

export type ApiPricingConfig = Record<
  'small_piece' | 'half_day' | 'full_day' | 'full_sleeve',
  PricingTier
>

export interface ArtistAvailability {
  days: string[]
  start_time: string
  end_time: string
  max_sessions_per_day: number
  blocked_dates: string[]
}

export const DEFAULT_PRICING: PricingConfig = {
  small: { min: 100, max: 300, deposit: 50 },
  half_day: { min: 400, max: 600, deposit: 100 },
  full_day: { min: 800, max: 1000, deposit: 100 },
  full_sleeve: { min: 800, max: 1000, deposit: 100 },
}

export const DEFAULT_API_PRICING: ApiPricingConfig = {
  small_piece: { min: 100, max: 300, deposit: 50 },
  half_day: { min: 400, max: 600, deposit: 100 },
  full_day: { min: 800, max: 1000, deposit: 100 },
  full_sleeve: { min: 800, max: 1000, deposit: 100 },
}

export const PRICING_LABELS: Record<keyof PricingConfig, string> = {
  small: 'Small piece',
  half_day: 'Half day session',
  full_day: 'Full day session',
  full_sleeve: 'Full sleeve (per session)',
}

export const API_PRICING_LABELS: Record<keyof ApiPricingConfig, string> = {
  small_piece: 'Small piece',
  half_day: 'Half day session',
  full_day: 'Full day session',
  full_sleeve: 'Full sleeve (per session)',
}

export const SPECIALTY_OPTIONS = [
  'Realism',
  'Blackwork',
  'Traditional',
  'Neo-traditional',
  'Fine line',
  'Japanese',
  'Portraits',
  'Cover-ups',
  'Color',
  'Geometric',
]

export const SCHEDULING_TOOL_OPTIONS = [
  'Google Calendar',
  'Booksy',
  'Square Appointments',
  'Vagaro',
  'Apple Calendar',
  'Physical book / notebook',
  'Instagram DMs',
  'Other',
] as const

export type SchedulingTool = (typeof SCHEDULING_TOOL_OPTIONS)[number]

export const WEEKDAYS = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
  { key: 'sat', label: 'Sat' },
  { key: 'sun', label: 'Sun' },
] as const

export const DEFAULT_AVAILABILITY: ArtistAvailability = {
  days: ['mon', 'tue', 'wed', 'thu', 'fri'],
  start_time: '10:00',
  end_time: '18:00',
  max_sessions_per_day: 2,
  blocked_dates: [],
}

export function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

export function buildTimeOptions(): string[] {
  const options: string[] = []
  for (let hour = 0; hour < 24; hour += 1) {
    for (const minute of [0, 30]) {
      options.push(
        `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
      )
    }
  }
  return options
}
