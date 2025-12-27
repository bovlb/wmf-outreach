"""Demo script showing the active staff endpoint."""
import asyncio
import httpx


async def demo():
    """Demonstrate the active staff endpoint."""
    base_url = "http://localhost:8000"
    username = "PegCult"  # Replace with actual username
    
    async with httpx.AsyncClient() as client:
        print("\n=== Get all staff from active courses ===")
        response = await client.get(f"{base_url}/api/users/{username}/active-staff")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Username: {data['username']}")
            print(f"\nAll staff members ({len(data['all_staff'])}):")
            for staff_member in data['all_staff']:
                print(f"  - {staff_member}")
            
            print(f"\nActive courses with staff ({len(data['courses'])}):")
            for course in data['courses']:
                print(f"\n  📚 {course['course_title']}")
                print(f"     Slug: {course['course_slug']}")
                print(f"     Staff ({len(course['staff'])}): {', '.join(course['staff'])}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(demo())
