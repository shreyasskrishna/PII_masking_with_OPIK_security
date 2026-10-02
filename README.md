<div align="center">

# 🔐 Privacy-Preserving Customer Support AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/Groq-Llama3-orange.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Secure, privacy-focused customer support API that protects user PII before sending it to LLMs.**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [API Usage](#-api-usage) • [Tech Stack](#-tech-stack)

</div>

---

## 📖 Overview

This project is a **secure middleware proxy** designed to integrate Large Language Models (LLMs) into customer support workflows without compromising user privacy. It automatically detects and masks Personally Identifiable Information (PII) like emails, phone numbers, and potential sensitive data before sending prompts to the AI provider.

## 🚀 Features

*   **Real-time PII Detection**: Automatically identifies emails, phone numbers, SSNs, credit cards, and more.
*   **Secure Masking**: Replaces sensitive data with tokens (e.g., `<EMAIL_1>`).
*   **Encryption**: Stores the mapping between tokens and real data using **Fernet Symmetric Encryption** (AES) in memory. Original data is never stored in plain text.
*   **LLM Integration**: Seamlessly works with Groq API (or simulated responses).
*   **FastAPI Backend**: High-performance asynchronous API.

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd customer_support_ai
python -m venv venv
venv\Scripts\activate
   
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```ini
GROQ_API_KEY=your_groq_api_key_here
ENCRYPTION_KEY=your_fernet_key_here  # Optional: Will generate temporary key if missing
```

---

## ⚡ Running the API

Start the high-performance FastAPI server:

```bash
python api.py
```
> The server will start at `http://0.0.0.0:8501`.

---

## 📖 API Usage

### 1. Search / Process Message
**Endpoint**: `POST /search`

Sends a user message to the bot. The system masks PII, queries the LLM, and unmasks the response.

**Request**:
```json
{
  "query": "My email is test@example.com and I need help with order #12345."
}
```

**Response**:
```json
{
  "masked_input": "My email is <EMAIL_1> and I need help with order #12345.",
  "masked_response": "I've checked order #12345. I sent details to <EMAIL_1>.",
  "pii_mapping": {
    "<EMAIL_1>": "gAAAAABl..."  // 🔒 Encrypted value
  }
}
```

### 2. Get Report
**Endpoint**: `GET /Report`

Retrieves the conversation history with original (unmasked) user and bot messages for auditing.

---

## 🔒 Security Architecture

### The Masking Pipeline

```text
USER INPUT: "My email is john@gmail.com and phone is 555-123-4567"
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: PII DETECTION                                      │
│  Regex patterns scan text and find:                         │
│  • EMAIL: "john@gmail.com"                                  │
│  • PHONE: "555-123-4567"                                    │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: MASKING                                            │
│  Replace PII with tokens:                                   │
│  • "john@gmail.com" → <EMAIL_1>                             │
│  • "555-123-4567" → <PHONE_1>                               │
│                                                             │
│  Masked: "My email is <EMAIL_1> and phone is <PHONE_1>"     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: STORE MAPPING (Local Encrypted Memory)             │
│                                                             │
│  mapping = {                                                │
│      "<EMAIL_1>": "gAAAAABl...", (Encrypted)                │
│      "<PHONE_1>": "gAAAAABk..."  (Encrypted)                │
│  }                                                          │
│                                                             │
│  ⚠️ This stays on YOUR server - never sent to LLM!          │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: SEND TO LLM (Groq)                                 │
│                                                             │
│  Only masked text sent: "My email is <EMAIL_1>..."          │
│  LLM never sees real data!                                  │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: LLM RESPONSE                                       │
│                                                             │
│  "I've sent a reset link to <EMAIL_1>. Verify via <PHONE_1>"│
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: UNMASK                                             │
│  Replace tokens with original values using stored mapping:  │
│  • <EMAIL_1> → "john@gmail.com"                             │
│  • <PHONE_1> → "555-123-4567"                               │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
FINAL OUTPUT: "I've sent a reset link to john@gmail.com. Verify via 555-123-4567"
```

1.  **Detection**: Regex patterns identify sensitive entities.
2.  **Encryption**: The sensitive value (e.g., `user@email.com`) is encrypted using a **Fernet Key**.
3.  **Storage**: The *encrypted* value is stored in a temporary dictionary.
4.  **LLM Processing**: The LLM only sees `<EMAIL_1>`, ensuring **Zero Data Leakage** to the AI provider.
5.  **Unmasking**: The response is reconstructed by decrypting the values only when presenting to the user.

### Supported PII Types
| Type | Token |
|------|-------|
| Email | `<EMAIL_1>` |
| Phone | `<PHONE_1>` |
| SSN | `<SSN_1>` |
| Credit Card | `<CC_1>` |
| IP Address | `<IP_1>` |
| Account No | `<ACCOUNT_1>` |

---

## 🧪 Testing

Run the included test script to verify the API and encryption are working correctly:

```bash
python test_api.py
```

---

<div align="center">

**Built for Data Privacy , Security and To prevent data leakage**

</div>
