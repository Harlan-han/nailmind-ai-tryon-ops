"""Generate mock data to test the data loop."""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import random
from app.database import SessionLocal
from app.models import User, NailDesign, TryOnRecord, Favorite, BookingIntent, TrendDaily

db = SessionLocal()

# Get existing designs
designs = db.query(NailDesign).all()
if not designs:
    print("No designs found. Please run seed.py first.")
    sys.exit(1)

# Get or create test users
users = []
for i in range(10):
    phone = f"138001380{i:02d}"
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(
            phone=phone,
            nickname=f"用户{i+1}",
            user_type="consumer"
        )
        db.add(user)
        db.flush()
    users.append(user)

db.commit()

# Generate try-on records for the past 14 days
end_date = datetime.now()
start_date = end_date - timedelta(days=14)

styles = ['法式', '渐变', '猫眼', '裸色', '闪粉', '爱心', '花朵', '几何']
colors = ['粉色', '红色', '裸色', '白色', '黑色', '蓝色']

for day in range(15):
    current_date = start_date + timedelta(days=day)
    daily_try_ons = random.randint(20, 80)

    for _ in range(daily_try_ons):
        user = random.choice(users)
        design = random.choice(designs)

        # Random time within the day
        hour = random.randint(9, 22)
        minute = random.randint(0, 59)
        record_time = current_date.replace(hour=hour, minute=minute)

        try_on = TryOnRecord(
            user_id=user.id,
            hand_photo_id=None,
            nail_design_id=design.id,
            status="completed",
            is_favorite=random.random() < 0.3,
            is_candidate=random.random() < 0.2,
            has_booking_intent=random.random() < 0.1,
            created_at=record_time
        )
        db.add(try_on)

        # Update design stats
        design.try_on_count += 1
        if try_on.is_favorite:
            design.favorite_count += 1
        if try_on.has_booking_intent:
            design.booking_count += 1

    # Generate daily trend record
    daily_favorites = random.randint(5, 25)
    daily_bookings = random.randint(1, 10)

    style_trend = {}
    for _ in range(daily_try_ons):
        style = random.choice(styles)
        style_trend[style] = style_trend.get(style, 0) + 1

    trend = TrendDaily(
        date=current_date.replace(hour=0, minute=0, second=0),
        total_try_ons=daily_try_ons,
        total_favorites=daily_favorites,
        total_booking_intents=daily_bookings,
        unique_users=random.randint(10, 30),
        style_trend=style_trend,
        hot_designs=[d.id for d in random.sample(designs, min(3, len(designs)))],
        ai_summary=f"{current_date.strftime('%m月%d日')}试戴量{daily_try_ons}次，较昨日{'上升' if random.random() > 0.4 else '下降'}",
        ai_recommendations=[
            {"action": "加推热门款式", "target": random.choice(designs).name}
        ]
    )
    db.add(trend)

    db.commit()

print(f"Generated mock data:")
print(f"- {len(users)} test users")
print(f"- Try-on records for past 14 days")
print(f"- Daily trend records")
print(f"- Design stats updated")

db.close()
