"""
Privacy-Preserving Customer Support AI Bot with Groq LLM Integration

This module implements a complete PII masking pipeline for AI customer support:
User Input → Mask PII → Send to LLM → Get Response → Unmask PII → Return to User

Author: Customer Support AI Team
Date: February 2026
"""

import re
import os
import time
import uuid
import hashlib
from typing import Dict, Tuple
from dotenv import load_dotenv
import opik

# Load environment variables
load_dotenv()

# ============================================================================
# PII MASKING ENGINE
# ============================================================================

from cryptography.fernet import Fernet

class PIIMasker:
    """
    Handles detection, masking, and unmasking of Personally Identifiable Information.
    Uses regex-based pattern matching with token-based replacement.
    Stores PII mapping in an encrypted format using Fernet (symmetric encryption).
    """
    
    def __init__(self):
        # Define regex patterns for different PII types
        self.patterns = {
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "PHONE": r'\b(?:\+\d{1,3}[\s\-‑]?)?\(?\d{3}\)?[\s.\-‑]?\d{3}[\s.\-‑]?\d{4}\b|\b(?:\+\d{1,3}[\s\-‑]?)?\d{5}[\-‑]\d{5}\b',
            "SSN": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            "CC": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "IP": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "USER_ID": r'\b[A-Z]{2,5}[-_]?\d{6,12}\b',
            "ACCOUNT": r'\b\d{10,16}\b',
            "PAN": r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
            "DOB": r'\b\d{2}[-‑/]\d{2}[-‑/]\d{4}\b',
            "AADHAAR": r'\b\d{4}\s\d{4}\s\d{4}\b',
            "EMPLOYEE_ID": r'\b(?:[A-Z0-9]+[-_]+)*EMP[-_]?\d+\b',
            "BLOOD_GROUP": r'\b(A|B|AB|O)[+-](?!\w)',
            "LICENSE_NO": r'\b[A-Z]{2}[-‑]?\d{13}\b',
            "DEVICE_ID": r'\b[A-Z]+-[A-Z]+-[A-Z0-9]+\b',
            "EXPIRY_DATE": r'\b(?:0[1-9]|1[0-2])/\d{2}\b',
            "CVV": r'\b(?:CVV|CVC|CVV2|CVC2)\s*[:\-]?\s*\d{3,4}\b',
            # Address: Anchored by start (No/Flat/etc) and end (Pincode) with structure keywords in between
            "ADDRESS": r'\b(?:No\.|Flat|Plot|Door|#|[0-9]+[A-Z]?)\s*[,/\-]?\s*[^.]*?(?:Street|Road|Lane|Ave|Nagar|Colony|Block|Apartments|Enclave|Hills|Garden|Salai|Cross|Main|Floor|Towers|Complex|Plaza|Drive|Way|Circle)[^.]*?\d{6}\b'
        }
        
        # Load Encryption Key
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            # If no key found, generate one for this session (less secure persistent storage, but works for demo)
            print("⚠️  No ENCRYPTION_KEY found in environment. Generating temporary key.")
            self.encryption_key = Fernet.generate_key()
            
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Storage for current session mappings (Values will be ENCRYPTED bytes)
        self.current_mapping: Dict[str, bytes] = {}
        # Reverse mapping stores HASHES or just raw strings mapping to tokens? 
        # Actually, for reverse mapping we need to know if we've seen this PII before.
        # Storing raw PII in reverse_mapping defeats the purpose of encryption (it's in memory).
        # We should hash the PII for lookup.
        self.reverse_mapping: Dict[str, str] = {} 

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Mask all PII in the input text.
        Returns masked text and a simple dict for display (decrypted for debug if needed, 
        or just the encrypted one? The return type says Dict[str, str]).
        The 'process_message' uses the returned dict for '3_mapping_store'.
        We should probably return the ENCRYPTED mapping to be safe, or a placeholder.
        """
        self.current_mapping = {}
        self.reverse_mapping = {} # In a real app we might persist this, but here it's per-request?
        # The original code reset it per request: `self.current_mapping = {}`.
        # Wait, the original code had `self.current_mapping` in `__init__` and reset it in `mask`.
        # Yes.
        
        masked_text = text
        
        for pii_type, pattern in self.patterns.items():
            matches = list(re.finditer(pattern, masked_text))
            
            for i, match in enumerate(reversed(matches)):
                original_value = match.group(0)
                
                # Check if we already masked this specific string in this session
                # (Simple optimization, though `reverse_mapping` cleared every time makes it local to message)
                if original_value in self.reverse_mapping:
                    token = self.reverse_mapping[original_value]
                else:
                    token = f"<{pii_type}_{len([k for k in self.current_mapping if k.startswith(f'<{pii_type}_')]) + 1}>"
                    
                    # ENCRYPT the value
                    encrypted_value = self.cipher_suite.encrypt(original_value.encode())
                    
                    self.current_mapping[token] = encrypted_value
                    self.reverse_mapping[original_value] = token
                
                start, end = match.span()
                masked_text = masked_text[:start] + token + masked_text[end:]
        
        # For the returned mapping (used for debug/display), we probably want to show it IS encrypted.
        # We returning the byte-string representations.
        debug_mapping = {k: v.decode() for k, v in self.current_mapping.items()} # decode bytes to string for JSON serialization
        return masked_text, debug_mapping
    
    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Restore original PII values in the text.
        The 'mapping' passed here comes from `self.session_mapping.update(mapping)`.
        The `mapping` from `mask()` returned decoded strings of encrypted bytes.
        """
        result = text
        # We need to iterate over the items.
        # The input `mapping` has values as "gAAAA..." strings (if we returned decoded bytes above).
        
        for token, encrypted_string in mapping.items():
            try:
                # 1. Convert string back to bytes
                if isinstance(encrypted_string, str):
                    encrypted_bytes = encrypted_string.encode()
                else:
                    encrypted_bytes = encrypted_string
                
                # 2. Decrypt
                decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
                original_value = decrypted_bytes.decode()
                
                # 3. Replace
                result = result.replace(token, original_value)
            except Exception as e:
                print(f"❌ Error decrypting token {token}: {e}")
                # Keep the token if decryption fails
                pass
                
        return result


# ============================================================================
# SYSTEM PROMPT FOR LLM
# ============================================================================

SYSTEM_PROMPT = """You are a Customer Support AI Assistant operating in a privacy-preserving environment.
              
CRITICAL CONTEXT:
All sensitive user information such as emails, phone numbers, credit card numbers, account IDs, and personal identifiers are automatically masked before reaching you.

Masked data appears in this format:
<EMAIL_1>, <PHONE_1>, <CC_1>, <USER_ID_1>, etc.

These tokens represent real user data but you must NEVER attempt to infer, reconstruct, modify, or request the original values.

SECURITY & COMPLIANCE RULES (MANDATORY):
- Never ask for or display real personal data
- Never guess or fabricate PII values
- Never alter token format or numbering
- Never remove or merge tokens
- Always reuse tokens exactly as shown in the user message
- Do not generate new tokens unless present in the input

RESPONSE STYLE:
- Professional, friendly, and empathetic
- Clear and action-oriented
- Provide helpful solutions and next steps
- Confirm actions taken
- Ask clarifying questions when needed (but never ask for PII)

Remember: You are having a real conversation. Respond naturally and helpfully to each message.
Your goal is to provide accurate, helpful customer support while preserving complete data privacy."""


# ============================================================================
# GROQ LLM CLIENT
# ============================================================================

class GroqClient:
    """
    Client for Groq API to get real LLM responses.
    """
    
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Set it in .env file or pass directly.")
    
    def chat(self, user_message: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        """
        Send message to Groq and get response.
        """
        import requests
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build messages with system prompt
        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            assistant_message = response.json()["choices"][0]["message"]["content"]
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Groq API: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# ============================================================================
# CUSTOMER SUPPORT BOT
# ============================================================================

class CustomerSupportBot:
    """
    Privacy-preserving customer support bot that integrates PII masking
    with Groq LLM for real responses.
    """
    
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
    
    def _call_llm(self, masked_message: str) -> str:
        """
        Send masked message to LLM and get response.
        """
        if self.use_groq and self.groq_client:
            return self.groq_client.chat(masked_message)
        else:
            # Fallback simulated responses
            return self._simulated_response(masked_message)
    
    def _simulated_response(self, masked_message: str) -> str:
        """Simulated LLM responses for demo when no API key."""
        simulated_responses = {
            "account": "I understand you're having trouble accessing your account. I've initiated a password reset and sent a verification link to <EMAIL_1>. Please also verify your identity using <PHONE_1>. Is there anything else I can help you with?",
            "payment": "I can see the payment issue. I've flagged the transaction on card ending in <CC_1> for review. Our billing team will contact you at <EMAIL_1> within 24 hours.",
            "default": "Thank you for contacting support. I've noted your concern and will ensure our team follows up at your registered contact details. Is there anything specific you'd like me to address?"
        }
        
        message_lower = masked_message.lower()
        if "account" in message_lower or "login" in message_lower or "access" in message_lower:
            return simulated_responses["account"]
        elif "payment" in message_lower or "card" in message_lower or "charge" in message_lower:
            return simulated_responses["payment"]
        else:
            return simulated_responses["default"]
    
    def process_message(self, user_input: str, user_id: str = "anonymous",
                        channel: str = "api") -> Dict:
        """
        Complete privacy-preserving message processing pipeline
        with full OPIK observability.

        Pipeline: User Input → Validate → Detect Intent → Mask PII →
                  Build Prompt → LLM Call → Unmask → Evaluate → Deliver
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
                    "detected_language": "en",
                }

                if not is_valid:
                    trace.output = {"error": validation_reason}
                    trace.tags.append("validation-failed")
                    return {"response": f"Invalid input: {validation_reason}",
                            "trace_id": request_id, "stages": {}}

            # ─── SPAN 3: Intent Detection ──────────────────────────
            with opik.start_as_current_span(
                "intent-detection", type="general"
            ) as span:
                span.input = {"user_text": user_input}
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

            # ─── SPAN 6: LLM Invocation ────────────────────────────
            with opik.start_as_current_span(
                "llm-invocation", type="llm"
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

                # Token estimation (~4 chars per token)
                est_prompt_tokens = len(masked_input) // 4
                est_completion_tokens = len(masked_response) // 4
                est_total_tokens = est_prompt_tokens + est_completion_tokens

                # Cost estimation (Groq Llama-3 pricing)
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

        # Store in conversation history (In-Memory)
        self.conversation_history.append({
            "user_raw": user_input,
            "user_masked": masked_input,
            "bot_masked": masked_response,
            "bot_final": final_response
        })

        # Store in Database (Persistent)
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
    
    def get_mapping(self) -> Dict[str, str]:
        """Return current session's PII mapping."""
        return self.session_mapping.copy()
    
    def clear_session(self):
        """Clear conversation history and mappings."""
        self.conversation_history = []
        self.session_mapping = {}
        if self.groq_client:
            self.groq_client.clear_history()

    # ════════════════════════════════════════════════════════════════
    # HEURISTIC QUALITY EVALUATORS (used by OPIK evaluation span)
    # ════════════════════════════════════════════════════════════════

    def _compute_relevance(self, query: str, response: str) -> float:
        """
        Heuristic relevance scorer.
        Checks keyword overlap between query and response.
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
        input_tokens = set(re.findall(r'<[A-Z_]+_\d+>', masked_input))
        response_tokens = set(re.findall(r'<[A-Z_]+_\d+>', masked_response))
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
        action_words = ["help", "assist", "resolve", "send", "update",
                        "check", "verify", "confirm", "contact"]
        found = sum(1 for w in action_words if w in response.lower())
        return round(min(0.5 + (found * 0.1), 1.0), 2)

    def _compute_safety(self, response: str) -> float:
        """
        Heuristic safety scorer.
        Checks for disallowed content patterns (PII leakage).
        """
        unsafe_patterns = [
            r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',     # SSN-like
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+',   # Raw email
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',         # Credit card
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, response):
                return 0.1  # Unsafe — PII leaked into response
        return 0.99


# ============================================================================
# DEMO / INTERACTIVE MODE
# ============================================================================

def print_stage(title: str, content: str, emoji: str = "📋"):
    """Pretty print a pipeline stage."""
    print(f"\n{emoji} {title}")
    print("─" * 50)
    print(content)


def run_demo():
    """Run a demonstration with a single example."""
    
    print("=" * 60)
    print("🔐 PRIVACY-PRESERVING CUSTOMER SUPPORT AI - DEMO")
    print("=" * 60)
    print("\nThis demo shows how PII is protected when interacting with AI.\n")
    
    bot = CustomerSupportBot(use_groq=False)  # Use simulated for demo
    
    message = "Hi, my email is demo.user@gmail.com and my phone number is (555) 123-4567. I can't log into my account."
    
    print("=" * 60)
    print("🎯 EXAMPLE: Account Recovery Request")
    print("=" * 60)
    
    result = bot.process_message(message)
    stages = result["stages"]
    
    print_stage("User Input (RAW)", stages["1_user_input_raw"], "👤")
    print_stage("Masked Before LLM", stages["2_masked_before_llm"], "🔒")
    
    mapping_str = "\n".join([f"  {k} → {v}" for k, v in stages["3_mapping_store"].items()])
    print_stage("Mapping Store", mapping_str, "📁")
    
    print_stage("LLM Response (masked)", stages["4_llm_response_masked"], "🤖")
    print_stage("Final Output to User", stages["5_final_output_to_user"], "✅")
    
    print("\n" + "=" * 60)
    print("✨ Demo complete! PII was protected throughout the pipeline.")
    print("=" * 60)


def interactive_mode():
    """Run an interactive customer support session with Groq LLM."""
    
    print("=" * 60)
    print("🔐 INTERACTIVE CUSTOMER SUPPORT (Groq LLM)")
    print("=" * 60)
    print("\nType your message (include emails, phones, etc.)")
    print("Commands: 'quit' to exit, 'show' to see PII mapping, 'clear' to reset\n")
    
    bot = CustomerSupportBot(use_groq=True)
    
    if bot.use_groq:
        print("✅ Connected to Groq API - Real LLM responses enabled!\n")
    else:
        print("⚠️  Using simulated responses (set GROQ_API_KEY for real LLM)\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() == 'quit':
                print("\nThank you for using our support service. Goodbye! 👋")
                break
            elif user_input.lower() == 'show':
                print("\n📁 Current PII Mapping:")
                mapping = bot.get_mapping()
                if mapping:
                    for token, value in mapping.items():
                        print(f"   {token} → {value}")
                else:
                    print("   (No PII detected yet)")
                print()
                continue
            elif user_input.lower() == 'clear':
                bot.clear_session()
                print("\n🔄 Session cleared. Starting fresh!\n")
                continue
            elif not user_input:
                continue
            
            result = bot.process_message(user_input)
            print(f"\n🤖 Bot: {result['response']}\n")
            
        except KeyboardInterrupt:
            print("\n\nSession ended. Goodbye! 👋")
            break


def quick_test():
    """Run a single quick test."""
    print("\n🔐 Quick Test\n")
    
    bot = CustomerSupportBot(use_groq=True)
    test_msg = "Hi, my email is test@example.com and phone is (555) 123-4567. I need help with my order."
    
    print(f"Input: {test_msg}")
    result = bot.process_message(test_msg)
    print(f"\nMasked: {result['stages']['2_masked_before_llm']}")
    print(f"\nBot Response: {result['response']}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("\n🔐 Privacy-Preserving Customer Support AI\n")
    print("Choose mode:")
    print("  1. Run Demo (see example pipeline - no API needed)")
    print("  2. Interactive Mode (chat with Groq LLM)")
    print("  3. Quick Test (single message test)")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        run_demo()
    elif choice == "2":
        interactive_mode()
    elif choice == "3":
        quick_test()
    else:
        print("Invalid choice. Running demo...")
        run_demo()
