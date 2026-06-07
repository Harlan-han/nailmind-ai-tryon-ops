import type { Metadata } from "next";
import "./globals.css";
import { TryOnProgressListener } from "./tryon-progress-listener";

export const metadata: Metadata = {
  title: "甲感 NailMind - AI美甲试戴",
  description: "先看上手效果，再决定做哪款。AI-powered nail try-on experience.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
        <TryOnProgressListener />
      </body>
    </html>
  );
}
