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

export interface ApiValidationError {
  loc?: (string | number)[]
  msg?: string
  type?: string
}

