def determine_origin(platform: str, attrs: dict) -> str:
    if not platform:
        return ""
    
    platform = platform.lower()
    
    # TODO: Apple should distinguish between system-level signin (e.g., iCloud settings on device)
    if platform == "apple":
        return "apple/system"
    
    try:
        client_type = attrs.get('user_agent_type', '').strip().lower() if attrs.get('user_agent_type') else ''
        client_name = attrs.get('user_agent_name', '').strip().lower() if attrs.get('user_agent_name') else ''
        secondary_name = attrs.get('user_agent_secondary_name', '').strip().lower() if attrs.get('user_agent_secondary_name') else ''
        client_session_type = attrs.get('client_session_type', '').strip().lower() if attrs.get('client_session_type') else ''
    except Exception:
        return f"{platform}/unknown"

    valid = [v for v in [client_type, client_name, client_session_type] if v and v != '']
    
    if len(valid) == 0:
        return f"{platform}/unknown"
    
    if client_type == 'browser' and secondary_name \
        or 'webview' in client_name.lower() or 'webview' in secondary_name.lower():
        return f"{platform}/app_webview"
    
    if client_type == 'browser' or  {'chrome', 'chromium', 'firefox', 'safari', 'edge'}.intersection({client_name, secondary_name, client_session_type}):
        return f"{platform}/web"
    
    if client_type == 'mobile app' or {'mobile', 'app'}.intersection({client_name, secondary_name, client_session_type}):
        return f"{platform}/mobile_app"
    
    elif client_type is not None and client_type != '':
        return f"{platform}/{client_type.replace(' ', '_')}"
    
    return ""
