/**
 * Formato compartido de cifras. Vive fuera de las paginas porque el mismo
 * importe se muestra en varias de ellas y, cuando cada pagina traia su propio
 * helper, el RCS aparecia como "$809.2K" en /scr y como "$809,207" en
 * /metodologia, y una fila mezclaba "$1051K" junto a "$4.79M".
 */

/** Moneda compacta. El umbral mantiene en la misma escala a los recuadros vecinos. */
export const compactMoney = (v: number): string =>
  Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${(v / 1e3).toFixed(1)}K`;

/** Moneda a peso entero: los centavos de una prima anual solo son ruido. */
export const wholeMoney = (v: number): string =>
  `$${Math.round(v).toLocaleString('en-US')}`;

/**
 * Los endpoints devuelven el nombre del pais en español y con acentos. Se
 * normaliza a una clave estable para poder traducirlo y para emparejarlo con
 * colores o comparaciones sin depender de la ortografia exacta.
 */
export function countryKey(name: string): 'mexico' | 'usa' | 'spain' | null {
  const n = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (n.includes('mexico')) return 'mexico';
  if (n.includes('estados unidos') || n.includes('usa') || n.includes('united states')) return 'usa';
  if (n.includes('espana') || n.includes('spain')) return 'spain';
  return null;
}

/** Nombre del pais en el idioma activo; si no se reconoce, se deja tal cual. */
export function countryLabel(t: (key: string) => string, name: string): string {
  const key = countryKey(name);
  return key ? t(`tables.countries.${key}`) : name;
}
