import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, Users, X } from 'lucide-react'
import React, { useRef, useState } from 'react'
import axios, { type AxiosError } from 'axios'
import type { Contact } from '../types'

interface Props {
  contacts:     Contact[]
  excelErrors:  string[]
  onDone:       (contacts: Contact[], filePath: string, errors: string[]) => void
}

export default function ExcelUpload({ contacts, excelErrors, onDone }: Props) {
  const inputRef    = useRef<HTMLInputElement>(null)
  const [dragging,  setDragging]  = useState(false)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)

  const handleFile = async (file: File) => {
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      setError('Please upload an Excel file (.xlsx or .xls)')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await axios.post('/api/upload-excel', fd)
      onDone(data.contacts, data.filePath, data.errors)
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
        <div className="p-2 bg-violet-600/20 rounded-xl">
          <FileSpreadsheet className="w-5 h-5 text-violet-400" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100">Excel Contact List</h3>
          <p className="text-xs text-slate-500">Column A: Name · Column B: Phone Number</p>
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
            {loading ? 'Uploading…' : 'Drop your Excel file here'}
          </p>
          <p className="text-slate-500 text-sm mt-1">or click to browse • .xlsx / .xls</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Success summary */}
      {contacts.length > 0 && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
            <CheckCircle className="w-4 h-4" />
            {contacts.length} contacts loaded successfully
          </div>
        </div>
      )}

      {/* Row-level validation errors */}
      {excelErrors.length > 0 && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-1 max-h-40 overflow-y-auto">
          <p className="text-amber-400 text-xs font-semibold uppercase tracking-wide mb-2">
            Validation warnings ({excelErrors.length})
          </p>
          {excelErrors.map((e, i) => (
            <p key={i} className="text-amber-300 text-xs flex items-start gap-1.5">
              <X className="w-3 h-3 mt-0.5 shrink-0 text-amber-500" />
              {e}
            </p>
          ))}
        </div>
      )}

      {/* Contact preview table */}
      {contacts.length > 0 && (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
          <div className="px-4 py-2 bg-slate-800/50 flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-400" />
            <span className="text-slate-400 text-xs font-medium uppercase tracking-wide">
              Contact Preview
            </span>
          </div>
          <div className="max-h-52 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/30 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-slate-500 font-medium w-8">#</th>
                  <th className="px-4 py-2 text-left text-slate-500 font-medium">Name</th>
                  <th className="px-4 py-2 text-left text-slate-500 font-medium">Phone</th>
                </tr>
              </thead>
              <tbody>
                {contacts.slice(0, 100).map((c, i) => (
                  <tr key={i} className="border-t border-slate-800/50 hover:bg-slate-800/20">
                    <td className="px-4 py-2 text-slate-600 text-xs">{i + 1}</td>
                    <td className="px-4 py-2 text-slate-200 font-medium rtl-text">{c.name}</td>
                    <td className="px-4 py-2 text-slate-400 font-mono text-xs">{c.phone}</td>
                  </tr>
                ))}
                {contacts.length > 100 && (
                  <tr className="border-t border-slate-800/50">
                    <td colSpan={3} className="px-4 py-2 text-slate-500 text-xs text-center">
                      … and {contacts.length - 100} more
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
