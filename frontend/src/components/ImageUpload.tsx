import { Upload, Image as ImageIcon, CheckCircle, AlertCircle } from 'lucide-react'
import { useRef, useState } from 'react'
import axios, { type AxiosError } from 'axios'
import type { UploadedImage } from '../types'

interface Props {
  image:   UploadedImage | null
  onDone:  (img: UploadedImage) => void
}

export default function ImageUpload({ image, onDone }: Props) {
  const inputRef  = useRef<HTMLInputElement>(null)
  const [dragging, setDragging]  = useState(false)
  const [loading,  setLoading]   = useState(false)
  const [error,    setError]     = useState<string | null>(null)

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (PNG, JPG, BMP, etc.)')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await axios.post('/api/upload-image', fd)
      onDone(data as UploadedImage)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? (e as AxiosError<{detail: string}>).response?.data?.detail : String(e)
      setError(msg ?? 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-blue-600/20 rounded-xl">
          <ImageIcon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100">Template Image</h3>
          <p className="text-xs text-slate-500">Greeting card that will be personalised per contact</p>
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragging ? 'drop-zone-active' : ''} ${loading ? 'opacity-60 pointer-events-none' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <Upload className="w-8 h-8 text-slate-500" />
        <div className="text-center">
          <p className="text-slate-300 font-medium">
            {loading ? 'Uploading…' : 'Drop your template image here'}
          </p>
          <p className="text-slate-500 text-sm mt-1">or click to browse • PNG / JPG / BMP / WebP</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {image && (
        <>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
              <CheckCircle className="w-4 h-4" />
              Image loaded · {image.width} × {image.height} px
            </div>
          </div>

          <div className="rounded-xl overflow-hidden border border-slate-800">
            <img
              src={image.url}
              alt="Template preview"
              className="w-full object-contain max-h-64 bg-checkerboard"
            />
          </div>
        </>
      )}
    </div>
  )
}
