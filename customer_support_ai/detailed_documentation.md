# Privacy-Preserving AI Customer Support - Technical Documentation

## 1. Introduction
This application represents a secure, privacy-first architecture for integrating Large Language Models (LLMs) into customer support workflows. It acts as a **middleware proxy** that intercepts user messages, identifies and masks sensitive Personally Identifiable Information (PII) before sending the data to an external AI provider (Groq), and then re-injects the original data into the response for the user. This ensures that the AI provider never sees the user's actual sensitive data.

## 2. Architecture Overview
The system follows a "Mask-Process-Unmask" pipeline:

1.  **Input Layer**: User sends a message via the API (FastAPI)
2.  **PII Detection & Masking**:
    -   The `PIIMasker` engine scans the text using Regex patterns (e.g., for Email, Phone, PAN, Aadhaar and etc...).
    -   Sensitive data is replaced with tokens (e.g., `test@example.com` -> `<EMAIL_1>`).
    -   The original values are **encrypted** and stored in a temporary session mapping.
3.  **AI Processing**:
    -   The masked message (e.g., "My email is <EMAIL_1>") is sent to the LLM (Groq/Llama-3).
    -   The LLM generates a response using the tokens (e.g., "I have sent a reset link to <EMAIL_1>").
4.  **Unmasking & Response**:
    -   The application receives the tokenized response.
    -   It looks up the encrypted mapping, decrypts the original value, and replaces the token.
    -   The final, readable message is returned to the user.
5.  **Persistence**: The conversation (original, masked, and mapping) is stored in MongoDB for audit trails.

## 3. Where Can We Use It?
This architectural pattern is applicable in any system where sensitive data interacts with untrusted or external components:
*   **Customer Support Chatbots**: Deploying intelligent agents that need to handle medical, financial, or personal queries without violating user trust.
*   **Automated Email Processing**: Systems that read customer emails to route tickets or draft replies.
*   **Data Analytics Pipelines**: Sanitizing production text logs before loading them into a data warehouse for analysis.
*   **Developer Environments**: Creating "sanitized" database dumps so developers can test with production-like data without seeing real user info.

## 4. When Should We Use It?
You should implement this layer when:
*   **Passing Data to Third Parties**: You want to use the intelligence of a powerful model (e.g., Llama 3 via Groq) but cannot legally or ethically send them your users' PII.
*   **Regulatory Compliance is Mandatory**: You operate under strict frameworks like **GDPR**, **CCPA**, **HIPAA**, or **PCI-DSS**.
*   **Data Minimization**: You want to follow the security best practice of only exposing necessary data to any processor.

## 5. What Are The Benefits?
*   **Zero-Trust AI**: The AI provider never sees the real data. Even if they are breached, your users' data is safe because the AI only stored tokens like `<CREDIT_CARD_1>`.
*   **Reversible Context**: Unlike simple redaction (which turns text into `***`), this system maintains *context*. The AI knows `<USER_1>` is the same person across the conversation, allowing it to provide personalized support without knowing the real name.
*   **Auditability**: You can log exactly what was sent to the AI and prove to auditors that PII was removed.

## 6. Technology Stack

### Backend
*   **Language**: Python 3.9+
*   **API Framework**: **FastAPI** (High-performance, easy-to-use API creation).
    *   *Usage*: Handles the `/search` and `/Report` endpoints.
*   **Server**: **Uvicorn** (ASGI server for running FastAPI).

### AI & Logic
*   **LLM Provider**: **Groq** (running Llama-3 70B).
    *   *Usage*: Provides intelligent conversational responses.
*   **PII Logic**: Custom Regex-based engine (`PIIMasker` class).

### Database
*   **Database**: **MongoDB** (NoSQL Database).
    *   *Driver*: `pymongo`.
    *   *Usage*: Stores conversation history, including raw input, masked input, bot responses, and the PII mapping (for audit/reconstruction).

### Security
*   **Encryption**: **Cryptography** library (symmetric encryption).
*   **Environment Management**: `python-dotenv` for securely loading API keys and DB credentials.

## 4. Database Implementation
The application uses **MongoDB** for its flexibility in handling JSON-like documents.

*   **Collection**: `conversations`
*   **Document Structure**:
    ```json
    {
        "session_id": "unique_session_id",
        "timestamp": "2024-02-13T10:00:00Z",
        "user_input": {
            "raw": "My email is test@example.com",  // (Ideally encrypted at rest in high-security envs)
            "masked": "My email is <EMAIL_1>"
        },
        "bot_response": {
            "masked": "Sent to <EMAIL_1>",
            "final": "Sent to test@example.com"
        },
        "pii_mapping": {
            "<EMAIL_1>": "gAAAAABl..." // Encrypted binary data
        }
    }
    ```

## 5. Security & Encryption

### Type of Encryption: **Fernet (Symmetric Encryption)**
The application uses **Fernet** from the `cryptography` library.

*   **Algorithm**: AES-128 in CBC mode with HMAC-SHA256 for authentication.
*   **Key**: A single symmetric key (`ENCRYPTION_KEY` in `.env`) is used for both encryption and decryption.

### Advantages of Fernet:
1.  **Speed**: Symmetric encryption is extremely fast, suitable for real-time chat applications.
2.  **Security**: It guarantees that a message cannot be manipulated or read without the key.
3.  **Simplicity**: It abstracts away the complexity of managing IVs (Initialization Vectors) and padding, reducing implementation errors.

## 6. PII Masking Implementation

### How it Works
The `PIIMasker` class uses Regular Expressions (Regex) to identify patterns.
*   **Detection**: It iterates through a dictionary of patterns (`EMAIL`, `PHONE`, `PAN`, `AADHAAR`, `DEVICE_ID`, `CVV`, etc.).
*   **Tokenization**:
    -   Found: `abc@xyz.com`
    -   Generated Token: `<EMAIL_1>`
*   **Storage**: The mapping `<EMAIL_1> -> abc@xyz.com` is created. The real value is **encrypted** before being stored in memory or DB.

### Detailed Regex Patterns Used (V3)
-   **PAN**: `[A-Z]{5}[0-9]{4}[A-Z]{1}`
-   **Aadhaar**: `\d{4}\s\d{4}\s\d{4}`
-   **GST/User IDs**, **Phone** (with +91 support), **Address** (complex multi-line support), **Device IDs**, **Credit Cards**, **CVV**, **Expiry Dates**.

### Advantages of this Approach
1.  **Determinism**: Regex is predictable. If data matches the pattern, it *will* be caught.
2.  **Context Preservation**: By replacing `John` with `<PERSON_1>` instead of `****`, the AI understands "The user's name is <PERSON_1>" and can use that handle in the conversation.
3.  **Reversibility**: Essential for customer support. The user needs to see "I updated your email to `bob@gmail.com`", not "I updated your email to `<EMAIL_1>`".

## 7. Alternative Approaches & Comparison for Data Security

While the regex-masking approach is robust for many use cases, here are other approaches for higher-security needs:

### A. Microsoft Presidio (Context-Aware NLP)
*   **What it is**: Uses Natural Language Processing (NLP) models (like spaCy/HuggingFace) along with regex to detect PII.
*   **Advantage**: detecting "My name is **Austin**" (Name) vs "I am going to **Austin**" (City). Regex often struggles with this context.
*   **Disadvantage**: Slower and more resource-intensive than Regex.

### B. Local LLM Scrubbing (Small Specialized Models)
*   **What it is**: Running a small, local LLM (like Llama-3-8B or specialized PII scrubbing models) *before* sending data to the main cloud provider.
*   **Advantage**: Can understand complex PII that regex misses (e.g., "The guy who lives next to the bank").
*   **Disadvantage**: High latency and hardware cost.

### C. Differential Privacy
*   **What it is**: Adding mathematical noise to datasets so individual records cannot be re-identified.
*   **Use Case**: Better for **Analytics/Training**, not for direct customer support chat where you need exact values.

### D. Homomorphic Encryption
*   **What it is**: Allows computation on encrypted data without decrypting it.
*   **Advantage**: The "Holy Grail" of security—the AI could process the encrypted text directly.
*   **Disadvantage**: Currently strictly theoretical for LLMs; it is thousands of times too slow for real-time chat.

## Conclusion
For this application, the **Regex Masking + Fernet Encryption** stack provides the best balance of **Performance** (real-time latency), **Security** (AES-128), and **Utility** (AI context retention).
