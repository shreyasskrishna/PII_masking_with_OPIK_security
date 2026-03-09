# OPIK Observability for Privacy-Preserving Customer Support AI

## Complete Instrumentation Guide — From Zero to Production-Ready

---

## Table of Contents

1. [What is OPIK?](#1-what-is-opik)
2. [Why Instrument This Chatbot?](#2-why-instrument-this-chatbot)
3. [Architecture: Observability Layer Design](#3-architecture-observability-layer-design)
4. [Setup & Configuration](#4-setup--configuration)
5. [Core Concepts: Traces, Spans & Transactions](#5-core-concepts-traces-spans--transactions)
6. [Span-by-Span Instrumentation Plan](#6-span-by-span-instrumentation-plan)
7. [Complete Instrumented Code](#7-complete-instrumented-code)
8. [Attributes, Metrics & Metadata Strategy](#8-attributes-metrics--metadata-strategy)
9. [Evaluation Span: Quality Metrics](#9-evaluation-span-quality-metrics)
10. [User Feedback Correlation](#10-user-feedback-correlation)
11. [OPIK Dashboard: What You Can Visualize](#11-opik-dashboard-what-you-can-visualize)
12. [Alerting & Anomaly Detection](#12-alerting--anomaly-detection)
13. [Cost Estimation Model](#13-cost-estimation-model)
14. [Production Best Practices](#14-production-best-practices)
15. [Summary](#15-summary)

---

## 1. What is OPIK?

**OPIK** (by Comet) is an open-source LLM observability platform for tracing, evaluating, and monitoring LLM applications. It provides:

| Capability | Description |
|---|---|
| **Tracing** | Captures the full execution path of every request as a hierarchical tree of spans |
| **Evaluation** | LLM-as-a-Judge metrics, heuristic scoring, and CI/CD integration |
| **Monitoring** | Dashboards for token usage, latency, error rates, and cost tracking |
| **Feedback** | Links user satisfaction (thumbs up/down) directly to specific traces |

> [!IMPORTANT]
> OPIK can be **self-hosted** (Docker/Kubernetes) or used via Comet Cloud. For a privacy-preserving chatbot handling PII, self-hosting is strongly recommended so that trace data stays within your infrastructure.

---

## 2. Why Instrument This Chatbot?

Our chatbot has a multi-step pipeline:

```
User Input → PII Masking → LLM Call (Groq) → Response Unmasking → Final Output
```

Without observability, we are **blind** to:

- **Where latency hides** — Is the Groq API slow, or is regex PII masking the bottleneck?
- **Quality degradation** — Are model responses getting worse after a prompt change?
- **Cost overruns** — How many tokens are we spending per conversation?
- **Error patterns** — Are API timeouts spiking at certain hours?
- **PII leakage risk** — Did the masker miss anything? Did the unmasker fail?

OPIK gives us **full-stack visibility** across all of these dimensions.

---

## 3. Architecture: Observability Layer Design

Below is how OPIK sits inside our existing architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OPIK TRACE (Transaction)                    │
│  trace_id: "txn-abc123"                                             │
│  session_id, user_id, channel, intent                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ SPAN 1       │  │ SPAN 2       │  │ SPAN 3                   │  │
│  │ Input        │  │ Input        │  │ Prompt                   │  │
│  │ Reception    │  │ Validation   │  │ Construction             │  │
│  │              │  │              │  │                          │  │
│  │ • raw text   │  │ • length chk │  │ • system_prompt version  │  │
│  │ • channel    │  │ • language   │  │ • masked user message    │  │
│  │ • timestamp  │  │ • safety     │  │ • conversation history   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐ │
│  │ SPAN 4       │  │ SPAN 5                                      │ │
│  │ PII Masking  │  │ LLM Invocation (type: "llm")                │ │
│  │              │  │                                              │ │
│  │ • pii_count  │  │ • model: llama-3.3-70b-versatile            │ │
│  │ • pii_types  │  │ • temperature: 0.7                          │ │
│  │ • latency_ms │  │ • max_tokens: 1024                          │ │
│  │              │  │ • provider: groq                             │ │
│  │              │  │ • prompt_tokens, completion_tokens           │ │
│  │              │  │ • latency_ms, error_state, retries           │ │
│  └──────────────┘  └──────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ SPAN 6       │  │ SPAN 7       │  │ SPAN 8                   │  │
│  │ Response     │  │ Final        │  │ Evaluation               │  │
│  │ Post-Process │  │ Delivery     │  │ (Quality Metrics)        │  │
│  │              │  │              │  │                          │  │
│  │ • unmasking  │  │ • total_ms   │  │ • relevance_score        │  │
│  │ • unmask_ok  │  │ • response   │  │ • hallucination_flag     │  │
│  │ • latency_ms │  │ • status     │  │ • completeness           │  │
│  │              │  │              │  │ • safety_score            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ FEEDBACK SCORE (attached post-hoc)                           │   │
│  │ • user_rating: 1-5 | thumbs_up/thumbs_down                  │   │
│  │ • correlated to trace_id                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Setup & Configuration

### 4.1 Install the SDK

```bash
pip install opik
```

Add to your `requirements.txt`:

```
opik>=1.0.0
```

### 4.2 Environment Variables

Add these to your `.env` file:

```env
# --- OPIK Configuration ---
OPIK_API_KEY=your_opik_api_key_here
OPIK_WORKSPACE=your_workspace_name
OPIK_PROJECT_NAME=customer-support-ai

# For self-hosted OPIK (recommended for PII-sensitive apps):
# OPIK_URL_OVERRIDE=http://localhost:5173/api

# For Comet Cloud:
OPIK_URL_OVERRIDE=https://www.comet.com/opik/api
```

### 4.3 Initialize OPIK in Your Application

```python
import opik

# OPIK reads OPIK_API_KEY, OPIK_WORKSPACE, and OPIK_URL_OVERRIDE
# from the environment automatically when using decorators or context managers.
# No explicit client initialization is needed for the @track decorator approach.
```

---

## 5. Core Concepts: Traces, Spans & Transactions

Understanding OPIK's data model is essential before instrumenting:

| Concept | Mapping to Our Chatbot | OPIK Equivalent |
|---|---|---|
| **Transaction** | One complete user request → response cycle | **Trace** |
| **Step** | Individual operation (e.g., PII masking, LLM call) | **Span** |
| **Thread** | An entire user conversation (multi-turn) | **Thread** (via `thread_id`) |
| **Feedback** | User thumbs up/down after a response | **Feedback Score** |

### Hierarchy

```
Thread (session_id)
  └── Trace (one request lifecycle)
        ├── Span: input_reception
        ├── Span: input_validation
        ├── Span: intent_detection
        ├── Span: pii_masking
        ├── Span: prompt_construction
        ├── Span: llm_invocation        ← type: "llm"
        ├── Span: response_postprocessing
        ├── Span: evaluation             ← quality metrics
        └── Span: response_delivery
```

> [!NOTE]
> Every span automatically records `start_time` and `end_time`. OPIK calculates `duration` from these, giving you per-span latency for free.

---

## 6. Span-by-Span Instrumentation Plan

Below is a detailed breakdown of **each span** we will create, what it captures, and why.

### Span 1: `input_reception`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Raw user text |
| **Output** | Acknowledged input |
| **Metadata** | `session_id`, `user_id`, `channel` (api/cli/streamlit), `timestamp` |
| **Purpose** | Entry point — captures WHERE the request came from and WHO sent it |

### Span 2: `input_validation`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Raw user text |
| **Output** | `{ "is_valid": true/false, "reason": "..." }` |
| **Metadata** | `input_length`, `detected_language`, `contains_profanity` |
| **Purpose** | Gate — reject empty, too-long, or abusive inputs before wasting LLM tokens |

### Span 3: `intent_detection`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Validated user text |
| **Output** | `{ "intent": "account_recovery", "confidence": 0.92 }` |
| **Metadata** | `intent_model_version`, `fallback_used` |
| **Purpose** | Classify user intent for routing, analytics, and prompt selection |

### Span 4: `pii_masking`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Raw user text |
| **Output** | Masked text (e.g., "My email is \<EMAIL_1\>") |
| **Metadata** | `pii_types_found: ["EMAIL", "PHONE"]`, `pii_count: 2`, `encryption_method: "fernet"` |
| **Purpose** | Critical security span — proves PII was stripped before LLM call |

### Span 5: `prompt_construction`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Masked text + conversation history length |
| **Output** | Full prompt messages array (system + history + user) |
| **Metadata** | `prompt_version: "v2.1"`, `system_prompt_hash`, `history_turns_included` |
| **Purpose** | Track which prompt version produced which results — essential for A/B testing |

### Span 6: `llm_invocation`
| Field | Value |
|---|---|
| **Type** | `llm` ← **Special OPIK type** |
| **Input** | Prompt messages |
| **Output** | Raw LLM response text |
| **Model** | `llama-3.3-70b-versatile` |
| **Provider** | `groq` |
| **Usage** | `{ "prompt_tokens": N, "completion_tokens": M, "total_tokens": N+M }` |
| **Metadata** | `temperature: 0.7`, `max_tokens: 1024`, `timeout_seconds: 30`, `retries: 0`, `error_state: null`, `http_status_code: 200`, `estimated_cost_usd: 0.0012` |
| **Purpose** | **The most important span.** Records everything about the model call — latency, tokens, cost, errors, configuration. |

> [!IMPORTANT]
> Use `type="llm"` for this span. OPIK treats LLM spans specially — they appear in dedicated model performance dashboards and support token usage tracking natively.

### Span 7: `response_postprocessing`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Masked LLM response |
| **Output** | Unmasked final response |
| **Metadata** | `unmask_success: true`, `tokens_replaced: 2`, `unmask_errors: []` |
| **Purpose** | Verify PII was correctly restored — if unmasking fails, the user gets broken output |

### Span 8: `evaluation`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | User query + LLM response |
| **Output** | `{ "relevance": 0.87, "hallucination_flag": false, "completeness": 0.91, "safety": 0.99 }` |
| **Metadata** | `evaluator_type: "heuristic"`, `evaluator_version: "v1.0"` |
| **Purpose** | Automated quality assessment — every response gets scored |

### Span 9: `response_delivery`
| Field | Value |
|---|---|
| **Type** | `general` |
| **Input** | Final response |
| **Output** | Delivery confirmation |
| **Metadata** | `total_latency_ms`, `status: "delivered"`, `delivery_channel` |
| **Purpose** | Closing span — records total end-to-end time and delivery status |

---

## 7. Complete Instrumented Code

Below is the **fully instrumented** version of `process_message` using OPIK context managers. This replaces the current `CustomerSupportBot.process_message` method.

### 7.1 Approach A: Context Managers (Recommended for Maximum Control)

```python
import opik
import time
import uuid
import hashlib
from typing import Dict

class CustomerSupportBot:
    """Privacy-preserving customer support bot with OPIK observability."""

    def __init__(self, use_groq: bool = True):
        from db_manager import DBManager
        self.db_manager = DBManager()
        self.masker = PIIMasker()
        self.use_groq = use_groq
        self.groq_client = None
        self.conversation_history = []
        self.session_mapping: Dict[str, str] = {}
        self.session_id = str(uuid.uuid4())  # Unique per session

        if use_groq:
            try:
                self.groq_client = GroqClient()
            except ValueError as e:
                print(f"⚠️  {e}")
                print("Falling back to simulated responses.\n")
                self.use_groq = False

    def process_message(self, user_input: str, user_id: str = "anonymous",
                        channel: str = "api") -> Dict:
        """
        Complete privacy-preserving message processing pipeline
        with full OPIK observability.
        """
        trace_start = time.perf_counter()
        request_id = str(uuid.uuid4())

        # ════════════════════════════════════════════════════════════
        # OPIK TRACE: One trace = one complete request lifecycle
        # ════════════════════════════════════════════════════════════
        with opik.start_as_current_trace(
            "chatbot-request",
            project_name="customer-support-ai"
        ) as trace:
            trace.input = {"user_message": user_input}
            trace.tags = ["customer-support", channel]
            trace.metadata = {
                "session_id": self.session_id,
                "user_id": user_id,
                "channel": channel,
                "request_id": request_id,
            }

            # ─── SPAN 1: Input Reception ───────────────────────────
            with opik.start_as_current_span(
                "input-reception", type="general"
            ) as span:
                span.input = {"raw_text": user_input}
                span.metadata = {
                    "session_id": self.session_id,
                    "user_id": user_id,
                    "channel": channel,
                    "input_length": len(user_input),
                }
                span.output = {"status": "received"}

            # ─── SPAN 2: Input Validation ──────────────────────────
            with opik.start_as_current_span(
                "input-validation", type="general"
            ) as span:
                span.input = {"raw_text": user_input}
                is_valid = True
                validation_reason = "ok"

                if not user_input or not user_input.strip():
                    is_valid = False
                    validation_reason = "empty_input"
                elif len(user_input) > 10000:
                    is_valid = False
                    validation_reason = "input_too_long"

                span.output = {
                    "is_valid": is_valid,
                    "reason": validation_reason,
                }
                span.metadata = {
                    "input_length": len(user_input),
                    "detected_language": "en",  # plug in langdetect here
                }

                if not is_valid:
                    trace.output = {"error": validation_reason}
                    trace.tags.append("validation-failed")
                    return {"response": f"Invalid input: {validation_reason}",
                            "stages": {}}

            # ─── SPAN 3: Intent Detection ──────────────────────────
            with opik.start_as_current_span(
                "intent-detection", type="general"
            ) as span:
                span.input = {"user_text": user_input}
                # Simple keyword-based intent (replace with ML model)
                intent = "general_inquiry"
                msg_lower = user_input.lower()
                if any(kw in msg_lower for kw in ["account", "login", "password"]):
                    intent = "account_recovery"
                elif any(kw in msg_lower for kw in ["payment", "card", "charge", "refund"]):
                    intent = "payment_issue"
                elif any(kw in msg_lower for kw in ["order", "shipping", "delivery"]):
                    intent = "order_inquiry"

                span.output = {"intent": intent, "confidence": 0.85}
                span.metadata = {"intent_method": "keyword_heuristic"}

            # ─── SPAN 4: PII Masking ───────────────────────────────
            with opik.start_as_current_span(
                "pii-masking", type="general"
            ) as span:
                mask_start = time.perf_counter()
                span.input = {"raw_text": user_input}

                masked_input, mapping = self.masker.mask(user_input)
                self.session_mapping.update(mapping)

                mask_latency = (time.perf_counter() - mask_start) * 1000
                pii_types = [k.split("_")[0].strip("<") for k in mapping.keys()]

                span.output = {
                    "masked_text": masked_input,
                    "pii_token_count": len(mapping),
                }
                span.metadata = {
                    "pii_types_found": list(set(pii_types)),
                    "pii_count": len(mapping),
                    "latency_ms": round(mask_latency, 2),
                    "encryption_method": "fernet_aes128",
                }

            # ─── SPAN 5: Prompt Construction ───────────────────────
            with opik.start_as_current_span(
                "prompt-construction", type="general"
            ) as span:
                system_prompt_hash = hashlib.md5(
                    SYSTEM_PROMPT.encode()
                ).hexdigest()[:8]

                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ]
                # Add conversation history if using Groq client
                if self.groq_client:
                    messages += self.groq_client.conversation_history
                messages.append({"role": "user", "content": masked_input})

                span.input = {"masked_user_message": masked_input}
                span.output = {"message_count": len(messages)}
                span.metadata = {
                    "prompt_version": "v1.0",
                    "system_prompt_hash": system_prompt_hash,
                    "history_turns_included": len(messages) - 2,
                }

            # ─── SPAN 6: LLM Invocation ───────────────────────────
            with opik.start_as_current_span(
                "llm-invocation", type="llm"  # ← Special LLM type
            ) as span:
                llm_start = time.perf_counter()
                span.input = {"prompt": masked_input}

                model_name = (self.groq_client.model
                              if self.groq_client else "simulated")

                span.model = model_name
                span.provider = "groq" if self.use_groq else "simulated"

                error_state = None
                retries = 0
                http_status = 200

                try:
                    masked_response = self._call_llm(masked_input)
                except Exception as e:
                    error_state = str(e)
                    masked_response = f"Error: {e}"
                    http_status = 500

                llm_latency = (time.perf_counter() - llm_start) * 1000

                # Estimate token counts (heuristic: ~4 chars per token)
                est_prompt_tokens = len(masked_input) // 4
                est_completion_tokens = len(masked_response) // 4
                est_total_tokens = est_prompt_tokens + est_completion_tokens

                # Cost estimation (Groq Llama-3 pricing example)
                cost_per_input_token = 0.00000059   # $0.59 / 1M tokens
                cost_per_output_token = 0.00000079  # $0.79 / 1M tokens
                estimated_cost = (est_prompt_tokens * cost_per_input_token +
                                  est_completion_tokens * cost_per_output_token)

                span.output = {"response": masked_response}
                span.usage = {
                    "prompt_tokens": est_prompt_tokens,
                    "completion_tokens": est_completion_tokens,
                    "total_tokens": est_total_tokens,
                }
                span.metadata = {
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "timeout_seconds": 30,
                    "retries": retries,
                    "error_state": error_state,
                    "http_status_code": http_status,
                    "latency_ms": round(llm_latency, 2),
                    "estimated_cost_usd": round(estimated_cost, 6),
                }

            # ─── SPAN 7: Response Post-Processing (Unmasking) ──────
            with opik.start_as_current_span(
                "response-postprocessing", type="general"
            ) as span:
                unmask_start = time.perf_counter()
                span.input = {"masked_response": masked_response}

                unmask_errors = []
                try:
                    final_response = self.masker.unmask(
                        masked_response, self.session_mapping
                    )
                    unmask_success = True
                except Exception as e:
                    final_response = masked_response
                    unmask_success = False
                    unmask_errors.append(str(e))

                unmask_latency = (time.perf_counter() - unmask_start) * 1000

                span.output = {
                    "final_response": final_response,
                    "unmask_success": unmask_success,
                }
                span.metadata = {
                    "tokens_replaced": len(self.session_mapping),
                    "unmask_errors": unmask_errors,
                    "latency_ms": round(unmask_latency, 2),
                }

            # ─── SPAN 8: Evaluation (Quality Metrics) ──────────────
            with opik.start_as_current_span(
                "evaluation", type="general"
            ) as span:
                span.input = {
                    "user_query": user_input,
                    "llm_response": final_response,
                }

                # Heuristic quality evaluators
                relevance_score = self._compute_relevance(
                    user_input, final_response
                )
                hallucination_flag = self._check_hallucination(
                    masked_input, masked_response
                )
                completeness_score = self._compute_completeness(
                    final_response
                )
                safety_score = self._compute_safety(final_response)

                span.output = {
                    "relevance_score": relevance_score,
                    "hallucination_flag": hallucination_flag,
                    "completeness_score": completeness_score,
                    "safety_score": safety_score,
                }
                span.metadata = {
                    "evaluator_type": "heuristic",
                    "evaluator_version": "v1.0",
                }

            # ─── SPAN 9: Response Delivery ─────────────────────────
            total_latency = (time.perf_counter() - trace_start) * 1000
            with opik.start_as_current_span(
                "response-delivery", type="general"
            ) as span:
                span.input = {"final_response": final_response}
                span.output = {"status": "delivered"}
                span.metadata = {
                    "total_latency_ms": round(total_latency, 2),
                    "delivery_channel": channel,
                }

            # ─── Close the Trace ───────────────────────────────────
            trace.output = {"response": final_response}
            trace.metadata.update({
                "intent": intent,
                "total_latency_ms": round(total_latency, 2),
                "pii_detected": len(mapping) > 0,
                "model_used": model_name,
                "estimated_cost_usd": round(estimated_cost, 6),
            })

        # Store in conversation history (unchanged)
        self.conversation_history.append({
            "user_raw": user_input,
            "user_masked": masked_input,
            "bot_masked": masked_response,
            "bot_final": final_response,
        })

        # Store in DB (unchanged)
        if hasattr(self, 'db_manager') and self.db_manager and self.db_manager.is_connected():
            self.db_manager.insert_message(
                session_id=self.session_id,
                user_raw=user_input,
                user_masked=masked_input,
                bot_masked=masked_response,
                bot_final=final_response,
                pii_mapping=self.session_mapping
            )

        return {
            "trace_id": request_id,
            "stages": {
                "1_user_input_raw": user_input,
                "2_masked_before_llm": masked_input,
                "3_mapping_store": self.session_mapping.copy(),
                "4_llm_response_masked": masked_response,
                "5_final_output_to_user": final_response,
            },
            "metrics": {
                "total_latency_ms": round(total_latency, 2),
                "llm_latency_ms": round(llm_latency, 2),
                "mask_latency_ms": round(mask_latency, 2),
                "est_tokens": est_total_tokens,
                "estimated_cost_usd": round(estimated_cost, 6),
            },
            "quality": {
                "relevance": relevance_score,
                "hallucination": hallucination_flag,
                "completeness": completeness_score,
                "safety": safety_score,
            },
            "response": final_response,
        }
```

### 7.2 Approach B: `@track` Decorator (Simpler, Less Granular)

For teams that want minimal code changes, OPIK's `@track` decorator auto-instruments functions:

```python
from opik import track

class CustomerSupportBot:

    @track(name="process-message", project_name="customer-support-ai")
    def process_message(self, user_input: str) -> Dict:
        masked_input, mapping = self._mask_pii(user_input)
        response = self._call_llm(masked_input)
        final = self._unmask_response(response, mapping)
        return {"response": final}

    @track(name="pii-masking")
    def _mask_pii(self, text: str):
        return self.masker.mask(text)

    @track(name="llm-call", type="llm")
    def _call_llm(self, masked_message: str) -> str:
        if self.use_groq and self.groq_client:
            return self.groq_client.chat(masked_message)
        return self._simulated_response(masked_message)

    @track(name="unmask-response")
    def _unmask_response(self, text: str, mapping: Dict) -> str:
        return self.masker.unmask(text, self.session_mapping)
```

> [!TIP]
> **When to use which approach:**
> - Use **Context Managers** (Approach A) when you need granular control over metadata, want to attach token usage, cost, and custom metrics fields.
> - Use **`@track` Decorators** (Approach B) for quick instrumentation with automatic input/output capture. Nested `@track` calls create nested spans automatically.

---

## 8. Attributes, Metrics & Metadata Strategy

### 8.1 Trace-Level Attributes (Filterable in OPIK Dashboard)

These go into `trace.metadata` and `trace.tags`:

| Attribute | Type | Example | Purpose |
|---|---|---|---|
| `session_id` | `string` | `"sess-a1b2c3"` | Group traces by conversation |
| `user_id` | `string` | `"user-42"` | Filter by specific user |
| `channel` | `string` | `"api"` / `"streamlit"` / `"cli"` | Filter by entry point |
| `intent` | `string` | `"account_recovery"` | Analyze by intent category |
| `model_used` | `string` | `"llama-3.3-70b"` | Compare model performance |
| `prompt_version` | `string` | `"v2.1"` | A/B test prompt versions |
| `pii_detected` | `boolean` | `true` | Filter PII-heavy requests |
| `total_latency_ms` | `float` | `1423.5` | End-to-end performance |

### 8.2 LLM Span Metrics (Built-in OPIK Support)

These use OPIK's native `span.usage`, `span.model`, and `span.provider` fields:

| Metric | Source | Dashboard Use |
|---|---|---|
| `prompt_tokens` | API response or estimation | Token budget tracking |
| `completion_tokens` | API response or estimation | Cost analysis |
| `model` | `span.model` | Model comparison charts |
| `provider` | `span.provider` | Provider reliability |
| `latency_ms` | `span.metadata` | P50/P95/P99 latency charts |
| `estimated_cost_usd` | Calculated | Cost anomaly alerts |

### 8.3 Custom Operational Metrics

| Metric | Span | Type | Alert Threshold |
|---|---|---|---|
| `mask_latency_ms` | `pii-masking` | `float` | > 100ms |
| `unmask_errors` | `response-postprocessing` | `list` | length > 0 |
| `pii_count` | `pii-masking` | `int` | > 10 (unusual) |
| `retries` | `llm-invocation` | `int` | > 2 |
| `error_state` | `llm-invocation` | `string` | not null |

---

## 9. Evaluation Span: Quality Metrics

The Evaluation span runs **automated quality checks** on every response. Here are the heuristic evaluator implementations:

```python
class CustomerSupportBot:
    # ... (existing code) ...

    def _compute_relevance(self, query: str, response: str) -> float:
        """
        Heuristic relevance scorer.
        Checks keyword overlap between query and response.
        Replace with an LLM-as-a-Judge call for production accuracy.
        """
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & response_words
        return round(min(len(overlap) / max(len(query_words), 1), 1.0), 2)

    def _check_hallucination(self, masked_input: str,
                              masked_response: str) -> bool:
        """
        Heuristic hallucination detector.
        Flags if the response contains PII tokens NOT present in the input.
        """
        import re
        input_tokens = set(re.findall(r'<[A-Z_]+_\d+>', masked_input))
        response_tokens = set(re.findall(r'<[A-Z_]+_\d+>', masked_response))
        # If response references tokens not in input → potential hallucination
        fabricated = response_tokens - input_tokens
        return len(fabricated) > 0

    def _compute_completeness(self, response: str) -> float:
        """
        Heuristic completeness scorer.
        Checks if response has actionable content (not too short/generic).
        """
        if len(response) < 20:
            return 0.2
        elif len(response) < 100:
            return 0.5
        # Check for action words
        action_words = ["help", "assist", "resolve", "send", "update",
                        "check", "verify", "confirm", "contact"]
        found = sum(1 for w in action_words if w in response.lower())
        return round(min(0.5 + (found * 0.1), 1.0), 2)

    def _compute_safety(self, response: str) -> float:
        """
        Heuristic safety scorer.
        Checks for disallowed content patterns.
        """
        unsafe_patterns = [
            r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',     # SSN-like
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+',   # Raw email (should be masked)
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',         # Credit card
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, response):
                return 0.1  # Unsafe — PII leaked into response
        return 0.99
```

> [!CAUTION]
> The heuristic evaluators above are **starting points**. For production, consider upgrading to **LLM-as-a-Judge** evaluators using OPIK's built-in evaluation framework, which uses a secondary LLM to grade response quality with much higher accuracy.

---

## 10. User Feedback Correlation

When a user rates a response (thumbs up/down), we need to attach that feedback to the **same OPIK trace** that produced the response.

### 10.1 Implementation

```python
import opik

def submit_feedback(trace_id: str, rating: int, comment: str = ""):
    """
    Attach user feedback to an OPIK trace.

    Args:
        trace_id: The OPIK trace ID returned during request processing
        rating: 1 (bad) to 5 (excellent), or 0/1 for thumbs down/up
        comment: Optional free-text feedback
    """
    client = opik.Opik()

    # Log feedback score linked to the trace
    client.log_traces_feedback_scores(
        scores=[
            {
                "id": str(uuid.uuid4()),
                "trace_id": trace_id,
                "name": "user_satisfaction",
                "value": rating / 5.0,       # Normalize to 0.0-1.0
                "reason": comment,
                "source": "user",
            }
        ]
    )
```

### 10.2 FastAPI Endpoint for Feedback

```python
class FeedbackRequest(BaseModel):
    trace_id: str
    rating: int           # 1-5
    comment: str = ""

@app.post("/feedback")
async def record_feedback(request: FeedbackRequest):
    """Record user satisfaction and link it to the OPIK trace."""
    submit_feedback(
        trace_id=request.trace_id,
        rating=request.rating,
        comment=request.comment,
    )
    return {"status": "feedback_recorded", "trace_id": request.trace_id}
```

### 10.3 What This Enables

With feedback linked to traces, you can answer:

- **"What prompt version gets the best ratings?"** → Filter by `prompt_version` tag, compare average `user_satisfaction` score
- **"Do longer responses get higher ratings?"** → Correlate `completion_tokens` with `user_satisfaction`
- **"Which intents have the lowest satisfaction?"** → Group by `intent` metadata, sort by feedback score

---

## 11. OPIK Dashboard: What You Can Visualize

Once instrumented, the OPIK dashboard provides:

### 11.1 Trace Waterfall View
```
chatbot-request (1423ms total)
├── input-reception      [2ms]   ████
├── input-validation     [1ms]   ██
├── intent-detection     [3ms]   ████
├── pii-masking         [12ms]   ██████████
├── prompt-construction  [1ms]   ██
├── llm-invocation    [1380ms]   ████████████████████████████████████████████████████
├── response-postproc    [8ms]   ████████
├── evaluation          [14ms]   ██████████
└── response-delivery    [2ms]   ████
```

### 11.2 Key Dashboard Panels

| Panel | What It Shows |
|---|---|
| **Latency Distribution** | P50, P95, P99 response times with per-span breakdown |
| **Token Usage Over Time** | Prompt vs. completion tokens per hour/day |
| **Error Rate** | % of traces with `error_state != null` |
| **Cost Tracking** | Cumulative and per-request cost estimation |
| **Quality Scores** | Distribution of relevance, hallucination, safety scores |
| **Feedback Correlation** | User satisfaction vs. model/prompt version |
| **PII Detection Stats** | Count and types of PII detected per session |
| **Model Comparison** | Side-by-side latency, quality, cost for different models |

---

## 12. Alerting & Anomaly Detection

Configure OPIK alerts for these critical thresholds:

| Alert | Condition | Severity |
|---|---|---|
| **Latency Spike** | P95 `total_latency_ms` > 5000ms for 5 min | 🔴 Critical |
| **Error Rate** | `error_state != null` in > 5% of traces over 10 min | 🔴 Critical |
| **Hallucination Rate** | `hallucination_flag == true` in > 10% of traces | 🟡 Warning |
| **Cost Anomaly** | Daily `estimated_cost_usd` exceeds budget by > 20% | 🟡 Warning |
| **PII Leakage** | `safety_score` < 0.5 in any trace | 🔴 Critical |
| **Unmask Failure** | `unmask_success == false` in any trace | 🔴 Critical |
| **Token Budget** | `total_tokens` > 4000 per request | 🟡 Warning |

---

## 13. Cost Estimation Model

Since the chatbot uses **Groq (Llama-3.3-70B)**, here is the cost model:

```python
# Groq pricing (as of early 2026 — verify current rates)
GROQ_PRICING = {
    "llama-3.3-70b-versatile": {
        "input_cost_per_1m_tokens": 0.59,   # $0.59 / 1M input tokens
        "output_cost_per_1m_tokens": 0.79,   # $0.79 / 1M output tokens
    }
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost in USD for a single request."""
    pricing = GROQ_PRICING.get(model, {"input_cost_per_1m_tokens": 1.0,
                                        "output_cost_per_1m_tokens": 1.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input_cost_per_1m_tokens"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output_cost_per_1m_tokens"]
    return round(input_cost + output_cost, 6)
```

This is logged in every `llm-invocation` span's metadata as `estimated_cost_usd`, enabling:
- Daily/weekly cost dashboards
- Per-intent cost analysis (account recovery vs. payment issues)
- Cost per prompt version comparison

---

## 14. Production Best Practices

### 14.1 Performance

| Practice | Details |
|---|---|
| **Async flushing** | Use `flush=False` (default) — OPIK batches and sends traces in the background |
| **Sampling** | In very high traffic, consider tracing only N% of requests using random sampling |
| **Lightweight metadata** | Don't attach full conversation histories to every span — use summaries |

### 14.2 Security & Privacy

> [!WARNING]
> **NEVER log raw PII in OPIK traces.** Always log the **masked** versions of inputs/outputs. The instrumented code above follows this pattern — only masked text goes into OPIK.

| Practice | Details |
|---|---|
| **Self-host OPIK** | Deploy OPIK on your own infrastructure so traces never leave your network |
| **Mask before trace** | The PII masking span runs BEFORE setting `trace.input` with masked text |
| **Encrypt at rest** | Ensure the OPIK backing store (PostgreSQL/ClickHouse) has encryption at rest |

### 14.3 Observability Hygiene

| Practice | Details |
|---|---|
| **Consistent naming** | Use kebab-case for span names: `llm-invocation`, not `LLM_Invocation` |
| **Version metadata** | Always include `prompt_version` and `evaluator_version` in metadata |
| **Thread linking** | Use `thread_id=self.session_id` to group all traces from one conversation |
| **Tag strategy** | Use tags for high-cardinality filtering: `["customer-support", "api", "v2.1"]` |

---

## 15. Summary

### What We Achieve

```
┌────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY OUTCOMES                       │
├────────────────────┬───────────────────────────────────────────┤
│ Functional Quality │ Relevance, hallucination, completeness,   │
│                    │ safety scored on EVERY response            │
├────────────────────┼───────────────────────────────────────────┤
│ Operational Perf.  │ Per-span latency, error rates, retries,   │
│                    │ token usage, P95/P99 dashboards            │
├────────────────────┼───────────────────────────────────────────┤
│ Business Outcomes  │ User satisfaction correlated with prompts, │
│                    │ models, intents; cost tracking per request │
├────────────────────┼───────────────────────────────────────────┤
│ Debugging          │ Full trace waterfall per request; instant  │
│                    │ root-cause analysis for failures           │
├────────────────────┼───────────────────────────────────────────┤
│ Security           │ PII masking proof in every trace; safety   │
│                    │ score alerts; zero raw PII in OPIK         │
└────────────────────┴───────────────────────────────────────────┘
```

### Files Modified/Created

| File | Change |
|---|---|
| `requirements.txt` | Add `opik>=1.0.0` |
| `.env` | Add `OPIK_API_KEY`, `OPIK_WORKSPACE`, `OPIK_PROJECT_NAME`, `OPIK_URL_OVERRIDE` |
| `customer_support_bot.py` | Wrap `process_message` with OPIK trace + 9 spans; add evaluator methods |
| `api.py` | Add `/feedback` endpoint; return `trace_id` from `/search` |

> [!TIP]
> **Start small:** Begin by adding just the OPIK trace + LLM span (Span 6) to `process_message`. Once that works, progressively add the remaining spans. This incremental approach minimizes risk and lets you validate the dashboard setup step-by-step.
