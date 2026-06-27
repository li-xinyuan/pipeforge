/**
 * Frontend error reporting utility.
 *
 * Captures unhandled errors and Vue warnings, sending them to the backend
 * /api/error-report endpoint. In production, this provides visibility into
 * frontend issues without requiring a third-party service like Sentry.
 */

interface ErrorReport {
  message: string
  stack?: string
  url: string
  line?: number
  column?: number
  userAgent: string
  timestamp: string
  level: 'error' | 'warning'
  context?: Record<string, unknown>
}

const ERROR_QUEUE: ErrorReport[] = []
let flushTimer: ReturnType<typeof setTimeout> | null = null
const FLUSH_INTERVAL = 5000 // Flush every 5 seconds
const MAX_QUEUE_SIZE = 20

/**
 * Queue an error report for batch submission.
 */
export function reportError(
  error: Error | string,
  context?: Record<string, unknown>,
  level: 'error' | 'warning' = 'error',
): void {
  const report: ErrorReport = {
    message: typeof error === 'string' ? error : error.message,
    stack: typeof error === 'string' ? undefined : error.stack,
    url: window.location.href,
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString(),
    level,
    context,
  }

  ERROR_QUEUE.push(report)

  // Flush immediately if queue is full
  if (ERROR_QUEUE.length >= MAX_QUEUE_SIZE) {
    void flushErrors()
  } else if (!flushTimer) {
    flushTimer = setTimeout(() => {
      void flushErrors()
    }, FLUSH_INTERVAL)
  }
}

/**
 * Send queued error reports to the backend.
 */
async function flushErrors(): Promise<void> {
  if (ERROR_QUEUE.length === 0) return
  flushTimer = null

  const reports = ERROR_QUEUE.splice(0, ERROR_QUEUE.length)

  try {
    // Use fetch directly to avoid circular dependency with useApi
    await fetch('/api/error-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reports }),
    }).catch(() => {
      // Silently ignore — error reporting should never break the app
    })
  } catch {
    // Silently ignore
  }
}

/**
 * Install global error handlers.
 * Call this once during app initialization.
 */
export function setupErrorReporting(): void {
  // Unhandled JS errors
  window.addEventListener('error', (event) => {
    reportError(event.error || event.message, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    })
  })

  // Unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    reportError(
      reason instanceof Error ? reason : String(reason),
      { type: 'unhandledrejection' },
    )
  })

  // Flush remaining errors on page unload
  window.addEventListener('beforeunload', () => {
    void flushErrors()
  })
}
