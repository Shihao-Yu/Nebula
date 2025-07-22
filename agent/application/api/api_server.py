@app.middleware("http")
async def tenant_security_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    
    # Validate tenant access
    if not await validate_tenant_access(tenant_id, request.headers.get("Authorization")):
        raise HTTPException(status_code=403, detail="Tenant access denied")
    
    # Add security context
    request.state.security_context = SecurityContext(
        tenant_id=tenant_id,
        user_id=extract_user_id(request.headers.get("Authorization")),
        permissions=await get_user_permissions(tenant_id, user_id)
    )
    
    response = await call_next(request)
    return response