import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

emails = [
    "ssvignesh2003@gmail.com",
    "vigneshajri2003@gmail.com",
    "demo03985@gmail.com",
    "vigneshsajri@gmail.com",
    "1ms24mc105@msrit.edu",
    "ssvigga2003@gmail.com",
]

for email in emails:
    if not User.objects.filter(email=email).exists():
        # Django requires a username, we'll just use the email prefix
        username = email.split('@')[0]
        # In case usernames collide, just append something
        if User.objects.filter(username=username).exists():
            username = f"{username}_1"
        user = User.objects.create_user(username=username, email=email, password='password123')
        print(f"Created user: {email} with password 'password123'")
    else:
        print(f"User already exists: {email}")
