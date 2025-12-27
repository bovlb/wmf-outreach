"""Script to inspect raw API payloads for debugging."""
import asyncio
import sys
import json
from app.services.outreach import outreach_client


async def inspect_user(username: str):
    """Fetch and display user stats payload."""
    print(f"\n=== User Stats: {username} ===")
    data = await outreach_client.get_user_stats(username)
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("Failed to fetch user stats")


async def inspect_course_users(school: str, title_slug: str):
    """Fetch and display course users payload."""
    print(f"\n=== Course Users: {school}/{title_slug} ===")
    data = await outreach_client.get_course_users(school, title_slug)
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("Failed to fetch course users")


async def inspect_course_details(school: str, title_slug: str):
    """Fetch and display course details payload."""
    print(f"\n=== Course Details: {school}/{title_slug} ===")
    data = await outreach_client.get_course_details(school, title_slug)
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("Failed to fetch course details")


async def main():
    """Main inspection function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  User stats:       python inspect_payloads.py user <username>")
        print("  Course users:     python inspect_payloads.py course-users <school> <title_slug>")
        print("  Course details:   python inspect_payloads.py course-details <school> <title_slug>")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "user" and len(sys.argv) >= 3:
        await inspect_user(sys.argv[2])
    elif command == "course-users" and len(sys.argv) >= 4:
        await inspect_course_users(sys.argv[2], sys.argv[3])
    elif command == "course-details" and len(sys.argv) >= 4:
        await inspect_course_details(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
