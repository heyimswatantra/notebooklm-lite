import styles from './Placeholder.module.css'

interface PlaceholderProps {
  lines?: number
  className?: string
}

export function Placeholder({ lines = 3, className = '' }: PlaceholderProps) {
  const count = Math.max(1, lines)
  return (
    <div className={`${styles.container} ${className}`} aria-hidden="true">
      {Array.from({ length: count }, (_, idx) => (
        <div key={idx} className={styles.line} />
      ))}
    </div>
  )
}

