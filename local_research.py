import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import time
import config


class LocalResearchClient:
    def __init__(self, base_url: Optional[str] = None, username: str = "admin", password: str = "admin"):
        self.base_url = base_url or config.LOCAL_RESEARCH_URL
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        self._authenticated = False

    def is_service_running(self) -> bool:
        """Check if the local research service is running."""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            return response.status_code in [200, 302, 401, 403]
        except requests.exceptions.RequestException:
            return False

    def login(self) -> bool:
        """Authenticate with the local research service."""
        try:
            login_page = self.session.get(f"{self.base_url}/auth/login", timeout=10)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            login_csrf = csrf_input.get('value') if csrf_input else None

            if not login_csrf:
                return False

            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                data={
                    "username": self.username,
                    "password": self.password,
                    "csrf_token": login_csrf
                },
                timeout=10
            )

            if login_response.status_code in [200, 302]:
                csrf_response = self.session.get(
                    f"{self.base_url}/auth/csrf-token",
                    timeout=10
                )
                if csrf_response.status_code == 200:
                    self.csrf_token = csrf_response.json().get("csrf_token")
                    self._authenticated = True
                    return True

            return False
        except requests.exceptions.RequestException:
            return False

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

        headers = {"X-CSRF-Token": self.csrf_token}
        
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
        if not self.is_service_running():
            return {
                "error": "Local research service is not running. Start it with: docker compose up -d",
                "status": "service_unavailable"
            }

        if not self._authenticated and not self.login():
            return {
                "error": "Failed to authenticate with local research service",
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
    username: str = "admin",
    password: str = "admin"
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
