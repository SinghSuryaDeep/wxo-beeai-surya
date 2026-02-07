#!/usr/bin/env python3
"""
WXO-compatible HTTP server
Converts WXO /chat/completions format to BeeAI agent calls
"""
import time
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from beeai_framework.agents.requirement import RequirementAgent
from ..config.settings import app_settings


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    stream: Optional[bool] = False


class WXOServer:
    """WXO-compatible HTTP server"""
    
    def __init__(self, agent: RequirementAgent):
        self.agent = agent
        self.app = FastAPI(title="BeeAI Predictive Maintenance Service")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/chat/completions")
        async def chat_completions(
            request: ChatCompletionRequest,
            x_api_key: Optional[str] = Header(None)
        ):
            """WXO-compatible chat completions endpoint"""
            
            # Verify API key
            if x_api_key != app_settings.api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Extract user message
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if not user_messages:
                raise HTTPException(status_code=400, detail="No user message found")
            
            prompt = user_messages[-1].content
            
            print(f"[WXO Server] Received: {prompt}")
            
            # Generate IDs
            timestamp = int(time.time())
            request_id = f"chatcmpl-beeai-{timestamp}"
            model_name = "beeai-granite-4-3b"
            
            try:
                # Run agent
                response = await self.agent.run(prompt)
                response_text = response.last_message.text
                
                print(f"[WXO Server] Response: {len(response_text)} chars")
                
                # Return SSE streaming response
                return StreamingResponse(
                    self._generate_sse_response(response_text, request_id, model_name),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
                
            except Exception as e:
                print(f"[WXO Server] ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                
                return StreamingResponse(
                    self._generate_error_sse_response(str(e), request_id, model_name),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "model": app_settings.llm_model,
                "timestamp": int(time.time())
            }
        
        @self.app.get("/.well-known/agent-card.json")
        async def agent_card():
            """Agent card for A2A protocol discovery"""
            return {
                "name": "BeeAI Predictive Maintenance Agent",
                "description": "AI-powered vehicle maintenance analysis",
                "version": "1.0.0",
                "capabilities": {
                    "streaming": True,
                    "function_calling": False
                },
                "preferredTransport": "HTTP",
                "url": f"http://{app_settings.wxo_host}:{app_settings.wxo_port}"
            }
    
    async def _generate_sse_response(self, response_text: str, request_id: str, model: str):
        """Generate SSE streaming response"""
        timestamp = int(time.time())
        
        # Content chunk
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": timestamp,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": response_text},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        # Final chunk
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": timestamp,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    async def _generate_error_sse_response(self, error_msg: str, request_id: str, model: str):
        """Generate error SSE response"""
        timestamp = int(time.time())
        error_content = f"⚠️ BeeAI Error: {error_msg}"
        
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": timestamp,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": error_content},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": timestamp,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    def serve(self):
        """Start the server"""
        import uvicorn
        print("=" * 60)
        print("🌐 BeeAI WXO Server Starting")
        print("=" * 60)
        print(f"Port: {app_settings.wxo_port}")
        print(f"Host: {app_settings.wxo_host}")
        print(f"Model: {app_settings.llm_model}")
        print(f"API Key: {app_settings.api_key}")
        print("=" * 60)
        
        uvicorn.run(
            self.app,
            host=app_settings.wxo_host,
            port=app_settings.wxo_port,
            log_level=app_settings.log_level.lower()
        )