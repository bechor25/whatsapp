import { useEffect, useRef, useState } from 'react'
import { MessageCircle, CheckCircle, XCircle, Loader, RefreshCw, ExternalLink, Smartphone } from 'lucide-react'
import axios, { type AxiosError } from 'axios'

interface Props {
  onStatusChange: (loggedIn: boolean) => void
}

type Transport = 'neonize' | 'playwright'

export default function WhatsAppSetup({ onStatusChange }: Props) {
  const [initialized, setInitialized] = useState(false)
  const [loggedIn,    setLoggedIn]    = useState(false)
  const [message,     setMessage]     = useState('Not connected yet.')
  const [loading,     setLoading]     = useState(false)
  const [polling,     setPolling]     = useState(false)
  // Which pairing flow the backend is running. neonize shows a QR in this page;
  // playwright opens a Chromium window the user scans there instead.
  const [transport,   setTransport]   = useState<Transport>('neonize')
  const [qrUrl,       setQrUrl]       = useState<string | null>(null)

  // Guards the auto-refresh so an expiring QR triggers exactly one re-pair,
  // not one per poll tick.
  const refreshingRef = useRef(false)

  const isBrowserFlow = transport === 'playwright'

  const applyStatus = (data: {
    transport?: Transport
    logged_in: boolean
    message: string
    qr_url?: string
    qr_stale?: boolean
  }) => {
    if (data.transport) setTransport(data.transport)
    setMessage(data.message)
    setQrUrl(data.qr_url ?? null)
    if (data.logged_in) {
      setLoggedIn(true)
      setPolling(false)
      setQrUrl(null)
      onStatusChange(true)
      return true
    }
    return false
  }

  /* ── Poll status while unpaired ─────────────────────────────────────── */
  useEffect(() => {
    if (!initialized || loggedIn) return
    setPolling(true)
    const id = setInterval(async () => {
      try {
        const { data } = await axios.get('/api/whatsapp/status')
        if (applyStatus(data)) {
          clearInterval(id)
          return
        }
        // whatsmeow rotates the pairing code every 60s by itself, so normally
        // there is nothing to do. Only once it stops rotating has the pairing
        // attempt died, and only then is a reconnect needed to get a live code.
        if (data.qr_stale && !refreshingRef.current) {
          refreshingRef.current = true
          setMessage('Pairing timed out — generating a new code…')
          try {
            await axios.post('/api/whatsapp/init')
          } finally {
            refreshingRef.current = false
          }
        }
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(id)
  }, [initialized, loggedIn, onStatusChange])

  const handleInit = async () => {
    setLoading(true)
    setQrUrl(null)
    setMessage('Connecting…')
    try {
      const { data } = await axios.post('/api/whatsapp/init')
      setMessage(data.message)
      setInitialized(true)
      if (data.logged_in) {
        setLoggedIn(true)
        onStatusChange(true)
      }
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? (e as AxiosError<{detail: string}>).response?.data?.detail : String(e)
      setMessage(`Error: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  const checkNow = async () => {
    try {
      const { data } = await axios.get('/api/whatsapp/status')
      applyStatus(data)
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 mb-1">
        <div className="p-2 bg-green-600/20 rounded-xl">
          <MessageCircle className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100">WhatsApp Setup</h3>
          <p className="text-xs text-slate-500">
            {isBrowserFlow
              ? 'Opens a browser — scan the QR once, session is saved for future runs'
              : 'Scan the QR once from your phone — session is saved for future runs'}
          </p>
        </div>
      </div>

      {/* Status card */}
      <div className={`p-4 rounded-2xl border flex items-start gap-3
        ${loggedIn
          ? 'bg-emerald-500/10 border-emerald-500/30'
          : initialized
            ? 'bg-amber-500/10 border-amber-500/30'
            : 'bg-slate-800/50 border-slate-700'
        }`}>
        {loggedIn ? (
          <CheckCircle className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
        ) : polling ? (
          <Loader className="w-5 h-5 text-amber-400 mt-0.5 shrink-0 animate-spin" />
        ) : (
          <XCircle className="w-5 h-5 text-slate-500 mt-0.5 shrink-0" />
        )}
        <div>
          <p className={`font-medium text-sm ${loggedIn ? 'text-emerald-300' : initialized ? 'text-amber-300' : 'text-slate-400'}`}>
            {loggedIn ? 'WhatsApp Ready ✓' : initialized ? 'Waiting for QR scan…' : 'Not connected'}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">{message}</p>
        </div>
      </div>

      {/* Pairing QR — rendered in-page by the neonize transport */}
      {!loggedIn && qrUrl && (
        <div className="p-4 bg-white rounded-2xl border border-slate-300 flex flex-col items-center gap-3">
          <img src={qrUrl} alt="WhatsApp pairing QR code" className="w-56 h-56" />
          <div className="flex items-center gap-2 text-slate-700">
            <Smartphone className="w-4 h-4 shrink-0" />
            <p className="text-xs text-center">
              WhatsApp → Settings → Linked Devices → <strong>Link a Device</strong>
            </p>
          </div>
          <p className="text-[11px] text-slate-500">
            The code refreshes itself — just scan whatever is shown
          </p>
        </div>
      )}

      {/* How it works */}
      {!initialized && (
        <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700 space-y-2 text-sm">
          <p className="font-medium text-slate-300">How it works:</p>
          <ol className="space-y-1.5 text-slate-400 list-decimal list-inside">
            <li>Click <span className="text-violet-400 font-medium">
              {isBrowserFlow ? 'Launch WhatsApp Browser' : 'Connect WhatsApp'}</span></li>
            {isBrowserFlow ? (
              <li>A Chrome window opens on
                <span className="text-blue-400 font-mono ml-1 text-xs">web.whatsapp.com</span></li>
            ) : (
              <li>A QR code appears right here on this page</li>
            )}
            <li>Scan it with your phone's WhatsApp (Linked Devices)</li>
            <li>Session is saved — future runs won't need a re-scan</li>
          </ol>
        </div>
      )}

      <div className="flex gap-3">
        {!loggedIn && (
          <button
            className="btn-primary flex-1"
            onClick={handleInit}
            disabled={loading}
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <ExternalLink className="w-4 h-4" />
            )}
            {initialized
              ? 'Restart Pairing'
              : isBrowserFlow ? 'Launch WhatsApp Browser' : 'Connect WhatsApp'}
          </button>
        )}

        {initialized && !loggedIn && (
          <button className="btn-secondary" onClick={checkNow}>
            <RefreshCw className="w-4 h-4" />
            Check Status
          </button>
        )}
      </div>

      {loggedIn && (
        <p className="text-center text-sm text-emerald-400">
          ✓ Connected to WhatsApp. Proceed to the next step.
        </p>
      )}
    </div>
  )
}
