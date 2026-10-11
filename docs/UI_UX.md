# UI / UX Design & Interface Specification

**Framework:** Next.js (App Router) + React + Tailwind CSS  
**Iconography:** Lucide React (`lucide-react`)  
**Theme:** Light Mode SaaS Workstation  
**Aesthetic:** Crisp Geometric SaaS, Sharp Edges (4px–6px Radii), High Contrast, Dense Productivity Layout  

---

## 1. Design System & SaaS Aesthetic Principles

* **Light-First B2B SaaS Workstation:** Engineered for productivity, clarity, and precision (inspired by modern B2B SaaS benchmarks like Linear, Stripe, and Vercel). High legibility with stark contrast, zero muddy gray fills, and crisp border boundaries.
* **Geometric / Subtle Radii:** **No bubbly pills or 16px/24px rounded corners.** 
  * Buttons, inputs, and badges: `rounded-[4px]` (`rounded-sm`).
  * Cards, tables, and dialog containers: `rounded-[6px]` (`rounded-md`).
  * Strict rule: Maximum corner radius anywhere in the app is **6px**.
* **Spatial Density & Layout Rhythm:** Tight, compact 4px grid spacing (`gap-2`, `gap-3`, `px-3`, `py-2`) maximizing information density without visual crowding.
* **Micro-Borders & Dividers:** Subtle, crisp 1px borders (`border-slate-200`) establish layout seams instead of heavy drop shadows.

---

## 2. Next.js Project & Component Architecture

```
transcriber-ui/
├── app/
│   ├── layout.tsx                  # Root layout, telemetry header, global providers
│   ├── page.tsx                    # Main Queue & Ingestion Dashboard
│   ├── studio/
│   │   └── [jobId]/
│   │       └── page.tsx            # Full-screen Interactive Transcript Studio
│   ├── settings/
│   │   └── page.tsx            # Hardware, model caches, and engine settings
│   └── globals.css                 # Design tokens, CSS variables, typography
├── components/
│   ├── layout/
│   │   ├── Header.tsx              # Top telemetry bar, VRAM meter, active worker status
│   │   └── SubHeader.tsx           # Page actions, quick filters, bulk export trigger
│   ├── queue/
│   │   ├── Dropzone.tsx            # Sharp multi-file drag-and-drop zone
│   │   ├── ConfigPanel.tsx         # Ingestion settings (Mode, Language, Diarize, Filter)
│   │   ├── JobTable.tsx            # Batch queue table with real-time SSE progress
│   │   ├── JobRow.tsx              # Individual job row with stage indicators
│   │   └── JobActions.tsx          # Context menu: cancel, retry, export, delete
│   ├── studio/
│   │   ├── MediaPlayer.tsx         # Waveform scrubber & video preview dock
│   │   ├── TranscriptFlow.tsx      # Virtualized transcript list with word highlights
│   │   ├── SegmentCard.tsx         # Individual sentence block with speaker badge
│   │   ├── WordSpan.tsx            # Click-to-seek, millisecond-aligned word span
│   │   ├── SpeakerModal.tsx        # Bulk speaker rename modal dialog
│   │   └── SearchReplaceBar.tsx    # Floating search & replace drawer
│   └── ui/                         # Base primitives (Radix UI + Tailwind)
│       ├── button.tsx
│       ├── badge.tsx
│       ├── input.tsx
│       ├── select.tsx
│       ├── table.tsx
│       ├── progress.tsx
│       └── dialog.tsx
```

---

## 3. Light Theme Color Palette & Tokens

```css
:root {
  /* Canvas & Surface Elevations */
  --bg-canvas: #f8fafc;            /* slate-50  - Main page background */
  --bg-surface: #ffffff;           /* white     - Cards, tables, modals */
  --bg-subtle: #f1f5f9;            /* slate-100 - Ingestion zones, header docks */
  --bg-hover: #e2e8f0;             /* slate-200 - Table row hover, button hover */
  
  /* Borders & Seams */
  --border-subtle: #e2e8f0;        /* slate-200 - Card borders, table dividers */
  --border-strong: #cbd5e1;        /* slate-300 - Input borders, active outlines */
  
  /* Typography */
  --text-primary: #0f172a;         /* slate-900 - Headings, transcript body text */
  --text-secondary: #475569;       /* slate-600 - Metadata, timestamps, labels */
  --text-muted: #94a3b8;           /* slate-400 - Placeholders, disabled states */
  
  /* Primary SaaS Accent (Deep Navy / Indigo) */
  --primary: #1e293b;              /* slate-800 - Primary CTA buttons */
  --primary-hover: #0f172a;        /* slate-900 - Hover state */
  --primary-foreground: #ffffff;   /* Text on primary CTA */
  --accent-blue: #2563eb;          /* blue-600  - Active word highlights, links */
  --accent-blue-subtle: #eff6ff;   /* blue-50   - Active segment background tint */
  
  /* Status Indicators */
  --success: #059669;              /* emerald-600 - Completed jobs, GPU online */
  --success-subtle: #ecfdf5;       /* emerald-50  - Completed badge background */
  --warning: #d97706;              /* amber-600   - In-progress / Queued */
  --warning-subtle: #fffbeb;       /* amber-50    - Queued badge background */
  --danger: #dc2626;               /* red-600     - Failed jobs, delete actions */
  --danger-subtle: #fef2f2;        /* red-50      - Failed badge background */
}
```

---

## 4. Lucide Icons Specification

Every interface element is paired with an exact, semantic Lucide icon (`lucide-react`):

| UI Component / Action | Lucide Icon Component | Visual Semantics |
| :--- | :--- | :--- |
| **System Logo** | `<Mic className="w-5 h-5 text-slate-900" />` | Core audio transcription identity |
| **Hardware Status: GPU** | `<Cpu className="w-4 h-4 text-emerald-600" />` | NVIDIA CUDA / Apple Silicon engine |
| **Hardware Status: Memory** | `<HardDrive className="w-4 h-4 text-slate-500" />` | VRAM / RAM consumption meter |
| **Worker Active Pulse** | `<Activity className="w-4 h-4 text-blue-600" />` | Background processing queue worker |
| **File Drag & Drop** | `<UploadCloud className="w-8 h-8 text-slate-400" />` | Ingestion area anchor |
| **Video File Type** | `<FileVideo className="w-4 h-4 text-purple-600" />` | MP4, MOV, MKV files |
| **Audio File Type** | `<FileAudio className="w-4 h-4 text-blue-600" />` | MP3, WAV, M4A, AAC files |
| **YouTube Link** | `<Link2 className="w-4 h-4 text-red-600" />` | Streaming URL ingestion |
| **Mode: Whale (Large-v3)** | `<Sparkles className="w-4 h-4 text-amber-500" />` | Maximum accuracy tier |
| **Mode: Whale Turbo** | `<Zap className="w-4 h-4 text-blue-600" />` | High-speed Large-v3-Turbo tier |
| **Language Selection** | `<Languages className="w-4 h-4 text-slate-500" />` | 98-language dropdown |
| **Transcribe to English** | `<ArrowRightLeft className="w-4 h-4 text-slate-500" />` | Zero-shot acoustic translation |
| **Speaker Diarization** | `<Users className="w-4 h-4 text-slate-500" />` | Multi-speaker recognition toggle |
| **Restore Audio Filter** | `<SlidersHorizontal className="w-4 h-4 text-slate-500" />` | DeepFilterNet noise suppression |
| **Job State: In Progress** | `<Loader2 className="w-4 h-4 animate-spin text-blue-600" />` | Active pipeline processing |
| **Job State: Completed** | `<CheckCircle2 className="w-4 h-4 text-emerald-600" />` | Successful transcript generation |
| **Job State: Failed** | `<AlertTriangle className="w-4 h-4 text-red-600" />` | Error state / stack trace trigger |
| **Job State: Queued** | `<Clock className="w-4 h-4 text-amber-600" />` | Waiting in sequential worker queue |
| **Action: Open Studio** | `<ExternalLink className="w-4 h-4" />` | Navigate to interactive editor |
| **Action: Export / Download** | `<Download className="w-4 h-4" />` | Single file or bulk ZIP download |
| **Action: Retry Job** | `<RotateCw className="w-4 h-4" />` | Re-queue failed file |
| **Action: Delete Job** | `<Trash2 className="w-4 h-4 text-red-600" />` | Cascade delete job and cache |
| **Player: Play / Pause** | `<Play className="w-4 h-4" />` / `<Pause className="w-4 h-4" />` | Audio/video playback toggle |
| **Player: Skip 5s Back** | `<RotateCcw className="w-4 h-4" />` | Seek back |
| **Player: Skip 5s Forward** | `<RotateCw className="w-4 h-4" />` | Seek forward |
| **Studio: Rename Speakers** | `<UserCheck className="w-4 h-4" />` | Open bulk speaker renamer |
| **Studio: Search & Replace**| `<Search className="w-4 h-4" />` | Open text search drawer |
| **Studio: Subtitle Settings**| `<Subtitles className="w-4 h-4" />` | Configure line breaks & CPL |

---

## 5. Main Dashboard View Layout

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  [Mic] Transcriber   │  [Cpu] NVIDIA RTX 2080 (CUDA)   │  [HardDrive] VRAM: 2.2/8.0 GB  │ [Activity] Active ●  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  [UploadCloud] Drag & Drop Media Files                            │  │
│  │                            Supports MP4, MOV, MKV, MP3, WAV (Up to 10 GB)                         │  │
│  │                                                                                                  │  │
│  │   [Sparkles] Mode: Whale ▼   [Languages] Lang: Auto ▼   [Users] Diarize: 2 Speakers ▼            │  │
│  │   [SlidersHorizontal] Restore Audio: ON                [Link2] Paste YouTube URL...              │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                        │
│  BATCH QUEUE (3 Files)                                              [Filter] [Download] Export All ZIP │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ [FileVideo] podcast_ep42.mp4   Whale  │ [Loader2] Transcribing (64%)  ETA: 35s  │ [ExternalLink] [Trash] │  │
│  │ [FileVideo] interview_raw.mov  Whale  │ [Clock] Queued in line                  │ [Trash]                │  │
│  │ [FileAudio] lecture_08.m4a     Turbo  │ [CheckCircle2] Completed (00:45:10)     │ [Open Studio] [Export] │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Layout Elements & Styling:
1. **Top Telemetry Header (`h-14 bg-white border-b border-slate-200 px-6`):**
   * Left: Sharp logo icon + wordmark (`font-semibold text-slate-900 tracking-tight`).
   * Center: Hardware pill badges (`bg-slate-50 border border-slate-200 text-slate-700 text-xs px-2.5 py-1 rounded-[4px]`).
   * Right: Worker status indicator with pulsing dot (`bg-emerald-500 w-2 h-2 rounded-full`).
2. **Ingestion Box (`bg-white border border-slate-200 rounded-[6px] p-6 shadow-sm`):**
   * Dashed upload container (`border-2 border-dashed border-slate-200 hover:border-slate-400 bg-slate-50/50 rounded-[4px] py-10`).
   * Crisp segmented controls and dropdowns with `rounded-[4px] border-slate-300 bg-white text-slate-900 text-sm shadow-xs`.
3. **Queue Table (`bg-white border border-slate-200 rounded-[6px] overflow-hidden`):**
   * Table Header (`bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-500 uppercase px-4 py-2.5`).
   * Table Rows (`border-b border-slate-100 hover:bg-slate-50/80 transition-colors px-4 py-3 text-sm`).
   * Progress Bar (`h-1.5 w-full bg-slate-100 rounded-[2px] overflow-hidden` with `bg-blue-600` fill).

---

## 6. Interactive Studio & Editor View Layout

When the user clicks **"Open Studio"**, the interface transitions to a focused workstation split:

```
┌──────────────────────────────────────────────────┬─────────────────────────────────────────────────────┐
│  MEDIA PLAYER & DOCK                             │  TRANSCRIPT STREAM                                  │
│                                                  │                                                     │
│  ┌────────────────────────────────────────────┐  │  [Search] Search transcript...  [UserCheck] Rename  │
│  │                                            │  │                                                     │
│  │             VIDEO / AUDIO DOCK             │  │  ┌────────────────────────────────────────────────┐ │
│  │                                            │  │  │ [00:01:14] SPEAKER_00 (Host)                   │ │
│  └────────────────────────────────────────────┘  │  │ Welcome back everyone. Today we are joined     │ │
│   [Play] [RotateCcw] [RotateCw] 01:14 / 45:10    │  │ by our special guest in the studio.            │ │
│   ══════════════════════════════●════════════    │  └────────────────────────────────────────────────┘ │
│                                                  │  ┌────────────────────────────────────────────────┐ │
│  AUDIO WAVEFORM SCRUBBER                         │  │ [00:01:22] SPEAKER_01 (Guest)                  │ │
│  ||||||||||||||||||||||||||||||||||||||||||||||  │  │ Thank you for having me. Excited to be here.   │ │
│                                                  │  └────────────────────────────────────────────────┘ │
│  [Download] Export SRT  [Download] Export DOCX   │                                                     │
└──────────────────────────────────────────────────┴─────────────────────────────────────────────────────┘
```

### Studio Interaction Highlights:
* **Segment Cards (`border border-slate-200 bg-white rounded-[4px] p-3 mb-2 shadow-xs hover:border-slate-300`):**
  * Top bar shows timestamp in monospace (`font-mono text-xs text-slate-500`) and speaker tag (`bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded-[3px] text-xs font-medium`).
  * Clicking an active segment highlights it with a crisp blue left border (`border-l-4 border-l-blue-600 bg-blue-50/30`).
* **Karaoke-Style Playback Word Highlighting:**
  * As audio plays, individual words illuminate with a distinct blue highlight:
    ```tsx
    <span className={isActive ? "bg-blue-100 text-blue-900 font-medium rounded-[2px] px-0.5" : "text-slate-800"}>
      {word.text}{" "}
    </span>
    ```
* **Click-to-Seek:** Clicking any word directly dispatches `audioElement.currentTime = word.startTime`.
* **Bulk Speaker Renamer Modal (`bg-white border border-slate-200 rounded-[6px] shadow-lg p-6 max-w-md`):**
  * Inputs to rename `SPEAKER_00` $\rightarrow$ `Sam Altman` and `SPEAKER_01` $\rightarrow$ `Bill Gates`.
  * Instant auto-update across all segments in the DOM and persistent SQLite update.

---

## 7. Keyboard Navigation & Accessibility

* **`Space`:** Toggle Play / Pause without losing cursor focus.
* **`Shift + Left / Right`:** Jump 5 seconds backward / forward.
* **`Tab` / `Shift + Tab`:** Navigate to next / previous transcript segment.
* **`Cmd / Ctrl + F`:** Focus search & replace input drawer.
* **`Cmd / Ctrl + S`:** Trigger manual save (auto-save debounces at 500ms).
* **`Esc`:** Defocus active editing block and return to audio navigation.

---

## 8. Corner Radius Tokens (Strict Geometric Rules)

```css
/* Tailwind theme extensions */
--radius-sm: 4px;   /* buttons, badges, inputs, dropdowns */
--radius-md: 6px;   /* cards, tables, modals, player containers */
--radius-none: 0px; /* square table headers, split pane seams */
```

All UI elements adhere strictly to this specification to ensure a sharp, polished, professional SaaS aesthetic.
