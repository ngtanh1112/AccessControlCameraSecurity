import type { ConversationResponse, EventResult } from "../api/client";
import { EventResultCard } from "./EventResultCard";

export type ChatEntry = {
  id: string;
  prompt: string;
  response?: ConversationResponse;
};

function isEventResult(value: unknown): value is EventResult {
  return typeof value === "object" && value !== null && "event_id" in value;
}

export function ChatMessage({ entry }: { entry: ChatEntry }) {
  const rawData: unknown[] = Array.isArray(entry.response?.data) ? entry.response.data : [];
  const events = rawData.reduce<EventResult[]>((result, value) => {
    if (isEventResult(value)) result.push(value);
    return result;
  }, []);
  return (
    <article className="chat-message">
      <div className="prompt-bubble"><span>You</span><p>{entry.prompt}</p></div>
      {entry.response !== undefined && <div className={entry.response.decision === "ALLOW" ? "answer-bubble allow-answer" : "answer-bubble deny-answer"}>
        <span>Security Console</span><p>{entry.response.answer}</p>
        {events.length > 0 && <section className="event-results" aria-label="Event results">{events.map((event) => <EventResultCard key={event.event_id} event={event} />)}</section>}
      </div>}
    </article>
  );
}
