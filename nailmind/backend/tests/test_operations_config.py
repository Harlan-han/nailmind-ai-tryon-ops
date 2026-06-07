import unittest


class OperationsConfigTest(unittest.TestCase):
    def _create_memory_db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def test_config_collects_effective_backend_tags_from_active_designs(self):
        from app import models
        from app.services.operations_config import build_operations_config

        db = self._create_memory_db()
        try:
            db.add(
                models.NailDesign(
                    name="款式 20",
                    image_url="/uploads/designs/design_20.jpg",
                    style_tags=["爱心", "可爱"],
                    color_tags=["粉色"],
                    scene_tags=["约会"],
                    status="active",
                )
            )
            db.commit()

            config = build_operations_config(db, saved_config={})

            self.assertIn("奶牛纹", config["styleTags"])
            self.assertIn("银色", config["colorTags"])
            self.assertIn("甜酷", config["sceneTags"])
            self.assertNotIn("爱心", config["styleTags"])
        finally:
            db.close()

    def test_saved_custom_tags_are_merged_with_design_tags(self):
        from app import models
        from app.services.operations_config import build_operations_config

        db = self._create_memory_db()
        try:
            db.add(
                models.NailDesign(
                    name="后台自定义款",
                    image_url="/uploads/designs/custom.jpg",
                    style_tags=["手绘"],
                    color_tags=["蓝色"],
                    scene_tags=["度假"],
                    status="active",
                )
            )
            db.commit()

            config = build_operations_config(
                db,
                saved_config={
                    "styleTags": ["后台新增风格"],
                    "colorTags": ["后台新增颜色"],
                    "sceneTags": ["后台新增场景"],
                },
            )

            self.assertIn("手绘", config["styleTags"])
            self.assertIn("后台新增风格", config["styleTags"])
            self.assertIn("后台新增颜色", config["colorTags"])
            self.assertIn("后台新增场景", config["sceneTags"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
