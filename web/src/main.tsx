import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { WorkspaceProvider } from "@/lib/workspace";
import { ToastProvider } from "@/components/ui/Toast";
import "./index.css";

const container = document.getElementById("root");
if (!container) throw new Error("Root element not found");

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <WorkspaceProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </WorkspaceProvider>
    </BrowserRouter>
  </StrictMode>,
);
