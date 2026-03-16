import { useRef, useState, useCallback, useEffect } from 'react'
import { Eye, RefreshCw, Move } from 'lucide-react'
import axios from 'axios'
import type { TextConfig, UploadedImage } from '../types'

interface Props {
  image:     UploadedImage | null
  config:    TextConfig
  onChange:  (cfg: TextConfig) => void
  sampleName?: string
}

export default function PreviewPanel({ image, config, onChange, sampleName = 'שם לדוגמה' }: Props) {
  const containerRef  = useRef<HTMLDivElement>(null)
  const [dragging,    setDragging]    = useState(false)
  const [serverUrl,   setServerUrl]   = useState<string | null>(null)
  const [generating,  setGenerating]  = useState(false)
  const debounceRef   = useRef<ReturnType<typeof setTimeout> | null>(null)

  /* ── Drag-to-position ─────────────────────────────────────────────────── */

  const getRelativePos = useCallback((clientX: number, clientY: number) => {
    if (!containerRef.current) return null
    const rect = containerRef.current.getBoundingClientRect()
    return {
      xPercent: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
      yPercent: Math.max(0, Math.min(1, (clientY - rect.top)  / rect.height)),
    }
  }, [])

  const onMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging) return
    const pos = getRelativePos(e.clientX, e.clientY)
    if (pos) onChange({ ...config, ...pos })
  }, [dragging, config, onChange, getRelativePos])

  const onMouseUp = useCallback(() => {
    if (dragging) {
      setDragging(false)
      generateServerPreview()
    }
  }, [dragging]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (dragging) {
      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('mouseup',  onMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup',  onMouseUp)
    }
  }, [dragging, onMouseMove, onMouseUp])

  /* ── Server-side preview generation ──────────────────────────────────── */

  const generateServerPreview = async () => {
    if (!image) return
    setGenerating(true)
    try {
      const { data } = await axios.post('/api/preview', {
        image_path:  image.filePath,
        sample_name: sampleName,
        text_config: toSnakeCase(config),
      })
      setServerUrl(data.previewUrl + `?t=${Date.now()}`)
    } catch { /* silently ignore */ }
    finally { setGenerating(false) }
  }

  // Debounce config changes → re-generate server preview
  useEffect(() => {
    if (!image) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(generateServerPreview, 600)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [config, image, sampleName]) // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Derived CSS for overlay text ────────────────────────────────────── */

  const overlayStyle: React.CSSProperties = {
    position:   'absolute',
    left:       `${config.xPercent * 100}%`,
    top:        `${config.yPercent * 100}%`,
    transform:
      config.align === 'center' ? 'translate(-50%, -50%)' :
      config.align === 'right'  ? 'translate(-100%, -50%)' :
                                   'translate(0, -50%)',
    color:      config.fontColor,
    fontSize:   `clamp(10px, ${config.fontSize * 0.5}px, 72px)`, // scale for preview
    fontFamily: config.fontName,
    direction:  'rtl',
    cursor:     dragging ? 'grabbing' : 'grab',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    textShadow:
      config.strokeWidth > 0
        ? `0 0 ${config.strokeWidth * 2}px ${config.strokeColor},
           1px 1px 0 ${config.strokeColor},
          -1px -1px 0 ${config.strokeColor}`
        : 'none',
    padding:    '2px 4px',
    background: dragging ? 'rgba(124,58,237,0.15)' : 'transparent',
    borderRadius: '4px',
    transition: dragging ? 'none' : 'background 0.2s',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 rounded-xl">
            <Eye className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">Live Preview</h3>
            <p className="text-xs text-slate-500">
              Drag the name to reposition · actual render is server-generated below
            </p>
          </div>
        </div>
        <button
          className="btn-secondary text-xs px-3 py-1.5"
          onClick={generateServerPreview}
          disabled={!image || generating}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {!image ? (
        <div className="flex items-center justify-center h-48 rounded-2xl border-2 border-dashed border-slate-800 text-slate-600">
          Upload a template image first
        </div>
      ) : (
        <>
          {/* ── Interactive overlay (CSS-based, instant) ── */}
          <div className="relative select-none">
            <div
              ref={containerRef}
              className="relative rounded-xl overflow-hidden border border-slate-800 cursor-crosshair"
            >
              <img
                src={image.url + `?t=base`}
                alt="Template"
                className="w-full block"
                draggable={false}
              />
              {/* Draggable text handle */}
              <div style={overlayStyle} onMouseDown={onMouseDown}>
                <span className="flex items-center gap-1">
                  <Move className="w-3 h-3 opacity-50" />
                  {sampleName}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-600 text-center mt-1">
              ↑ Drag the name to set position (
              {Math.round(config.xPercent * 100)}%,
              {Math.round(config.yPercent * 100)}%
              )
            </p>
          </div>

          {/* ── Server-rendered preview (actual Pillow output) ── */}
          {serverUrl && (
            <div className="space-y-2">
              <p className="text-xs text-slate-500 flex items-center gap-1">
                <Eye className="w-3.5 h-3.5" />
                Server-rendered output (Hebrew BiDi applied):
              </p>
              <div className="rounded-xl overflow-hidden border border-violet-800/40">
                {generating ? (
                  <div className="h-32 flex items-center justify-center bg-slate-900 text-slate-500 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                    Generating…
                  </div>
                ) : (
                  <img src={serverUrl} alt="Server preview" className="w-full block" />
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function toSnakeCase(cfg: TextConfig) {
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
