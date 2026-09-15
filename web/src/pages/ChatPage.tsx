import { type FormEvent, useState } from "react";

import { ApiError, type ConversationResponse, sendConversationMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { ChatMessage, type ChatEntry } from "../components/ChatMessage";
import { ExecutionTracePanel } from "../components/ExecutionTracePanel";

const quickPrompts = [
  "Camera nào tôi được xem?",
  "Tìm tất cả sự kiện",
  "CAM-A01 từ 00:40 đến 01:00 có gì?",
  "CAM-B01 từ 00:40 đến 01:00 có gì?",
  "Xem video EVT-B01-001",
];

export function ChatPage() {
  const { token } = useAuth();
  const [message, setMessage] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [trace, setTrace] = useState<ConversationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  async function submitPrompt(prompt: string) {
    if (!token || !prompt.trim() || isSending) return;
    const entry: ChatEntry = { id: crypto.randomUUID(), prompt: prompt.trim() };
    setEntries((current) => [...current, entry]);
    setMessage("");
    setError(null);
    setIsSending(true);
    try {
      const response = await sendConversationMessage(token, entry.prompt);
      setEntries((current) => current.map((item) => item.id === entry.id ? { ...item, response } : item));
      setTrace(response);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.message : "Unable to send the prompt.");
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitPrompt(message);
  }

  return (
    <AppShell>
      <section className="chat-heading"><div><p className="eyebrow">DETERMINISTIC CONVERSATION</p><h1>Camera query</h1><p>Each request is evaluated by the backend before any tool runs.</p></div></section>
      <section className="quick-prompts" aria-label="Quick prompts">
        {quickPrompts.map((prompt) => <button key={prompt} type="button" onClick={() => void submitPrompt(prompt)} disabled={isSending}>{prompt}</button>)}
      </section>
      <section className="chat-layout">
        <div className="chat-area">
          <div className="message-history" aria-live="polite">
            {entries.length === 0 && <p className="state-message">Choose a quick prompt or ask about cameras and events.</p>}
            {entries.map((entry) => <ChatMessage key={entry.id} entry={entry} />)}
          </div>
          {error !== null && <p className="form-error" role="alert">{error}</p>}
          <form className="chat-composer" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="chat-message">Message</label>
            <input id="chat-message" placeholder="Ask about a camera or event…" value={message} onChange={(event) => setMessage(event.target.value)} disabled={isSending} />
            <button className="primary-button" type="submit" disabled={isSending || !message.trim()}>{isSending ? "Sending…" : "Send"}</button>
          </form>
        </div>
        <ExecutionTracePanel trace={trace} />
      </section>
    </AppShell>
  );
}
