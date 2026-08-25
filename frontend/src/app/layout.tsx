// src/app/layout.tsx — Root layout

import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Government Scheme AI Assistant",
  description:
    "AI-powered platform to discover government schemes, check eligibility, and get evidence-based guidance from official documents.",
  keywords: ["government schemes", "AI assistant", "eligibility", "welfare", "India"],
  authors: [{ name: "GovScheme AI" }],
  robots: "index, follow",
  openGraph: {
    title: "Government Scheme AI Assistant",
    description: "Discover schemes you qualify for with AI-powered eligibility analysis.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
