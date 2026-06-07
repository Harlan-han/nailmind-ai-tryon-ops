"""Generate test data for operations dashboard."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User, NailDesign, TryOnRecord, Favorite, BookingIntent
from datetime import datetime, timedelta
import random

def generate_test_data():
    db = SessionLocal()

    print("=" * 60)
    print("生成测试数据")
    print("=" * 60)

    # Get test user
    user = db.query(User).filter(User.phone == "13800138000").first()
    if not user:
        user = User(phone="13800138000", nickname="测试用户", user_type="consumer")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get all designs
    designs = db.query(NailDesign).filter(NailDesign.status == "active").all()
    if not designs:
        print("错误: 没有款式数据，请先运行 seed.py")
        db.close()
        return

    print(f"\n找到 {len(designs)} 个款式")
    print(f"用户ID: {user.id}")

    # Clear existing test data (keep designs)
    db.query(BookingIntent).delete()
    db.query(Favorite).delete()
    db.query(TryOnRecord).delete()
    db.commit()

    # Reset design counts
    for design in designs:
        design.view_count = random.randint(10, 100)
        design.try_on_count = 0
        design.favorite_count = 0
        design.booking_count = 0
    db.commit()

    print("\n生成试戴记录...")

    # Generate try-on records for last 30 days
    today = datetime.now()
    for day in range(30):
        date = today - timedelta(days=day)

        # Random number of try-ons per day (5-20)
        num_try_ons = random.randint(5, 20)

        for _ in range(num_try_ons):
            design = random.choice(designs)

            # Create try-on record
            try_on = TryOnRecord(
                user_id=user.id,
                hand_photo_id=1,  # Mock hand photo
                nail_design_id=design.id,
                status="completed",
                result_image_url=design.image_url,  # Use design image as result
                is_favorite=random.random() < 0.3,  # 30% chance of being favorited
                is_candidate=random.random() < 0.2,  # 20% chance of being candidate
                has_booking_intent=random.random() < 0.1,  # 10% chance of booking
                created_at=date,
                completed_at=date
            )
            db.add(try_on)
            db.commit()
            db.refresh(try_on)

            # Update design stats
            design.try_on_count += 1

            # Create favorite if marked
            if try_on.is_favorite:
                favorite = Favorite(
                    user_id=user.id,
                    nail_design_id=design.id,
                    try_on_record_id=try_on.id
                )
                db.add(favorite)
                design.favorite_count += 1

            # Create booking if marked
            if try_on.has_booking_intent:
                booking = BookingIntent(
                    user_id=user.id,
                    try_on_record_id=try_on.id,
                    nail_design_id=design.id,
                    phone="13800138000",
                    preferred_date=date + timedelta(days=random.randint(1, 7)),
                    notes="测试预约"
                )
                db.add(booking)
                design.booking_count += 1

            db.commit()

    # Generate today's data specifically
    print("\n生成今日数据...")
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

    for _ in range(15):  # 15 try-ons today
        design = random.choice(designs)
        try_on = TryOnRecord(
            user_id=user.id,
            hand_photo_id=1,
            nail_design_id=design.id,
            status="completed",
            result_image_url=design.image_url,
            is_favorite=random.random() < 0.4,
            is_candidate=random.random() < 0.3,
            has_booking_intent=random.random() < 0.15,
            created_at=today_start + timedelta(hours=random.randint(8, 20)),
            completed_at=today_start + timedelta(hours=random.randint(8, 20))
        )
        db.add(try_on)
        db.commit()
        db.refresh(try_on)

        design.try_on_count += 1

        if try_on.is_favorite:
            favorite = Favorite(
                user_id=user.id,
                nail_design_id=design.id,
                try_on_record_id=try_on.id
            )
            db.add(favorite)
            design.favorite_count += 1

        if try_on.has_booking_intent:
            booking = BookingIntent(
                user_id=user.id,
                try_on_record_id=try_on.id,
                nail_design_id=design.id,
                phone="13800138000",
                preferred_date=today_start + timedelta(days=random.randint(1, 3)),
                notes="今日测试预约"
            )
            db.add(booking)
            design.booking_count += 1

        db.commit()

    # Update some designs as hot
    print("\n设置热门款式...")
    hot_designs = sorted(designs, key=lambda d: d.try_on_count, reverse=True)[:8]
    for design in hot_designs:
        design.is_hot = True
    db.commit()

    # Count final stats
    total_try_ons = db.query(TryOnRecord).count()
    total_favorites = db.query(Favorite).count()
    total_bookings = db.query(BookingIntent).count()
    today_try_ons = db.query(TryOnRecord).filter(TryOnRecord.created_at >= today_start).count()

    print("\n" + "=" * 60)
    print("测试数据生成完成!")
    print("=" * 60)
    print(f"总试戴记录: {total_try_ons}")
    print(f"总收藏: {total_favorites}")
    print(f"总预约: {total_bookings}")
    print(f"今日试戴: {today_try_ons}")
    print(f"热门款式: {len(hot_designs)}")
    print("\n你可以刷新运营后台查看数据了")
    print("=" * 60)

    db.close()

if __name__ == "__main__":
    generate_test_data()
