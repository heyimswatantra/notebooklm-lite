import { useCallback, useEffect, useRef, useState } from 'react'
import { listDocuments } from '../api/client'
import type { Document } from '../api/types'

export interface UseDocumentsResult {
  documents: Document[]
  loading: boolean
  error: string | null
  refresh: (targetNotebookId?: number) => void
}

export function useDocuments(selectedNotebookId: number | null): UseDocumentsResult {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState<number>(0)

  const activeNotebookIdRef = useRef<number | null>(selectedNotebookId)
  useEffect(() => {
    activeNotebookIdRef.current = selectedNotebookId
  }, [selectedNotebookId])

  useEffect(() => {
    if (selectedNotebookId === null) {
      return
    }

    const controller = new AbortController()

    Promise.resolve().then(() => {
      if (controller.signal.aborted) return
      setLoading(true)
      setError(null)
    })

    listDocuments(selectedNotebookId, controller.signal)
      .then((docs) => {
        if (!controller.signal.aborted && activeNotebookIdRef.current === selectedNotebookId) {
          setDocuments(docs)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted && activeNotebookIdRef.current === selectedNotebookId) {
          setError('Could not load documents. Reload the page.')
          setLoading(false)
        }
      })

    return () => {
      controller.abort()
    }
  }, [selectedNotebookId, reloadCount])

  const refresh = useCallback((targetNotebookId?: number) => {
    const currentId = activeNotebookIdRef.current
    if (currentId === null) return

    // If an upload was tied to a specific notebook, only refresh if that notebook is still selected
    if (targetNotebookId !== undefined && targetNotebookId !== currentId) {
      return
    }

    setReloadCount((c) => c + 1)
  }, [])

  return {
    documents: selectedNotebookId === null ? [] : documents,
    loading: selectedNotebookId === null ? false : loading,
    error: selectedNotebookId === null ? null : error,
    refresh,
  }
}

