from ytmusicapi import YTMusic
import traceback

try:
    print("Initializing...")
    # headers_auth.cfg is in ../setup/
    from os import path
    cfg_path = path.join(path.dirname(__file__), '..', 'setup', 'headers_auth.cfg')
    ytmusic = YTMusic(cfg_path)
    print("Initialized.")

    print("\n--- Available Methods ---")
    methods = [m for m in dir(ytmusic) if not m.startswith('_')]
    print(methods)
    print("-------------------------\n")

    if hasattr(ytmusic, 'get_account_info'):
        print("Calling get_account_info()...")
        try:
            info = ytmusic.get_account_info()
            print("Result:", info)
        except Exception:
            traceback.print_exc()
    else:
        print("get_account_info method does NOT exist.")

except Exception:
    traceback.print_exc()
