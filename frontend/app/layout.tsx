import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TMUX — Local AI Transcription & Diarization Workstation",
  description: "High-accuracy local transcription, speaker diarization, and batch queue engine powered by OpenAI Whisper.",
  keywords: ["TMUX", "transcription", "diarization", "Whisper", "AI", "audio", "speech-to-text"],
  icons: {
    icon: "/tmux-square.png",
    shortcut: "/favicon.ico",
    apple: "/tmux-square.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#2563eb",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/* bg-gray-50 = off-white canvas; selection uses blue brand */}
      <body
        suppressHydrationWarning
        className="min-h-screen bg-gray-50 text-slate-900 antialiased selection:bg-blue-100 selection:text-blue-900 font-sans"
      >
        {children}
      </body>
    </html>
  );
}
