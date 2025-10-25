import os, json, base64
from cryptography.fernet import Fernet
from solana.keypair import Keypair
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# SECURE SIGNER LOADER
# ==========================================================
def load_keypair_secure():
    """
    Safely load and decrypt Solana keypair using Fernet encryption.
    Requires:
      - ENCRYPTION_KEY in .env
      - SOL_KEYFILE_PATH in .env
    """
    key_path = os.getenv("SOL_KEYFILE_PATH")
    enc_key = os.getenv("ENCRYPTION_KEY")

    if not key_path or not enc_key:
        raise RuntimeError("Missing SOL_KEYFILE_PATH or ENCRYPTION_KEY in .env")

    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Keyfile not found at {key_path}")

    # Decrypt the keyfile
    with open(key_path, "rb") as f:
        encrypted_data = f.read()
    fernet = Fernet(enc_key.encode())
    decrypted = fernet.decrypt(encrypted_data)
    secret_list = json.loads(decrypted.decode())
    kp = Keypair.from_secret_key(bytes(secret_list))
    return kp
