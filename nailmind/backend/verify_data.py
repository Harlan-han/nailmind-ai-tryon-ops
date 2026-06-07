"""验证数据完整性和图片可访问性."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import NailDesign
import os

def verify_data():
    db = SessionLocal()

    print("=" * 60)
    print("NailMind 数据验证报告")
    print("=" * 60)

    # 1. 检查数据库中的设计数量
    designs = db.query(NailDesign).all()
    print(f"\n1. 数据库中的款式数量: {len(designs)}")

    if len(designs) == 0:
        print("   警告: 数据库为空! 请先运行 seed.py")
        db.close()
        return

    # 2. 检查图片路径格式
    print("\n2. 检查图片路径格式:")
    for d in designs[:3]:
        print(f"   - {d.name}: {d.image_url}")

    # 3. 检查实际文件是否存在
    print("\n3. 检查图片文件是否存在:")
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads", "designs")

    if not os.path.exists(uploads_dir):
        print(f"   错误: 目录不存在: {uploads_dir}")
        db.close()
        return

    found = 0
    missing = []

    for d in designs:
        # 从 image_url 提取文件名
        filename = os.path.basename(d.image_url)
        filepath = os.path.join(uploads_dir, filename)

        if os.path.exists(filepath):
            found += 1
        else:
            missing.append(filename)

    print(f"   找到: {found}/{len(designs)} 张图片")

    if missing:
        print(f"   缺失: {missing[:5]}..." if len(missing) > 5 else f"   缺失: {missing}")

    # 4. 生成测试URL
    print("\n4. 图片访问URL示例:")
    for d in designs[:3]:
        print(f"   - http://localhost:8000{d.image_url}")

    print("\n5. 验证方法:")
    print("   - 直接浏览器访问上述URL看能否显示图片")
    print("   - 检查 frontend/.next/cache 是否清除")
    print("   - 检查浏览器 DevTools Network 面板")

    db.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    verify_data()
