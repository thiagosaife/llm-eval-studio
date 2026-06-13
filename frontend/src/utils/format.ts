// Small presentation helpers shared across the results views.

/** Score → two-decimal string, or an em dash for "not applicable". */
export function formatScore(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return v.toFixed(2)
}

/**
 * Continuous red→amber→green scale for a 0–1 score. Null is muted grey.
 * Used for score pills, summary bars, and table cells so a bad number always
 * *looks* bad at a glance.
 */
export function scoreColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'var(--c-muted)'
  const clamped = Math.max(0, Math.min(1, v))
  const hue = clamped * 130 // 0 = red, 130 = green
  return `hsl(${hue}, 60%, 42%)`
}

const FAMILY_LABELS: Record<string, string> = {
  lexical: 'Lexical',
  semantic: 'Semantic',
  classification: 'Classification',
  model_judge: 'LLM judge',
  rag: 'RAG',
  operational: 'Operational',
}

export function familyLabel(family: string): string {
  return FAMILY_LABELS[family] ?? family
}

// --- word-level diff (case inspector) --------------------------------------

export interface DiffSegment {
  text: string
  status: 'same' | 'changed'
}

interface Tok {
  raw: string
  norm: string | null // null for whitespace / punctuation-only (neutral)
}

function splitTokens(text: string): Tok[] {
  return text
    .split(/(\s+)/)
    .filter((s) => s !== '')
    .map((raw) => {
      if (/^\s+$/.test(raw)) return { raw, norm: null }
      const norm = (raw.toLowerCase().match(/[a-z0-9]+/g) ?? []).join('')
      return { raw, norm: norm.length ? norm : null }
    })
}

/**
 * Align prediction vs. reference at the word level via a longest-common-
 * subsequence match. Returns each side's tokens flagged `same` (aligned) or
 * `changed` (present here but not matched on the other side). This makes a
 * lexical metric's basis tangible — `changed` words are exactly what cost it.
 */
export function wordDiff(
  a: string | null | undefined,
  b: string | null | undefined,
): { left: DiffSegment[]; right: DiffSegment[] } {
  const A = splitTokens(a ?? '')
  const B = splitTokens(b ?? '')

  // Indices of the comparable (word) tokens on each side, and their keys.
  const ai = A.map((t, i) => ({ t, i })).filter((x) => x.t.norm !== null)
  const bi = B.map((t, i) => ({ t, i })).filter((x) => x.t.norm !== null)
  const an = ai.map((x) => x.t.norm as string)
  const bn = bi.map((x) => x.t.norm as string)

  const m = an.length
  const n = bn.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array<number>(n + 1).fill(0))
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = an[i] === bn[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }

  const matchedA = new Set<number>()
  const matchedB = new Set<number>()
  let i = 0
  let j = 0
  while (i < m && j < n) {
    if (an[i] === bn[j]) {
      matchedA.add(ai[i].i)
      matchedB.add(bi[j].i)
      i++
      j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i++
    } else {
      j++
    }
  }

  const toSegments = (toks: Tok[], matched: Set<number>): DiffSegment[] =>
    toks.map((t, idx) => ({
      text: t.raw,
      status: t.norm === null || matched.has(idx) ? 'same' : 'changed',
    }))

  return { left: toSegments(A, matchedA), right: toSegments(B, matchedB) }
}
