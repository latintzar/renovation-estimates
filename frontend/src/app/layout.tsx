import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3002';
export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: 'Renovation estimates', template: '%s | Renovation estimates' },
  description: 'Property analysis, comparable standards and auditable renovation quantities.',
  icons: { icon: (process.env.NEXT_PUBLIC_BASE_PATH||'')+'/favicon.svg' },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: "#FDFBF7", // Leo cream background
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
    >
      <body 
        className="bg-[#FDFBF7] min-h-screen antialiased font-sans"
        style={{ fontFamily: "'Source Sans 3', system-ui, sans-serif" }}
        suppressHydrationWarning
      >
          <Providers>{children}</Providers>
          </body>
    </html>
  );
}
