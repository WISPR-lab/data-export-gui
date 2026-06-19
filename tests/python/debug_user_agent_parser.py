# To run: source venv/bin/activate && python tests/debug_user_agent_parser.py

import sys
import os

# Add python_core to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, 'python_core'))

from field_normalization.user_agent import UserAgentParser

parser = UserAgentParser()

test_cases = [
    "App : GMAIL_APP. App Version : 6.0.241126. Os : IOS_OS. Os Version : 17.7.1. Device Type : MOBILE.",
    "App : GMM_APP. App Version : 24.47.3. Os : IOS_OS. Os Version : 17.7.1. Device Type : MOBILE.",
    "Os : IOS_OS. Os Version : 12.1.3. Device Type : MOBILE.",
    "App : OTHER_APP. Os : UNKNOWN_OS. Os Version : . Device Type : UNKNOWN.",
    "App : SAFARI. App Version : 17.8. Os : MAC_OS. Os Version : 10.15.7. Device Type : PC.",
    "App : YOUTUBE_APP. App Version : 21.17.3. Os : IOS_OS. Os Version : 26.4.2. Device Type : MOBILE.",
    "App : SAFARI_WEBVIEW_APP. Os : IOS_OS. Os Version : 18.7. Device Type : MOBILE.",
    "App : ASSISTANT_APP. App Version : 1.2026.1710205. Os : IOS_OS. Os Version : 26.4.2. Device Type : MOBILE.",
    # "com.google.Gmail/6.0.241126 iSL/3.4 iPhone/17.7.1 hw/iPhone11_8 (gzip),gzip(gfe)",
]

print("=" * 80)
print("USER AGENT PARSER DEBUG OUTPUT")
print("=" * 80)

for i, ua_string in enumerate(test_cases, 1):
    print(f"\n[Test Case {i}]")
    print(f"Input UA: {ua_string[:100]}..." if len(ua_string) > 100 else f"Input UA: {ua_string}")
    print()
    
    result = parser.parse({'user_agent_original': ua_string}, 
                           file_info={'manifest_file_id': 'ggl_access_log_activity'})
    
    if result:
        print("Parsed fields:")
        for key in sorted(result.keys()):
            print(f"  {key}: {result[key]}")
    else:
        print("(No fields parsed)")
    
    print("-" * 80)
