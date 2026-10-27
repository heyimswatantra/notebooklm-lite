import { useMemo, useState } from 'react'
import type { ChatResponse } from '../api/types'
import { parseAnswerSegments } from '../utils/citations'
import { Placeholder } from './Placeholder'
import styles from './ChatPanel.module.css'

interface ChatPanelProps {
  documentsCount: number
  response: ChatResponse | null
  loading: boolean
  error: string | null
  activeLabel: number | null
  onAsk: (question: string) => Promise<void>
  onSelectSource: (label: number) => void
}

export function ChatPanel({
  documentsCount,
  response,
  loading,
  error,
  activeLabel,
  onAsk,
  onSelectSource,
}: ChatPanelProps) {
  const [questionText, setQuestionText] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  const answer = response?.answer
  const segments = useMemo(() => {
    if (!answer) return []
    return parseAnswerSegments(answer)
  }, [answer])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = questionText.trim()
    if (!trimmed) {
      setValidationError('Question cannot be empty.')
      return
    }
    if (trimmed.length > 2000) {
      setValidationError('Question cannot exceed 2000 characters.')
      return
    }

    setValidationError(null)
    await onAsk(trimmed)
  }

  if (documentsCount === 0) {
    return (
      <section className={styles.container} aria-label="Chat section">
        <h2 className={styles.sectionTitle}>Chat</h2>
        <p className={styles.disabledNotice}>
          Upload a PDF to ask questions.
        </p>
      </section>
    )
  }

  return (
    <section className={styles.container} aria-label="Chat section">
      <h2 className={styles.sectionTitle}>Chat</h2>

      <form onSubmit={handleSubmit} className={styles.form}>
        <textarea
          value={questionText}
          onChange={(e) => {
            setQuestionText(e.target.value)
            if (validationError) setValidationError(null)
          }}
          placeholder="Ask a question about your documents..."
          aria-label="Question"
          disabled={loading}
          rows={3}
          maxLength={2000}
          className={styles.textarea}
        />

        <div className={styles.formFooter}>
          <span className={styles.hint}>
            Each question is answered independently from your documents.
          </span>
          <button
            type="submit"
            disabled={loading}
            className={styles.askButton}
          >
            {loading ? 'Asking...' : 'ask'}
          </button>
        </div>
      </form>

      <div aria-live="polite" className={styles.liveStatus}>
        {loading && (
          <p className={styles.searchingText}>
            Searching documents and generating answer...
          </p>
        )}
      </div>

      {loading && <Placeholder lines={3} />}

      {(validationError || error) && (
        <p role="alert" className={styles.errorText}>
          {validationError ?? error}
        </p>
      )}

      {response && !loading && (
        <div className={styles.answerCard}>
          <div className={styles.questionEcho}>{response.question}</div>
          <div className={styles.answerBody}>
            {segments.map((seg, idx) => {
              if (seg.type === 'text') {
                return <span key={idx}>{seg.content}</span>
              }

              const source = response.sources.find((s) => s.label === seg.label)
              const labelDesc = source
                ? `Source ${seg.label}: ${source.filename}, page ${source.page_number}`
                : `Source ${seg.label}`

              return (
                <button
                  key={`${seg.label}-${idx}`}
                  type="button"
                  onClick={() => onSelectSource(seg.label)}
                  data-citation-label={seg.label}
                  className={`${styles.citation} ${
                    activeLabel === seg.label ? styles.citationActive : ''
                  }`}
                  aria-label={labelDesc}
                >
                  {seg.raw}
                </button>
              )
            })}
          </div>
          {!response.answered && (
            <p className={styles.unansweredNotice}>
              Context was insufficient to fully answer this question.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
