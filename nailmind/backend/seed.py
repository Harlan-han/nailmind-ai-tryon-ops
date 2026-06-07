"""Seed script to populate the local database with bundled sample assets."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, Base, engine
from app.models import NailDesign, User
import os

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if we already have designs imported
existing_count = db.query(NailDesign).count()
if existing_count > 0:
    print(f"Database already has {existing_count} designs, skipping seed")
    db.close()
    sys.exit(0)

# Verify local sample images exist
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads", "designs")
if not os.path.exists(uploads_dir):
    print("Error: No uploads/designs directory found. Sync or copy sample assets first.")
    db.close()
    sys.exit(1)

# Create designs using bundled cover images
sample_designs = []
for i in range(1, 26):
    design_file = f"design_{i:02d}.jpg"
    design_path = os.path.join(uploads_dir, design_file)

    if os.path.exists(design_path):
        # Assign different tags based on design number for variety
        tag_options = [
            (["法式", "经典"], ["裸色", "白色"], ["日常", "通勤", "婚礼"]),
            (["渐变", "裸色"], ["裸色", "粉色"], ["日常", "通勤"]),
            (["猫眼", "闪粉"], ["灰色", "银色"], ["派对", "约会"]),
            (["爱心", "可爱"], ["粉色", "红色"], ["约会", "派对"]),
            (["红色", "节日"], ["红色", "金色"], ["节日", "派对"]),
            (["花朵", "手绘"], ["粉色", "白色"], ["日常", "约会"]),
            (["几何", "简约"], ["黑色", "白色"], ["通勤", "日常"]),
            (["极光", "闪粉"], ["粉色", "蓝色"], ["派对", "约会"]),
        ]
        tag_idx = (i - 1) % len(tag_options)
        style_tags, color_tags, scene_tags = tag_options[tag_idx]

        sample_designs.append({
            "name": f"款式 {i:02d}",
            "description": f"官方样例款式 #{i}",
            "image_url": f"/uploads/designs/{design_file}",
            "style_tags": style_tags,
            "color_tags": color_tags[:1],  # Just first color
            "scene_tags": scene_tags[:2],  # Just first two scenes
            "length": ["短", "中", "长"][(i-1) % 3],
            "shape": ["圆", "方", "椭圆", "杏仁"][(i-1) % 4],
            "is_hot": i <= 8,  # First 8 are hot
            "is_new": i > 17,  # Last few are new
        })

if len(sample_designs) == 0:
    print("Error: No sample design images found in uploads/designs/")
    db.close()
    sys.exit(1)

# Insert designs
for design_data in sample_designs:
    design = NailDesign(**design_data)
    db.add(design)

db.commit()

# Create a test user if not exists
test_user = db.query(User).filter(User.phone == "13800138000").first()
if not test_user:
    test_user = User(phone="13800138000", nickname="测试用户", user_type="consumer")
    db.add(test_user)
    db.commit()

print(f"Seeded {len(sample_designs)} sample nail designs from bundled assets")
db.close()
