import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, sendChat } from '../api/client'
import type { ChatResponse, SourceChunk } from '../api/types'

export interface UseChatResult {
  response: ChatResponse | null
  sources: SourceChunk[]
  loading: boolean
  error: string | null
  activeLabel: number | null
  askQuestion: (question: string) => Promise<void>
  setActiveLabel: (label: number | null) => void
  clearChat: () => void
}

export function useChat(selectedNotebookId: number | null): UseChatResult {
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [activeLabel, setActiveLabel] = useState<number | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const activeNotebookIdRef = useRef<number | null>(selectedNotebookId)
  useEffect(() => {
    activeNotebookIdRef.current = selectedNotebookId
  }, [selectedNotebookId])

  // Clear chat state and abort when selected notebook changes
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [selectedNotebookId])

  const clearChat = useCallback(() => {
    setResponse(null)
    setLoading(false)
    setError(null)
    setActiveLabel(null)
  }, [])

  const askQuestion = useCallback(
    async (questionText: string) => {
      const currentId = activeNotebookIdRef.current
      if (currentId === null) return

      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      const controller = new AbortController()
      abortControllerRef.current = controller

      setLoading(true)
      setError(null)
      setActiveLabel(null)

      try {
        const result = await sendChat(currentId, questionText, 5, controller.signal)
        if (activeNotebookIdRef.current === currentId) {
          setResponse(result)
          setLoading(false)
        }
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return
        }
        if (activeNotebookIdRef.current === currentId) {
          if (err instanceof ApiError) {
            setError(err.detail)
          } else {
            setError('Something went wrong. Check your connection and try again.')
          }
          setLoading(false)
        }
      }
    },
    [],
  )

  return {
    response: selectedNotebookId === null ? null : response,
    sources: selectedNotebookId === null ? [] : response?.sources ?? [],
    loading: selectedNotebookId === null ? false : loading,
    error: selectedNotebookId === null ? null : error,
    activeLabel: selectedNotebookId === null ? null : activeLabel,
    askQuestion,
    setActiveLabel,
    clearChat,
  }
}

