import requests
import json
import pandas as pd
from collections import defaultdict
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime
import os
import hashlib
import math
def sanitize_value(value):
    """Convert out-of-range floats to JSON-compatible values"""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if abs(value) > 1e15:  # Very large numbers
            return str(value)
        if abs(value) < 1e-10 and value != 0:
            return 0
    return value

def sanitize_row(row):
    """Process all values in a row"""
    return [sanitize_value(x) for x in row]
# Google Sheets configuration
SHEET_ID = "1c04Mf3QpGDa0TunD6El9othMyjccc8hOcLrWaaJUdyM"
SCOPE = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "service_account.json"  # Replace with your credentials file

# List of target accounts
TARGET_ACCOUNTS = [
    '0xF02e86D9E0eFd57aD034FaF52201B79917fE0713',
    '0x52cfa98fb7339f6e2e70f2f68acbb7b7dcebe46a'
]

# API Setup
BASE_URLS = {
    "transfers": "https://api.arkm.com/transfers?base={address}&flow=all&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens=",
    "balances": "https://api.arkm.com/balances/address/{address}",
    "swaps": "https://api.arkm.com/swaps?for={address}&sortKey=time&sortDir=desc&limit=16&offset=0",
    "inflow": "https://api.arkm.com/transfers?base={address}&flow=in&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens=",
    "outflow": "https://api.arkm.com/transfers?base={address}&flow=out&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens="
}

headers = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Origin": "https://intel.arkm.com",
    "Referer": "https://intel.arkm.com/",
    "X-Payload": "aefe32cea2c4a2eb303e1e6ee59fa451de3821e7578a350859b69894a3e8ed48",
    "X-Timestamp": "1752663115",
}

cookies = {
    "arkham_is_authed": "true",
    "arkham_platform_session": "90f2b6be-c860-44d3-a0f5-764e5655a6e3"
}


class GoogleSheetUpdater:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheets = {}
        self.seen_hashes = defaultdict(set)
        
    def connect(self):
        """Authenticate with Google Sheets API"""
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
            self.client = gspread.authorize(creds)
            print("✅ Successfully connected to Google Sheets API")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Google Sheets: {e}")
            return False
    
    def get_sheet(self):
        """Access the existing Google Sheet"""
        try:
            self.sheet = self.client.open_by_key(SHEET_ID)
            print(f"📄 Accessed sheet: {self.sheet.title}")
            return True
        except Exception as e:
            print(f"❌ Failed to access sheet: {e}")
            return False
    
    def initialize_worksheets(self):
        """Get all required worksheets with exact name matching"""
        sheet_mapping = {
            'transfers': 'transfers',
            'swaps': 'swaps',
            'inflow': 'inflow',
            'outflow': 'outflow',
            'balances_tokens': 'balances_tokens',
            'balances_totals': 'balances_totals'
        }
        
        for key, name in sheet_mapping.items():
            try:
                # Clear existing worksheet if it has data
                worksheet = self.sheet.worksheet(name)
                worksheet.clear()
                self.worksheets[key] = worksheet
                print(f"✔️ Prepared worksheet: {name}")
            except gspread.WorksheetNotFound:
                print(f"⚠️ Worksheet '{name}' not found. Creating...")
                try:
                    self.worksheets[key] = self.sheet.add_worksheet(
                        title=name, rows=1000, cols=20
                    )
                    print(f"✅ Created worksheet: {name}")
                except Exception as e:
                    print(f"❌ Failed to create worksheet: {e}")
                    return False
            except Exception as e:
                print(f"❌ Error accessing worksheet: {e}")
                return False
        return True

    def update_worksheet(self, worksheet_name: str, df: pd.DataFrame):
        """Completely refresh worksheet with new data"""
        if df.empty:
            print(f"⚠️ No data for {worksheet_name}")
            return
        
        try:
            worksheet = self.worksheets[worksheet_name]
            
            # Clear existing content
            worksheet.clear()
            
            # Add headers (no sanitization needed for headers)
            headers = df.columns.tolist()
            worksheet.append_row(headers)
            
            # Add all data rows WITH SANITIZATION
            data = df.values.tolist()
            for i in range(0, len(data), 100):  # Batch in chunks of 100
                batch = data[i:i+100]
                sanitized_batch = [sanitize_row(row) for row in batch]  # Using standalone function
                worksheet.append_rows(sanitized_batch)
            
            print(f"✅ Updated {worksheet_name} with {len(df)} rows")
            
        except Exception as e:
            print(f"❌ Failed to update {worksheet_name}: {e}")


def fetch_and_combine_data():
    """Fetch data from API and combine for all accounts"""
    print("\n🔍 Fetching data from API...")
    combined_data = {
        "transfers": {"transfers": []},
        "balances": {"balances": defaultdict(list), "totalBalance": {}, "totalBalance24hAgo": {}},
        "swaps": {"swaps": []},
        "inflow": {"transfers": []},
        "outflow": {"transfers": []}
    }

    for account in TARGET_ACCOUNTS:
        print(f"  🐋 Processing {account[:6]}...{account[-4:]}")
        
        for endpoint, base_url in BASE_URLS.items():
            url = base_url.format(address=account)
            try:
                response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if endpoint == "balances":
                        for chain, tokens in data.get("balances", {}).items():
                            for token in tokens:
                                token['account'] = account
                                combined_data["balances"]["balances"][chain].append(token)
                        
                        for chain, value in data.get("totalBalance", {}).items():
                            combined_data["balances"]["totalBalance"][f"{account}_{chain}"] = value
                        
                        for chain, value in data.get("totalBalance24hAgo", {}).items():
                            combined_data["balances"]["totalBalance24hAgo"][f"{account}_{chain}"] = value
                    
                    elif endpoint in ["transfers", "inflow", "outflow"]:
                        for transfer in data.get("transfers", []):
                            transfer['account'] = account
                            combined_data[endpoint]["transfers"].append(transfer)
                    
                    elif endpoint == "swaps":
                        for swap in data.get("swaps", []):
                            swap['account'] = account
                            combined_data["swaps"]["swaps"].append(swap)
                
            except Exception as e:
                print(f"⚠️ Error fetching {endpoint} for {account}: {e}")

    # Save combined JSON files
    for endpoint, data in combined_data.items():
        if endpoint == "balances":
            data["balances"] = dict(data["balances"])
        
        with open(f"{endpoint}.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Saved {endpoint}.json")
    
    return combined_data

def process_data_to_sheets(gsheet_updater, combined_data):
    """Process data and update Google Sheets"""
    print("\n📤 Updating Google Sheets...")
    
    # Process and update each worksheet
    try:
        # Transfers
        transfers_df = pd.json_normalize(combined_data["transfers"]["transfers"])
        gsheet_updater.update_worksheet('transfers', transfers_df)
        
        # Inflow
        inflow_df = pd.json_normalize(combined_data["inflow"]["transfers"])
        gsheet_updater.update_worksheet('inflow', inflow_df)
        
        # Outflow
        outflow_df = pd.json_normalize(combined_data["outflow"]["transfers"])
        gsheet_updater.update_worksheet('outflow', outflow_df)
        
        # Swaps
        swaps_df = pd.json_normalize(combined_data["swaps"]["swaps"])
        gsheet_updater.update_worksheet('swaps', swaps_df)
        
        # Balances Tokens
        token_rows = []
        for chain, tokens in combined_data["balances"]["balances"].items():
            for token in tokens:
                token['chain'] = chain
                token_rows.append(token)
        balances_tokens_df = pd.DataFrame(token_rows)
        gsheet_updater.update_worksheet('balances_tokens', balances_tokens_df)
        
        # Balances Totals
        rows = []
        now = combined_data["balances"]["totalBalance"]
        past = combined_data["balances"]["totalBalance24hAgo"]
        for key in set(now.keys()).union(past.keys()):
            account_chain = key.split('_')
            rows.append({
                "account": account_chain[0],
                "chain": account_chain[1] if len(account_chain) > 1 else "",
                "totalBalance": now.get(key, 0),
                "totalBalance24hAgo": past.get(key, 0),
                "balanceChange": now.get(key, 0) - past.get(key, 0)
            })
        balances_totals_df = pd.DataFrame(rows)
        gsheet_updater.update_worksheet('balances_totals', balances_totals_df)
        
    except Exception as e:
        print(f"❌ Error processing data: {e}")

def main():
    print("\n" + "="*50)
    print("🐋 WHALE ACTIVITY DASHBOARD UPDATER")
    print("="*50 + "\n")
    
    # Initialize Google Sheets connection
    gsheet_updater = GoogleSheetUpdater()
    if not gsheet_updater.connect() or not gsheet_updater.get_sheet():
        return
    
    if not gsheet_updater.initialize_worksheets():
        return
    
    while True:
        start_time = time.time()
        print(f"\n🔄 Starting update at {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Fetch and process data
            combined_data = fetch_and_combine_data()
            process_data_to_sheets(gsheet_updater, combined_data)
            
            elapsed = time.time() - start_time
            print(f"\n✅ Update completed in {elapsed:.1f} seconds")
            
        except Exception as e:
            print(f"\n❌ Update failed: {e}")
        
        # Wait 5 minutes before next run
        sleep_time = max(0, 300 - (time.time() - start_time))
        print(f"\n😴 Next update in {sleep_time//60} minutes...")
        time.sleep(sleep_time)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user")
