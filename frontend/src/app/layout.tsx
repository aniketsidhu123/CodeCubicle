import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tracelight · Ask for data, see where it came from",
  description:
    "AI-powered data intelligence platform. Describe the data you need in plain English, and Tracelight collects, cleans, and traces every record to its source.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
