import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import TawkChat from "@/components/TawkChat";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareerOS — AI Career Intelligence System",
  description:
    "The AI-powered career operating system that tells you exactly why you're not getting hired — and how to fix it.",
  openGraph: {
    title: "CareerOS",
    description: "AI-powered career intelligence for tech professionals",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className={`${inter.className} antialiased`}>
          {children}
          <TawkChat />
        </body>
      </html>
    </ClerkProvider>
  );
}
