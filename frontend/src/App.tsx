import { useEffect, useState } from 'react'
import { createNotebook, listNotebooks } from './api/client'
import type { Notebook } from './api/types'
import { DocumentList } from './components/DocumentList'
import { NotebookRail } from './components/NotebookRail'
import { UploadControl } from './components/UploadControl'
import { ChatPanel } from './components/ChatPanel'
import { SourcesPanel } from './components/SourcesPanel'
import { useDocuments } from './hooks/useDocuments'
import { useChat } from './hooks/useChat'
import styles from './App.module.css'

export function App() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [loadingNotebooks, setLoadingNotebooks] = useState(true)
  const [notebooksError, setNotebooksError] = useState<string | null>(null)
  const [selectedNotebookId, setSelectedNotebookId] = useState<number | null>(null)

  const { documents, loading: docsLoading, error: docsError, refresh: refreshDocs } =
    useDocuments(selectedNotebookId)

  const {
    response: chatResponse,
    sources,
    loading: chatLoading,
    error: chatError,
    activeLabel,
    askQuestion,
    setActiveLabel,
  } = useChat(selectedNotebookId)

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

  const handleSelectCitation = (label: number) => {
    setActiveLabel(label)
    const el = document.getElementById(`source-${label}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const handleSelectSource = (label: number) => {
    setActiveLabel(label)
    const citationEl = document.querySelector(`[data-citation-label="${label}"]`)
    if (citationEl) {
      citationEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
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

      {/* Main Content Area */}
      <div className={styles.contentArea}>
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

          {/* Chat Section */}
          {selectedNotebookId !== null && (
            <ChatPanel
              documentsCount={documents.length}
              response={chatResponse}
              loading={chatLoading}
              error={chatError}
              activeLabel={activeLabel}
              onAsk={askQuestion}
              onSelectSource={handleSelectCitation}
            />
          )}
        </main>

        {/* Evidence Column (Desktop right column; stacks below on tablet/phone) */}
        <aside className={styles.evidencePanel} aria-label="Evidence panel">
          <SourcesPanel
            sources={sources}
            loading={chatLoading}
            activeLabel={activeLabel}
            onSelectSource={handleSelectSource}
          />
        </aside>
      </div>
    </div>
  )
}

export default App
