"""HTTP client for Outreach Dashboard API."""
import httpx
from typing import Optional, Dict, Any
from app.config import settings


class OutreachDashboardClient:
    """Client for Outreach Dashboard API."""
    
    def __init__(self):
        """Initialize HTTP client."""
        self.base_url = settings.outreach_base_url
        self.timeout = httpx.Timeout(settings.http_timeout)
        
    async def get_user_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user stats from Outreach Dashboard.
        
        Args:
            username: Dashboard username
            
        Returns:
            User stats JSON or None on error
        """
        url = f"{self.base_url}/user_stats.json"
        params = {"username": username}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as e:
                print(f"Error fetching user stats for {username}: {e}")
                return None
                
    async def get_course_users(self, school: str, title_slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch course users/roster from Outreach Dashboard.
        
        Args:
            school: Course school slug
            title_slug: Course title slug
            
        Returns:
            Course users JSON or None on error
        """
        url = f"{self.base_url}/courses/{school}/{title_slug}/users.json"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as e:
                print(f"Error fetching course users for {school}/{title_slug}: {e}")
                return None
                
    async def get_course_details(self, school: str, title_slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch course details from Outreach Dashboard.
        
        Args:
            school: Course school slug
            title_slug: Course title slug
            
        Returns:
            Course details JSON or None on error
        """
        url = f"{self.base_url}/courses/{school}/{title_slug}/course.json"
        print(url)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as e:
                print(f"Error fetching course details for {school}/{title_slug}: {e}")
                return None


# Global client instance
outreach_client = OutreachDashboardClient()
