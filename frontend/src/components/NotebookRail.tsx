import { useState } from 'react'
import type { Notebook } from '../api/types'
import { Placeholder } from './Placeholder'
import styles from './NotebookRail.module.css'

interface NotebookRailProps {
  notebooks: Notebook[]
  selectedNotebookId: number | null
  loading: boolean
  error: string | null
  onSelectNotebook: (id: number) => void
  onCreateNotebook: (name: string) => Promise<void>
}

export function NotebookRail({
  notebooks,
  selectedNotebookId,
  loading,
  error,
  onSelectNotebook,
  onCreateNotebook,
}: NotebookRailProps) {
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [phoneCreateOpen, setPhoneCreateOpen] = useState(false)

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setCreateError('Notebook name cannot be empty.')
      return
    }

    setCreating(true)
    setCreateError(null)

    try {
      await onCreateNotebook(trimmed)
      setName('')
      setPhoneCreateOpen(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Notebook name cannot be empty.'
      setCreateError(msg)
    } finally {
      setCreating(false)
    }
  }

  return (
    <nav className={styles.rail} aria-label="Notebooks">
      {/* Desktop / Tablet rail */}
      <div className={styles.desktopRail}>
        <div className={styles.brand}>notebooklm lite</div>

        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Notebooks</h2>

          <form onSubmit={handleCreate} className={styles.createForm}>
            <div className={styles.inputRow}>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (createError) setCreateError(null)
                }}
                placeholder="New notebook name"
                aria-label="New notebook name"
                disabled={creating}
                className={styles.input}
              />
              <button
                type="submit"
                disabled={creating}
                className={styles.createButton}
              >
                {creating ? 'Creating...' : 'create'}
              </button>
            </div>
            {createError && (
              <p role="alert" className={styles.errorText}>
                {createError}
              </p>
            )}
          </form>
        </div>

        {loading && <Placeholder lines={3} />}

        {error && (
          <p role="alert" className={styles.errorText}>
            {error}
          </p>
        )}

        {!loading && !error && notebooks.length === 0 && (
          <p className={styles.emptyText}>No notebooks yet. Create one above.</p>
        )}

        {!loading && !error && notebooks.length > 0 && (
          <ul className={styles.list} role="list">
            {notebooks.map((nb) => {
              const isSelected = selectedNotebookId === nb.id
              return (
                <li key={nb.id}>
                  <button
                    type="button"
                    onClick={() => onSelectNotebook(nb.id)}
                    aria-current={isSelected ? 'true' : undefined}
                    className={`${styles.item} ${isSelected ? styles.selected : ''}`}
                  >
                    {nb.name}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Phone horizontal strip (<640px) */}
      <div className={styles.phoneStrip}>
        <div className={styles.phoneHeader}>
          <div className={styles.brand}>notebooklm lite</div>
          <button
            type="button"
            onClick={() => setPhoneCreateOpen((prev) => !prev)}
            className={styles.phoneToggleBtn}
            aria-expanded={phoneCreateOpen}
          >
            {phoneCreateOpen ? 'Cancel' : '+ create'}
          </button>
        </div>

        {phoneCreateOpen && (
          <form onSubmit={handleCreate} className={styles.createForm}>
            <div className={styles.inputRow}>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (createError) setCreateError(null)
                }}
                placeholder="New notebook name"
                aria-label="New notebook name"
                disabled={creating}
                className={styles.input}
              />
              <button
                type="submit"
                disabled={creating}
                className={styles.createButton}
              >
                {creating ? 'Creating...' : 'create'}
              </button>
            </div>
            {createError && (
              <p role="alert" className={styles.errorText}>
                {createError}
              </p>
            )}
          </form>
        )}

        {loading ? (
          <Placeholder lines={1} />
        ) : error ? (
          <p role="alert" className={styles.errorText}>
            {error}
          </p>
        ) : notebooks.length === 0 ? (
          <p className={styles.emptyText}>No notebooks yet. Create one above.</p>
        ) : (
          <select
            value={selectedNotebookId ?? ''}
            onChange={(e) => {
              const val = e.target.value
              if (val) onSelectNotebook(Number(val))
            }}
            aria-label="Select notebook"
            className={styles.phoneSelect}
          >
            <option value="" disabled>
              Select a notebook
            </option>
            {notebooks.map((nb) => (
              <option key={nb.id} value={nb.id}>
                {nb.name}
              </option>
            ))}
          </select>
        )}
      </div>
    </nav>
  )
}

