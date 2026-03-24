import { useEffect, useMemo, useState } from "react";
import { fetchLocalLlmModels, sendLocalLlmChat } from "../api/client";
import type { LocalLlmMessage, LocalLlmModelOption } from "../types";

const DEFAULT_SYSTEM_PROMPT =
  "You are a local medical-assistant style helper. Stay concise, avoid external web data, and keep all discussion on the local machine. If the user asks for clinical conclusions, give cautious, non-diagnostic guidance.";

const QUICK_PROMPTS = [
  {
    title: "Summarize case",
    detail: "Turn the current note into a short plain-language summary.",
    prompt: "Summarize this case in plain language.",
  },
  {
    title: "Family update",
    detail: "Draft a calm update that a parent or family member can read.",
    prompt: "Draft a brief family-friendly update.",
  },
  {
    title: "Next questions",
    detail: "Suggest the next clinical questions to ask or check.",
    prompt: "List the next questions to ask.",
  },
  {
    title: "Differential",
    detail: "Give a concise differential overview with high-level reasoning.",
    prompt: "Give a concise differential overview.",
  },
];

export default function Assistant() {
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [models, setModels] = useState<LocalLlmModelOption[]>([]);
  const [model, setModel] = useState("Qwen3.5-4B-Q4_K_M.gguf");
  const [modelLabel, setModelLabel] = useState("Qwen 3.5 4B Q4 K M");
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(512);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalLlmMessage[]>([
    { role: "assistant", content: "Ask anything about the local model." },
  ]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const chatMessages = useMemo(
    () =>
      [
        { role: "system" as const, content: systemPrompt.trim() },
        ...messages,
      ].filter((msg) => msg.content.trim()),
    [systemPrompt, messages],
  );

  useEffect(() => {
    let cancelled = false;
    fetchLocalLlmModels()
      .then((data) => {
        if (cancelled) return;
        setModels(data.models);
        const selected =
          data.models.find((item) => item.filename === data.selected) ??
          data.models.find((item) => item.is_default) ??
          data.models[0];
        if (selected) {
          setModel(selected.filename);
          setModelLabel(selected.label);
        }
      })
      .catch(() => {
        // Leave defaults in place.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages = [...messages, { role: "user" as const, content: text }];
    setError(null);
    setLoading(true);
    setMessages(nextMessages);
    setInput("");

    try {
      const response = await sendLocalLlmChat({
        messages: [
          { role: "system", content: systemPrompt.trim() },
          ...nextMessages,
        ],
        model,
        temperature,
        max_tokens: maxTokens,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([{ role: "assistant", content: "Ask anything about the local model." }]);
    setError(null);
  };

  return (
    <div className="assistant-page assistant-page-light">
      <header className="assistant-topbar-light">
        <div>
          <div className="assistant-page-title">Local AI Assistant</div>
          <div className="assistant-page-subtitle">
            Private chat workspace with local prompts and model controls
          </div>
        </div>

        <button
          className="assistant-settings-btn assistant-settings-btn-light"
          type="button"
          aria-label="Open model settings"
          onClick={() => setSettingsOpen(true)}
        >
          ⚙
        </button>
      </header>

      <main className="assistant-chat-shell-light">
        <section className="assistant-hero-plain">
          <div>
            <h2>How can I help you?</h2>
            <p className="text-muted mb-0">
              Use a quick prompt or type your own message below.
            </p>
          </div>
          <div className="assistant-prompt-grid assistant-prompt-grid-plain">
            {QUICK_PROMPTS.map((item) => (
              <button
                key={item.title}
                className="assistant-prompt-card"
                onClick={() => setInput(item.prompt)}
              >
                <div className="assistant-prompt-card-title">{item.title}</div>
                <div className="assistant-prompt-card-detail">{item.detail}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="assistant-chat-panel-light">
          <div className="chat-thread assistant-chat-thread-light assistant-chat-thread-expand">
            {chatMessages.slice(1).map((msg, idx) => (
              <div
                key={`${msg.role}-${idx}`}
                className={`assistant-message-row ${msg.role}`}
              >
                {msg.role === "user" ? (
                  <div className="assistant-user-bubble">
                    <div className="chat-content">{msg.content}</div>
                  </div>
                ) : (
                  <div className="assistant-response">
                    <div className="chat-role">assistant</div>
                    <div className="chat-content">{msg.content}</div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="assistant-composer-light">
            <textarea
              className="assistant-input-light"
              rows={4}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Local AI"
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                  e.preventDefault();
                  void handleSend();
                }
              }}
            />

            <div className="assistant-composer-footer-light">
              <div className="assistant-compose-hint">Ctrl/⌘ + Enter to send</div>
              <div className="flex-gap">
                <button className="btn btn-outline" onClick={handleReset}>
                  New chat
                </button>
                <button
                  className="btn btn-primary"
                  disabled={loading}
                  onClick={handleSend}
                >
                  {loading ? "Sending…" : "Send"}
                </button>
              </div>
            </div>

            {error && <div className="alert alert-danger mt-1">{error}</div>}
          </div>
        </section>
      </main>

      {settingsOpen && (
        <div className="assistant-modal-backdrop" onClick={() => setSettingsOpen(false)}>
          <div className="assistant-modal assistant-modal-light" onClick={(e) => e.stopPropagation()}>
            <div className="assistant-modal-header assistant-modal-header-light">
              <h3>Model settings</h3>
              <button
                className="assistant-modal-close assistant-modal-close-light"
                type="button"
                aria-label="Close settings"
                onClick={() => setSettingsOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="assistant-modal-body assistant-modal-body-light">
              <label className="assistant-field-light">
                <span>Model</span>
                <select
                  className="form-control"
                  value={model}
                  onChange={(e) => {
                    const filename = e.target.value;
                    setModel(filename);
                    const selected = models.find((item) => item.filename === filename);
                    setModelLabel(selected?.label || filename);
                  }}
                >
                  {models.length > 0 ? (
                    models.map((item) => (
                      <option key={item.filename} value={item.filename}>
                        {item.label}
                        {item.is_default ? " (default)" : ""}
                      </option>
                    ))
                  ) : (
                    <option value="Qwen3.5-4B-Q4_K_M.gguf">
                      Qwen 3.5 4B Q4 K M (default)
                    </option>
                  )}
                </select>
                <small className="text-muted">Selected: {modelLabel}</small>
              </label>

              <div className="row mb-1">
                <div className="col-2">
                  <label className="assistant-field-light">
                    <span>Temperature</span>
                    <input
                      className="form-control"
                      type="number"
                      min="0"
                      max="2"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(Number(e.target.value))}
                    />
                  </label>
                </div>
                <div className="col-2">
                  <label className="assistant-field-light">
                    <span>Max tokens</span>
                    <input
                      className="form-control"
                      type="number"
                      min="1"
                      step="1"
                      value={maxTokens}
                      onChange={(e) => setMaxTokens(Number(e.target.value))}
                    />
                  </label>
                </div>
              </div>

              <label className="assistant-field-light">
                <span>System prompt</span>
                <textarea
                  className="form-control"
                  rows={5}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                />
              </label>

              <p className="text-muted mb-0">
                Changing the selected model file requires restarting the local LLM server.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}