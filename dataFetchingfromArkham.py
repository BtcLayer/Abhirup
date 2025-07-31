# import requests
# import json
# import pandas as pd
# from collections import defaultdict
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials
# import time
# from datetime import datetime
# import os
# import hashlib

# # List of target accounts
# TARGET_ACCOUNTS = [
#     '0xF02e86D9E0eFd57aD034FaF52201B79917fE0713',
#     '0x52cfa98fb7339f6e2e70f2f68acbb7b7dcebe46a',
#     '0xB224228b0Fe71ceBf95EE25339166CD626759b52',
#     '0x274d9E726844AB52E351e8F1272e7fc3f58B7E5F',
#     '0x8Fa4EE1776032B612206E754eC2382b534D4ac6F',
#     '0x2291f52bddc937b5b840d15e551e1da8c80c2b3c',
#     '0x006A46eD4fA06E0c8abf4394E7794D5cFB7eB992',
#     '0x4cc7a9a050a90b73ef1122a4fa665a9dd11683a8',
#     '0x5d66c1782664115999c47c9fa5cd031f495d3e4f',
#     '0x8d15f64920dda38883b0bb44129c1f660392e167',
#     '0xeadc152AC1014acE57C6b353F89adF5FaFfE9D55',
#     '0xd85351181b3f264ee0fdfa94518464d7c3defada',
#     '0xF5a5409aD9894F74a3cE4b89520F59708a288372',
#     '0x5efc9d10e42fb517456f4ac41eb5e2ebe42c8918',
#     '0x0f3a1bfd2a873c36bae8a7d442247fe4b8b88a69',
#     '0xC76C7253592E27f090019f9949585366f799d6f7',
#     '0xA5068741AEcfEb8F8ff503D6E73E13B6586a6980',
#     '0x40B5A4CcFC57f43aD6b8FD77C590B7F4174872b3',
#     '0xd007058e9b58E74C33c6bF6fbCd38BaAB813cBB6',
#     '0xE887312c0595a10aC88e32ebb8e9F660Ad9aB7F7',
#     '0xd5ec14a83b7d95be1e2ac12523e2dee12cbeea6c',
#     '0xF965A1210B41d72c5FAca937d8F3834A8816Db4f',
#     '0x50D1B550f854b785cEDf754114e28D496c8A89C1',
#     '0x6297f7efa107ef33bd0d287d1d4410dd40b3bd96',
#     '0x3744DA57184575064838BBc87A0FC791F5E39eA2',
#     '0x1C11BA15939E1C16eC7ca1678dF6160Ea2063Bc5',
#     '0xB175e4B5458f125A6E96f0A146F20da656BE5e88',
#     '0xf304A4229561AEBa13425710acf1F46c9f24f1EB',
#     '0x88e529A6ccd302c948689Cd5156C83D4614FAE92',
#     '0x11dbF181dD5c075C2abD92Cb9579c4809406b5Be',
#     '0x0C329C0566476e4c3dc7692842EEeFB580e6d368',
#     '0x2fb074FA59c9294c71246825C1c9A0c7782d41a4',
#     '0xf584F8728B874a6a5c7A8d4d387C9aae9172D621',
#     '0x7da82C7AB4771ff031b66538D2fB9b0B047f6CF9',
#     '0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe',
#     '0x3a3C006053a9B40286B9951A11bE4C5808c11dc8',
#     '0x5109EBF8dA80411187F861592c0AF48B95376Dc9',
#     '0xF9B43deb017253448eea94Ad790dB67541487021',
#     '0xeD9b8F05224B881A222ece2E20Bd2F4BdB71D0F8',
#     '0x9168765ee952de7c6f8fc6fad5ec209b960b7622',
#     '0x1a2ed985A0318B2b9a6E17168F9Ca03c048AC35A'
# ]
# SHEET_ID = "1c04Mf3QpGDa0TunD6El9othMyjccc8hOcLrWaaJUdyM"
# SCOPE = ["https://spreadsheets.google.com/feeds", 
#          "https://www.googleapis.com/auth/drive"]
# CREDS_FILE = "service_account.json"  # Your service account credentials file

# class GoogleSheetUpdater:
#     def __init__(self):
#         self.client = None
#         self.sheet = None
#         self.worksheets = {}
#         self.seen_hashes = defaultdict(set)
        
#     def connect(self):
#         """Authenticate with Google Sheets API"""
#         try:
#             creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
#             self.client = gspread.authorize(creds)
#             print("Successfully connected to Google Sheets API")
#             return True
#         except Exception as e:
#             print(f"Failed to connect to Google Sheets: {e}")
#             return False
    
#     def get_sheet(self):
#         """Access the existing Google Sheet"""
#         try:
#             self.sheet = self.client.open_by_key(SHEET_ID)
#             print(f"Accessed existing sheet: {self.sheet.title}")
#             return True
#         except Exception as e:
#             print(f"Failed to access sheet: {e}")
#             return False
    
#     def initialize_worksheets(self):
#         """Get all required worksheets"""
#         sheet_names = {
#             'transfers': 'Transfers',
#             'swaps': 'Swaps',
#             'inflow': 'Inflow',
#             'outflow': 'Outflow',
#             'balances_tokens': 'Balances_Tokens',
#             'balances_totals': 'Balances_Totals'
#         }
        
#         for key, name in sheet_names.items():
#             try:
#                 self.worksheets[key] = self.sheet.worksheet(name)
#                 print(f"Accessed worksheet: {name}")
#             except Exception as e:
#                 print(f"Error accessing worksheet {name}: {e}")
#                 return False
#         return True
    
#     def get_data_hash(self, row):
#         """Generate unique hash for a row of data"""
#         return hashlib.md5(str(row).encode()).hexdigest()
    
#     def update_worksheet(self, worksheet_name: str, df: pd.DataFrame):
#         """Update worksheet with new data, skipping duplicates"""
#         if df.empty:
#             return
        
#         try:
#             worksheet = self.worksheets[worksheet_name]
#             existing_data = worksheet.get_all_records()
#             existing_df = pd.DataFrame(existing_data)
            
#             # Filter new rows
#             new_rows = []
#             for _, row in df.iterrows():
#                 row_hash = self.get_data_hash(row)
#                 if row_hash not in self.seen_hashes[worksheet_name]:
#                     new_rows.append(row)
#                     self.seen_hashes[worksheet_name].add(row_hash)
            
#             if new_rows:
#                 new_df = pd.DataFrame(new_rows)
#                 worksheet.append_rows(new_df.values.tolist())
#                 print(f"Added {len(new_df)} new rows to {worksheet_name}")
#             else:
#                 print(f"No new data to append to {worksheet_name}")
                
#         except Exception as e:
#             print(f"Error updating worksheet {worksheet_name}: {e}")
# # --------- API Setup ---------
# BASE_URLS = {
#     "transfers": "https://api.arkm.com/transfers?base={address}&flow=all&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens=",
#     "balances": "https://api.arkm.com/balances/address/{address}",
#     "swaps": "https://api.arkm.com/swaps?for={address}&sortKey=time&sortDir=desc&limit=16&offset=0",
#     "inflow": "https://api.arkm.com/transfers?base={address}&flow=in&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens=",
#     "outflow": "https://api.arkm.com/transfers?base={address}&flow=out&usdGte=1&sortKey=time&sortDir=desc&limit=16&offset=0&tokens="
# }

# headers = {
#     "Accept": "application/json, text/plain, */*",
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
#     "Origin": "https://intel.arkm.com",
#     "Referer": "https://intel.arkm.com/",
#     "X-Payload": "aefe32cea2c4a2eb303e1e6ee59fa451de3821e7578a350859b69894a3e8ed48",
#     "X-Timestamp": "1752663115",
# }

# cookies = {
#     "arkham_is_authed": "true",
#     "arkham_platform_session": "90f2b6be-c860-44d3-a0f5-764e5655a6e3"
# }

# def fetch_and_combine_data():
#     combined_data = {
#         "transfers": {"transfers": []},
#         "balances": {"balances": defaultdict(list), "totalBalance": {}, "totalBalance24hAgo": {}},
#         "swaps": {"swaps": []},
#         "inflow": {"transfers": []},
#         "outflow": {"transfers": []}
#     }

#     for account in TARGET_ACCOUNTS:
#         print(f"\nFetching data for {account}...")
        
#         for endpoint, base_url in BASE_URLS.items():
#             url = base_url.format(address=account)
#             try:
#                 print(f"  - {endpoint}")
#                 response = requests.get(url, headers=headers, cookies=cookies)
                
#                 if response.status_code == 200:
#                     data = response.json()
                    
#                     if endpoint == "balances":
#                         # Process balances data
#                         for chain, tokens in data.get("balances", {}).items():
#                             for token in tokens:
#                                 token['account'] = account  # Add account info
#                                 combined_data["balances"]["balances"][chain].append(token)
                        
#                         # Process total balances
#                         for chain, value in data.get("totalBalance", {}).items():
#                             combined_data["balances"]["totalBalance"][f"{account}_{chain}"] = value
                        
#                         for chain, value in data.get("totalBalance24hAgo", {}).items():
#                             combined_data["balances"]["totalBalance24hAgo"][f"{account}_{chain}"] = value
                    
#                     elif endpoint in ["transfers", "inflow", "outflow"]:
#                         for transfer in data.get("transfers", []):
#                             transfer['account'] = account  # Add account info
#                             combined_data[endpoint]["transfers"].append(transfer)
                    
#                     elif endpoint == "swaps":
#                         for swap in data.get("swaps", []):
#                             swap['account'] = account  # Add account info
#                             combined_data["swaps"]["swaps"].append(swap)
                
#                 else:
#                     print(f"Failed for {account} {endpoint}: HTTP {response.status_code}")
            
#             except Exception as e:
#                 print(f"Error fetching {account} {endpoint}: {str(e)}")

#     # Save combined JSON files
#     for endpoint, data in combined_data.items():
#         # Convert defaultdict to regular dict for JSON serialization
#         if endpoint == "balances":
#             data["balances"] = dict(data["balances"])
        
#         with open(f"{endpoint}.json", "w") as f:
#             json.dump(data, f, indent=4)
#         print(f"Saved combined {endpoint}.json")

# def json_to_csv():
#     # Process swaps
#     with open("swaps.json", "r") as f:
#         swaps_data = json.load(f)
#     pd.json_normalize(swaps_data["swaps"]).to_csv("swaps.csv", index=False)
#     print("Saved swaps.csv")

#     # Process transfers
#     with open("transfers.json", "r") as f:
#         transfers_data = json.load(f)
#     pd.json_normalize(transfers_data["transfers"]).to_csv("transfers.csv", index=False)
#     print("Saved transfers.csv")

#     # Process inflow
#     with open("inflow.json", "r") as f:
#         inflow_data = json.load(f)
#     pd.json_normalize(inflow_data["transfers"]).to_csv("inflow.csv", index=False)
#     print("Saved inflow.csv")

#     # Process outflow
#     with open("outflow.json", "r") as f:
#         outflow_data = json.load(f)
#     pd.json_normalize(outflow_data["transfers"]).to_csv("outflow.csv", index=False)
#     print("Saved outflow.csv")

#     # Process balances
#     with open("balances.json", "r") as f:
#         balances_data = json.load(f)
    
#     # Token-level balances
#     token_rows = []
#     for chain, tokens in balances_data.get("balances", {}).items():
#         for token in tokens:
#             token['chain'] = chain
#             token_rows.append(token)
#     pd.DataFrame(token_rows).to_csv("balances_tokens.csv", index=False)
#     print("Saved balances_tokens.csv")

#     # Chain-level total balance summary
#     now = balances_data.get("totalBalance", {})
#     past = balances_data.get("totalBalance24hAgo", {})
#     rows = []
#     for key in set(now.keys()).union(past.keys()):
#         account_chain = key.split('_')
#         rows.append({
#             "account": account_chain[0],
#             "chain": account_chain[1] if len(account_chain) > 1 else "",
#             "totalBalance": now.get(key, 0),
#             "totalBalance24hAgo": past.get(key, 0),
#             "balanceChange": now.get(key, 0) - past.get(key, 0)
#         })
#     pd.DataFrame(rows).to_csv("balances_totals.csv", index=False)
#     print("Saved balances_totals.csv")
# # --------- Main Function ---------
# def main():
#     fetch_and_combine_data()
#     json_to_csv()

# if __name__ == "__main__":
#     main()
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