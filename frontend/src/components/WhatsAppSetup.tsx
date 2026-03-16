import { useEffect, useState } from 'react'
import { MessageCircle, CheckCircle, XCircle, Loader, RefreshCw, ExternalLink } from 'lucide-react'
import axios, { type AxiosError } from 'axios'

interface Props {
  onStatusChange: (loggedIn: boolean) => void
}

export default function WhatsAppSetup({ onStatusChange }: Props) {
  const [initialized, setInitialized] = useState(false)
  const [loggedIn,    setLoggedIn]    = useState(false)
  const [message,     setMessage]     = useState('WhatsApp Web not started yet.')
  const [loading,     setLoading]     = useState(false)
  const [polling,     setPolling]     = useState(false)

  /* ── Poll status every 3 s once browser is up ──────────────────────── */
  useEffect(() => {
    if (!initialized || loggedIn) return
    setPolling(true)
    const id = setInterval(async () => {
      try {
        const { data } = await axios.get('/api/whatsapp/status')
        setMessage(data.message)
        if (data.logged_in) {
          setLoggedIn(true)
          setPolling(false)
          onStatusChange(true)
          clearInterval(id)
        }
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(id)
  }, [initialized, loggedIn, onStatusChange])

  const handleInit = async () => {
    setLoading(true)
    setMessage('Launching browser…')
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
      setMessage(data.message)
      if (data.logged_in) {
        setLoggedIn(true)
        setPolling(false)
        onStatusChange(true)
      }
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 mb-1">
        <div className="p-2 bg-green-600/20 rounded-xl">
          <MessageCircle className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100">WhatsApp Web Setup</h3>
          <p className="text-xs text-slate-500">
            Opens a browser — scan QR once, session is saved for future runs
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

      {/* How it works */}
      {!initialized && (
        <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700 space-y-2 text-sm">
          <p className="font-medium text-slate-300">How it works:</p>
          <ol className="space-y-1.5 text-slate-400 list-decimal list-inside">
            <li>Click <span className="text-violet-400 font-medium">Launch WhatsApp Browser</span></li>
            <li>A Chrome window opens → navigate to
              <span className="text-blue-400 font-mono ml-1 text-xs">web.whatsapp.com</span></li>
            <li>Scan the QR code with your phone's WhatsApp</li>
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
            {initialized ? 'Restart Browser' : 'Launch WhatsApp Browser'}
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
          ✓ You are logged in to WhatsApp Web. Proceed to the next step.
        </p>
      )}
    </div>
  )
}
