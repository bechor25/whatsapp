import { Play, StopCircle, Clock, Users, MessageCircle, Image as ImageIcon, RotateCcw, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import { useState } from 'react'
import type { Contact, ProcessingState } from '../types'

interface Props {
  contacts:        Contact[]
  hasImage:        boolean
  whatsappReady:   boolean
  processingState: ProcessingState
  onStart:         (sendWA: boolean, delayMin: number, delayMax: number, caption: string, runId: string) => void
  onStop:          () => void
}

export default function ProcessingPanel({
  contacts,
  hasImage,
  whatsappReady,
  processingState,
  onStart,
  onStop,
}: Props) {
  const [sendWA,   setSendWA]   = useState(true)
  // A range, not a constant: every pause is drawn randomly from it, because a
  // fixed interval is itself something WhatsApp's spam detection looks for.
  const [delayMin, setDelayMin] = useState(30)
  const [delayMax, setDelayMax] = useState(90)
  const [caption,  setCaption]  = useState('')
  const [runId,    setRunId]    = useState('')

  const { isProcessing, total, completed, failed, current } = processingState
  const progress = total > 0 ? Math.round((completed + failed) / total * 100) : 0
  const canStart = contacts.length > 0 && hasImage && (!sendWA || whatsappReady) && !isProcessing

  const lo = Math.min(delayMin, delayMax)
  const hi = Math.max(delayMin, delayMax)
  // Rough wall-clock for the whole run, at the average of the chosen range.
  const etaMinutes = Math.round(contacts.length * ((lo + hi) / 2) / 60)
  const etaLabel = etaMinutes >= 60
    ? `~${(etaMinutes / 60).toFixed(1)} hours`
    : `~${etaMinutes} min`
  // Under ~30s average with a real list is where accounts start getting flagged.
  const tooFast = sendWA && contacts.length > 20 && (lo + hi) / 2 < 30

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 mb-1">
        <div className="p-2 bg-emerald-600/20 rounded-xl">
          <Play className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h2 className="font-semibold text-slate-100">Send Messages</h2>
          <p className="text-xs text-slate-400">Generate images and optionally send via WhatsApp</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Contacts', value: contacts.length, icon: Users,         color: 'text-violet-400'  },
          { label: 'WhatsApp', value: whatsappReady ? 'Ready' : 'Not set',
            icon: MessageCircle, color: whatsappReady ? 'text-emerald-400' : 'text-slate-400' },
          { label: 'Template', value: hasImage ? 'Loaded' : 'Missing',
            icon: ImageIcon,    color: hasImage ? 'text-blue-400' : 'text-red-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card p-3 flex flex-col gap-1">
            <Icon className={`w-4 h-4 ${color}`} />
            <span className="text-xs text-slate-400">{label}</span>
            <span className={`font-semibold text-sm ${color}`}>{value}</span>
          </div>
        ))}
      </div>

      {/* Options */}
      <div className="space-y-4">
        {/* Send via WhatsApp toggle */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={sendWA}
            aria-label="Send via WhatsApp"
            onClick={() => setSendWA(!sendWA)}
            className="group flex items-center gap-3 -my-2 py-2 rounded-xl cursor-pointer
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400
                       focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          >
            <span
              className={`relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0
                ${sendWA ? 'bg-violet-600' : 'bg-slate-600'}`}
            >
              <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all duration-200
                ${sendWA ? 'left-6' : 'left-1'}`} />
            </span>
            <span className="text-slate-300 group-hover:text-slate-100 transition-colors">
              Send via WhatsApp
            </span>
          </button>
          {sendWA && !whatsappReady && (
            <span className="badge badge-warning">WhatsApp not connected</span>
          )}
        </div>

        {sendWA && (
          <>
            {/* Randomised delay range */}
            <div>
              <span className="label flex items-center gap-1.5" id="delay-label">
                <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                Delay Between Messages — random {lo}–{hi}s
              </span>
              <div className="flex items-center gap-3" role="group" aria-labelledby="delay-label">
                <input
                  type="number"
                  min={0}
                  max={600}
                  value={delayMin}
                  onChange={(e) => setDelayMin(Number(e.target.value))}
                  className="input-field w-24"
                  aria-label="Minimum delay in seconds"
                />
                <span className="text-slate-400 text-sm">to</span>
                <input
                  type="number"
                  min={0}
                  max={600}
                  value={delayMax}
                  onChange={(e) => setDelayMax(Number(e.target.value))}
                  className="input-field w-24"
                  aria-label="Maximum delay in seconds"
                />
                <span className="text-slate-400 text-sm">seconds</span>
                {contacts.length > 0 && (
                  <span className="text-xs text-slate-400 ml-auto">{etaLabel} total</span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Each pause is picked at random from this range — a constant interval
                is itself a signal WhatsApp's spam detection looks for.
              </p>
              {tooFast && (
                <div className="mt-2 flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
                  <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-amber-300">
                    Under 30s average across {contacts.length} contacts is a common
                    trigger for account blocks. 30–90s is the usual safe band, and
                    large lists are safer split over several days.
                  </p>
                </div>
              )}
            </div>

            {/* Resumable run */}
            <div>
              <label className="label flex items-center gap-1.5" htmlFor="campaign-name">
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                Campaign Name (optional)
              </label>
              <input
                id="campaign-name"
                className="input-field"
                placeholder="e.g. rosh-hashana-2026"
                value={runId}
                onChange={(e) => setRunId(e.target.value)}
              />
              <p className="text-xs text-slate-400 mt-1">
                Naming a campaign records who was already sent to. If it is
                interrupted, starting it again with the same name skips them
                instead of messaging them twice.
              </p>
            </div>

            {/* Caption */}
            <div>
              <label className="label" htmlFor="caption">Image Caption (optional)</label>
              <input
                id="caption"
                className="input-field"
                placeholder="e.g. Happy New Year! 🎉"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
              />
            </div>
          </>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        {!isProcessing ? (
          <button
            className="btn-success flex-1"
            disabled={!canStart}
            onClick={() => onStart(sendWA, lo, hi, caption, runId)}
          >
            <Play className="w-4 h-4" />
            {sendWA ? `Send to ${contacts.length} Contacts` : `Generate ${contacts.length} Images`}
          </button>
        ) : (
          <button className="btn-danger flex-1" onClick={onStop}>
            <StopCircle className="w-4 h-4" />
            Stop Processing
          </button>
        )}
      </div>

      {/* Validation hints */}
      {!canStart && !isProcessing && (
        <div className="text-xs text-slate-400 space-y-1">
          {contacts.length === 0 && <p>• No contacts loaded — upload an Excel file first.</p>}
          {!hasImage           && <p>• No template image — upload an image first.</p>}
          {sendWA && !whatsappReady && <p>• WhatsApp not connected — set it up in the previous step.</p>}
        </div>
      )}

      {/* Progress */}
      {(isProcessing || total > 0) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">{current || 'Idle'}</span>
            <span className="text-slate-400">{completed + failed} / {total}</span>
          </div>
          <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden">
            <div className="progress-bar h-full" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex gap-4 text-xs">
            <span className="text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />{completed} sent
            </span>
            {failed > 0 && (
              <span className="text-red-400 flex items-center gap-1">
                <XCircle className="w-3.5 h-3.5" aria-hidden="true" />{failed} failed
              </span>
            )}
            <span className="text-slate-400 ml-auto">{progress}%</span>
          </div>
        </div>
      )}
    </div>
  )
}
