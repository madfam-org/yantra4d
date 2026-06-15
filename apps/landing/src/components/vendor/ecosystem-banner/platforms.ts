/**
 * MADFAM Ecosystem Platform List — Source of Truth
 *
 * Add/edit a platform here and it propagates to every landing that imports
 * `EcosystemBanner` from `@dhanam/ui`.
 *
 * Verified live on 2026-05-04 via HEAD probe (200/301/302/405-method-allowed).
 * Two known-good platforms (sim4d.io, phynd-crm.madfam.io) were OMITTED from
 * the v1 default list because their apex domains were not resolving at audit
 * time. Re-add them once they're live by uncommenting the entries below.
 */
export interface EcosystemPlatform {
  /** Short uppercase keyword shown before the colon, e.g. "BUDGETING & WEALTH". */
  keyword: string;
  /** Platform display name shown after the colon, e.g. "Dhanam". */
  name: string;
  /** Apex domain URL, e.g. "https://dhan.am". No trailing slash. */
  url: string;
}

export const DEFAULT_ECOSYSTEM_PLATFORMS: readonly EcosystemPlatform[] = [
  { keyword: 'BUDGETING & WEALTH', name: 'Dhanam', url: 'https://dhan.am' },
  { keyword: 'AI AGENT OFFICE', name: 'Selva', url: 'https://selva.town' },
  { keyword: 'COMPLIANCE & CFDI', name: 'Karafiel', url: 'https://karafiel.mx' },
  { keyword: 'AUTHENTICATION', name: 'Janua', url: 'https://auth.madfam.io' },
  { keyword: 'DEPLOYMENT', name: 'Enclii', url: 'https://enclii.dev' },
  { keyword: 'LEGAL OPS', name: 'Tezca', url: 'https://tezca.mx' },
  { keyword: 'PHYGITAL FABRICATION', name: 'Yantra4D', url: 'https://yantra4d.com' },
  { keyword: 'QUOTING ENGINE', name: 'Cotiza', url: 'https://cotiza.studio' },
  { keyword: 'INDUSTRY INTELLIGENCE', name: 'Forge Sight', url: 'https://forgesight.quest' },
  { keyword: 'MANUFACTURING', name: 'Pravara', url: 'https://mes.madfam.io' },
  { keyword: 'GAMES', name: 'Rondelio', url: 'https://rondel.io' },
  { keyword: 'ROUTING & LOGISTICS', name: 'RouteCraft', url: 'https://routecraft.app' },
  { keyword: 'CLIENT PORTAL & CRM', name: 'PhyndCRM', url: 'https://phynd.app' },
  // { keyword: 'PARAMETRIC CAD', name: 'Sim4D', url: 'https://sim4d.io' },                    // 2026-05-04: connection refused
] as const;
