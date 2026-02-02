import sqlite3
import requests
import os
from time import sleep

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking all property images for 404 errors...\n")

# Get all images
cursor.execute("SELECT id, image_url, property_id FROM api_propertyimage ORDER BY property_id, id")
images = cursor.fetchall()

broken_images = []

for img_id, url, prop_id in images:
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        status = response.status_code
        
        if status == 404:
            print(f"[X] Property {prop_id}, Image ID {img_id}: 404 NOT FOUND")
            print(f"    URL: {url[:80]}...")
            broken_images.append((img_id, url, prop_id))
        elif status >= 400:
            print(f"[!] Property {prop_id}, Image ID {img_id}: HTTP {status}")
            print(f"    URL: {url[:80]}...")
            broken_images.append((img_id, url, prop_id))
        else:
            print(f"[OK] Property {prop_id}, Image ID {img_id}: {status}")
        
        sleep(0.1)  # Be nice to Unsplash
        
    except Exception as e:
        print(f"[X] Property {prop_id}, Image ID {img_id}: ERROR - {str(e)[:50]}")
        print(f"    URL: {url[:80]}...")
        broken_images.append((img_id, url, prop_id))

conn.close()

print(f"\n{'='*60}")
print(f"Summary: {len(broken_images)} broken images found out of {len(images)} total")
print(f"{'='*60}")

if broken_images:
    print("\nBroken images:")
    for img_id, url, prop_id in broken_images:
        print(f"  - Property {prop_id}, Image ID {img_id}")
else:
    print("\nAll images are working!")
