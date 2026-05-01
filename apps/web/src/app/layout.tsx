import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "阳光阅读",
  description: "Sunshine Reading 前端演示（mock 数据）",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className="bg-zinc-50 text-zinc-900 antialiased">
        <SiteHeader />
        <main className="mx-auto min-h-[calc(100vh-7rem)] w-full max-w-5xl px-4 pb-24 pt-4 md:pb-8">{children}</main>
        <BottomNav />
      </body>
    </html>
  );
}
