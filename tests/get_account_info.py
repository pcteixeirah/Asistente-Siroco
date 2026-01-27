from ytmusicapi import YTMusic
import pprint

# 1. Initialize with your config file
try:
    from os import path
    cfg_path = path.join(path.dirname(__file__), '..', 'setup', 'headers_auth.cfg')
    ytmusic = YTMusic(cfg_path)
    
    # 2. Get account/channel information
    if hasattr(ytmusic, 'get_account_info'):
            user_info = ytmusic.get_account_info()
            print("Full Account Info:")
            pprint.pprint(user_info)
            
            # Handle potential key differences
            name = user_info.get('account_name') or user_info.get('accountName', 'Unknown')
            handle = user_info.get('channel_handle') or user_info.get('channelHandle', 'Unknown')
            
            print(f"\nAccount Name: {name}")
            print(f"Channel Handle: {handle}")
    else:
        print("Method 'get_account_info' not found. Using get_account_info (if available) or checking alternative.")


except Exception as e:
    print(f"Error initializing: {e}")
