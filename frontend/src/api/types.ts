export interface Notebook {
  id: number
  name: string
  created_at: string
}

export interface Document {
  id: number
  filename: string
  page_count: number
  chunk_count: number
  created_at: string
}

export interface SourceChunk {
  label: number
  chunk_id: number
  document_id: number
  filename: string
  page_number: number
  chunk_index: number
  score: number
  text: string
  cited: boolean
}

export interface ChatResponse {
  question: string
  answer: string
  answered: boolean
  citations: number[]
  sources: SourceChunk[]
}

export interface ApiValidationError {
  loc?: (string | number)[]
  msg?: string
  type?: string
}
