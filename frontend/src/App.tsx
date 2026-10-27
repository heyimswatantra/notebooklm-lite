import { useEffect, useState } from 'react'
import { createNotebook, listNotebooks } from './api/client'
import type { Notebook } from './api/types'
import { DocumentList } from './components/DocumentList'
import { NotebookRail } from './components/NotebookRail'
import { UploadControl } from './components/UploadControl'
import { useDocuments } from './hooks/useDocuments'
import styles from './App.module.css'

export function App() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [loadingNotebooks, setLoadingNotebooks] = useState(true)
  const [notebooksError, setNotebooksError] = useState<string | null>(null)
  const [selectedNotebookId, setSelectedNotebookId] = useState<number | null>(null)

  const { documents, loading: docsLoading, error: docsError, refresh: refreshDocs } =
    useDocuments(selectedNotebookId)

  useEffect(() => {
    let active = true
    listNotebooks()
      .then((data) => {
        if (active) {
          setNotebooks(data)
          setLoadingNotebooks(false)
        }
      })
      .catch(() => {
        if (active) {
          setNotebooksError('Could not load notebooks. Reload the page.')
          setLoadingNotebooks(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  const handleSelectNotebook = (id: number) => {
    setSelectedNotebookId(id)
  }

  const handleCreateNotebook = async (name: string) => {
    const created = await createNotebook(name)
    setNotebooks((prev) => [created, ...prev])
    setSelectedNotebookId(created.id)
  }

  const handleUploadSuccess = (targetNotebookId: number) => {
    refreshDocs(targetNotebookId)
  }

  const selectedNotebook = notebooks.find((nb) => nb.id === selectedNotebookId)

  return (
    <div className={styles.layout}>
      {/* Left Rail / Top Strip */}
      <aside className={styles.railContainer}>
        <NotebookRail
          notebooks={notebooks}
          selectedNotebookId={selectedNotebookId}
          loading={loadingNotebooks}
          error={notebooksError}
          onSelectNotebook={handleSelectNotebook}
          onCreateNotebook={handleCreateNotebook}
        />
      </aside>

      {/* Main Area */}
      <main className={styles.mainColumn}>
        <div className={styles.headerSection}>
          {selectedNotebook ? (
            <h1 className={styles.notebookTitle}>{selectedNotebook.name}</h1>
          ) : (
            <h1 className={styles.notebookTitle}>Notebook</h1>
          )}
        </div>

        <section className={styles.documentsSection} aria-label="Documents section">
          <DocumentList
            documents={documents}
            selectedNotebookId={selectedNotebookId}
            loading={docsLoading}
            error={docsError}
          />
          <UploadControl
            selectedNotebookId={selectedNotebookId}
            onUploadSuccess={handleUploadSuccess}
          />
        </section>

        {/* Reserved Chat Region (M6b) */}
        <section className={styles.chatReserved} aria-label="Chat section">
          <p>Chat will appear here.</p>
        </section>

        {/* Tablet / Phone stacked evidence section */}
        <section className={styles.tabletEvidence} aria-label="Evidence section">
          <p>Sources will appear here.</p>
        </section>
      </main>

      {/* Desktop Evidence Column (M6b) */}
      <aside className={styles.evidencePanel} aria-label="Evidence panel">
        <div className={styles.evidenceReserved}>
          <p>Sources will appear here.</p>
        </div>
      </aside>
    </div>
  )
}

export default App
