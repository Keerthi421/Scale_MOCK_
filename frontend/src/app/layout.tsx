import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InterviewForge — System Design Practice",
  description:
    "Practice high-level system design on an interactive architecture canvas with AI review.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="h-dvh overflow-hidden">{children}</body>
    </html>
  );
}
