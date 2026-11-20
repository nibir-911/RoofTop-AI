export const PROMPT_VERSION = 'v20'            // must equal backend PROMPT_VERSION
export const SEND_LONG_SIDE = 1536             // px, longest side sent to the backend
export const SEND_QUALITY = 0.92
export const plantsKeyOf = (plants) => (plants || []).map(p => typeof p === 'string'
  ? (p.replace(/\([^\)]*[\u0980-\u09FF][^\)]*\)/g, '').trim() || p.split('(')[0].trim())
  : (p?.name_en || p?.name || '')).filter(Boolean)
export const zonesSig = (zones) => (zones || []).map(z => `${z.cellId}:${z.zone}:${z.sun}`).sort().join(',')
export const pinsSig = (pins) => (pins || []).map(p => `${p.x.toFixed(3)},${p.y.toFixed(3)}`).join(';')
export const makeFingerprint = ({ photoId, pins, zones, variant, lighting, plants }) =>
  [photoId, pinsSig(pins), zonesSig(zones), variant, lighting, plantsKeyOf(plants).slice().sort().join(','), PROMPT_VERSION].join('|')
