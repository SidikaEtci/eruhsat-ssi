"""
Simple & Secure Authentication System
No JWT required - uses session tokens
"""
import hashlib
import secrets
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

# Setup paths without config dependency
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)


class AuthManager:
    """Session-based authentication manager"""
    
    def __init__(self):
        self.users_file = DATA_DIR / "users.json"
        self.sessions_file = DATA_DIR / "sessions.json"
        self.sessions: Dict[str, dict] = {}
        
        # Initialize
        self._init_default_users()
        self._load_sessions()
    
    def _init_default_users(self):
        """Create default users if not exist"""
        if not self.users_file.exists():
            default_users = {
                "admin": {
                    "password_hash": self._hash_password("admin123"),
                    "role": "admin",
                    "name": "System Administrator",
                    "created_at": datetime.now().isoformat()
                },
                "zabita": {
                    "password_hash": self._hash_password("zabita123"),
                    "role": "officer",
                    "name": "Enforcement Officer",
                    "created_at": datetime.now().isoformat()
                }
            }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(default_users, f, indent=2, ensure_ascii=False)
            
            print("\n   Default users created:")
            print("     admin / admin123 (Administrator)")
            print("     zabita / zabita123 (Officer)\n")
    
    _PASSWORD_SALT = "turkey_elicense_platform_2024"
    _LEGACY_PASSWORD_SALT = "konya_eruhsat_2024"

    def _hash_password(self, password: str, salt: str | None = None) -> str:
        """Hash password with SHA-256"""
        salt = salt or self._PASSWORD_SALT
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        if stored_hash == self._hash_password(password):
            return True
        return stored_hash == self._hash_password(password, self._LEGACY_PASSWORD_SALT)

    def _upgrade_password_hash(self, username: str, password: str) -> None:
        """Re-hash with current salt after a successful legacy login."""
        with open(self.users_file, "r", encoding="utf-8") as file:
            users = json.load(file)
        users[username]["password_hash"] = self._hash_password(password)
        with open(self.users_file, "w", encoding="utf-8") as file:
            json.dump(users, file, indent=2, ensure_ascii=False)
    
    def _load_sessions(self):
        """Load active sessions from file"""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
                
                # Clean expired sessions
                self._clean_expired_sessions()
            except:
                self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to file"""
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(self.sessions, f, indent=2, ensure_ascii=False)
    
    def _clean_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = []
        
        for token, session in self.sessions.items():
            expires_at = datetime.fromisoformat(session['expires_at'])
            if now > expires_at:
                expired.append(token)
        
        for token in expired:
            del self.sessions[token]
        
        if expired:
            self._save_sessions()
    
    def login(self, username: str, password: str) -> Optional[dict]:
        """
        Authenticate user and create session
        
        Returns:
            dict with token and user info if successful
            None if authentication fails
        """
        # Load users
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except:
            print("   Cannot load users file")
            return None
        
        # Check username
        if username not in users:
            print(f"   User not found: {username}")
            return None
        
        user = users[username]
        
        # Verify password (supports legacy salt from older deployments)
        if not self._verify_password(password, user["password_hash"]):
            print(f"   Wrong password for: {username}")
            return None

        if user["password_hash"] != self._hash_password(password):
            self._upgrade_password_hash(username, password)
        
        # Create session token
        token = secrets.token_urlsafe(32)
        
        # Session expires in 8 hours
        expires_at = datetime.now() + timedelta(hours=8)
        
        # Store session
        self.sessions[token] = {
            "username": username,
            "role": user["role"],
            "name": user["name"],
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        self._save_sessions()
        
        print(f"   User logged in: {username} ({user['role']})")
        
        return {
            "token": token,
            "username": username,
            "role": user["role"],
            "name": user["name"],
            "expires_at": expires_at.isoformat()
        }
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify session token
        
        Returns:
            User info if valid
            None if invalid or expired
        """
        if not token or token not in self.sessions:
            return None
        
        session = self.sessions[token]
        
        # Check expiration
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            # Remove expired session
            del self.sessions[token]
            self._save_sessions()
            return None
        
        return session
    
    def logout(self, token: str) -> bool:
        """
        Logout user (remove session)
        
        Returns:
            True if successful
            False if token not found
        """
        if token in self.sessions:
            username = self.sessions[token]["username"]
            del self.sessions[token]
            self._save_sessions()
            print(f"   User logged out: {username}")
            return True
        return False
    
    def get_active_sessions(self) -> list:
        """Get all active sessions (for admin)"""
        self._clean_expired_sessions()
        return [
            {
                "username": session["username"],
                "name": session["name"],
                "role": session["role"],
                "created_at": session["created_at"]
            }
            for session in self.sessions.values()
        ]


# Test
if __name__ == "__main__":
    print("\n" + "="*60)
    print("AUTHENTICATION SYSTEM TEST")
    print("="*60 + "\n")
    
    auth = AuthManager()
    
    # Test login
    print("Test 1: Login zabita")
    result = auth.login("zabita", "zabita123")
    
    if result:
        print("   Success!")
        print(f"Token: {result['token'][:30]}...")
        
        # Test verify
        print("\nTest 2: Verify token")
        verified = auth.verify_token(result["token"])
        print(f"   Verified: {verified['username']}")
        
        # Test logout
        print("\nTest 3: Logout")
        auth.logout(result["token"])
        print("   Logged out")
    else:
        print("   Login failed!")