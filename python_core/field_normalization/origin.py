def determine_origin(platform: str, attrs: dict) -> str:
    if not platform:
        return ""
    
    platform = platform.lower()
    
    # TODO: Apple should distinguish between system-level signin (e.g., iCloud settings on device)
    if platform == "apple":
        return "apple/system"
    
    client_type = attrs.get('user_agent_type', '').strip().lower() if attrs.get('user_agent_type') else ''
    client_name = attrs.get('user_agent.name', '').strip() if attrs.get('user_agent.name') else ''
    secondary_name = attrs.get('user_agent_secondary.name', '').strip() if attrs.get('user_agent_secondary.name') else ''
    
    if client_type == 'browser' and secondary_name \
        or 'webview' in client_name.lower() or 'webview' in secondary_name.lower():
        return f"{platform}/app_webview"
    
    if client_type == 'mobile app':
        return f"{platform}/mobile_app"
    
    if client_type == 'browser':
        return f"{platform}/web"
    
    elif client_type is not None and client_type != '':
        return f"{platform}/{client_type.replace(' ', '_')}"
    
    return f"{platform}/unknown"
