import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchLocalLlmModels, sendLocalLlmChat } from "../api/client";
import type { LocalLlmMessage, LocalLlmModelOption } from "../types";

const DEFAULT_SYSTEM_PROMPT =
  "You are a local medical-assistant style helper. Stay concise, avoid external web data, and keep all discussion on the local machine. If the user asks for clinical conclusions, give cautious, non-diagnostic guidance.";

const CHAT_STORAGE_KEY = "ha.local-llm.assistant.chat.v1";

type StoredAssistantChat = {
  systemPrompt: string;
  model: string;
  modelLabel: string;
  temperature: number;
  maxTokens: number;
  messages: LocalLlmMessage[];
};

type ChatSession = StoredAssistantChat & {
  id: string;
  summary: string;
  createdAt: number;
  updatedAt: number;
};

type StoredAssistantState = {
  currentSessionId: string;
  sessions: ChatSession[];
};

type CitationItem = {
  type: string;
  label: string;
  fields: Record<string, unknown>;
};

function createSessionId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function summarizeFirstUserInput(messages: LocalLlmMessage[]) {
  const firstUser = messages
    .find((msg) => msg.role === "user")
    ?.content?.trim();
  if (!firstUser) return "New chat";
  return truncateText(firstUser, 56);
}

function createSession(overrides: Partial<ChatSession> = {}): ChatSession {
  const createdAt = overrides.createdAt ?? Date.now();
  const messages = overrides.messages ?? [];
  return {
    id: overrides.id ?? createSessionId(),
    summary: overrides.summary ?? summarizeFirstUserInput(messages),
    systemPrompt: overrides.systemPrompt ?? DEFAULT_SYSTEM_PROMPT,
    model: overrides.model ?? "Qwen3.5-4B-Q4_K_M.gguf",
    modelLabel: overrides.modelLabel ?? "Qwen 3.5 4B Q4 K M",
    temperature: overrides.temperature ?? 0.2,
    maxTokens: overrides.maxTokens ?? 512,
    messages,
    createdAt,
    updatedAt: overrides.updatedAt ?? createdAt,
  };
}

function isValidChatMessage(value: unknown): value is LocalLlmMessage {
  return (
    !!value &&
    typeof value === "object" &&
    (value as LocalLlmMessage).role !== undefined &&
    (value as LocalLlmMessage).content !== undefined &&
    ["system", "user", "assistant"].includes((value as LocalLlmMessage).role) &&
    typeof (value as LocalLlmMessage).content === "string"
  );
}

function loadStoredState(): StoredAssistantState {
  const fallbackSession = createSession();
  if (typeof window === "undefined") {
    return {
      currentSessionId: fallbackSession.id,
      sessions: [fallbackSession],
    };
  }

  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<StoredAssistantState>;
      if (Array.isArray(parsed.sessions) && parsed.sessions.length > 0) {
        const sessions = parsed.sessions
          .filter((session): session is ChatSession => {
            const candidate = session as Partial<ChatSession>;
            return !!candidate && typeof candidate.id === "string";
          })
          .map((session) => ({
            ...createSession(session),
            ...session,
            summary:
              typeof session.summary === "string" && session.summary.trim()
                ? session.summary.trim()
                : summarizeFirstUserInput(session.messages || []),
            messages: Array.isArray(session.messages)
              ? session.messages.filter(isValidChatMessage)
              : [],
          }));
        if (sessions.length > 0) {
          const currentSessionId =
            typeof parsed.currentSessionId === "string" &&
            sessions.some((session) => session.id === parsed.currentSessionId)
              ? parsed.currentSessionId
              : sessions[0].id;
          return { currentSessionId, sessions };
        }
      }
    }

    const legacyRaw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (legacyRaw) {
      const legacy = JSON.parse(legacyRaw) as Partial<StoredAssistantChat>;
      const messages = Array.isArray(legacy.messages)
        ? legacy.messages.filter(isValidChatMessage)
        : [];
      const session = createSession({
        systemPrompt: legacy.systemPrompt || DEFAULT_SYSTEM_PROMPT,
        model: legacy.model || fallbackSession.model,
        modelLabel: legacy.modelLabel || fallbackSession.modelLabel,
        temperature:
          typeof legacy.temperature === "number"
            ? legacy.temperature
            : fallbackSession.temperature,
        maxTokens:
          typeof legacy.maxTokens === "number"
            ? legacy.maxTokens
            : fallbackSession.maxTokens,
        messages,
        summary: summarizeFirstUserInput(messages),
      });
      return { currentSessionId: session.id, sessions: [session] };
    }
  } catch {
    // Ignore malformed local storage and fall back to an empty session.
  }

  return { currentSessionId: fallbackSession.id, sessions: [fallbackSession] };
}

const QUICK_PROMPTS = [
  {
    title: "Summarize case",
    prompt: "Summarize this case in plain language.",
  },
  {
    title: "Family update",
    prompt: "Draft a brief family-friendly update.",
  },
  {
    title: "Next questions",
    prompt: "List the next questions to ask.",
  },
  {
    title: "Differential",
    prompt: "Give a concise differential overview.",
  },
];

function truncateText(text: string, limit = 88) {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 1)}…`;
}

export default function Assistant() {
  const initialState = useMemo(loadStoredState, []);
  const [sessions, setSessions] = useState<ChatSession[]>(
    initialState.sessions,
  );
  const [currentSessionId, setCurrentSessionId] = useState(
    initialState.currentSessionId,
  );
  const [models, setModels] = useState<LocalLlmModelOption[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [lastCitations, setLastCitations] = useState<CitationItem[]>([]);

  const currentSession =
    sessions.find((session) => session.id === currentSessionId) ?? sessions[0];

  const systemPrompt = currentSession.systemPrompt;
  const model = currentSession.model;
  const temperature = currentSession.temperature;
  const maxTokens = currentSession.maxTokens;
  const messages = currentSession.messages;

  const chatMessages = useMemo(
    () =>
      [
        { role: "system" as const, content: systemPrompt.trim() },
        ...messages,
      ].filter((msg) => msg.content.trim()),
    [systemPrompt, messages],
  );

  const historyItems = useMemo(() => sessions, [sessions]);

  const updateCurrentSession = useCallback(
    (updater: (session: ChatSession) => ChatSession) => {
      setSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId ? updater(session) : session,
        ),
      );
    },
    [currentSessionId],
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
          updateCurrentSession((session) =>
            session.messages.length === 0 &&
            session.model === "Qwen3.5-4B-Q4_K_M.gguf"
              ? {
                  ...session,
                  model: selected.filename,
                  modelLabel: selected.label,
                  updatedAt: Date.now(),
                }
              : session,
          );
        }
      })
      .catch(() => {
        // Leave defaults in place.
      });
    return () => {
      cancelled = true;
    };
  }, [updateCurrentSession]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      CHAT_STORAGE_KEY,
      JSON.stringify({
        currentSessionId,
        sessions,
      } satisfies StoredAssistantState),
    );
  }, [currentSessionId, sessions]);

  const loadSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setInput("");
    setError(null);
  };

  const startNewChat = () => {
    const nextSession = createSession();
    setSessions((prev) => [...prev, nextSession]);
    setCurrentSessionId(nextSession.id);
    setInput("");
    setError(null);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages = [
      ...messages,
      { role: "user" as const, content: text },
    ];
    setError(null);
    setLoading(true);
    setInput("");

    const nextSummary =
      currentSession.summary === "New chat"
        ? summarizeFirstUserInput(nextMessages)
        : currentSession.summary;

    updateCurrentSession((session) => ({
      ...session,
      summary: nextSummary,
      messages: nextMessages,
      updatedAt: Date.now(),
    }));

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
      setLastCitations(response.citations || []);
      updateCurrentSession((session) => ({
        ...session,
        summary: nextSummary,
        messages: [
          ...nextMessages,
          { role: "assistant", content: response.reply },
        ],
        updatedAt: Date.now(),
      }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    startNewChat();
    setLastCitations([]);
  };

  return (
    <div className="assistant-page assistant-page-light">
      <header className="assistant-topbar-light">
        <div>
          <div className="assistant-page-title">Local AI Assistant</div>
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
        <aside className="assistant-history-panel-light">
          <div className="assistant-panel-header-light">
            <div>
              <div className="assistant-panel-title-light">Chat history</div>
            </div>
            <button className="btn btn-outline btn-sm" onClick={startNewChat}>
              New chat
            </button>
          </div>

          <div className="assistant-history-list-light">
            {historyItems.length > 0 ? (
              historyItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`assistant-history-item-light ${
                    item.id === currentSessionId ? "active" : ""
                  }`}
                  onClick={() => loadSession(item)}
                  title="Click to restore this chat"
                >
                  <span className="assistant-history-title-light">
                    {item.summary || "New chat"}
                  </span>
                  <span className="assistant-history-preview-light">
                    {item.messages.filter((msg) => msg.role === "user").length}{" "}
                    user message
                    {item.messages.filter((msg) => msg.role === "user")
                      .length === 1
                      ? ""
                      : "s"}
                  </span>
                </button>
              ))
            ) : (
              <div className="assistant-history-empty-light">
                No saved chat yet.
              </div>
            )}
          </div>
        </aside>

        <section className="assistant-main-column-light">
          <section className="assistant-hero-plain">
            <div>
              <h2>How can I help you?</h2>
            </div>
            <div className="assistant-prompt-grid assistant-prompt-grid-plain">
              {QUICK_PROMPTS.map((item) => (
                <button
                  key={item.title}
                  className="assistant-prompt-card"
                  type="button"
                  onClick={() => setInput(item.prompt)}
                >
                  <div className="assistant-prompt-card-title">
                    {item.title}
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="assistant-chat-panel-light">
            <div className="chat-thread assistant-chat-thread-light assistant-chat-thread-expand">
              {messages.length > 0 ? (
                chatMessages.slice(1).map((msg, idx) => (
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
                ))
              ) : (
                <div className="assistant-empty-state-light">
                  <div className="assistant-empty-state-title-light">
                    Start a new chat
                  </div>
                </div>
              )}
            </div>

            {lastCitations.length > 0 && (
              <div className="assistant-citations-light">
                <div className="assistant-citations-title-light">
                  Local research sources used
                </div>
                <div className="assistant-citations-list-light">
                  {lastCitations.map((citation) => {
                    const citationTitle =
                      citation.fields.title == null
                        ? ""
                        : String(citation.fields.title);
                    return (
                      <div
                        key={`${citation.type}-${citation.label}`}
                        className="assistant-citation-item-light"
                      >
                        <div className="assistant-citation-label-light">
                          {citation.label}
                        </div>
                        {citationTitle && (
                          <div className="assistant-citation-title-light">
                            {citationTitle}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

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
        </section>
      </main>

      {settingsOpen && (
        <div
          className="assistant-modal-backdrop"
          onClick={() => setSettingsOpen(false)}
        >
          <div
            className="assistant-modal assistant-modal-light"
            onClick={(e) => e.stopPropagation()}
          >
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
                    const selected = models.find(
                      (item) => item.filename === filename,
                    );
                    updateCurrentSession((session) => ({
                      ...session,
                      model: filename,
                      modelLabel: selected?.label || filename,
                      updatedAt: Date.now(),
                    }));
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
                      onChange={(e) =>
                        updateCurrentSession((session) => ({
                          ...session,
                          temperature: Number(e.target.value),
                          updatedAt: Date.now(),
                        }))
                      }
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
                      onChange={(e) =>
                        updateCurrentSession((session) => ({
                          ...session,
                          maxTokens: Number(e.target.value),
                          updatedAt: Date.now(),
                        }))
                      }
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
                  onChange={(e) =>
                    updateCurrentSession((session) => ({
                      ...session,
                      systemPrompt: e.target.value,
                      updatedAt: Date.now(),
                    }))
                  }
                />
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
