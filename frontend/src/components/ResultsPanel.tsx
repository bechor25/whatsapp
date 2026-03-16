import { ExternalLink, CheckCircle, XCircle, Loader, Download } from 'lucide-react'
import type { ProcessResult } from '../types'

interface Props {
  results: ProcessResult[]
}

const STATUS_CONF = {
  sent:       { label: 'Sent',       cls: 'badge-success',  Icon: CheckCircle },
  generated:  { label: 'Generated',  cls: 'badge-info',     Icon: CheckCircle },
  failed:     { label: 'Failed',     cls: 'badge-error',    Icon: XCircle     },
  processing: { label: 'Processing', cls: 'badge-warning',  Icon: Loader      },
} as const

export default function ResultsPanel({ results }: Props) {
  if (results.length === 0) return null

  const handleDownload = (url: string, name: string) => {
    const a = document.createElement('a')
    a.href = url
    a.download = `greeting_${name.replace(/\s+/g, '_')}.png`
    a.click()
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-100 text-sm uppercase tracking-wide">
          Results — {results.length} contacts
        </h3>
        <div className="flex gap-2 text-xs">
          <span className="badge badge-success">{results.filter(r => r.status === 'sent').length} sent</span>
          <span className="badge badge-info">{results.filter(r => r.status === 'generated').length} generated</span>
          {results.some(r => r.status === 'failed') && (
            <span className="badge badge-error">{results.filter(r => r.status === 'failed').length} failed</span>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 overflow-hidden">
        <div className="max-h-[420px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/60 sticky top-0">
              <tr>
                <th className="px-4 py-2.5 text-left text-slate-500 font-medium w-8">#</th>
                <th className="px-4 py-2.5 text-left text-slate-500 font-medium">Name</th>
                <th className="px-4 py-2.5 text-left text-slate-500 font-medium">Phone</th>
                <th className="px-4 py-2.5 text-left text-slate-500 font-medium">Status</th>
                <th className="px-4 py-2.5 text-left text-slate-500 font-medium">Image</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const conf = STATUS_CONF[r.status] ?? STATUS_CONF.generated
                const { Icon } = conf
                return (
                  <tr key={r.index} className="border-t border-slate-800/50 hover:bg-slate-800/20">
                    <td className="px-4 py-2.5 text-slate-600 text-xs">{r.index}</td>
                    <td className="px-4 py-2.5 text-slate-200 font-medium rtl-text">{r.name}</td>
                    <td className="px-4 py-2.5 text-slate-400 font-mono text-xs">{r.phone}</td>
                    <td className="px-4 py-2.5">
                      <span className={`badge ${conf.cls} inline-flex items-center gap-1`}>
                        <Icon className={`w-3 h-3 ${r.status === 'processing' ? 'animate-spin' : ''}`} />
                        {conf.label}
                      </span>
                      {r.error && (
                        <p className="text-red-400 text-xs mt-0.5 max-w-xs truncate" title={r.error}>
                          {r.error}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {r.imageUrl ? (
                        <div className="flex items-center gap-2">
                          <img
                            src={r.imageUrl}
                            alt={r.name}
                            className="w-10 h-10 object-cover rounded-lg border border-slate-700"
                          />
                          <div className="flex gap-1">
                            <a
                              href={r.imageUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                              title="Open image"
                            >
                              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                            </a>
                            <button
                              className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                              title="Download image"
                              onClick={() => handleDownload(r.imageUrl!, r.name)}
                            >
                              <Download className="w-3.5 h-3.5 text-slate-400" />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-600 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
