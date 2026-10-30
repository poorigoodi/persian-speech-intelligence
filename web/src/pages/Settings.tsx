import { CheckCircle2, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { DEFAULT_SETTINGS, useWorkspace, type WorkspaceSettings } from "@/lib/workspace";

export function SettingsPage() {
  const { settings, setSettings, backendOk } = useWorkspace();
  const { push } = useToast();

  function update<K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) {
    setSettings({ ...settings, [key]: value });
  }

  return (
    <div className="space-y-4">
      <PageHeader
        crumb="WORKSPACE / SETTINGS"
        title="Settings"
        subtitle="Configure your speech intelligence workspace."
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSettings(DEFAULT_SETTINGS);
                push("Settings restored to defaults.", "info");
              }}
            >
              <RotateCcw className="size-3.5" />
              Reset Defaults
            </Button>
            <Button
              size="sm"
              onClick={() => push("Workspace preferences saved locally.", "success")}
            >
              <CheckCircle2 className="size-3.5" />
              Save Changes
            </Button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2">
        {/* Profile & Account */}
        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">Profile & Account</h2>

          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-[140px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-display-name" className="text-[12px] text-mute2">
                Display Name
              </label>
              <input
                id="psi-display-name"
                value={settings.displayName}
                onChange={(e) => update("displayName", e.target.value)}
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              />
            </div>

            <div className="grid grid-cols-[140px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-email" className="text-[12px] text-mute2">
                Email
              </label>
              <input
                id="psi-email"
                type="email"
                value={settings.email}
                onChange={(e) => update("email", e.target.value)}
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              />
            </div>
          </div>
        </Card>

        {/* Language & Transcription */}
        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">Language & Transcription</h2>

          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-[150px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-default-lang" className="text-[12px] text-mute2">
                Default Language
              </label>
              <select
                id="psi-default-lang"
                value={settings.defaultLanguage}
                onChange={(e) =>
                  update("defaultLanguage", e.target.value as WorkspaceSettings["defaultLanguage"])
                }
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                <option value="auto">Auto-detect</option>
                <option value="fa">Persian (Farsi)</option>
                <option value="en">English</option>
              </select>
            </div>

            <div className="grid grid-cols-[150px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-trans-mode" className="text-[12px] text-mute2">
                Transcription Mode
              </label>
              <select
                id="psi-trans-mode"
                value={settings.transcriptionMode}
                onChange={(e) =>
                  update(
                    "transcriptionMode",
                    e.target.value as WorkspaceSettings["transcriptionMode"],
                  )
                }
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                <option value="accurate">Accurate</option>
                <option value="fast">Fast</option>
              </select>
            </div>
          </div>
        </Card>

        {/* AI Preferences */}
        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">AI Preferences</h2>

          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-[160px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-stt-model" className="text-[12px] text-mute2">
                Speech-to-Text Model
              </label>
              <select
                id="psi-stt-model"
                value={settings.sttModel}
                onChange={(e) => update("sttModel", e.target.value)}
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                <option value="default">Default (Faster-Whisper Large-v3)</option>
                <option value="farsi-v3">Farsi Fine-tuned Whisper</option>
              </select>
            </div>

            <div className="grid grid-cols-[160px_minmax(0,1fr)] items-center gap-3">
              <label htmlFor="psi-llm-model" className="text-[12px] text-mute2">
                LLM Summary Model
              </label>
              <select
                id="psi-llm-model"
                value={settings.summaryModel}
                onChange={(e) => update("summaryModel", e.target.value)}
                className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                <option value="api">API (Qwen3-2B Instruct)</option>
                <option value="local">Local OpenAI-Compatible</option>
              </select>
            </div>

            <div className="grid grid-cols-[160px_minmax(0,1fr)] items-center gap-3">
              <span className="text-[12px] text-mute2">Speaker Detection</span>
              <button
                type="button"
                onClick={() => update("speakerDetection", !settings.speakerDetection)}
                className="inline-flex h-9 w-fit items-center gap-2 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-semibold text-ink transition hover:border-violet-900"
              >
                <span
                  className={`size-2 rounded-full ${
                    settings.speakerDetection ? "bg-emerald-400" : "bg-mute"
                  }`}
                />
                {settings.speakerDetection ? "Enabled" : "Disabled"}
              </button>
            </div>
          </div>
        </Card>

        {/* Appearance */}
        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">Appearance</h2>

          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-[140px_minmax(0,1fr)] items-center gap-3">
              <span className="text-[12px] text-mute2">Theme</span>
              <div className="flex items-center gap-4 text-[12px]">
                {(["dark", "light"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => update("theme", t)}
                    className={`inline-flex items-center gap-2 font-medium capitalize ${
                      settings.theme === t ? "text-ink" : "text-mute hover:text-mute2"
                    }`}
                  >
                    <span
                      className={`size-2.5 rounded-full border ${
                        settings.theme === t
                          ? "border-violet-400 bg-violet-500"
                          : "border-navy-600 bg-navy-800"
                      }`}
                    />
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-[140px_minmax(0,1fr)] items-center gap-3">
              <span className="text-[12px] text-mute2">Notifications</span>
              <button
                type="button"
                onClick={() => update("notifications", !settings.notifications)}
                className="inline-flex h-9 w-fit items-center gap-2 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-semibold text-ink transition hover:border-violet-900"
              >
                <span
                  className={`size-2 rounded-full ${
                    settings.notifications ? "bg-emerald-400" : "bg-mute"
                  }`}
                />
                {settings.notifications ? "Enabled" : "Disabled"}
              </button>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-mute">
          <span>
            Placeholder note: User profile and AI preferences are stored in browser localStorage. Backend model configuration is managed via server `.env` variables.
          </span>
          <span className="inline-flex items-center gap-1.5 font-medium text-mute2">
            <span
              className={`size-2 rounded-full ${backendOk ? "bg-emerald-400" : "bg-amber-400"}`}
            />
            Backend API: {backendOk ? "Connected" : "Offline"}
          </span>
        </div>
      </Card>
    </div>
  );
}
