import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { UploadPage } from "@/pages/Upload";
import { FilesPage } from "@/pages/Files";
import { ChatPage } from "@/pages/Chat";
import { AnalysisPage } from "@/pages/Analysis";
import { ExportPage } from "@/pages/Export";
import { SettingsPage } from "@/pages/Settings";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="files" element={<FilesPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="export" element={<ExportPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
