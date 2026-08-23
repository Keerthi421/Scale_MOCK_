import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pins the workspace root to this project so Next.js stops guessing when it
  // sees the unrelated lockfile in the parent Windows user directory.
  outputFileTracingRoot: __dirname,
  // The API base is read at build time so the client bundle never contains a
  // secret — only the public origin of our own backend.
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  },
};

export default nextConfig;
