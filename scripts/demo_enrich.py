"""Demo script showing enriched user course data."""
import asyncio
import httpx


async def demo():
    """Demonstrate the enriched user endpoint."""
    base_url = "http://localhost:8000"
    username = "PegCult"  # Replace with actual username
    
    async with httpx.AsyncClient() as client:
        print("\n=== Basic user courses (no enrichment) ===")
        response = await client.get(f"{base_url}/api/users/{username}")
        if response.status_code == 200:
            data = response.json()
            print(f"Username: {data['username']}")
            print(f"Is instructor: {data['is_instructor']}")
            print(f"Is student: {data['is_student']}")
            print(f"\nCourses ({len(data['courses'])}):")
            for course in data['courses']:
                print(f"  - {course['course_title']}")
                print(f"    Role: {course['user_role']}")
                print(f"    Slug: {course['course_slug']}")
                print(f"    Active: {course.get('active', 'N/A')}")
                print(f"    Staff: {course.get('staff', 'N/A')}")
        else:
            print(f"Error: {response.status_code}")
            
        print("\n" + "="*60)
        print("\n=== Enriched user courses (with active + staff) ===")
        response = await client.get(f"{base_url}/api/users/{username}?enrich=true")
        if response.status_code == 200:
            data = response.json()
            print(f"Username: {data['username']}")
            print(f"Is instructor: {data['is_instructor']}")
            print(f"Is student: {data['is_student']}")
            print(f"\nCourses ({len(data['courses'])}):")
            for course in data['courses']:
                print(f"  - {course['course_title']}")
                print(f"    Role: {course['user_role']}")
                print(f"    Slug: {course['course_slug']}")
                print(f"    Active: {course.get('active', 'N/A')}")
                if course.get('staff'):
                    print(f"    Staff ({len(course['staff'])}): {', '.join(course['staff'])}")
                else:
                    print(f"    Staff: N/A")
        else:
            print(f"Error: {response.status_code}")


if __name__ == "__main__":
    asyncio.run(demo())
