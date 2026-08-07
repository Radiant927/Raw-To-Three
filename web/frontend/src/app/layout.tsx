import type { Metadata } from "next";
import { Orbitron, JetBrains_Mono, Noto_Sans_SC } from "next/font/google";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import "./globals.css";

const orbitron = Orbitron({
  subsets: ["latin"],
  variable: "--font-orbitron",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const notoSansSC = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-noto-sans-sc",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RT Pipeline | 照片到3D高斯模型重建平台",
  description:
    "基于 COLMAP + 2D Gaussian Splatting + Open3D 的照片到3D高斯模型重建平台，上传多角度照片即可生成高质量3D模型。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      data-scroll-behavior="smooth"
      className={`${orbitron.variable} ${jetbrainsMono.variable} ${notoSansSC.variable}`}
    >
      <body className="min-h-screen flex flex-col bg-[#0a0e17] text-[#e2e8f0] antialiased">
        <Navbar />
        <main className="flex-1 pt-16">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
