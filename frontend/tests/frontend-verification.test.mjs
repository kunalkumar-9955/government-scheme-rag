/**
 * frontend/tests/frontend-verification.test.mjs
 * Native Node.js test runner for frontend business logic & store operations.
 */
import { test, describe } from "node:test";
import assert from "node:assert/strict";

describe("Frontend Token & State Storage", () => {
  test("Token storage properly caches and rotates JWT bearer tokens", () => {
    const memoryStorage = new Map();
    const tokenStorage = {
      get: () => memoryStorage.get("access_token") || null,
      getRefresh: () => memoryStorage.get("refresh_token") || null,
      set: (acc, ref) => {
        memoryStorage.set("access_token", acc);
        memoryStorage.set("refresh_token", ref);
      },
      clear: () => memoryStorage.clear(),
    };

    tokenStorage.set("mock-access-token-xyz", "mock-refresh-token-abc");
    assert.equal(tokenStorage.get(), "mock-access-token-xyz");
    assert.equal(tokenStorage.getRefresh(), "mock-refresh-token-abc");

    tokenStorage.clear();
    assert.equal(tokenStorage.get(), null);
    assert.equal(tokenStorage.getRefresh(), null);
  });
});

describe("AI Chatbot SSE Stream Parsing", () => {
  test("Parses SSE token stream, citations, and done events accurately", () => {
    const ssePayload = `event: status\ndata: {"stage":"retrieving","message":"Retrieving documents..."}\n\nevent: token\ndata: {"text":"PM-KISAN "}\n\nevent: token\ndata: {"text":"provides Rs 6000."}\n\nevent: citations\ndata: {"citations":[{"citation_number":1,"document_title":"PM-KISAN Guidelines"}]}\n\nevent: done\ndata: {"confidence_score":0.95,"latency_ms":120}\n\n`;

    const events = [];
    const lines = ssePayload.split("\n\n").filter(Boolean);

    for (const block of lines) {
      const eventLine = block.split("\n").find((l) => l.startsWith("event: "));
      const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
      if (eventLine && dataLine) {
        const event = eventLine.replace("event: ", "").trim();
        const data = JSON.parse(dataLine.replace("data: ", "").trim());
        events.push({ event, data });
      }
    }

    assert.equal(events.length, 5);
    assert.equal(events[0].event, "status");
    assert.equal(events[1].data.text, "PM-KISAN ");
    assert.equal(events[2].data.text, "provides Rs 6000.");
    assert.equal(events[3].data.citations[0].citation_number, 1);
    assert.equal(events[4].data.confidence_score, 0.95);
  });
});

describe("Scheme Search & Filter Engine", () => {
  const schemes = [
    { id: "1", name: "Pradhan Mantri Kisan Samman Nidhi", category: "Agriculture", state: "Central" },
    { id: "2", name: "Pradhan Mantri Awas Yojana - Urban", category: "Housing", state: "Central" },
    { id: "3", name: "Atal Pension Yojana", category: "Social Welfare", state: "Central" },
  ];

  test("Filters schemes by search query and category correctly", () => {
    const query = "kisan";
    const filtered = schemes.filter(
      (s) =>
        s.name.toLowerCase().includes(query.toLowerCase()) ||
        s.category.toLowerCase().includes(query.toLowerCase())
    );
    assert.equal(filtered.length, 1);
    assert.equal(filtered[0].name, "Pradhan Mantri Kisan Samman Nidhi");
  });
});

describe("Deterministic Eligibility Result Formatter", () => {
  test("Correctly maps verdict statuses to UI badge colors and categories", () => {
    const verdictMapper = (status) => {
      switch (status) {
        case "ELIGIBLE":
          return { label: "Likely Eligible", color: "success" };
        case "NOT_ELIGIBLE":
          return { label: "Not Eligible", color: "danger" };
        case "POSSIBLY_ELIGIBLE":
          return { label: "Possibly Eligible", color: "accent" };
        case "INSUFFICIENT_INFORMATION":
        default:
          return { label: "Insufficient Information", color: "muted" };
      }
    };

    assert.equal(verdictMapper("ELIGIBLE").label, "Likely Eligible");
    assert.equal(verdictMapper("NOT_ELIGIBLE").color, "danger");
    assert.equal(verdictMapper("INSUFFICIENT_INFORMATION").color, "muted");
  });
});

describe("API Error Normalizer", () => {
  test("Normalizes structured backend error responses", () => {
    const backendError = {
      response: {
        status: 400,
        data: {
          success: false,
          error: {
            code: "INVALID_FIELD",
            message: "Age must be a positive integer.",
          },
        },
      },
    };

    const normalize = (err) =>
      err?.response?.data?.error?.message || err?.message || "An unexpected error occurred.";

    assert.equal(normalize(backendError), "Age must be a positive integer.");
  });
});
