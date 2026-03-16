import { Terminal, Trash2 } from 'lucide-react'
import type { LogEntry } from '../types'

interface Props {
  logs:     LogEntry[]
  onClear?: () => void
}

const STATUS_STYLES: Record<string, string> = {
  success: 'text-emerald-400',
  error:   'text-red-400',
  warning: 'text-amber-400',
  info:    'text-blue-400',
}

export default function StatusLog({ logs, onClear }: Props) {
  if (logs.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Activity Log</span>
        </div>
        {onClear && (
          <button
            className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400 transition-colors"
            onClick={onClear}
          >
            <Trash2 className="w-3 h-3" />
            Clear
          </button>
        )}
      </div>

      <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 max-h-52 overflow-y-auto font-mono text-xs space-y-1">
        {logs.map((entry, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-slate-600 shrink-0">{entry.time}</span>
            <span className={STATUS_STYLES[entry.status] ?? 'text-slate-300'}>
              {entry.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
