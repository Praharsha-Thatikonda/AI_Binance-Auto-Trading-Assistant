from web3 import Web3
from eth_account import Account
import secrets
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import AppGeneratedWallet, WalletBalance, WalletTransaction

class Web3Service:
    def __init__(self):
        self.w3 = Web3()
        # Enable features if needed, e.g. unaudited hdwallet
        Account.enable_unaudited_hdwallet_features()

    def create_wallet(self, db: Session, user_id: int):
        """Creates a new Web3 wallet for the user. Limit 24."""
        count = db.query(AppGeneratedWallet).filter(AppGeneratedWallet.user_id == user_id).count()
        if count >= 24:
            raise Exception("Maximum wallet limit (24) reached.")

        # Generate private key
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        
        wallet = AppGeneratedWallet(
            user_id=user_id,
            address=acct.address,
            private_key=private_key,
            created_at=str(datetime.now())
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
        return wallet

    def get_wallet(self, db: Session, user_id: int):
        # Return the first one as default/primary
        return db.query(AppGeneratedWallet).filter(AppGeneratedWallet.user_id == user_id).first()

    def get_wallets(self, db: Session, user_id: int):
        """Returns all wallets for the user."""
        return db.query(AppGeneratedWallet).filter(AppGeneratedWallet.user_id == user_id).all()

    def delete_wallet(self, db: Session, user_id: int, address: str):
        """Deletes a specific wallet for the user."""
        wallet = db.query(AppGeneratedWallet).filter(
            AppGeneratedWallet.user_id == user_id,
            AppGeneratedWallet.address == address
        ).first()
        
        if not wallet:
            raise Exception("Wallet not found")
            
        db.delete(wallet)
        db.commit()
        return True

    def process_internal_tx(self, web3_db: Session, wallet_db: Session, user_id: int, to_address: str, amount: float, currency: str = "ETH"):
        # 1. Get Sender Wallet
        sender_wallet = self.get_wallet(web3_db, user_id)
        if not sender_wallet:
            raise Exception("No Web3 wallet found. Please create one first.")

        # 2. Verify Sender Balance (Web3 Ledger)
        from app.database import Web3Balance
        balance_entry = wallet_db.query(Web3Balance).filter(
            Web3Balance.user_id == user_id,
            Web3Balance.currency == currency
        ).first()
        
        if not balance_entry or balance_entry.amount < amount:
            raise Exception("Insufficient balance")

        # 3. Verify Receiver (Internal Check)
        receiver_wallet = web3_db.query(AppGeneratedWallet).filter(AppGeneratedWallet.address == to_address).first()
        
        # If receiver is not internal, we still process it as a "send" but funds leave the system (burn)
        if not receiver_wallet:
            # Optional: Validate it's a valid checksum address if possible
            if not self.w3.is_address(to_address):
                 raise Exception("Invalid Ethereum address")
        
        # 4. Sign Transaction (Simulation of cryptographic intent)
        # We sign a dummy transaction to verify we have the key and generate a hash
        tx = {
            'to': to_address,
            'value': self.w3.to_wei(amount, 'ether'),
            'gas': 21000,
            'gasPrice': self.w3.to_wei('50', 'gwei'),
            'nonce': 0, # In a real app, we'd track nonce
            'chainId': 1337 
        }
        signed = Account.sign_transaction(tx, sender_wallet.private_key)
        tx_hash = signed.hash.hex()

        # 5. Execute Ledger Update
        balance_entry.amount -= amount
        balance_entry.updated_at = str(datetime.now())
        
        if receiver_wallet:
            receiver_balance = wallet_db.query(Web3Balance).filter(
                Web3Balance.user_id == receiver_wallet.user_id,
                Web3Balance.currency == currency
            ).first()
            if not receiver_balance:
                receiver_balance = Web3Balance(user_id=receiver_wallet.user_id, currency=currency, amount=0.0, updated_at=str(datetime.now()))
                wallet_db.add(receiver_balance)
            receiver_balance.amount += amount
            receiver_balance.updated_at = str(datetime.now())

        # 6. Record Transaction
        tx_record = WalletTransaction(
            user_id=user_id,
            type="WEB3_SEND",
            currency=currency,
            amount=amount,
            status="COMPLETED",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tx_hash=tx_hash,
            to_address=to_address,
            wallet_type="web3"
        )
        wallet_db.add(tx_record)
        wallet_db.commit()
        
        return {
            "tx_hash": tx_hash,
            "from": sender_wallet.address,
            "to": to_address,
            "amount": amount,
            "currency": currency
        }

web3_service = Web3Service()
