import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "ValoPredictML — 발로란트 5v5 승률 예측",
  description: "맵 + 선수·요원 5v5 라인업으로 승률과 근거를 예측하는 시연 도구",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-[2200px] mx-auto px-4 sm:px-6 lg:px-8 2xl:px-12 py-5">
          {children}
        </main>
      </body>
    </html>
  );
}
