import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import time
import config


class LocalResearchClient:
    def __init__(self, base_url: Optional[str] = None, username: str = None, password: str = None, verbose: bool = False):
        self.base_url = base_url or config.LOCAL_RESEARCH_URL
        self.username = username or config.LDR_USERNAME
        self.password = password or config.LDR_PASSWORD
        self.session = requests.Session()
        self.csrf_token = None
        self._authenticated = False
        self.verbose = verbose

    def _log(self, msg: str):
        if self.verbose:
            print(f"[LDR] {msg}")

    def is_service_running(self) -> bool:
        """Check if the local research service is running."""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            return response.status_code in [200, 302, 401, 403, 404]
        except requests.exceptions.RequestException as e:
            self._log(f"Service not reachable: {e}")
            return False

    def _get_csrf_token(self, url: str) -> Optional[str]:
        """Extract CSRF token from a page."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                self._log(f"Failed to get page {url}: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            token = csrf_input.get('value') if csrf_input else None
            
            if not token:
                self._log("No CSRF token found in page")
            return token
        except Exception as e:
            self._log(f"Error getting CSRF token: {e}")
            return None

    def register_user(self) -> tuple[bool, str]:
        """Try to register a new user account. Returns (success, message)."""
        try:
            self._log(f"Attempting to register user '{self.username}'...")
            
            # Get registration page
            register_url = f"{self.base_url}/auth/register"
            register_page = self.session.get(register_url, timeout=10)
            
            if register_page.status_code == 404:
                self._log("Registration page not found - auth may be disabled")
                return True, "Registration page not found (auth likely disabled)"
            
            if register_page.status_code != 200:
                self._log(f"Registration page returned {register_page.status_code}")
                return False, f"Registration page returned {register_page.status_code}"
            
            # Extract CSRF token
            soup = BeautifulSoup(register_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            csrf_token = csrf_input.get('value') if csrf_input else None
            
            # Also try meta tag for CSRF
            if not csrf_token:
                csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                csrf_token = csrf_meta.get('content') if csrf_meta else None
            
            if not csrf_token:
                self._log("No CSRF token found, trying without it...")
            
            # Prepare registration data
            register_data = {
                "username": self.username,
                "password": self.password,
            }
            
            # Check for different password field names
            password_fields = ['confirm_password', 'confirmPassword', 'password_confirm', 'password2']
            for field in password_fields:
                if soup.find('input', {'name': field}):
                    register_data[field] = self.password
            
            if csrf_token:
                register_data["csrf_token"] = csrf_token

            self._log(f"Sending registration request with fields: {list(register_data.keys())}")
            
            register_response = self.session.post(
                register_url,
                data=register_data,
                timeout=10,
                allow_redirects=True
            )

            self._log(f"Registration response status: {register_response.status_code}")
            
            if register_response.status_code in [200, 302]:
                response_text = register_response.text.lower()
                
                # Check for success indicators
                if any(s in response_text for s in ["success", "registered", "account created", "welcome"]):
                    self._log("Registration successful!")
                    return True, "Registration successful"
                
                # Check if user already exists (also success - proceed to login)
                if any(s in response_text for s in ["already exists", "username taken", "already registered"]):
                    self._log("User already exists")
                    return True, "User already exists, proceeding to login"
                
                # Check for errors
                if any(s in response_text for s in ["error", "invalid", "failed"]):
                    # Extract error message if possible
                    self._log(f"Registration may have failed - check response")
                
                # If we got redirected to login or home page, registration likely succeeded
                if "/auth/login" in register_response.url or register_response.url.rstrip("/").endswith(":5000"):
                    self._log("Redirected after registration - likely success")
                    return True, "Registration request sent (redirected)"
                
                return True, "Registration request sent"
            
            return False, f"Registration failed with status {register_response.status_code}"
        except requests.exceptions.RequestException as e:
            self._log(f"Registration error: {e}")
            return False, f"Registration error: {e}"

    def login(self) -> tuple[bool, str]:
        """Authenticate with the local research service. Returns (success, message)."""
        try:
            self._log(f"Attempting to login as '{self.username}'...")
            
            csrf_token = self._get_csrf_token(f"{self.base_url}/auth/login")
            if not csrf_token:
                # Try without CSRF (some versions don't require it)
                self._log("No CSRF token, trying login without it...")

            login_data = {
                "username": self.username,
                "password": self.password,
            }
            if csrf_token:
                login_data["csrf_token"] = csrf_token

            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                data=login_data,
                timeout=10,
                allow_redirects=True
            )

            if login_response.status_code in [200, 302]:
                # Try to get API CSRF token
                try:
                    csrf_response = self.session.get(
                        f"{self.base_url}/auth/csrf-token",
                        timeout=10
                    )
                    if csrf_response.status_code == 200:
                        self.csrf_token = csrf_response.json().get("csrf_token")
                        self._authenticated = True
                        self._log("Login successful!")
                        return True, "Login successful"
                except:
                    pass
                
                # Even without API CSRF token, consider authenticated if login succeeded
                self._authenticated = True
                self._log("Login successful (no API CSRF token)")
                return True, "Login successful"

            # Check for specific error messages
            if "invalid" in login_response.text.lower() or "incorrect" in login_response.text.lower():
                return False, "Invalid username or password"
            
            self._log(f"Login failed with status {login_response.status_code}")
            return False, f"Login failed with status {login_response.status_code}"
        except requests.exceptions.RequestException as e:
            self._log(f"Login error: {e}")
            return False, f"Login error: {e}"

    def try_no_auth(self) -> bool:
        """Try to use the API without authentication (some LDR versions allow this)."""
        try:
            self._log("Checking if API works without authentication...")
            
            # Try various endpoints that might not require auth
            for endpoint in ["/api/settings", "/api/available_models", "/api/version"]:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        self._authenticated = True
                        self._log(f"API accessible without authentication via {endpoint}")
                        return True
                except:
                    continue
        except:
            pass
        return False
    
    def register_via_api(self) -> tuple[bool, str]:
        """Try to register via REST API (if LDR supports it)."""
        try:
            self._log("Trying API-based registration...")
            
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self._log("API registration successful!")
                return True, "API registration successful"
            
            return False, f"API registration returned {response.status_code}"
        except requests.exceptions.RequestException as e:
            self._log(f"API registration not available: {e}")
            return False, "API registration not available"

    def ensure_authenticated(self) -> tuple[bool, str]:
        """
        Ensure the client is authenticated, attempting registration if needed.
        
        Returns:
            Tuple of (success, error_message)
        """
        if self._authenticated:
            return True, ""
            
        if not self.is_service_running():
            return False, f"Local research service not running at {self.base_url}.\n\nStart it with:\n  curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.yml\n  MODEL=qwen3.5:4b docker compose up -d\n\nThen wait 30 seconds for it to initialize."
        
        # Try without auth first
        if self.try_no_auth():
            return True, ""
        
        # Try API-based registration (cleaner)
        api_success, api_msg = self.register_via_api()
        if api_success:
            time.sleep(0.5)
            success, msg = self.login()
            if success:
                return True, ""
        
        # Try login with provided credentials
        success, msg = self.login()
        if success:
            return True, ""
        
        self._log(f"Login failed: {msg}")
        
        # Try form-based registration
        reg_success, reg_msg = self.register_user()
        if reg_success:
            time.sleep(1)
            success, msg = self.login()
            if success:
                return True, ""
        
        # Try common default credentials
        default_creds = [
            ("admin", "admin"),
            ("admin", "password"),
            ("user", "user"),
        ]
        
        for user, pwd in default_creds:
            if user != self.username:
                self._log(f"Trying default credentials: {user}/{pwd}")
                self.username = user
                self.password = pwd
                success, msg = self.login()
                if success:
                    self._log(f"Authenticated with default credentials: {user}")
                    return True, ""
        
        return False, f"""Failed to authenticate with Local Deep Research.

AUTOMATIC AUTHENTICATION FAILED.

This usually means registration is disabled in LDR config.

QUICK FIX:
1. Open http://localhost:5000/auth/register in your browser
2. Create a user manually
3. Set credentials:
   export LDR_USERNAME="your_username"
   export LDR_PASSWORD="your_password"

OR disable LDR auth entirely by editing docker-compose.yml:
   Add: LDR_APP_ALLOW_REGISTRATIONS=true
   (and ensure the line is NOT commented out)"""

    def start_research(
        self,
        query: str,
        model: str = None,
        search_engines: List[str] = None,
        iterations: int = 2,
        questions_per_iteration: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Start a research task."""
        if not self._authenticated and not self.login():
            return None

        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token

        payload = {
            "query": query,
            "iterations": iterations,
            "questions_per_iteration": questions_per_iteration,
            "search_engines": search_engines or ["searxng", "wikipedia"]
        }

        if model:
            payload["model"] = model

        try:
            response = self.session.post(
                f"{self.base_url}/api/start_research",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_research_status(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a research task."""
        if not self._authenticated and not self.login():
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/api/research/{research_id}/status",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_research_results(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Get the results of a completed research task."""
        if not self._authenticated and not self.login():
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/api/report/{research_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def extract_stakeholders_with_llm(
        self,
        research_text: str,
        event_context: str
    ) -> List[Dict[str, Any]]:
        """
        Use LDR's built-in LLM to extract and quantify stakeholder data.
        
        This is used as a fallback when OpenRouter is not available.
        
        Args:
            research_text: The raw research output
            event_context: The original event query for context
            
        Returns:
            List of player dicts with position, salience, clout, resolve
        """
        success, error_msg = self.ensure_authenticated()
        if not success:
            return []
        
        extraction_prompt = f"""
Analyze the following research text about stakeholders in: "{event_context}"

Extract each stakeholder and rate them on these scales:

1. position (0-100): Their stance on the issue
   - 0 = Strongly against conflict escalation / pro-peace / pro-negotiation
   - 50 = Neutral / ambivalent / seeking balance
   - 100 = Strongly supports escalation / military action / hardline position

2. salience (0-100): How important this issue is to them
   - 0 = Low priority, many other concerns
   - 100 = Critical priority, central to their interests

3. clout (0.1-10.0): Their relative influence/power
   - 0.1 = Minimal influence
   - 1.0 = Average influence
   - 10.0 = Dominant power

4. resolve (0-100): How firm/unwavering is their position
   - 0 = Very flexible, easily swayed
   - 100 = Absolutely firm, will not compromise

Return ONLY a JSON array with this exact format:
[
  {{
    "id": "Stakeholder Name",
    "position": 85,
    "salience": 90,
    "clout": 2.5,
    "resolve": 75,
    "rationale": "Brief explanation of ratings"
  }}
]

Research text:
{research_text[:8000]}
"""
        
        try:
            headers = {"X-CSRF-Token": self.csrf_token}
            payload = {
                "query": extraction_prompt,
                "iterations": 1,
                "questions_per_iteration": 1,
                "search_engines": []
            }
            
            response = self.session.post(
                f"{self.base_url}/api/start_research",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            research_id = result.get("research_id")
            
            if not research_id:
                return []
            
            elapsed = 0
            while elapsed < 120:
                status = self.get_research_status(research_id)
                if status.get("status") == "completed":
                    results = self.get_research_results(research_id)
                    summary = results.get("summary", "")
                    
                    import re
                    import json as json_module
                    json_match = re.search(r'\[[\s\S]*\]', summary)
                    if json_match:
                        try:
                            players = json_module.loads(json_match.group())
                            return self._validate_players(players)
                        except json_module.JSONDecodeError:
                            pass
                    return []
                
                if status.get("status") == "failed":
                    return []
                
                time.sleep(3)
                elapsed += 3
            
            return []
        except requests.exceptions.RequestException:
            return []
    
    def _validate_players(self, players: List[Dict]) -> List[Dict[str, Any]]:
        """Validate and sanitize player data."""
        validated = []
        for p in players:
            try:
                validated.append({
                    "id": str(p.get("id", "Unknown"))[:50],
                    "position": max(0, min(100, float(p.get("position", 50)))),
                    "salience": max(0, min(100, float(p.get("salience", 50)))),
                    "clout": max(0.1, min(10.0, float(p.get("clout", 1.0)))),
                    "resolve": max(0, min(100, float(p.get("resolve", 50)))),
                    "rationale": str(p.get("rationale", ""))[:200]
                })
            except (ValueError, TypeError):
                continue
        return validated

    def search_stakeholders(
        self,
        event_query: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Search for stakeholders related to an event/conflict.
        
        Args:
            event_query: The event to research (e.g., "Iran war stakeholders")
            max_wait_seconds: Maximum time to wait for results
            poll_interval: Seconds between status checks
            
        Returns:
            Research results with stakeholder information
        """
        success, error_msg = self.ensure_authenticated()
        if not success:
            return {
                "error": error_msg,
                "status": "auth_failed"
            }

        enhanced_query = f"""
        Who are the key stakeholders, decision-makers, and influential parties in: {event_query}
        
        For each stakeholder, identify:
        1. Their official position and role
        2. Their stance on the issue (support/oppose/neutral)
        3. Their level of influence (high/medium/low)
        4. Their priorities and interests
        5. Their relationships with other stakeholders
        """

        start_result = self.start_research(
            query=enhanced_query,
            iterations=3,
            questions_per_iteration=4,
            search_engines=["searxng", "wikipedia"]
        )

        if "error" in start_result:
            return start_result

        research_id = start_result.get("research_id")
        if not research_id:
            return {"error": "Failed to start research", "details": start_result}

        elapsed = 0
        while elapsed < max_wait_seconds:
            status = self.get_research_status(research_id)
            
            if status.get("status") == "completed":
                results = self.get_research_results(research_id)
                results["research_id"] = research_id
                return results
            
            if status.get("status") == "failed":
                return {
                    "error": "Research failed",
                    "details": status,
                    "research_id": research_id
                }

            time.sleep(poll_interval)
            elapsed += poll_interval

        return {
            "error": "Research timed out",
            "research_id": research_id,
            "status": "timeout"
        }


def search_stakeholders(
    query: str,
    base_url: str = None,
    username: str = "researcher",
    password: str = "researcher123"
) -> Dict[str, Any]:
    """
    Convenience function to search for stakeholders.
    
    Args:
        query: Event/conflict to research
        base_url: Optional override for LDR URL
        username: Login username
        password: Login password
        
    Returns:
        Research results
    """
    client = LocalResearchClient(
        base_url=base_url,
        username=username,
        password=password
    )
    return client.search_stakeholders(query)
