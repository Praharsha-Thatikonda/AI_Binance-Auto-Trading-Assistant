try:
    from web3 import Web3
    from eth_account import Account
    print("Web3 and Account imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
