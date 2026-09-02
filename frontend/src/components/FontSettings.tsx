import { useEffect, useState } from 'react'
import { HexColorPicker } from 'react-colorful'
import { Type, AlignLeft, AlignCenter, AlignRight } from 'lucide-react'
import axios from 'axios'
import type { TextConfig, FontInfo } from '../types'

interface Props {
  config:   TextConfig
  onChange: (cfg: TextConfig) => void
}

export default function FontSettings({ config, onChange }: Props) {
  const [fonts,  setFonts]  = useState<FontInfo[]>([])
  const [showCP, setShowCP] = useState(false)

  useEffect(() => {
    axios.get('/api/fonts').then(({ data }) => setFonts(data.fonts || []))
  }, [])

  const set = (partial: Partial<TextConfig>) => onChange({ ...config, ...partial })

  const ALIGNS: { v: TextConfig['align']; Icon: typeof AlignLeft; label: string }[] = [
    { v: 'left',   Icon: AlignLeft,   label: 'Left'   },
    { v: 'center', Icon: AlignCenter, label: 'Center' },
    { v: 'right',  Icon: AlignRight,  label: 'Right'  },
  ]

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 mb-1">
        <div className="p-2 bg-purple-600/20 rounded-xl">
          <Type className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h2 className="font-semibold text-slate-100">Text Settings</h2>
          <p className="text-xs text-slate-400">Font, size, colour, and alignment for the name</p>
        </div>
      </div>

      {/* Font selector */}
      <div>
        <label className="label" htmlFor="font-family">Font Family</label>
        <select
          id="font-family"
          className="input-field"
          value={config.fontName}
          onChange={(e) => set({ fontName: e.target.value })}
        >
          {fonts.map((f) => (
            <option key={f.path} value={f.name}>
              {f.name} {f.source === 'custom' ? '★' : ''}
            </option>
          ))}
          {fonts.length === 0 && <option value="Arial">Arial (default)</option>}
        </select>
        <p className="text-xs text-slate-400 mt-1">
          ★ = bundled Hebrew font in backend/fonts/
        </p>
      </div>

      {/* Font size */}
      <div>
        <label className="label" htmlFor="font-size">Font Size — {config.fontSize}px</label>
        <div className="flex items-center gap-3">
          <input
            id="font-size"
            type="range"
            min={12}
            max={300}
            step={2}
            value={config.fontSize}
            onChange={(e) => set({ fontSize: Number(e.target.value) })}
            className="flex-1 accent-violet-500"
          />
          <input
            type="number"
            min={12}
            max={300}
            value={config.fontSize}
            onChange={(e) => set({ fontSize: Number(e.target.value) })}
            className="input-field w-20"
          />
        </div>
      </div>

      {/* Font colour */}
      <div>
        <span className="label" id="font-colour-label">Font Colour</span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label={`Font colour, currently ${config.fontColor}. Open colour picker`}
            aria-expanded={showCP}
            className="w-10 h-10 rounded-xl border-2 border-slate-600 shrink-0 shadow-inner cursor-pointer
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400
                       focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            style={{ backgroundColor: config.fontColor }}
            onClick={() => setShowCP(!showCP)}
          />
          <input
            type="text"
            aria-labelledby="font-colour-label"
            value={config.fontColor}
            onFocus={() => setShowCP(true)}
            onChange={(e) => set({ fontColor: e.target.value })}
            className="input-field font-mono"
            placeholder="#FFFFFF"
          />
        </div>
        {showCP && (
          <div className="mt-3 relative z-20">
            <HexColorPicker
              color={config.fontColor}
              onChange={(c) => set({ fontColor: c })}
            />
            <button
              className="mt-2 text-xs text-slate-400 hover:text-slate-200"
              onClick={() => setShowCP(false)}
            >
              Close
            </button>
          </div>
        )}
      </div>

      {/* Stroke */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label" htmlFor="stroke-width">Stroke / Outline — {config.strokeWidth}px</label>
          <input
            id="stroke-width"
            type="range"
            min={0}
            max={10}
            step={1}
            value={config.strokeWidth}
            onChange={(e) => set({ strokeWidth: Number(e.target.value) })}
            className="w-full accent-violet-500"
          />
        </div>
        <div>
          <label className="label" htmlFor="stroke-colour">Stroke Colour</label>
          <input
            id="stroke-colour"
            type="color"
            value={config.strokeColor}
            onChange={(e) => set({ strokeColor: e.target.value })}
            className="w-full h-10 rounded-xl border border-slate-700 bg-slate-800 cursor-pointer p-1"
          />
        </div>
      </div>

      {/* Alignment */}
      <div>
        <span className="label" id="text-align-label">Text Alignment</span>
        <div className="flex gap-2" role="group" aria-labelledby="text-align-label">
          {ALIGNS.map(({ v, Icon, label }) => (
            <button
              key={v}
              type="button"
              onClick={() => set({ align: v })}
              aria-pressed={config.align === v}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-sm font-medium transition-all duration-150
                min-h-[44px] cursor-pointer focus-visible:outline-none focus-visible:ring-2
                focus-visible:ring-violet-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                ${config.align === v
                  ? 'bg-violet-600/30 border-violet-500 text-violet-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
                }`}
              title={label}
            >
              <Icon className="w-4 h-4" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-400 italic">
        💡 Drag the name text directly on the Preview panel to reposition it.
      </p>
    </div>
  )
}
