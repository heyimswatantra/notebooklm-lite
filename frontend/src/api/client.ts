import type { Document, Notebook, ApiValidationError, ChatResponse } from './types'

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024

function normalizeDetail(status: number, detail: unknown): string {
  if (typeof detail === 'string') {
    if (status === 422 && detail.toLowerCase().includes('no extractable text')) {
      return 'No extractable text in this PDF. It may be a scanned image.'
    }
    if (status === 502) {
      if (detail.toLowerCase().includes('llm service')) {
        return 'Model service failed. Try again.'
      }
      return 'Embedding service failed. Nothing was saved. Try again.'
    }
    if (status === 404) {
      return 'Notebook not found. Select another notebook.'
    }
    if (status === 413) {
      return 'File exceeds 20 MB limit.'
    }
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = (detail as ApiValidationError[])
      .map((item) => {
        if (!item || typeof item.msg !== 'string') return ''
        return item.msg.replace(/^Value error,\s*/i, '')
      })
      .filter(Boolean)

    if (messages.length > 0) {
      return messages.join('; ')
    }
  }

  if (status === 502) {
    return 'Service temporarily unavailable. Try again.'
  }
  if (status >= 500) {
    return 'Something went wrong. Check your connection and try again.'
  }
  if (status === 404) {
    return 'Notebook not found. Select another notebook.'
  }
  if (status === 413) {
    return 'File exceeds 20 MB limit.'
  }

  return 'Something went wrong. Check your connection and try again.'
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, options)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new ApiError(0, 'Something went wrong. Check your connection and try again.')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = normalizeDetail(res.status, body?.detail)
    throw new ApiError(res.status, detail)
  }

  return (await res.json()) as T
}

export async function listNotebooks(): Promise<Notebook[]> {
  return request<Notebook[]>('/api/notebooks')
}

export async function createNotebook(name: string): Promise<Notebook> {
  const trimmed = name.trim()
  if (!trimmed) {
    throw new ApiError(422, 'Notebook name cannot be empty.')
  }

  return request<Notebook>('/api/notebooks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name: trimmed }),
  })
}

export async function listDocuments(notebookId: number, signal?: AbortSignal): Promise<Document[]> {
  return request<Document[]>(`/api/notebooks/${notebookId}/documents`, { signal })
}

export async function uploadDocument(notebookId: number, file: File): Promise<Document> {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new ApiError(400, 'Select a .pdf file.')
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    throw new ApiError(413, 'File exceeds 20 MB limit.')
  }

  const formData = new FormData()
  formData.append('file', file)

  return request<Document>(`/api/notebooks/${notebookId}/documents`, {
    method: 'POST',
    body: formData,
  })
}

export async function sendChat(
  notebookId: number,
  question: string,
  k: number = 5,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const trimmed = question.trim()
  if (!trimmed) {
    throw new ApiError(422, 'Question cannot be empty.')
  }
  if (trimmed.length > 2000) {
    throw new ApiError(422, 'Question cannot exceed 2000 characters.')
  }

  return request<ChatResponse>(`/api/notebooks/${notebookId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question: trimmed, k }),
    signal,
  })
}
