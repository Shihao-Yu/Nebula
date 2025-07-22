# WebSocket endpoint for real-time agent interaction
@app.websocket("/ws/agent/{tenant_id}/{session_id}")
async def agent_websocket(
    websocket: WebSocket,
    tenant_id: str,
    session_id: str,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)]
):
    await websocket.accept()
    
    try:
        # Stream agent responses
        async for event in agent.process_stream(websocket):
            await websocket.send_json({
                "type": event.type,  # "thinking", "tool_call", "response", etc.
                "data": event.data,
                "timestamp": time.time()
            })
    except WebSocketDisconnect:
        await cleanup_session(session_id)