import { useState, useCallback } from 'react'
import axios from 'axios'
import {
  FileSpreadsheet,
  Image as ImageIcon,
  Settings2,
  MessageCircle,
  Zap,
  CheckCircle,
  ChevronRight,
} from 'lucide-react'

import ExcelUpload     from './components/ExcelUpload'
import ImageUpload     from './components/ImageUpload'
import FontSettings    from './components/FontSettings'
import PreviewPanel    from './components/PreviewPanel'
import WhatsAppSetup   from './components/WhatsAppSetup'
import ProcessingPanel from './components/ProcessingPanel'
import ResultsPanel    from './components/ResultsPanel'
import StatusLog       from './components/StatusLog'
import { useWebSocket }from './hooks/useWebSocket'

import type {
  AppStep,
  Contact,
  FontInfo as _FontInfo,
  LogEntry,
  ProcessingState,
  TextConfig,
  UploadedImage,
} from './types'

// ── Default text config ───────────────────────────────────────────────────────
const DEFAULT_CONFIG: TextConfig = {
  fontName:    'Arial',
  fontSize:    72,
  fontColor:   '#FFFFFF',
  xPercent:    0.5,
  yPercent:    0.5,
  align:       'center',
  strokeWidth: 2,
  strokeColor: '#000000',
}

const DEFAULT_STATE: ProcessingState = {
  isProcessing: false,
  total:        0,
  completed:    0,
  failed:       0,
  current:      '',
  results:      [],
  logs:         [],
}

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS: { id: AppStep; label: string; icon: typeof Zap }[] = [
  { id: 'upload',    label: '1. Upload Files',  icon: FileSpreadsheet },
  { id: 'configure', label: '2. Configure Text', icon: Settings2       },
  { id: 'whatsapp',  label: '3. WhatsApp',       icon: MessageCircle   },
  { id: 'process',   label: '4. Send',           icon: Zap             },
]

export default function App() {
  const [step,         setStep]         = useState<AppStep>('upload')
  const [contacts,     setContacts]     = useState<Contact[]>([])
  const [excelErrors,  setExcelErrors]  = useState<string[]>([])
  const [excelPath,    setExcelPath]    = useState('')
  const [image,        setImage]        = useState<UploadedImage | null>(null)
  const [textConfig,   setTextConfig]   = useState<TextConfig>(DEFAULT_CONFIG)
  const [waReady,      setWaReady]      = useState(false)
  const [procState,    setProcState]    = useState<ProcessingState>(DEFAULT_STATE)

  /* ── WebSocket for real-time updates ─────────────────────────────────── */
  useWebSocket('ws://localhost:8000/ws/progress', useCallback((msg) => {
    if (msg.type === 'heartbeat') return
    if (msg.data) {
      const d = msg.data as ProcessingState
      setProcState({
        isProcessing: d.isProcessing,
        total:        d.total,
        completed:    d.completed,
        failed:       d.failed,
        current:      d.current,
        results:      d.results ?? [],
        logs:         d.logs    ?? [],
      })
    }
  }, []))

  /* ── Processing actions ──────────────────────────────────────────────── */
  const handleStart = async (sendWA: boolean, delay: number, caption: string) => {
    await axios.post('/api/process/start', {
      image_path:     image!.filePath,
      contacts:       contacts,
      text_config:    toSnake(textConfig),
      send_whatsapp:  sendWA,
      caption:        caption,
      delay_seconds:  delay,
    })
  }

  const handleStop = async () => {
    await axios.post('/api/process/stop')
  }

  /* ── Step navigation ─────────────────────────────────────────────────── */
  const isStepDone = (id: AppStep): boolean => {
    switch (id) {
      case 'upload':    return contacts.length > 0 && image !== null
      case 'configure': return true
      case 'whatsapp':  return waReady
      default:          return false
    }
  }

  const stepIndex   = STEPS.findIndex(s => s.id === step)
  const canGoNext   = stepIndex < STEPS.length - 1
  const canGoPrev   = stepIndex > 0

  const goNext = () => canGoNext && setStep(STEPS[stepIndex + 1].id)
  const goPrev = () => canGoPrev && setStep(STEPS[stepIndex - 1].id)

  /* ── Render ──────────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen gradient-bg">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-violet-600 to-blue-600 rounded-xl flex items-center justify-center shadow-lg glow-violet">
              <MessageCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-slate-100 text-lg leading-none">WhatsApp Greeting Sender</h1>
              <p className="text-xs text-slate-500 mt-0.5">Personalised greeting images · Local · Free</p>
            </div>
          </div>

          {/* Step pills */}
          <nav className="hidden md:flex items-center gap-1">
            {STEPS.map((s, i) => {
              const Icon  = s.icon
              const done  = isStepDone(s.id)
              const active = s.id === step
              return (
                <button
                  key={s.id}
                  onClick={() => setStep(s.id)}
                  className={`step-tab
                    ${active ? 'step-tab-active' : done ? 'step-tab-done' : 'step-tab-inactive'}`}
                >
                  {done && !active
                    ? <CheckCircle className="w-4 h-4" />
                    : <Icon className="w-4 h-4" />
                  }
                  <span className="hidden lg:inline">{s.label}</span>
                  {i < STEPS.length - 1 && (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-700 hidden lg:block" />
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">

        {/* ── Step 1: Upload ────────────────────────────────────────────── */}
        {step === 'upload' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <ExcelUpload
                contacts={contacts}
                excelErrors={excelErrors}
                onDone={(c, _path, errs) => {
                  setContacts(c)
                  setExcelPath(_path)
                  setExcelErrors(errs)
                }}
              />
            </div>
            <div className="card p-6">
              <ImageUpload image={image} onDone={setImage} />
            </div>
          </div>
        )}

        {/* ── Step 2: Configure ─────────────────────────────────────────── */}
        {step === 'configure' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <FontSettings config={textConfig} onChange={setTextConfig} />
            </div>
            <div className="card p-6">
              <PreviewPanel
                image={image}
                config={textConfig}
                onChange={setTextConfig}
                sampleName="שם לדוגמה"
              />
            </div>
          </div>
        )}

        {/* ── Step 3: WhatsApp ──────────────────────────────────────────── */}
        {step === 'whatsapp' && (
          <div className="max-w-xl mx-auto">
            <div className="card p-6">
              <WhatsAppSetup onStatusChange={setWaReady} />
            </div>
          </div>
        )}

        {/* ── Step 4: Process ───────────────────────────────────────────── */}
        {step === 'process' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="card p-6">
                <ProcessingPanel
                  contacts={contacts}
                  hasImage={image !== null}
                  whatsappReady={waReady}
                  processingState={procState}
                  onStart={handleStart}
                  onStop={handleStop}
                />
              </div>
              <div className="card p-6">
                <StatusLog
                  logs={procState.logs}
                  onClear={() => setProcState(prev => ({ ...prev, logs: [] }))}
                />
              </div>
            </div>

            {procState.results.length > 0 && (
              <div className="card p-6">
                <ResultsPanel results={procState.results} />
              </div>
            )}
          </div>
        )}

        {/* ── Navigation buttons ────────────────────────────────────────── */}
        <div className="flex items-center justify-between pt-2">
          <button
            className="btn-secondary"
            onClick={goPrev}
            disabled={!canGoPrev}
          >
            ← Back
          </button>

          <p className="text-xs text-slate-600">
            Step {stepIndex + 1} of {STEPS.length}
          </p>

          {canGoNext && (
            <button
              className="btn-primary"
              onClick={goNext}
              disabled={
                step === 'upload' && (contacts.length === 0 || image === null)
              }
            >
              Next →
            </button>
          )}

          {!canGoNext && (
            <div className="w-24" />
          )}
        </div>
      </main>
    </div>
  )
}

/* ── Utility ─────────────────────────────────────────────────────────────── */
function toSnake(cfg: TextConfig) {
  return {
    font_name:    cfg.fontName,
    font_size:    cfg.fontSize,
    font_color:   cfg.fontColor,
    x_percent:    cfg.xPercent,
    y_percent:    cfg.yPercent,
    align:        cfg.align,
    stroke_width: cfg.strokeWidth,
    stroke_color: cfg.strokeColor,
  }
}
