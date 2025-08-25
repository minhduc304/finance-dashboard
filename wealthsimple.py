import os
import getpass
import json
from datetime import datetime, timedelta
from ws_api import WealthsimpleAPI, WSAPISession
from typing import TextIO, List

SESSION_FILE = 'ws_session.json'
HOLDINGS_CACHE_FILE = 'holdings_cache.json'
CACHE_DURATION = timedelta(days=.25)


def persist_session(session_json) -> TextIO:
    with open(SESSION_FILE, 'w') as f:
        f.write(session_json)

def load_session() -> None:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return WSAPISession.from_json(f.read())
    return None

def show_account_activities(ws: WealthsimpleAPI, accounts: List, account_name: str, how_many=10) -> str:
    account_query = None
    for account in accounts:
        if account_name in account['id']:
            account_query = account
    
    activities = ws.get_activities(account_query['id'], how_many=how_many)
    print(f"\n--- Activity for {account_query['description']} ---")
    for activity in activities:
        print(f"  Date: {activity['occurredAt']}")
        print(f"  Description: {activity['description']}")
        print(f"  Amount: {activity['amount']} {activity['currency']}")
        print("-" * 20)

def refresh_cache():
    return None

def show_holdings_in_tfsa(ws: WealthsimpleAPI, accounts: List, symbol_format='both') -> str:
    # Check cache first
    if os.path.exists(HOLDINGS_CACHE_FILE):
        with open(HOLDINGS_CACHE_FILE, 'r') as f:
            try:
                cached_data = json.load(f)
                timestamp_str = cached_data.get('timestamp')
                cache_format = cached_data.get('format', 'both')
                if timestamp_str and cache_format == symbol_format:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if datetime.now() - timestamp < CACHE_DURATION:
                        print("\n--- Holdings for TFSA (from cache) ---")
                        for security_id, quantity in cached_data.get('holdings', {}).items():
                            print(f"{security_id}: {quantity}")
                        return
            except (json.JSONDecodeError, KeyError):
                # Invalid cache file, treat as cache miss
                pass

    # If cache is missed or stale, fetch from API
    tfsa_account = None
    for account in accounts:
        if 'TFSA' in account['description']:
            tfsa_account = account
            break

    if tfsa_account:
        print(f"\n--- Holdings for {tfsa_account['description']} ---")
        balances = ws.get_account_balances(tfsa_account['id'], symbol_format)
        
        # Save to cache
        with open(HOLDINGS_CACHE_FILE, 'w') as f:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'format': symbol_format,
                'holdings': balances
            }
            json.dump(cache_data, f)

        for security_id, quantity in balances.items():
            print(f"{security_id}: {quantity}")
    else:
        print("No TFSA account found.")

def main():
    session = load_session()
    ws = None

    if session:
        try:
            ws = WealthsimpleAPI.from_token(session, persist_session)
            print("Successfully logged in using saved session.")
        except Exception as e:
            print(f"Could not use saved session: {e}")
            ws = None

    if not ws:
        email = input("Enter your Wealthsimple email: ")
        password = getpass.getpass("Enter your Wealthsimple password: ")
        try:
            session_obj = WealthsimpleAPI.login(email, password, persist_session_fct=persist_session)
            ws = WealthsimpleAPI.from_token(session_obj, persist_session)
        except Exception as e:
            if "2FA code required" in str(e):
                otp = input("Enter your 2FA code: ")
                session_obj = WealthsimpleAPI.login(email, password, otp_answer=otp, persist_session_fct=persist_session)
                ws = WealthsimpleAPI.from_token(session_obj, persist_session)
            else:
                raise e
        print("Login successful.")
    
    accounts = ws.get_accounts()
    show_holdings_in_tfsa(ws, accounts, 'both')
    

if __name__ == "__main__":
    main()