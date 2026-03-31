import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "OmniRAG - Enterprise Multimodal RAG",
  description: "Ground-truth knowledge intelligence platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased text-foreground bg-background`}>
        <div className="flex min-h-screen relative overflow-hidden">
          <Sidebar />
          <div className="flex-1 md:pl-64 flex flex-col h-screen">
            <TopBar />
            <main className="flex-1 overflow-y-auto w-full p-4 lg:p-8 bg-muted/10 relative">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
