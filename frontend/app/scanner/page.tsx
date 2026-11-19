import type { Metadata } from "next";

import ScannerPage from "@/features/scanner/ScannerPage";

export const metadata: Metadata = {
  title: "Market Scanner — PIMS",
};

export default function ScannerRoute() {
  return <ScannerPage />;
}