"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type MouseEvent,
  type KeyboardEvent,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useChatStore } from "@/store/chatStore";
import { useAuthStore } from "@/store/authStore";
import { chatApi } from "@/lib/api/endpoints";
import { tokenStorage } from "@/lib/api/client";

import type {
  Conversation,
  Citation,
  SSEDoneEvent,
} from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api/v1";

/* =========================================================
   SSE Authentication Helper
   ========================================================= */

/**
 * Native fetch() does not use Axios interceptors.
 * The chat endpoint is an SSE/native fetch request, so a
 * 401 must be refreshed and retried manually.
 *
 * A shared Promise prevents multiple simultaneous 401s from
 * sending multiple refresh requests.
 */
let sseRefreshPromise: Promise<string> | null = null;

const refreshAccessTokenForSSE =
  async (): Promise<string> => {
    if (sseRefreshPromise) {
      return sseRefreshPromise;
    }

    const refreshToken =
      tokenStorage.getRefresh();

    if (!refreshToken) {
      tokenStorage.clear();

      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }

      throw new Error(
        "No refresh token available. Please login again."
      );
    }

    sseRefreshPromise = (async () => {
      try {
        const response =
          await fetch(
            `${API_BASE}/auth/refresh/`,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
                Accept:
                  "application/json",
              },
              body: JSON.stringify({
                refresh_token:
                  refreshToken,
              }),
            }
          );

        if (!response.ok) {
          throw new Error(
            `Token refresh failed: ${response.status}`
          );
        }

        const result =
          await response.json();

        const data =
          result?.data;

        const newAccessToken =
          data?.access_token;

        const newRefreshToken =
          data?.refresh_token ||
          refreshToken;

        if (!newAccessToken) {
          throw new Error(
            "Refresh endpoint did not return access_token."
          );
        }

        tokenStorage.set(
          newAccessToken,
          newRefreshToken
        );

        return newAccessToken;
      } catch (error) {
        console.error(
          "SSE token refresh failed:",
          error
        );

        tokenStorage.clear();

        if (
          typeof window !== "undefined"
        ) {
          window.location.href =
            "/login";
        }

        throw error;
      } finally {
        sseRefreshPromise = null;
      }
    })();

    return sseRefreshPromise;
  };


/* =========================================================
   Markdown Helpers
   ========================================================= */

/**
 * Backend responses can occasionally arrive with Markdown
 * heading markers flattened into the previous paragraph:
 *
 *   Answer ... #### Benefit ...
 *
 * ReactMarkdown cannot treat "####" in the middle of a
 * paragraph as a heading. Normalize those boundaries before
 * rendering while preserving normal Markdown content.
 */
/**
 * Normalize AI-generated Markdown before ReactMarkdown rendering.
 *
 * Goals:
 * 1. Convert escaped newlines into real newlines.
 * 2. Keep Markdown headings as separate blocks.
 * 3. Prevent:
 *
 *      ### BenefitsThe scheme...
 *
 *    from becoming one visual block.
 * 4. Preserve normal Markdown content.
 * 5. Avoid damaging URLs, hashes, or normal text.
 */
const normalizeAssistantMarkdown = (
  content: string | null | undefined
): string => {
  if (!content) return "";

  let text = String(content);

  // ---------------------------------------------------------
  // 1. Normalize line endings
  // ---------------------------------------------------------

  text = text.replace(/\r\n/g, "\n");
  text = text.replace(/\r/g, "\n");

  // Backend / streaming responses can sometimes contain
  // literal escaped newline characters.
  text = text.replace(/\\r\\n/g, "\n");
  text = text.replace(/\\n/g, "\n");

  // ---------------------------------------------------------
  // 2. Remove accidental code fences around Markdown
  // ---------------------------------------------------------

  text = text.replace(
    /^\s*```(?:markdown|md)?\s*\n?/i,
    ""
  );

  text = text.replace(
    /\n?\s*```\s*$/i,
    ""
  );

  // ---------------------------------------------------------
  // 3. Ensure headings always start on a new block
  // ---------------------------------------------------------

  text = text.replace(
    /([^\n])\s+(#{1,6})\s+/g,
    "$1\n\n$2 "
  );

  // ---------------------------------------------------------
  // 4. Normalize heading syntax
  // ---------------------------------------------------------

  text = text.replace(
    /^[ \t]*(#{1,6})[ \t]+/gm,
    "$1 "
  );

  // ---------------------------------------------------------
  // 5. IMPORTANT:
  // Force known AI response headings to end with a newline.
  //
  // This specifically prevents:
  //
  // ### BenefitsThe scheme...
  //
  // from being rendered as:
  //
  // BenefitsThe scheme...
  // ---------------------------------------------------------

  const knownHeadings = [
    "Overview",
    "Benefits",
    "Eligibility",
    "Required Documents",
    "How to Apply",
    "Official Government Scheme Information",
    "Eligibility Evaluation Result",
    "Official Evidence & Citations",
    "Sources",
    "Conclusion",
  ];

  for (const heading of knownHeadings) {
    const escapedHeading = heading.replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&"
    );

    // Handles:
    //
    // ### BenefitsThe scheme...
    //
    // and converts it to:
    //
    // ### Benefits
    //
    // The scheme...
    text = text.replace(
      new RegExp(
        `(#{1,6})\\s*${escapedHeading}(?=\\S)`,
        "gi"
      ),
      `$1 ${heading}\n\n`
    );

    // Handles normal heading followed immediately by text
    // on the same line.
    text = text.replace(
      new RegExp(
        `(#{1,6})\\s*${escapedHeading}[ \\t]+([^\\n])`,
        "gi"
      ),
      `$1 ${heading}\n\n$2`
    );
  }

  // ---------------------------------------------------------
  // 6. Ensure Markdown headings followed by content have
  // a blank line.
  // ---------------------------------------------------------

  text = text.replace(
    /^(#{1,6}) ([^\n]+)\n(?=[^\n#])/gm,
    "$1 $2\n\n"
  );

  // ---------------------------------------------------------
  // 7. Clean excessive blank lines
  // ---------------------------------------------------------

  text = text.replace(
    /\n{3,}/g,
    "\n\n"
  );

  // ---------------------------------------------------------
  // 8. Remove trailing whitespace
  // ---------------------------------------------------------

  text = text
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n");

  // ---------------------------------------------------------
  // 9. Final cleanup
  // ---------------------------------------------------------

  return text.trim();
};

const SUGGESTED_QUERIES = [
  "What schemes am I eligible for based on my profile?",
  "Tell me about PM Kisan Samman Nidhi — eligibility and benefits",
  "What housing schemes are available for BPL families?",
  "How can I apply for Ayushman Bharat health insurance?",
  "Are there any schemes for women entrepreneurs?",
  "What education scholarships exist for SC/ST students?",
];

/* =========================================================
   Citation Helpers
   ========================================================= */

/**
 * Backend citation_number can sometimes be:
 * - missing
 * - null
 * - empty
 * - duplicated
 *
 * So UI always gets a safe display number.
 */
const getCitationNumber = (
  cite: Citation,
  index: number
): string => {
  const rawNumber = (cite as any)?.citation_number;

  if (
    rawNumber !== undefined &&
    rawNumber !== null &&
    String(rawNumber).trim() !== ""
  ) {
    return String(rawNumber);
  }

  return String(index + 1);
};

/**
 * React key must ALWAYS be unique.
 *
 * citation_number alone is not enough because backend can
 * return duplicate or empty citation numbers.
 */
const getCitationKey = (
  cite: Citation,
  index: number,
  prefix = "citation"
): string => {
  const number = getCitationNumber(cite, index);

  const source =
    (cite as any)?.source_url ||
    (cite as any)?.document_name ||
    (cite as any)?.document_title ||
    (cite as any)?.scheme_name ||
    "source";

  return `${prefix}-${number}-${index}-${source}`;
};

/**
 * Safe citation title.
 */
const getCitationTitle = (cite: Citation): string => {
  return (
    (cite as any)?.scheme_name ||
    (cite as any)?.document_name ||
    (cite as any)?.document_title ||
    "Scheme Guidelines"
  );
};

/**
 * Safe section name.
 */
const getCitationSection = (cite: Citation): string => {
  return (
    (cite as any)?.section ||
    (cite as any)?.section_title ||
    ""
  );
};

/**
 * Safe page number.
 */
const getCitationPage = (cite: Citation): string => {
  const page =
    (cite as any)?.page_number ??
    (cite as any)?.page ??
    "";

  return page !== "" && page !== null && page !== undefined
    ? String(page)
    : "";
};

export default function ChatPage() {
  const { user } = useAuthStore();

  const {
    conversations,
    activeConversation,
    messages,
    streaming,

    setConversations,
    addConversation,
    removeConversation,
    setActiveConversation,
    setMessages,
    addMessage,

    appendStreamToken,
    setStreamingCitations,
    setStreamingStage,
    startStreaming,
    stopStreaming,
    setLoadingConversations,
  } = useChatStore();

  const [inputValue, setInputValue] = useState("");
  const [isCreatingConv, setIsCreatingConv] = useState(false);
  const [selectedCitation, setSelectedCitation] =
    useState<Citation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* =========================================================
     Load Conversations
     ========================================================= */

  useEffect(() => {
    loadConversations();
  }, []);

  /* =========================================================
     Auto Scroll
     ========================================================= */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, streaming.streamingText]);

  /* =========================================================
     Conversations
     ========================================================= */

  const loadConversations = async () => {
    setLoadingConversations(true);

    try {
      const res = await chatApi.listConversations();

      setConversations(
        res.data.data || []
      );
    } catch (error) {
      console.error(
        "Failed to load conversations:",
        error
      );
    } finally {
      setLoadingConversations(false);
    }
  };

  const createNewConversation = async () => {
    setIsCreatingConv(true);

    try {
      const res =
        await chatApi.createConversation();

      const conv = res.data.data!;

      addConversation(conv);
      setActiveConversation(conv);
      setMessages([]);
    } catch (error) {
      console.error(
        "Failed to create conversation:",
        error
      );
    } finally {
      setIsCreatingConv(false);
    }
  };

  const loadConversation = async (
    conv: Conversation
  ) => {
    setActiveConversation(conv);

    try {
      const res =
        await chatApi.getConversation(conv.id);

      setMessages(
        res.data.data?.messages || []
      );
    } catch (error) {
      console.error(
        "Failed to load conversation:",
        error
      );
    }
  };

  const deleteConversation = async (
    convId: string,
    e: MouseEvent
  ) => {
    e.stopPropagation();

    try {
      await chatApi.deleteConversation(convId);

      removeConversation(convId);

      if (
        activeConversation?.id === convId
      ) {
        setActiveConversation(null);
        setMessages([]);
      }
    } catch (error) {
      console.error(
        "Failed to delete conversation:",
        error
      );
    }
  };

  /* =========================================================
     Send Message
     ========================================================= */

  const sendMessage = useCallback(
    async (query: string) => {
      if (
        !query.trim() ||
        streaming.isStreaming
      ) {
        return;
      }

      let conv = activeConversation;

      /* -----------------------------------------
         Auto-create conversation
         ----------------------------------------- */

      if (!conv) {
        setIsCreatingConv(true);

        try {
          const res =
            await chatApi.createConversation();

          conv = res.data.data!;

          addConversation(conv);
          setActiveConversation(conv);
        } catch (error) {
          console.error(
            "Failed to create conversation:",
            error
          );
          setIsCreatingConv(false);
          return;
        } finally {
          setIsCreatingConv(false);
        }
      }

      /* -----------------------------------------
         Add User Message
         ----------------------------------------- */

      const userMsg = {
        id: crypto.randomUUID(),
        role: "user" as const,
        content: query,
        cited_sources: [],
        query_type: "",
        confidence_score: null,
        latency_ms: null,
        feedback_rating: null,
        created_at:
          new Date().toISOString(),
      };

      addMessage(userMsg);

      setInputValue("");

      startStreaming();

      /* -----------------------------------------
         Access Token + SSE Request
         ----------------------------------------- */

      const makeStreamRequest = async (
        accessToken: string
      ): Promise<Response> => {
        return fetch(
          `${API_BASE}/chat/conversations/${conv!.id}/messages/`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
              Authorization:
                `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              content: query,
            }),
          }
        );
      };

      try {
        /*
         * Native fetch() does NOT use Axios interceptors.
         * Therefore a 401 from the SSE endpoint is handled
         * here explicitly.
         */
        let token =
          tokenStorage.getAccess();

        if (!token) {
          throw new Error(
            "Authentication token is missing. Please login again."
          );
        }

        // First request with the current access token.
        let response =
          await makeStreamRequest(token);

        // Access token expired -> refresh -> retry same request.
        if (response.status === 401) {
          console.warn(
            "SSE request returned 401. Refreshing access token..."
          );

          token =
            await refreshAccessTokenForSSE();

          response =
            await makeStreamRequest(token);
        }

        if (!response.ok) {
          let errorMessage =
            `Stream failed: ${response.status}`;

          try {
            const errorText =
              await response.text();

            if (errorText) {
              errorMessage +=
                ` - ${errorText.slice(0, 500)}`;
            }
          } catch {
            // Ignore error-body parsing failures.
          }

          throw new Error(
            errorMessage
          );
        }

        if (!response.body) {
          throw new Error(
            "Streaming response body is empty."
          );
        }

        const reader =
          response.body.getReader();

        const decoder =
          new TextDecoder("utf-8");

        let buffer = "";

        let finalData:
          | SSEDoneEvent
          | null = null;

        /* -----------------------------------------
           Read SSE Stream
           ----------------------------------------- */

        while (true) {
          const {
            done,
            value,
          } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(
            value,
            { stream: true }
          );

          const lines =
            buffer.split(/\r?\n/);

          // Keep an incomplete SSE line for the next chunk.
          buffer =
            lines.pop() || "";

          for (const line of lines) {
            const trimmed =
              line.trim();

            if (!trimmed) {
              continue;
            }

            // SSE event name. Payload identifies the event.
            if (
              trimmed.startsWith(
                "event:"
              )
            ) {
              continue;
            }

            if (
              !trimmed.startsWith(
                "data:"
              )
            ) {
              continue;
            }

            const dataStr =
              trimmed
                .slice(5)
                .trim();

            if (
              !dataStr ||
              dataStr === "[DONE]"
            ) {
              continue;
            }

            try {
              const parsed =
                JSON.parse(
                  dataStr
                );

              /* -----------------------------
                 Token Event
                 ----------------------------- */

              if (
                parsed &&
                typeof parsed ===
                  "object" &&
                "text" in parsed &&
                parsed.text !==
                  undefined
              ) {
                appendStreamToken(
                  String(
                    parsed.text
                  )
                );

                continue;
              }

              /* -----------------------------
                 Stage Event
                 ----------------------------- */

              if (
                parsed &&
                typeof parsed ===
                  "object" &&
                "stage" in parsed
              ) {
                setStreamingStage(
                  parsed.message ||
                    parsed.stage ||
                    "Processing..."
                );

                continue;
              }

              /* -----------------------------
                 Citation Event
                 ----------------------------- */

              if (
                parsed &&
                typeof parsed ===
                  "object" &&
                "citations" in
                  parsed &&
                !(
                  "full_answer" in
                  parsed
                )
              ) {
                setStreamingCitations(
                  Array.isArray(
                    parsed.citations
                  )
                    ? parsed.citations
                    : []
                );

                continue;
              }

              /* -----------------------------
                 Final Event
                 ----------------------------- */

              if (
                parsed &&
                typeof parsed ===
                  "object" &&
                "full_answer" in
                  parsed
              ) {
                finalData =
                  parsed as SSEDoneEvent;
              }
            } catch (parseError) {
              console.warn(
                "Invalid SSE JSON:",
                dataStr,
                parseError
              );
            }
          }
        }

        /* -----------------------------------------
           Final Response
           ----------------------------------------- */

        if (finalData) {
          const finalCitations =
            Array.isArray(
              finalData.citations
            )
              ? finalData.citations
              : [];

          stopStreaming({
            ...finalData,
            citations:
              finalCitations,
          });

          const assistantMsg = {
            id:
              crypto.randomUUID(),

            role:
              "assistant" as const,

            content:
              finalData.full_answer ||
              "",

            cited_sources:
              finalCitations,

            query_type:
              finalData.query_type ||
              "",

            confidence_score:
              finalData.confidence_score ??
              null,

            latency_ms:
              finalData.latency_ms ??
              null,

            feedback_rating:
              null,

            created_at:
              new Date().toISOString(),
          };

          addMessage(
            assistantMsg
          );
        } else {
          /*
           * Stream ended without the final full_answer event.
           * Do not leave the UI stuck in streaming state.
           */
          console.warn(
            "SSE stream finished without a final full_answer event."
          );

          stopStreaming({
            citations: [],
            confidence_score: 0,
            latency_ms: 0,
            query_type: "",
            full_answer: "",
          });
        }
      } catch (err) {
        console.error(
          "Chat streaming error:",
          err
        );

        stopStreaming({
          citations: [],
          confidence_score: 0,
          latency_ms: 0,
          query_type: "",
          full_answer: "",
        });

        addMessage({
          id:
            crypto.randomUUID(),

          role:
            "assistant",

          content:
            err instanceof Error
              ? err.message
              : "I encountered an error while generating a response. Please try again.",

          cited_sources: [],

          query_type: "",

          confidence_score:
            null,

          latency_ms:
            null,

          feedback_rating:
            null,

          created_at:
            new Date().toISOString(),
        });
      }
    },
    [
      activeConversation,
      streaming.isStreaming,
      addConversation,
      addMessage,
      setActiveConversation,
      startStreaming,
      stopStreaming,
      appendStreamToken,
      setStreamingCitations,
      setStreamingStage,
    ]
  );


  /* =========================================================
     Keyboard
     ========================================================= */

  const handleKeyDown = (
    e: KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      e.key === "Enter" &&
      !e.shiftKey
    ) {
      e.preventDefault();

      sendMessage(
        inputValue
      );
    }
  };

  /* =========================================================
     Render
     ========================================================= */

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* =====================================================
          Conversations Panel
          ===================================================== */}

      <div
        style={{
          width: "260px",
          background:
            "var(--color-bg-surface)",
          borderRight:
            "1px solid var(--color-border)",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: "1rem",
            borderBottom:
              "1px solid var(--color-border)",
          }}
        >
          <button
            className="btn-primary"
            onClick={
              createNewConversation
            }
            disabled={
              isCreatingConv
            }
            style={{
              width: "100%",
              justifyContent:
                "center",
              fontSize: "0.85rem",
            }}
          >
            {isCreatingConv ? (
              <div
                className="spinner"
                style={{
                  width: 14,
                  height: 14,
                }}
              />
            ) : (
              "＋"
            )}
            &nbsp;New Chat
          </button>
        </div>

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "0.5rem",
          }}
        >
          <AnimatePresence>
            {conversations.map(
              (conv) => (
                <motion.div
                  key={`conversation-${conv.id}`}
                  initial={{
                    opacity: 0,
                    x: -10,
                  }}
                  animate={{
                    opacity: 1,
                    x: 0,
                  }}
                  exit={{
                    opacity: 0,
                    x: -10,
                  }}
                  onClick={() =>
                    loadConversation(
                      conv
                    )
                  }
                  style={{
                    padding:
                      "0.65rem 0.75rem",
                    borderRadius:
                      "var(--radius-md)",
                    marginBottom:
                      "0.2rem",
                    cursor:
                      "pointer",
                    background:
                      activeConversation?.id ===
                        conv.id
                        ? "var(--color-bg-overlay)"
                        : "transparent",
                    border:
                      activeConversation?.id ===
                        conv.id
                        ? "1px solid var(--color-border-subtle)"
                        : "1px solid transparent",
                    display: "flex",
                    alignItems:
                      "center",
                    gap: "0.5rem",
                    transition:
                      "all 0.15s",
                  }}
                >
                  <span
                    style={{
                      fontSize:
                        "0.85rem",
                    }}
                  >
                    💬
                  </span>

                  <div
                    style={{
                      flex: 1,
                      overflow:
                        "hidden",
                    }}
                  >
                    <p
                      style={{
                        fontSize:
                          "0.8rem",
                        fontWeight: 500,
                        overflow:
                          "hidden",
                        textOverflow:
                          "ellipsis",
                        whiteSpace:
                          "nowrap",
                        color:
                          "var(--color-text-primary)",
                      }}
                    >
                      {conv.title ||
                        "New Conversation"}
                    </p>

                    <p
                      style={{
                        fontSize:
                          "0.7rem",
                        color:
                          "var(--color-text-muted)",
                      }}
                    >
                      {
                        conv.message_count
                      }{" "}
                      messages
                    </p>
                  </div>

                  <button
                    onClick={(e) =>
                      deleteConversation(
                        conv.id,
                        e
                      )
                    }
                    className="btn-ghost"
                    style={{
                      padding:
                        "0.15rem 0.3rem",
                      fontSize:
                        "0.7rem",
                      opacity: 0.5,
                    }}
                  >
                    ✕
                  </button>
                </motion.div>
              )
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* =====================================================
          Main Chat Area
          ===================================================== */}

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}

        <div
          style={{
            padding:
              "1rem 1.5rem",
            borderBottom:
              "1px solid var(--color-border)",
            display: "flex",
            alignItems:
              "center",
            gap: "0.75rem",
            background:
              "var(--color-bg-surface)",
          }}
        >
          <span
            style={{
              fontSize:
                "1.3rem",
            }}
          >
            🤖
          </span>

          <div>
            <h2
              style={{
                fontSize:
                  "1rem",
                fontWeight: 600,
                margin: 0,
              }}
            >
              Government Scheme AI
            </h2>

            <p
              style={{
                fontSize:
                  "0.75rem",
                color:
                  "var(--color-text-muted)",
                margin: 0,
              }}
            >
              Powered by official
              government documents
            </p>
          </div>

          {activeConversation && (
            <div
              style={{
                marginLeft: "auto",
                display: "flex",
                alignItems:
                  "center",
                gap: "0.6rem",
              }}
            >
              <span
                className="badge badge-success"
                style={{
                  fontSize:
                    "0.68rem",
                }}
              >
                ● Active
              </span>

              <button
                onClick={async () => {
                  if (
                    activeConversation
                  ) {
                    try {
                      await chatApi.deleteConversation(
                        activeConversation.id
                      );

                      removeConversation(
                        activeConversation.id
                      );

                      setActiveConversation(
                        null
                      );

                      setMessages(
                        []
                      );
                    } catch (
                    error
                    ) {
                      console.error(
                        "Failed to clear chat:",
                        error
                      );
                    }
                  }
                }}
                className="btn-ghost"
                style={{
                  fontSize:
                    "0.75rem",
                  padding:
                    "0.25rem 0.5rem",
                  color:
                    "var(--color-danger)",
                }}
              >
                🗑️ Clear Chat
              </button>
            </div>
          )}
        </div>

        {/* ===================================================
            Messages
            =================================================== */}

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "1.5rem",
          }}
        >
          {messages.length === 0 &&
            !streaming.isStreaming ? (
            /* Welcome */

            <div
              style={{
                textAlign:
                  "center",
                maxWidth:
                  "600px",
                margin:
                  "2rem auto",
              }}
            >
              <div
                style={{
                  fontSize:
                    "3rem",
                  marginBottom:
                    "1rem",
                }}
              >
                🏛️
              </div>

              <h2
                style={{
                  fontSize:
                    "1.5rem",
                  marginBottom:
                    "0.75rem",
                }}
              >
                Hello,{" "}
                {user?.email?.split(
                  "@"
                )[0] ||
                  "there"}
                !
              </h2>

              <p
                style={{
                  color:
                    "var(--color-text-secondary)",
                  marginBottom:
                    "2rem",
                  lineHeight:
                    1.7,
                }}
              >
                Ask me anything
                about government
                schemes. I'll search
                official documents
                and give you
                evidence-based
                answers with source
                citations.
              </p>

              <div
                style={{
                  display:
                    "grid",
                  gridTemplateColumns:
                    "repeat(2, 1fr)",
                  gap:
                    "0.75rem",
                  textAlign:
                    "left",
                }}
              >
                {SUGGESTED_QUERIES.map(
                  (q) => (
                    <button
                      key={`suggestion-${q}`}
                      onClick={() =>
                        sendMessage(q)
                      }
                      className="card"
                      style={{
                        border:
                          "1px solid var(--color-border)",
                        textAlign:
                          "left",
                        cursor:
                          "pointer",
                        padding:
                          "0.75rem",
                        fontSize:
                          "0.8rem",
                        color:
                          "var(--color-text-secondary)",
                        transition:
                          "all 0.15s",
                      }}
                      onMouseEnter={(
                        e
                      ) => {
                        e.currentTarget.style.borderColor =
                          "var(--color-primary)";
                        e.currentTarget.style.color =
                          "var(--color-text-primary)";
                      }}
                      onMouseLeave={(
                        e
                      ) => {
                        e.currentTarget.style.borderColor =
                          "var(--color-border)";
                        e.currentTarget.style.color =
                          "var(--color-text-secondary)";
                      }}
                    >
                      {q}
                    </button>
                  )
                )}
              </div>
            </div>
          ) : (
            /* Message List */

            <div
              style={{
                maxWidth:
                  "800px",
                margin:
                  "0 auto",
              }}
            >
              <AnimatePresence>
                {messages.map(
                  (msg) => (
                    <motion.div
                      key={`message-${msg.id}`}
                      initial={{
                        opacity: 0,
                        y: 10,
                      }}
                      animate={{
                        opacity: 1,
                        y: 0,
                      }}
                      style={{
                        display:
                          "flex",
                        flexDirection:
                          msg.role ===
                            "user"
                            ? "row-reverse"
                            : "row",
                        gap:
                          "0.75rem",
                        marginBottom:
                          "1.5rem",
                        alignItems:
                          "flex-start",
                      }}
                    >
                      {/* Avatar */}

                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius:
                            "50%",
                          background:
                            msg.role ===
                              "user"
                              ? "var(--gradient-primary)"
                              : "var(--color-bg-overlay)",
                          display:
                            "flex",
                          alignItems:
                            "center",
                          justifyContent:
                            "center",
                          fontSize:
                            "0.85rem",
                          flexShrink:
                            0,
                          border:
                            msg.role ===
                              "assistant"
                              ? "1px solid var(--color-border)"
                              : "none",
                        }}
                      >
                        {msg.role ===
                          "user"
                          ? user?.email?.[0]?.toUpperCase() ||
                          "U"
                          : "🤖"}
                      </div>

                      {/* Bubble */}

                      <div
                        style={{
                          maxWidth:
                            "75%",
                        }}
                      >
                        <div
                          style={{
                            padding:
                              "0.875rem 1rem",
                            borderRadius:
                              msg.role ===
                                "user"
                                ? "var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)"
                                : "var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg)",
                            background:
                              msg.role ===
                                "user"
                                ? "var(--gradient-primary)"
                                : "var(--color-bg-elevated)",
                            border:
                              msg.role ===
                                "assistant"
                                ? "1px solid var(--color-border)"
                                : "none",
                            fontSize:
                              "0.9rem",
                            lineHeight:
                              1.65,
                          }}
                        >
                          {msg.role === "assistant" ? (
                            <div
                              className="markdown-body"
                              style={{
                                whiteSpace: "normal",
                                wordBreak: "break-word",
                              }}
                            >
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  h1: ({ children }) => (
                                    <h1
                                      style={{
                                        fontSize: "1.25rem",
                                        fontWeight: 700,
                                        margin: "0 0 0.75rem",
                                        lineHeight: 1.3,
                                      }}
                                    >
                                      {children}
                                    </h1>
                                  ),
                                  h2: ({ children }) => (
                                    <h2
                                      style={{
                                        fontSize: "1.1rem",
                                        fontWeight: 700,
                                        margin: "1rem 0 0.5rem",
                                        lineHeight: 1.4,
                                      }}
                                    >
                                      {children}
                                    </h2>
                                  ),
                                  h3: ({ children }) => (
                                    <h3
                                      style={{
                                        fontSize: "1rem",
                                        fontWeight: 700,
                                        margin: "0.9rem 0 0.4rem",
                                        lineHeight: 1.4,
                                        color: "var(--color-primary)",
                                      }}
                                    >
                                      {children}
                                    </h3>
                                  ),
                                  h4: ({ children }) => (
                                    <h4
                                      style={{
                                        fontSize: "0.95rem",
                                        fontWeight: 700,
                                        margin: "0.8rem 0 0.35rem",
                                        lineHeight: 1.4,
                                        color: "var(--color-primary)",
                                      }}
                                    >
                                      {children}
                                    </h4>
                                  ),
                                  p: ({ children }) => (
                                    <p
                                      style={{
                                        margin: "0 0 0.7rem",
                                        lineHeight: 1.65,
                                      }}
                                    >
                                      {children}
                                    </p>
                                  ),
                                  ul: ({ children }) => (
                                    <ul
                                      style={{
                                        margin: "0.5rem 0 0.8rem",
                                        paddingLeft: "1.4rem",
                                      }}
                                    >
                                      {children}
                                    </ul>
                                  ),
                                  ol: ({ children }) => (
                                    <ol
                                      style={{
                                        margin: "0.5rem 0 0.8rem",
                                        paddingLeft: "1.4rem",
                                      }}
                                    >
                                      {children}
                                    </ol>
                                  ),
                                  li: ({ children }) => (
                                    <li
                                      style={{
                                        marginBottom: "0.35rem",
                                        lineHeight: 1.55,
                                      }}
                                    >
                                      {children}
                                    </li>
                                  ),
                                  strong: ({ children }) => (
                                    <strong style={{ fontWeight: 700 }}>
                                      {children}
                                    </strong>
                                  ),
                                  a: ({ href, children }) => (
                                    <a
                                      href={href}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{
                                        color: "var(--color-primary)",
                                        textDecoration: "underline",
                                      }}
                                    >
                                      {children}
                                    </a>
                                  ),
                                  blockquote: ({ children }) => (
                                    <blockquote
                                      style={{
                                        margin: "0.75rem 0",
                                        padding: "0.5rem 0.75rem",
                                        borderLeft:
                                          "3px solid var(--color-primary)",
                                        background:
                                          "var(--color-bg-overlay)",
                                        borderRadius: "var(--radius-sm)",
                                      }}
                                    >
                                      {children}
                                    </blockquote>
                                  ),
                                }}
                              >
                                {normalizeAssistantMarkdown(msg.content)}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <p
                              style={{
                                margin: 0,
                              }}
                            >
                              {
                                msg.content
                              }
                            </p>
                          )}
                        </div>

                        {/* Insufficient Evidence */}

                        {msg.role ===
                          "assistant" &&
                          msg.content
                            .toLowerCase()
                            .includes(
                              "insufficient evidence"
                            ) && (
                            <div
                              style={{
                                marginTop:
                                  "0.5rem",
                                padding:
                                  "0.5rem 0.75rem",
                                background:
                                  "hsla(38, 92%, 50%, 0.1)",
                                borderRadius:
                                  "var(--radius-md)",
                                border:
                                  "1px solid var(--color-accent)",
                                display:
                                  "flex",
                                alignItems:
                                  "center",
                                gap:
                                  "0.5rem",
                                fontSize:
                                  "0.78rem",
                                color:
                                  "var(--color-accent)",
                              }}
                            >
                              <span>
                                ⚠️
                              </span>

                              <span>
                                <strong>
                                  Evidence
                                  Grounding
                                  Notice:
                                </strong>{" "}
                                Official
                                verified
                                documentation
                                was not found
                                for this query
                                in the database.
                              </span>
                            </div>
                          )}

                        {/* Feedback */}

                        {msg.role ===
                          "assistant" && (
                            <div
                              style={{
                                display:
                                  "flex",
                                alignItems:
                                  "center",
                                gap:
                                  "0.4rem",
                                marginTop:
                                  "0.35rem",
                              }}
                            >
                              <button
                                onClick={async () => {
                                  try {
                                    await chatApi.sendFeedback(
                                      msg.id,
                                      {
                                        rating: 1,
                                      }
                                    );
                                  } catch { }
                                }}
                                className="btn-ghost"
                                style={{
                                  fontSize:
                                    "0.72rem",
                                  padding:
                                    "0.15rem 0.4rem",
                                  opacity:
                                    0.7,
                                }}
                              >
                                👍 Helpful
                              </button>

                              <button
                                onClick={async () => {
                                  try {
                                    await chatApi.sendFeedback(
                                      msg.id,
                                      {
                                        rating:
                                          -1,
                                      }
                                    );
                                  } catch { }
                                }}
                                className="btn-ghost"
                                style={{
                                  fontSize:
                                    "0.72rem",
                                  padding:
                                    "0.15rem 0.4rem",
                                  opacity:
                                    0.7,
                                }}
                              >
                                👎 Report Issue
                              </button>
                            </div>
                          )}

                        {/* =================================================
                            Rich Citations
                            ================================================= */}

                        {msg.role ===
                          "assistant" &&
                          Array.isArray(
                            msg.cited_sources
                          ) &&
                          msg.cited_sources
                            .length >
                          0 && (
                            <div
                              style={{
                                marginTop:
                                  "0.75rem",
                              }}
                            >
                              <p
                                style={{
                                  fontSize:
                                    "0.75rem",
                                  fontWeight:
                                    600,
                                  color:
                                    "var(--color-text-muted)",
                                  marginBottom:
                                    "0.4rem",
                                  textTransform:
                                    "uppercase",
                                  letterSpacing:
                                    "0.05em",
                                }}
                              >
                                Official
                                Evidence &
                                Citations
                              </p>

                              <div
                                style={{
                                  display:
                                    "grid",
                                  gridTemplateColumns:
                                    "repeat(auto-fill, minmax(220px, 1fr))",
                                  gap:
                                    "0.5rem",
                                }}
                              >
                                {msg.cited_sources.map(
                                  (
                                    cite,
                                    index
                                  ) => {
                                    const citationNumber =
                                      getCitationNumber(
                                        cite,
                                        index
                                      );

                                    const citationKey =
                                      getCitationKey(
                                        cite,
                                        index,
                                        `message-${msg.id}`
                                      );

                                    const title =
                                      getCitationTitle(
                                        cite
                                      );

                                    const page =
                                      getCitationPage(
                                        cite
                                      );

                                    const section =
                                      getCitationSection(
                                        cite
                                      );

                                    return (
                                      <div
                                        key={
                                          citationKey
                                        }
                                        onClick={() =>
                                          setSelectedCitation(
                                            cite
                                          )
                                        }
                                        className="card"
                                        style={{
                                          border:
                                            "1px solid var(--color-border)",
                                          padding:
                                            "0.6rem 0.75rem",
                                          cursor:
                                            "pointer",
                                          borderRadius:
                                            "var(--radius-md)",
                                          background:
                                            "var(--color-bg-overlay)",
                                          transition:
                                            "all 0.15s ease",
                                        }}
                                        onMouseEnter={(
                                          e
                                        ) => {
                                          e.currentTarget.style.borderColor =
                                            "var(--color-primary)";
                                        }}
                                        onMouseLeave={(
                                          e
                                        ) => {
                                          e.currentTarget.style.borderColor =
                                            "var(--color-border)";
                                        }}
                                      >
                                        <div
                                          style={{
                                            display:
                                              "flex",
                                            alignItems:
                                              "center",
                                            justifyContent:
                                              "space-between",
                                            marginBottom:
                                              "0.25rem",
                                          }}
                                        >
                                          <span
                                            style={{
                                              fontWeight:
                                                600,
                                              fontSize:
                                                "0.8rem",
                                              color:
                                                "var(--color-primary)",
                                            }}
                                          >
                                            [
                                            {
                                              citationNumber
                                            }
                                            ]{" "}
                                            {
                                              title
                                            }
                                          </span>
                                        </div>

                                        <div
                                          style={{
                                            fontSize:
                                              "0.75rem",
                                            color:
                                              "var(--color-text-secondary)",
                                            display:
                                              "flex",
                                            gap:
                                              "0.35rem",
                                            flexWrap:
                                              "wrap",
                                            marginBottom:
                                              "0.3rem",
                                          }}
                                        >
                                          {page && (
                                            <span>
                                              Page{" "}
                                              {
                                                page
                                              }
                                            </span>
                                          )}

                                          {page &&
                                            section && (
                                              <span>
                                                •
                                              </span>
                                            )}

                                          {section && (
                                            <span>
                                              {
                                                section
                                              }
                                            </span>
                                          )}
                                        </div>

                                        <div
                                          style={{
                                            display:
                                              "flex",
                                            justifyContent:
                                              "space-between",
                                            alignItems:
                                              "center",
                                            borderTop:
                                              "1px solid hsla(0,0%,100%,0.06)",
                                            paddingTop:
                                              "0.3rem",
                                          }}
                                        >
                                          {(
                                            cite as any
                                          )?.source_url ? (
                                            <a
                                              href={
                                                (
                                                  cite as any
                                                )
                                                  .source_url
                                              }
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              onClick={(
                                                e
                                              ) =>
                                                e.stopPropagation()
                                              }
                                              style={{
                                                fontSize:
                                                  "0.72rem",
                                                color:
                                                  "var(--color-primary)",
                                                textDecoration:
                                                  "underline",
                                              }}
                                            >
                                              View Source
                                              ↗
                                            </a>
                                          ) : (
                                            <span
                                              style={{
                                                fontSize:
                                                  "0.72rem",
                                                color:
                                                  "var(--color-text-muted)",
                                              }}
                                            >
                                              Official
                                              Guideline
                                            </span>
                                          )}

                                          {(
                                            cite as any
                                          )
                                            ?.document_version && (
                                              <span
                                                style={{
                                                  fontSize:
                                                    "0.7rem",
                                                  color:
                                                    "var(--color-text-muted)",
                                                }}
                                              >
                                                v
                                                {
                                                  (
                                                    cite as any
                                                  )
                                                    .document_version
                                                }
                                              </span>
                                            )}
                                        </div>
                                      </div>
                                    );
                                  }
                                )}
                              </div>
                            </div>
                          )}

                        {/* Metadata */}

                        {msg.role ===
                          "assistant" &&
                          msg.confidence_score !=
                          null && (
                            <div
                              style={{
                                marginTop:
                                  "0.4rem",
                                display:
                                  "flex",
                                gap:
                                  "0.75rem",
                              }}
                            >
                              <span
                                style={{
                                  fontSize:
                                    "0.7rem",
                                  color:
                                    "var(--color-text-muted)",
                                }}
                              >
                                Confidence:{" "}
                                {(
                                  msg.confidence_score *
                                  100
                                ).toFixed(
                                  0
                                )}
                                %
                              </span>

                              {msg.latency_ms && (
                                <span
                                  style={{
                                    fontSize:
                                      "0.7rem",
                                    color:
                                      "var(--color-text-muted)",
                                  }}
                                >
                                  {
                                    msg.latency_ms
                                  }
                                  ms
                                </span>
                              )}
                            </div>
                          )}
                      </div>
                    </motion.div>
                  )
                )}
              </AnimatePresence>

              {/* =========================================================
                  Streaming Response
                  ========================================================= */}

              {streaming.isStreaming && (
                <motion.div
                  initial={{
                    opacity: 0,
                    y: 10,
                  }}
                  animate={{
                    opacity: 1,
                    y: 0,
                  }}
                  style={{
                    display:
                      "flex",
                    gap:
                      "0.75rem",
                    marginBottom:
                      "1.5rem",
                    alignItems:
                      "flex-start",
                  }}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius:
                        "50%",
                      background:
                        "var(--color-bg-overlay)",
                      display:
                        "flex",
                      alignItems:
                        "center",
                      justifyContent:
                        "center",
                      fontSize:
                        "0.85rem",
                      flexShrink: 0,
                      border:
                        "1px solid var(--color-border)",
                    }}
                  >
                    🤖
                  </div>

                  <div
                    style={{
                      maxWidth:
                        "75%",
                    }}
                  >
                    <div
                      style={{
                        padding:
                          "0.875rem 1rem",
                        borderRadius:
                          "var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg)",
                        background:
                          "var(--color-bg-elevated)",
                        border:
                          "1px solid var(--color-border)",
                        fontSize:
                          "0.9rem",
                        lineHeight:
                          1.65,
                      }}
                    >
                      {streaming.streamingStage && (
                        <p
                          style={{
                            color:
                              "var(--color-primary)",
                            fontSize:
                              "0.8rem",
                            margin:
                              "0 0 0.5rem",
                            display:
                              "flex",
                            alignItems:
                              "center",
                            gap:
                              "0.5rem",
                          }}
                        >
                          <span
                            className="spinner"
                            style={{
                              width: 12,
                              height: 12,
                            }}
                          />

                          {typeof streaming.streamingStage ===
                            "string"
                            ? streaming.streamingStage
                            : (
                              streaming.streamingStage as any
                            )
                              ?.message ||
                            "Processing..."}
                        </p>
                      )}

                      <div
                        className="markdown-body"
                        style={{
                          whiteSpace: "normal",
                          wordBreak: "break-word",
                        }}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {normalizeAssistantMarkdown(
                            streaming.streamingText
                          )}
                        </ReactMarkdown>
                      </div>
                    </div>

                    {/* Live Streaming Citations */}

                    {Array.isArray(
                      streaming.streamingCitations
                    ) &&
                      streaming
                        .streamingCitations
                        .length >
                      0 && (
                        <div
                          style={{
                            marginTop:
                              "0.75rem",
                          }}
                        >
                          <p
                            style={{
                              fontSize:
                                "0.75rem",
                              fontWeight:
                                600,
                              color:
                                "var(--color-text-muted)",
                              marginBottom:
                                "0.4rem",
                              textTransform:
                                "uppercase",
                              letterSpacing:
                                "0.05em",
                            }}
                          >
                            Identified Sources
                          </p>

                          <div
                            style={{
                              display:
                                "grid",
                              gridTemplateColumns:
                                "repeat(auto-fill, minmax(200px, 1fr))",
                              gap:
                                "0.5rem",
                            }}
                          >
                            {streaming.streamingCitations.map(
                              (
                                cite,
                                index
                              ) => {
                                const citationNumber =
                                  getCitationNumber(
                                    cite,
                                    index
                                  );

                                const citationKey =
                                  getCitationKey(
                                    cite,
                                    index,
                                    "streaming"
                                  );

                                const title =
                                  getCitationTitle(
                                    cite
                                  );

                                const page =
                                  getCitationPage(
                                    cite
                                  );

                                const section =
                                  getCitationSection(
                                    cite
                                  );

                                return (
                                  <div
                                    key={
                                      citationKey
                                    }
                                    onClick={() =>
                                      setSelectedCitation(
                                        cite
                                      )
                                    }
                                    className="card"
                                    style={{
                                      border:
                                        "1px solid var(--color-border)",
                                      padding:
                                        "0.5rem 0.75rem",
                                      cursor:
                                        "pointer",
                                      borderRadius:
                                        "var(--radius-md)",
                                      background:
                                        "var(--color-bg-overlay)",
                                    }}
                                  >
                                    <span
                                      style={{
                                        fontWeight:
                                          600,
                                        fontSize:
                                          "0.78rem",
                                        color:
                                          "var(--color-primary)",
                                      }}
                                    >
                                      [
                                      {
                                        citationNumber
                                      }
                                      ]{" "}
                                      {title}
                                    </span>

                                    <div
                                      style={{
                                        fontSize:
                                          "0.72rem",
                                        color:
                                          "var(--color-text-secondary)",
                                        marginTop:
                                          "0.2rem",
                                      }}
                                    >
                                      {page &&
                                        `Page ${page}`}

                                      {page &&
                                        section &&
                                        " • "}

                                      {section}
                                    </div>
                                  </div>
                                );
                              }
                            )}
                          </div>
                        </div>
                      )}
                  </div>
                </motion.div>
              )}

              <div
                ref={messagesEndRef}
              />
            </div>
          )}
        </div>

        {/* =====================================================
            Input Bar
            ===================================================== */}

        <div
          style={{
            padding:
              "1rem 1.5rem 1.5rem",
            borderTop:
              "1px solid var(--color-border)",
            background:
              "var(--color-bg-surface)",
          }}
        >
          <div
            style={{
              maxWidth:
                "800px",
              margin:
                "0 auto",
              display:
                "flex",
              gap:
                "0.75rem",
              alignItems:
                "flex-end",
              background:
                "var(--color-bg-overlay)",
              border:
                "1px solid var(--color-border)",
              borderRadius:
                "var(--radius-xl)",
              padding:
                "0.5rem 0.75rem",
            }}
          >
            <textarea
              ref={inputRef}
              value={
                inputValue
              }
              onChange={(e) =>
                setInputValue(
                  e.target.value
                )
              }
              onKeyDown={
                handleKeyDown
              }
              placeholder="Ask about scheme eligibility, benefits, application process, required documents..."
              rows={1}
              style={{
                flex: 1,
                background:
                  "transparent",
                border: "none",
                outline:
                  "none",
                color:
                  "var(--color-text-primary)",
                fontSize:
                  "0.9rem",
                resize:
                  "none",
                lineHeight:
                  1.5,
                maxHeight:
                  "120px",
                padding:
                  "0.35rem 0.25rem",
              }}
              onInput={(e) => {
                const textarea =
                  e.target as HTMLTextAreaElement;

                textarea.style.height =
                  "auto";

                textarea.style.height =
                  Math.min(
                    textarea.scrollHeight,
                    120
                  ) + "px";
              }}
            />

            <button
              onClick={() =>
                sendMessage(
                  inputValue
                )
              }
              disabled={
                !inputValue.trim() ||
                streaming.isStreaming
              }
              className="btn-primary"
              style={{
                padding:
                  "0.6rem 1rem",
                flexShrink: 0,
                alignSelf:
                  "flex-end",
              }}
            >
              {streaming.isStreaming ? (
                <div
                  className="spinner"
                  style={{
                    width: 16,
                    height: 16,
                  }}
                />
              ) : (
                "→"
              )}
            </button>
          </div>

          <p
            style={{
              textAlign:
                "center",
              fontSize:
                "0.72rem",
              color:
                "var(--color-text-muted)",
              marginTop:
                "0.5rem",
            }}
          >
            Answers are sourced
            strictly from official
            government documents with
            verifiable citations.
          </p>
        </div>
      </div>

      {/* =====================================================
          Citation Modal
          ===================================================== */}

      <AnimatePresence>
        {selectedCitation && (
          <motion.div
            initial={{
              opacity: 0,
            }}
            animate={{
              opacity: 1,
            }}
            exit={{
              opacity: 0,
            }}
            onClick={() =>
              setSelectedCitation(
                null
              )
            }
            style={{
              position:
                "fixed",
              inset: 0,
              background:
                "hsla(222, 47%, 5%, 0.85)",
              display:
                "flex",
              alignItems:
                "center",
              justifyContent:
                "center",
              zIndex: 100,
              padding:
                "1.5rem",
              backdropFilter:
                "blur(4px)",
            }}
          >
            <motion.div
              initial={{
                opacity: 0,
                scale: 0.95,
                y: 10,
              }}
              animate={{
                opacity: 1,
                scale: 1,
                y: 0,
              }}
              exit={{
                opacity: 0,
                scale: 0.95,
              }}
              onClick={(e) =>
                e.stopPropagation()
              }
              className="card-elevated"
              style={{
                maxWidth:
                  "620px",
                width:
                  "100%",
                borderRadius:
                  "var(--radius-xl)",
                border:
                  "1px solid var(--color-border)",
              }}
            >
              <div
                style={{
                  display:
                    "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "flex-start",
                  marginBottom:
                    "1rem",
                }}
              >
                <div>
                  <span
                    className="badge badge-primary"
                    style={{
                      marginBottom:
                        "0.4rem",
                    }}
                  >
                    Source [
                    {(selectedCitation as any)
                      ?.citation_number ||
                      "1"}
                    ]
                  </span>

                  <h3
                    style={{
                      fontSize:
                        "1.05rem",
                      fontWeight:
                        700,
                      margin: 0,
                      color:
                        "var(--color-text-primary)",
                    }}
                  >
                    {getCitationTitle(
                      selectedCitation
                    )}
                  </h3>

                  <p
                    style={{
                      color:
                        "var(--color-text-secondary)",
                      fontSize:
                        "0.82rem",
                      marginTop:
                        "0.25rem",
                    }}
                  >
                    {(selectedCitation as any)
                      ?.document_name ||
                      (
                        selectedCitation as any
                      )
                        ?.document_title ||
                      ""}
                  </p>
                </div>

                <button
                  onClick={() =>
                    setSelectedCitation(
                      null
                    )
                  }
                  className="btn-ghost"
                  style={{
                    fontSize:
                      "1.1rem",
                  }}
                >
                  ✕
                </button>
              </div>

              {/* Badges */}

              <div
                style={{
                  display:
                    "flex",
                  gap:
                    "0.5rem",
                  marginBottom:
                    "1rem",
                  flexWrap:
                    "wrap",
                }}
              >
                {getCitationPage(
                  selectedCitation
                ) && (
                    <span className="badge badge-primary">
                      Page{" "}
                      {getCitationPage(
                        selectedCitation
                      )}
                    </span>
                  )}

                {getCitationSection(
                  selectedCitation
                ) && (
                    <span className="badge badge-accent">
                      {getCitationSection(
                        selectedCitation
                      )}
                    </span>
                  )}

                {(selectedCitation as any)
                  ?.document_version && (
                    <span
                      className="badge"
                      style={{
                        background:
                          "var(--color-bg-overlay)",
                        border:
                          "1px solid var(--color-border)",
                      }}
                    >
                      Version{" "}
                      {
                        (
                          selectedCitation as any
                        )
                          .document_version
                      }
                    </span>
                  )}

                {(selectedCitation as any)
                  ?.ministry && (
                    <span className="badge badge-secondary">
                      {
                        (
                          selectedCitation as any
                        )
                          .ministry
                      }
                    </span>
                  )}
              </div>

              {/* Excerpt */}

              <div
                style={{
                  marginBottom:
                    "1rem",
                }}
              >
                <p
                  style={{
                    fontSize:
                      "0.75rem",
                    fontWeight:
                      600,
                    color:
                      "var(--color-text-muted)",
                    marginBottom:
                      "0.35rem",
                    textTransform:
                      "uppercase",
                  }}
                >
                  Verified Document
                  Excerpt
                </p>

                <div
                  style={{
                    background:
                      "var(--color-bg-overlay)",
                    borderRadius:
                      "var(--radius-md)",
                    padding:
                      "1rem",
                    fontSize:
                      "0.85rem",
                    lineHeight:
                      1.7,
                    color:
                      "var(--color-text-secondary)",
                    borderLeft:
                      "3px solid var(--color-primary)",
                  }}
                >
                  "
                  {(selectedCitation as any)
                    ?.snippet ||
                    "Official clause text retrieved from scheme documentation."}
                  "
                </div>
              </div>

              {/* Actions */}

              <div
                style={{
                  display:
                    "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "center",
                  paddingTop:
                    "0.75rem",
                  borderTop:
                    "1px solid var(--color-border)",
                }}
              >
                {(selectedCitation as any)
                  ?.source_url ? (
                  <a
                    href={
                      (
                        selectedCitation as any
                      )
                        .source_url
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary"
                    style={{
                      fontSize:
                        "0.8rem",
                      padding:
                        "0.5rem 1rem",
                      textDecoration:
                        "none",
                    }}
                  >
                    View Official
                    Source ↗
                  </a>
                ) : (
                  <span
                    style={{
                      fontSize:
                        "0.78rem",
                      color:
                        "var(--color-text-muted)",
                    }}
                  >
                    Official Central /
                    State Gazette Record
                  </span>
                )}

                <button
                  onClick={() =>
                    setSelectedCitation(
                      null
                    )
                  }
                  className="btn-secondary"
                  style={{
                    fontSize:
                      "0.8rem",
                  }}
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}