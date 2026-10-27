export type AnswerSegment =
  | { type: 'text'; content: string }
  | { type: 'citation'; label: number; raw: string }

const BRACKET_RE = /\[([^\]]+)\]/g
const LABEL_LIST_RE = /^\d+(?:\s*,\s*\d+)*$/

export function parseAnswerSegments(text: string): AnswerSegment[] {
  const segments: AnswerSegment[] = []
  let lastIndex = 0

  for (const match of text.matchAll(BRACKET_RE)) {
    const fullMatch = match[0]
    const content = match[1].trim()
    const matchIndex = match.index ?? 0

    if (matchIndex > lastIndex) {
      segments.push({
        type: 'text',
        content: text.slice(lastIndex, matchIndex),
      })
    }

    if (LABEL_LIST_RE.test(content)) {
      const parts = content.split(',').map((s) => parseInt(s.trim(), 10))
      for (const label of parts) {
        segments.push({
          type: 'citation',
          label,
          raw: `[${label}]`,
        })
      }
    } else {
      // Non-citation brackets like [sic]
      segments.push({
        type: 'text',
        content: fullMatch,
      })
    }

    lastIndex = matchIndex + fullMatch.length
  }

  if (lastIndex < text.length) {
    segments.push({
      type: 'text',
      content: text.slice(lastIndex),
    })
  }

  return segments
}

