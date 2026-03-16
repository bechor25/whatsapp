// ── Domain types ──────────────────────────────────────────────────────────────

export interface TextConfig {
  fontName:    string;
  fontSize:    number;
  fontColor:   string;
  xPercent:    number; // 0–1 relative to image width
  yPercent:    number; // 0–1 relative to image height
  align:       'left' | 'center' | 'right';
  strokeWidth: number;
  strokeColor: string;
}

export interface Contact {
  name:           string;
  phone:          string;
  original_phone?: string;
}

export interface ProcessResult {
  index:    number;
  name:     string;
  phone:    string;
  imageUrl: string | null;
  status:   'processing' | 'generated' | 'sent' | 'failed';
  error:    string | null;
}

export interface LogEntry {
  time:    string;
  message: string;
  status:  'success' | 'error' | 'warning' | 'info';
}

export interface ProcessingState {
  isProcessing: boolean;
  total:        number;
  completed:    number;
  failed:       number;
  current:      string;
  results:      ProcessResult[];
  logs:         LogEntry[];
}

export interface FontInfo {
  name:   string;
  path:   string;
  source: 'custom' | 'system';
}

export interface UploadedImage {
  filePath: string;
  url:      string;
  width:    number;
  height:   number;
}

// ── App step navigation ───────────────────────────────────────────────────────
export type AppStep = 'upload' | 'configure' | 'whatsapp' | 'process';
