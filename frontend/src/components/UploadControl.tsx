import { useEffect, useState } from 'react'
import { ApiError, uploadDocument } from '../api/client'
import styles from './UploadControl.module.css'

interface UploadControlProps {
  selectedNotebookId: number | null
  onUploadSuccess: (targetNotebookId: number, filename: string) => void
}

export function UploadControl({
  selectedNotebookId,
  onUploadSuccess,
}: UploadControlProps) {
  const [uploading, setUploading] = useState(false)
  const [currentFile, setCurrentFile] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!successMsg) return
    const timer = setTimeout(() => {
      setSuccessMsg(null)
    }, 4000)
    return () => clearTimeout(timer)
  }, [successMsg])

  if (selectedNotebookId === null) {
    return null
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    const targetNotebookId = selectedNotebookId
    setErrorMsg(null)
    setSuccessMsg(null)

    // Client-side pre-checks
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMsg('Select a .pdf file.')
      return
    }

    if (file.size > 20 * 1024 * 1024) {
      setErrorMsg('File exceeds 20 MB limit.')
      return
    }

    setUploading(true)
    setCurrentFile(file.name)

    try {
      await uploadDocument(targetNotebookId, file)
      setUploading(false)
      setCurrentFile(null)
      setSuccessMsg(`${file.name} uploaded successfully.`)
      onUploadSuccess(targetNotebookId, file.name)
    } catch (err: unknown) {
      setUploading(false)
      setCurrentFile(null)
      if (err instanceof ApiError) {
        setErrorMsg(err.detail)
      } else {
        setErrorMsg('Something went wrong. Check your connection and try again.')
      }
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.controlRow}>
        <input
          type="file"
          id="pdf-upload"
          accept=".pdf"
          disabled={uploading}
          onChange={handleFileChange}
          className={styles.hiddenInput}
        />
        <label
          htmlFor="pdf-upload"
          className={`${styles.uploadButton} ${uploading ? styles.disabled : ''}`}
        >
          choose file
        </label>
        <span className={styles.hint}>pdf, up to 20 mb</span>
      </div>

      <div aria-live="polite" className={styles.liveRegion}>
        {uploading && currentFile && (
          <p className={styles.progressText}>
            Uploading and processing {currentFile}... This may take a minute.
          </p>
        )}
        {successMsg && !uploading && (
          <p className={styles.successText}>{successMsg}</p>
        )}
      </div>

      {errorMsg && (
        <p role="alert" className={styles.errorText}>
          {errorMsg}
        </p>
      )}
    </div>
  )
}

