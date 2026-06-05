import type { Metadata } from "next";
import { Bebas_Neue, Noto_Sans_KR } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

// 큰 숫자/짧은 영문 제목 전용 (--font-display). 한국어 본문엔 쓰지 않는다.
const bebas = Bebas_Neue({
  subsets: ["latin"],
  weight: "400",
  display: "swap",
  variable: "--font-bebas",
});

// 한국어 본문 폰트 (--font-sans 폴백 체인 선두). 가독성 우선.
const notoKr = Noto_Sans_KR({
  subsets: ["latin"],
  weight: ["400", "500", "700", "800"],
  display: "swap",
  variable: "--font-noto-kr",
});

export const metadata: Metadata = {
  title: "ValoPredictML — 발로란트 5v5 승률 예측",
  description: "맵 + 선수·요원 5v5 라인업으로 승률과 근거를 예측하는 시연 도구",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ko"
      className={`h-full antialiased ${notoKr.variable} ${bebas.variable}`}
    >
      <body className="min-h-full flex flex-col">
        <Navbar />
        <main className="flex-1 w-full max-w-[1280px] mx-auto px-4 sm:px-6 py-3">
          {children}
        </main>
      </body>
    </html>
  );
}
