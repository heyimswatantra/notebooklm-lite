import type { Document } from '../api/types'
import { Placeholder } from './Placeholder'
import styles from './DocumentList.module.css'

interface DocumentListProps {
  documents: Document[]
  selectedNotebookId: number | null
  loading: boolean
  error: string | null
}

export function DocumentList({
  documents,
  selectedNotebookId,
  loading,
  error,
}: DocumentListProps) {
  if (selectedNotebookId === null) {
    return (
      <div className={styles.container}>
        <h2 className={styles.sectionTitle}>Documents</h2>
        <p className={styles.instructionText}>
          Select a notebook or create one to get started.
        </p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.sectionTitle}>Documents</h2>

      {loading && <Placeholder lines={3} />}

      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}

      {!loading && !error && documents.length === 0 && (
        <p className={styles.emptyText}>
          No documents yet. Upload a PDF to get started.
        </p>
      )}

      {!loading && !error && documents.length > 0 && (
        <div className={styles.table} role="table" aria-label="Documents in notebook">
          {documents.map((doc) => (
            <div key={doc.id} className={styles.row} role="row">
              <span className={styles.filename} role="cell">
                {doc.filename}
              </span>
              <span className={styles.meta} role="cell">
                <span>{doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}</span>
                <span>{doc.chunk_count} {doc.chunk_count === 1 ? 'chunk' : 'chunks'}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

