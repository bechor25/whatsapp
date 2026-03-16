import { Play, StopCircle, Clock, Users, MessageCircle, Image as ImageIcon } from 'lucide-react'
import { useState } from 'react'
import type { Contact, ProcessingState } from '../types'

interface Props {
  contacts:        Contact[]
  hasImage:        boolean
  whatsappReady:   boolean
  processingState: ProcessingState
  onStart:         (sendWA: boolean, delay: number, caption: string) => void
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
  const [delay,    setDelay]    = useState(3)
  const [caption,  setCaption]  = useState('')

  const { isProcessing, total, completed, failed, current } = processingState
  const progress = total > 0 ? Math.round((completed + failed) / total * 100) : 0
  const canStart = contacts.length > 0 && hasImage && (!sendWA || whatsappReady) && !isProcessing

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 mb-1">
        <div className="p-2 bg-emerald-600/20 rounded-xl">
          <Play className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100">Send Messages</h3>
          <p className="text-xs text-slate-500">Generate images and optionally send via WhatsApp</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Contacts', value: contacts.length, icon: Users,         color: 'text-violet-400'  },
          { label: 'WhatsApp', value: whatsappReady ? 'Ready' : 'Not set',
            icon: MessageCircle, color: whatsappReady ? 'text-emerald-400' : 'text-slate-500' },
          { label: 'Template', value: hasImage ? 'Loaded' : 'Missing',
            icon: ImageIcon,    color: hasImage ? 'text-blue-400' : 'text-red-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card p-3 flex flex-col gap-1">
            <Icon className={`w-4 h-4 ${color}`} />
            <span className="text-xs text-slate-500">{label}</span>
            <span className={`font-semibold text-sm ${color}`}>{value}</span>
          </div>
        ))}
      </div>

      {/* Options */}
      <div className="space-y-4">
        {/* Send via WhatsApp toggle */}
        <label className="flex items-center gap-3 cursor-pointer group">
          <div
            className={`relative w-11 h-6 rounded-full transition-colors duration-200
              ${sendWA ? 'bg-violet-600' : 'bg-slate-700'}`}
            onClick={() => setSendWA(!sendWA)}
          >
            <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all duration-200
              ${sendWA ? 'left-6' : 'left-1'}`} />
          </div>
          <span className="text-slate-300 group-hover:text-slate-100 transition-colors">
            Send via WhatsApp Web
          </span>
          {sendWA && !whatsappReady && (
            <span className="badge badge-warning">WhatsApp not connected</span>
          )}
        </label>

        {sendWA && (
          <>
            {/* Delay */}
            <div>
              <label className="label flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Delay Between Messages — {delay}s
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={30}
                  step={1}
                  value={delay}
                  onChange={(e) => setDelay(Number(e.target.value))}
                  className="flex-1 accent-violet-500"
                />
                <input
                  type="number"
                  min={0}
                  max={60}
                  value={delay}
                  onChange={(e) => setDelay(Number(e.target.value))}
                  className="input-field w-20"
                />
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Higher delays reduce the risk of WhatsApp blocking your number.
              </p>
            </div>

            {/* Caption */}
            <div>
              <label className="label">Image Caption (optional)</label>
              <input
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
            onClick={() => onStart(sendWA, delay, caption)}
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
        <div className="text-xs text-slate-500 space-y-1">
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
            <span className="text-emerald-400">✓ {completed} sent</span>
            {failed > 0 && <span className="text-red-400">✗ {failed} failed</span>}
            <span className="text-slate-500 ml-auto">{progress}%</span>
          </div>
        </div>
      )}
    </div>
  )
}
