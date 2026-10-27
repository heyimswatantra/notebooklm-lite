import type { SourceChunk } from '../api/types'
import { Placeholder } from './Placeholder'
import styles from './SourcesPanel.module.css'

interface SourcesPanelProps {
  sources: SourceChunk[]
  loading: boolean
  activeLabel: number | null
  onSelectSource: (label: number) => void
}

export function SourcesPanel({
  sources,
  loading,
  activeLabel,
  onSelectSource,
}: SourcesPanelProps) {
  const citedCount = sources.filter((s) => s.cited).length

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.title}>Sources</h2>
        {sources.length > 0 && (
          <span className={styles.count}>
            {sources.length} retrieved
            {citedCount > 0 ? `, ${citedCount} cited` : ''}
          </span>
        )}
      </div>

      {loading && <Placeholder lines={4} />}

      {!loading && sources.length === 0 && (
        <p className={styles.emptyText}>
          Sources will appear here after you ask a question.
        </p>
      )}

      {!loading && sources.length > 0 && (
        <div className={styles.list} role="feed" aria-label="Retrieved sources">
          {sources.map((source) => {
            const isActive = activeLabel === source.label
            return (
              <article
                key={source.label}
                id={`source-${source.label}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectSource(source.label)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelectSource(source.label)
                  }
                }}
                className={`${styles.card} ${isActive ? styles.cardActive : ''}`}
                aria-current={isActive ? 'true' : undefined}
                aria-label={`Source ${source.label} from ${source.filename}, page ${source.page_number}`}
              >
                <div className={styles.cardHeader}>
                  <div className={styles.metaLeft}>
                    <span className={styles.labelBadge}>[{source.label}]</span>
                    {source.cited && <span className={styles.citedBadge}>Cited</span>}
                    <span className={styles.sourceLocation}>
                      {source.filename}, p. {source.page_number}
                    </span>
                  </div>
                  <span className={styles.score}>
                    score {source.score.toFixed(2)}
                  </span>
                </div>
                <div className={styles.cardText}>{source.text}</div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}

