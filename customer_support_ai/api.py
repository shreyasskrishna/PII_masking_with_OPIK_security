
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from customer_support_bot import CustomerSupportBot
import uvicorn
import uuid
import opik

app = FastAPI(
    title="Privacy-Preserving Customer Support API",
    description="API for PII masking and unmasking in customer support chats",
    version="1.0.0"
)

# Initialize the bot
# use_groq=True will try to connect to Groq, falling back to simulation if no key
bot = CustomerSupportBot(use_groq=True)

class SearchRequest(BaseModel):
    query: str

class FeedbackRequest(BaseModel):
    trace_id: str
    rating: int           # 1-5
    comment: str = ""

class SearchResponse(BaseModel):
    user_input_masked: str
    bot_response_masked: str
    bot_response_final_unmasked_for_user: str # The user specifically asked "other detailes should be displayed properly", which usually means the unmasked response for the user to read, OR the masked response?
    # Re-reading request: "search for labeling the masked content , in this the confidential details should be masked and other detailes should be displayed properly"
    # This implies the response the user SEES on this endpoint.
    # Usually you see the unmasked response if you are the user. But if the goal is to see "labeling masked content", maybe they want to see the masked version?
    # User said: "in this the confidential details should be masked and other detailes should be displayed properly"
    # This likely means the OUTPUT of this endpoint should show the Masked version?
    # BUT, normally a user wants to read the answer. 
    # Let's look at the next part: "Report for displaying the unmasked contents"
    # This strongly implies /search should show MASKED content (at least for PII).
    # So I will return the MASKED response in /search.
    
    # Wait, "other detailes should be displayed properly". This means non-PII text is visible.
    # So: "Your email <EMAIL_1> is saved." -> "Your email" and "is saved" are visible.
    # That is exactly what the masked string is.
    
    stages: Optional[Dict] = None

@app.post("/search")
async def search(request: SearchRequest):
    """
    Endpoint for labeling masked content and getting a response.
    Confidential details are masked.
    """
    try:
        result = bot.process_message(request.query, channel="api")

        return {
            "trace_id": result.get("trace_id"),
            "masked_input": result["stages"]["2_masked_before_llm"],
            "masked_response": result["stages"]["4_llm_response_masked"],
            "pii_mapping": result["stages"]["3_mapping_store"],
            "metrics": result.get("metrics"),
            "quality": result.get("quality"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def record_feedback(request: FeedbackRequest):
    """
    Record user satisfaction and link it to the OPIK trace.
    Rating: 1 (bad) to 5 (excellent)
    """
    try:
        client = opik.Opik()
        client.log_traces_feedback_scores(
            scores=[
                {
                    "id": str(uuid.uuid4()),
                    "trace_id": request.trace_id,
                    "name": "user_satisfaction",
                    "value": request.rating / 5.0,  # Normalize to 0.0-1.0
                    "reason": request.comment,
                    "source": "user",
                }
            ]
        )
        return {"status": "feedback_recorded", "trace_id": request.trace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/Report")
async def report():
    """
    Endpoint for displaying the unmasked contents of the conversation history.
    """
    # content stored in bot.conversation_history has keys: user_raw, user_masked, bot_masked, bot_final
    # Fetch from Database if available
    if hasattr(bot, 'db_manager') and bot.db_manager.is_connected():
        db_history = bot.db_manager.get_history(limit=50) # Get last 50
        
        # Transform DB format to Report format
        report_data = []
        for doc in db_history:
            report_data.append({
                "timestamp": doc.get("timestamp"),
                "user_original": doc["user_input"]["raw"],
                "bot_original": doc["bot_response"]["final"]
            })
        return {"source": "MongoDB", "conversation_history": report_data}
    else:
        # Fallback to in-memory
        history = bot.conversation_history
        report_data = []
        for entry in history:
            report_data.append({
                "source": "Memory (Temporary)",
                "user_original": entry["user_raw"],
                "bot_original": entry["bot_final"]
            })
            
        return {"conversation_history": report_data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8501)
