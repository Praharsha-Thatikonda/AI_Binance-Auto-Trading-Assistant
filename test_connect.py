import ccxt
import sys

def test_connection(api_key, api_secret, use_testnet=False):
    print(f"Testing connection... (Testnet: {use_testnet})")
    print(f"API Key Length: {len(api_key)}")
    print(f"Secret Key Length: {len(api_secret)}")
    
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        })
        
        if use_testnet:
            exchange.set_sandbox_mode(True)
            
        # 1. Check Time Sync
        print("Syncing time...")
        exchange.load_time_difference()
        print("Time synced.")

        # 2. Check Balance (Requires Permissions)
        print("Fetching balance...")
        balance = exchange.fetch_balance()
        print("SUCCESS! Connection established.")
        print("Balances:", [k for k, v in balance['total'].items() if v > 0])
        
    except ccxt.AuthenticationError as e:
        print("\nERROR: Authentication Failed (-2015)")
        print("Reasons:")
        print("1. IP Address not whitelisted (and 'Restrict access to trusted IPs' is ON).")
        print("2. 'Enable Spot & Margin Trading' permission is OFF in API settings.")
        print("3. API Key or Secret is wrong.")
        print(f"Original Error: {e}")
    except Exception as e:
        print(f"\nERROR: {str(e)}")

if __name__ == "__main__":
    print("--- Binance Connection Tester ---")
    key = input("Enter API Key: ").strip()
    secret = input("Enter Secret Key: ").strip()
    testnet = input("Use Testnet? (y/n): ").lower() == 'y'
    
    test_connection(key, secret, testnet)
