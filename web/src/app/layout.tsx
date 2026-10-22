import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Moja općina u brojkama",
  description:
    "Kako vaša općina ili grad troši novac, što nabavlja i koje su javne usluge u blizini.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="hr">
      <body>{children}</body>
    </html>
  );
}
