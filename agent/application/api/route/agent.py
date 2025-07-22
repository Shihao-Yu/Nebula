# REST endpoint for simple interactions
@app.post("/api/v1/agent/chat")
async def chat_endpoint(
    request: ChatRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)]
):
    # For simple Q&A, return complete response
    response = await agent.process_request(request)
    return ChatResponse(response=response)

# REST endpoint that initiates WebSocket session
@app.post("/api/v1/agent/session/create")
async def create_session(
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)]
):
    session_id = str(uuid4())
    ws_url = f"/ws/agent/{tenant_context.tenant_id}/{session_id}"
    
    return {
        "session_id": session_id,
        "websocket_url": ws_url,
        "expires_at": time.time() + 3600
    }