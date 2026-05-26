import json
import os

from cryptography.fernet import Fernet, MultiFernet


def encryptor(password):
    password = password.encode()
    key = Fernet.generate_key()
    f = Fernet(key)
    encrypted = f.encrypt(password)
    decoded = encrypted.decode()
    key = key.decode()
    return decoded, key


def decrypt(data):
    password = data[0]
    key = data[1]
    f = Fernet(key)
    decrypted = f.decrypt(password)
    return decrypted.decode()
