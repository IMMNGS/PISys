import { useEffect, useMemo, useState } from "react";
import { fetchLocalLlmModels, sendLocalLlmChat } from "../api/client";
import type { LocalLlmMessage, LocalLlmModelOption } from "../types";

const DEFAULT_SYSTEM_PROMPT =
  "You are a local medical-assistant style helper. Stay concise, avoid external web data, and keep all discussion on the local machine. If the user asks for clinical conclusions, give cautious, non-diagnostic guidance.";

export default function LocalLlm() {
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
        // Leave the default selection in place if the API is unavailable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages = [
      ...messages,
      { role: "user" as const, content: text },
    ];
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
    setMessages([
      { role: "assistant", content: "Ask anything about the local model." },
    ]);
    setError(null);
  };

  return (
    <>
      <h2>Local LLM</h2>
      <p className="text-muted mb-2">
        Start with Qwen3.5 9B locally. This page sends prompts to a loopback
        chat-completions server, keeping the model on your machine.
      </p>

      <div className="card mb-2">
        <div className="card-header primary">Model Settings</div>
        <div className="card-body">
          <div className="row mb-1">
            <div className="col-2">
              <label className="mb-1">
                <strong>Model</strong>
              </label>
              <select
                className="form-control"
                value={model}
                onChange={(e) => {
                  const filename = e.target.value;
                  setModel(filename);
                  const selected = models.find(
                    (item) => item.filename === filename,
                  );
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
            </div>
            <div className="col-2">
              <label className="mb-1">
                <strong>Temperature</strong>
              </label>
              <input
                className="form-control"
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
              />
            </div>
            <div className="col-2">
              <label className="mb-1">
                <strong>Max tokens</strong>
              </label>
              <input
                className="form-control"
                type="number"
                min="1"
                step="1"
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
              />
            </div>
          </div>

          <label className="mb-1">
            <strong>System prompt</strong>
          </label>
          <textarea
            className="form-control"
            rows={4}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
          <p className="text-muted mt-1" style={{ marginBottom: 0 }}>
            Changing the selected model file requires restarting the local LLM
            server.
          </p>
        </div>
      </div>

      <div className="card mb-2">
        <div className="card-header primary">Chat</div>
        <div className="card-body">
          <div className="chat-thread mb-1">
            {chatMessages.slice(1).map((msg, idx) => (
              <div
                key={`${msg.role}-${idx}`}
                className={`chat-message ${msg.role}`}
              >
                <div className="chat-role">{msg.role}</div>
                <div className="chat-content">{msg.content}</div>
              </div>
            ))}
          </div>

          <textarea
            className="form-control mb-1"
            rows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the model something locally..."
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                void handleSend();
              }
            }}
          />

          <div className="flex-gap">
            <button
              className="btn btn-primary"
              disabled={loading}
              onClick={handleSend}
            >
              {loading ? "Sending…" : "Send"}
            </button>
            <button className="btn btn-outline-secondary" onClick={handleReset}>
              Reset chat
            </button>
          </div>

          <p className="text-muted mt-1" style={{ marginBottom: 0 }}>
            Tip: Ctrl/Cmd + Enter sends the prompt.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
    </>
  );
}
