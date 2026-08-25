// src/store/chatStore.ts — Zustand chat state

import { create } from "zustand";
import type { Conversation, Message, Citation, SSEDoneEvent } from "@/types";

interface StreamingState {
  isStreaming: boolean;
  streamingText: string;
  streamingCitations: Citation[];
  streamingStage: string;
}

interface ChatState {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  messages: Message[];
  streaming: StreamingState;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (id: string) => void;
  setActiveConversation: (conversation: Conversation | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (data: Partial<Message>) => void;
  appendStreamToken: (text: string) => void;
  setStreamingCitations: (citations: Citation[]) => void;
  setStreamingStage: (stage: string) => void;
  startStreaming: () => void;
  stopStreaming: (doneData: SSEDoneEvent) => void;
  resetStreaming: () => void;
  setLoadingConversations: (loading: boolean) => void;
  setLoadingMessages: (loading: boolean) => void;
}

const defaultStreaming: StreamingState = {
  isStreaming: false,
  streamingText: "",
  streamingCitations: [],
  streamingStage: "",
};

export const useChatStore = create<ChatState>()((set, get) => ({
  conversations: [],
  activeConversation: null,
  messages: [],
  streaming: defaultStreaming,
  isLoadingConversations: false,
  isLoadingMessages: false,

  setConversations: (conversations) => set({ conversations }),
  addConversation: (conversation) =>
    set((state) => ({ conversations: [conversation, ...state.conversations] })),
  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      activeConversation: state.activeConversation?.id === id ? null : state.activeConversation,
    })),
  setActiveConversation: (conversation) => set({ activeConversation: conversation, messages: [] }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (data) =>
    set((state) => ({
      messages: state.messages.map((m, i) =>
        i === state.messages.length - 1 ? { ...m, ...data } : m
      ),
    })),

  appendStreamToken: (text) =>
    set((state) => ({
      streaming: { ...state.streaming, streamingText: state.streaming.streamingText + text },
    })),
  setStreamingCitations: (citations) =>
    set((state) => ({ streaming: { ...state.streaming, streamingCitations: citations } })),
  setStreamingStage: (stage) =>
    set((state) => ({ streaming: { ...state.streaming, streamingStage: stage } })),
  startStreaming: () =>
    set({ streaming: { ...defaultStreaming, isStreaming: true } }),
  stopStreaming: (doneData) =>
    set((state) => ({
      streaming: { ...state.streaming, isStreaming: false },
    })),
  resetStreaming: () => set({ streaming: defaultStreaming }),

  setLoadingConversations: (loading) => set({ isLoadingConversations: loading }),
  setLoadingMessages: (loading) => set({ isLoadingMessages: loading }),
}));
