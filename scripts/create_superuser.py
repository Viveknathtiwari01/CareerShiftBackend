import asyncio
import os
import sys

# Ensure the backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role
from app.services.security import SecurityService

async def create_superuser():
    print("=== Create Super Admin ===")
    email = input("Email:")
    username = input("Username:")
    password = input("Password:")
    first_name = input("First Name (optional):")
    last_name = input("Last Name (optional):")

    if not email or not username or not password:
        print("Error: Email, Username, and Password are required.")
        return

    hashed_pw = SecurityService.get_password_hash(password)

    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalars().first()
        if existing_user:
            print("Error: A user with this email already exists.")
            return
            
        # Ensure Super Admin role exists
        result = await db.execute(select(Role).where(Role.name == "Super Admin"))
        super_admin_role = result.scalars().first()
        
        if not super_admin_role:
            super_admin_role = Role(name="Super Admin", description="Full system access")
            db.add(super_admin_role)
            await db.commit()

        # Create the super user
        new_user = User(
            email=email,
            username=username,
            password_hash=hashed_pw,
            first_name=first_name,
            last_name=last_name
        )
        new_user.roles.append(super_admin_role)

        db.add(new_user)
        await db.commit()
        print(f"\nSuccess! Super Admin '{username}' created successfully.")

if __name__ == "__main__":
    asyncio.run(create_superuser())
