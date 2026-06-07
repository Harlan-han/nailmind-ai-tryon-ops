import unittest


class DesignVisualTagsTest(unittest.TestCase):
    def test_visual_override_replaces_seed_tags_for_existing_design(self):
        from app.services.design_visual_tags import design_to_response

        class Design:
            id = 20
            name = "款式 20"
            description = "旧描述"
            image_url = "/uploads/designs/design_20.jpg"
            thumbnail_url = None
            style_tags = ["爱心", "可爱"]
            color_tags = ["粉色"]
            scene_tags = ["约会"]
            length = None
            shape = None
            status = "active"
            is_hot = False
            is_new = False
            view_count = 0
            try_on_count = 0
            favorite_count = 0
            booking_count = 0
            created_at = None

        response = design_to_response(Design())

        self.assertIn("奶牛纹", response["style_tags"])
        self.assertIn("水钻", response["style_tags"])
        self.assertIn("银色", response["color_tags"])
        self.assertNotIn("爱心", response["style_tags"])

    def test_manual_admin_tags_take_precedence_over_visual_defaults(self):
        from app.services.design_visual_tags import design_to_response

        class Design:
            id = 20
            name = "后台改过的款式"
            description = "后台编辑描述"
            image_url = "/uploads/designs/design_20.jpg"
            thumbnail_url = None
            style_tags = ["后台风格"]
            color_tags = ["后台颜色"]
            scene_tags = ["后台场景"]
            length = "后台长度"
            shape = "后台形状"
            status = "active"
            is_hot = False
            is_new = False
            view_count = 0
            try_on_count = 0
            favorite_count = 0
            booking_count = 0
            created_at = None

        response = design_to_response(Design())

        self.assertEqual(response["style_tags"], ["后台风格"])
        self.assertEqual(response["color_tags"], ["后台颜色"])
        self.assertEqual(response["scene_tags"], ["后台场景"])
        self.assertEqual(response["length"], "后台长度")
        self.assertEqual(response["shape"], "后台形状")

    def test_english_tags_are_normalized_before_response_and_collection(self):
        from app.services.design_visual_tags import collect_visual_tags, design_to_response, matches_design_filters

        class Design:
            id = 4
            name = "后台英文标签"
            description = "后台编辑描述"
            image_url = "/uploads/designs/design_04.jpg"
            thumbnail_url = None
            style_tags = ["cat eye", "chrome", "后台风格"]
            color_tags = ["silver", "nude"]
            scene_tags = ["daily", "party"]
            length = "medium"
            shape = "almond"
            status = "active"
            is_hot = False
            is_new = False
            view_count = 0
            try_on_count = 0
            favorite_count = 0
            booking_count = 0
            created_at = None

        response = design_to_response(Design())

        self.assertEqual(response["style_tags"], ["猫眼", "镜面", "后台风格"])
        self.assertEqual(response["color_tags"], ["银色", "裸色"])
        self.assertEqual(response["scene_tags"], ["日常", "派对"])
        self.assertEqual(response["length"], "中长甲")
        self.assertEqual(response["shape"], "杏仁形")

        collected_styles = collect_visual_tags([Design()], "style_tags")
        self.assertIn("猫眼", collected_styles)
        self.assertIn("镜面", collected_styles)
        self.assertNotIn("cat eye", collected_styles)
        self.assertNotIn("chrome", collected_styles)
        self.assertTrue(matches_design_filters(response, style_tags=["cat eye"], color_tags=["silver"], scene_tags=["party"], q=None))

    def test_filtering_uses_visual_tags_instead_of_old_seed_tags(self):
        from app.services.design_visual_tags import design_to_response, matches_design_filters

        class Design:
            id = 20
            name = "款式 20"
            description = ""
            image_url = "/uploads/designs/design_20.jpg"
            thumbnail_url = None
            style_tags = ["爱心", "可爱"]
            color_tags = ["粉色"]
            scene_tags = ["约会"]
            length = None
            shape = None
            status = "active"
            is_hot = False
            is_new = False
            view_count = 0
            try_on_count = 0
            favorite_count = 0
            booking_count = 0
            created_at = None

        response = design_to_response(Design())

        self.assertTrue(matches_design_filters(response, style_tags=["奶牛纹"], color_tags=["银色"], scene_tags=None, q="甜酷"))
        self.assertFalse(matches_design_filters(response, style_tags=["爱心"], color_tags=None, scene_tags=None, q=None))

    def test_search_matches_name_tags_scene_length_and_shape(self):
        from app.services.design_visual_tags import matches_design_filters

        design = {
            "name": "款式 17",
            "description": "",
            "style_tags": ["法式", "蝴蝶结", "立体装饰"],
            "color_tags": ["白色", "裸色", "银色"],
            "scene_tags": ["婚礼", "派对", "高级感"],
            "length": "长甲",
            "shape": "方形",
        }

        self.assertTrue(matches_design_filters(design, None, None, None, "婚礼"))
        self.assertTrue(matches_design_filters(design, None, None, None, "方形"))
        self.assertTrue(matches_design_filters(design, None, None, None, "蝴蝶"))
        self.assertFalse(matches_design_filters(design, None, None, None, "猫眼"))


if __name__ == "__main__":
    unittest.main()
