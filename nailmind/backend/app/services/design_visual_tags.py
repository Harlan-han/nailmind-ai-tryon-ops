"""Visual tag overrides for the imported nail design images."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class VisualDesignTags:
    style_tags: list[str]
    color_tags: list[str]
    scene_tags: list[str]
    length: str
    shape: str
    description: str


VISUAL_TAGS_BY_FILENAME: dict[str, VisualDesignTags] = {
    "design_01.jpg": VisualDesignTags(
        style_tags=["纯色", "裸感", "极简"],
        color_tags=["裸色", "米色"],
        scene_tags=["日常", "通勤", "高级感"],
        length="短甲",
        shape="圆形",
        description="低饱和奶油裸色短甲，适合干净自然的日常和通勤场景。",
    ),
    "design_02.jpg": VisualDesignTags(
        style_tags=["跳色", "纯色", "秋冬感"],
        color_tags=["橄榄绿", "奶油白", "裸色"],
        scene_tags=["通勤", "秋冬", "日常"],
        length="中长甲",
        shape="圆形",
        description="橄榄绿与奶油白跳色组合，带一点秋冬氛围但整体克制。",
    ),
    "design_03.jpg": VisualDesignTags(
        style_tags=["黑色系", "豹纹", "跳色"],
        color_tags=["黑色", "酒红", "棕色"],
        scene_tags=["派对", "约会", "甜酷"],
        length="中长甲",
        shape="方圆形",
        description="黑色、酒红与豹纹跳色，视觉冲击强，适合甜酷和派对造型。",
    ),
    "design_04.jpg": VisualDesignTags(
        style_tags=["猫眼", "金属感", "跳色"],
        color_tags=["银色", "灰色", "裸色"],
        scene_tags=["通勤", "高级感", "派对"],
        length="中长甲",
        shape="杏仁形",
        description="银灰猫眼与裸灰跳色，冷调金属光泽明显。",
    ),
    "design_05.jpg": VisualDesignTags(
        style_tags=["奶牛纹", "纯色", "跳色"],
        color_tags=["白色", "黑色", "裸色"],
        scene_tags=["日常", "可爱", "通勤"],
        length="短甲",
        shape="方圆形",
        description="白色短甲搭配黑白奶牛纹点缀，干净且有趣。",
    ),
    "design_06.jpg": VisualDesignTags(
        style_tags=["裸感", "水钻", "金箔", "立体装饰"],
        color_tags=["裸色", "金色", "透明"],
        scene_tags=["婚礼", "约会", "高级感"],
        length="中长甲",
        shape="杏仁形",
        description="裸透底色叠加金箔和水钻，精致感强，适合婚礼或约会。",
    ),
    "design_07.jpg": VisualDesignTags(
        style_tags=["法式", "奶牛纹", "水钻"],
        color_tags=["裸色", "白色", "黑色", "银色"],
        scene_tags=["甜酷", "派对", "约会"],
        length="长甲",
        shape="尖形",
        description="长尖甲法式底，加入奶牛纹与水钻装饰，风格偏甜酷。",
    ),
    "design_08.jpg": VisualDesignTags(
        style_tags=["法式", "水钻", "黑色系"],
        color_tags=["黑色", "裸色", "银色"],
        scene_tags=["派对", "甜酷", "高级感"],
        length="长甲",
        shape="尖形",
        description="黑色法式长尖甲配水钻装饰，适合更强风格化造型。",
    ),
    "design_09.jpg": VisualDesignTags(
        style_tags=["黑色系", "星星", "手绘"],
        color_tags=["黑色", "裸色"],
        scene_tags=["派对", "甜酷", "约会"],
        length="中长甲",
        shape="方圆形",
        description="黑色亮面甲搭配星星手绘，适合夜晚、派对和甜酷穿搭。",
    ),
    "design_10.jpg": VisualDesignTags(
        style_tags=["法式", "蝴蝶结", "立体装饰", "珍珠"],
        color_tags=["粉色", "裸色", "白色"],
        scene_tags=["约会", "婚礼", "甜美"],
        length="中长甲",
        shape="杏仁形",
        description="粉裸法式与白色蝴蝶结装饰，甜美感明显。",
    ),
    "design_11.jpg": VisualDesignTags(
        style_tags=["闪粉", "水钻", "裸感"],
        color_tags=["裸色", "银色", "透明"],
        scene_tags=["派对", "婚礼", "高级感"],
        length="长甲",
        shape="杏仁形",
        description="裸透底叠加银色闪粉与水钻，高光感强。",
    ),
    "design_12.jpg": VisualDesignTags(
        style_tags=["花朵", "黑色系", "手绘"],
        color_tags=["黑色", "裸色", "白色"],
        scene_tags=["甜酷", "度假", "约会"],
        length="中长甲",
        shape="方圆形",
        description="黑白花朵手绘搭配裸色底，清爽但有个性。",
    ),
    "design_13.jpg": VisualDesignTags(
        style_tags=["法式", "渐变", "闪粉", "水钻"],
        color_tags=["白色", "裸色", "银色"],
        scene_tags=["婚礼", "高级感", "通勤"],
        length="中长甲",
        shape="方圆形",
        description="白色渐变法式配银色闪粉与水钻，温柔精致。",
    ),
    "design_14.jpg": VisualDesignTags(
        style_tags=["猫眼", "珠光", "裸感"],
        color_tags=["裸色", "香槟色", "白色"],
        scene_tags=["通勤", "高级感", "约会"],
        length="长甲",
        shape="杏仁形",
        description="香槟裸色猫眼长甲，光泽柔和，适合高级温柔风格。",
    ),
    "design_15.jpg": VisualDesignTags(
        style_tags=["花朵", "格纹", "可爱", "手绘"],
        color_tags=["红色", "蓝色", "粉色", "裸色"],
        scene_tags=["可爱", "春夏", "约会"],
        length="短甲",
        shape="圆形",
        description="短甲上叠加小花、格纹和多色点缀，偏可爱春夏感。",
    ),
    "design_16.jpg": VisualDesignTags(
        style_tags=["水钻", "花朵", "裸感", "立体装饰"],
        color_tags=["粉色", "裸色", "金色"],
        scene_tags=["约会", "婚礼", "甜美"],
        length="中长甲",
        shape="圆形",
        description="粉裸底叠加花朵、水钻和金色点缀，适合甜美场景。",
    ),
    "design_17.jpg": VisualDesignTags(
        style_tags=["法式", "蝴蝶结", "水钻", "立体装饰"],
        color_tags=["白色", "裸色", "银色"],
        scene_tags=["婚礼", "派对", "高级感"],
        length="长甲",
        shape="方形",
        description="白色长方甲法式搭配蝴蝶结和大颗水钻，仪式感强。",
    ),
    "design_18.jpg": VisualDesignTags(
        style_tags=["水钻", "多巴胺", "跳色", "立体装饰"],
        color_tags=["红色", "蓝色", "金色", "裸色"],
        scene_tags=["派对", "节日", "个性"],
        length="短甲",
        shape="方圆形",
        description="短甲多色跳色配彩钻装饰，活泼且适合节日造型。",
    ),
    "design_19.jpg": VisualDesignTags(
        style_tags=["法式", "水钻", "金箔"],
        color_tags=["裸色", "白色", "金色"],
        scene_tags=["婚礼", "约会", "高级感"],
        length="中长甲",
        shape="杏仁形",
        description="白金法式配水钻和金箔，精致偏仙气。",
    ),
    "design_20.jpg": VisualDesignTags(
        style_tags=["奶牛纹", "水钻", "法式", "立体装饰"],
        color_tags=["裸色", "黑色", "银色"],
        scene_tags=["甜酷", "派对", "个性"],
        length="长甲",
        shape="杏仁形",
        description="裸色长甲搭配奶牛纹、水钻和银色装饰，个性甜酷。",
    ),
    "design_21.jpg": VisualDesignTags(
        style_tags=["金属感", "猫眼", "跳色", "水钻"],
        color_tags=["金色", "蓝色", "紫色", "裸色"],
        scene_tags=["派对", "节日", "高级感"],
        length="短甲",
        shape="方圆形",
        description="短甲多色金属猫眼与水钻跳色，亮眼且偏派对。",
    ),
    "design_22.jpg": VisualDesignTags(
        style_tags=["镜面", "金属感", "纯色"],
        color_tags=["玫瑰金", "粉色"],
        scene_tags=["派对", "高级感", "甜酷"],
        length="中长甲",
        shape="杏仁形",
        description="玫瑰金镜面甲，金属反光强，适合高存在感造型。",
    ),
    "design_23.jpg": VisualDesignTags(
        style_tags=["裸感", "渐变", "极简"],
        color_tags=["裸色", "奶油白"],
        scene_tags=["日常", "通勤", "约会"],
        length="中长甲",
        shape="杏仁形",
        description="裸粉到奶油白的柔和渐变，低调耐看。",
    ),
    "design_24.jpg": VisualDesignTags(
        style_tags=["猫眼", "闪粉", "金属感"],
        color_tags=["灰色", "银色", "裸色"],
        scene_tags=["通勤", "高级感", "派对"],
        length="中长甲",
        shape="方圆形",
        description="灰银猫眼与闪粉点缀，冷感高级。",
    ),
    "design_25.jpg": VisualDesignTags(
        style_tags=["法式", "红色系", "爱心", "线条"],
        color_tags=["红色", "粉色", "裸色"],
        scene_tags=["约会", "节日", "甜美"],
        length="中长甲",
        shape="方圆形",
        description="粉裸底红色法式边和爱心线条，甜美适合约会节日。",
    ),
}

SEED_STYLE_TAG_SIGNATURES = {
    ("法式", "经典"),
    ("渐变", "裸色"),
    ("猫眼", "闪粉"),
    ("爱心", "可爱"),
    ("红色", "节日"),
    ("花朵", "手绘"),
    ("几何", "简约"),
    ("极光", "闪粉"),
}

SEED_COLOR_TAG_SIGNATURES = {
    ("裸色",),
    ("灰色",),
    ("粉色",),
    ("红色",),
    ("黑色",),
}

SEED_SCENE_TAG_SIGNATURES = {
    ("日常", "通勤"),
    ("约会",),
    ("派对", "约会"),
    ("约会", "派对"),
    ("节日", "派对"),
}

SEED_LENGTH_VALUES = {"短", "中", "长"}
SEED_SHAPE_VALUES = {"圆", "方", "尖", "椭圆"}

TAG_ALIASES = {
    "cat eye": "猫眼",
    "cat-eye": "猫眼",
    "cateye": "猫眼",
    "chrome": "镜面",
    "mirror": "镜面",
    "metallic": "金属感",
    "metal": "金属感",
    "french": "法式",
    "minimal": "极简",
    "minimalist": "极简",
    "nude": "裸色",
    "glitter": "闪粉",
    "sparkle": "闪粉",
    "rhinestone": "水钻",
    "rhinestones": "水钻",
    "pearl": "珍珠",
    "bow": "蝴蝶结",
    "butterfly bow": "蝴蝶结",
    "flower": "花朵",
    "floral": "花朵",
    "cow print": "奶牛纹",
    "cow": "奶牛纹",
    "leopard": "豹纹",
    "leopard print": "豹纹",
    "gradient": "渐变",
    "ombre": "渐变",
    "heart": "爱心",
    "line": "线条",
    "lines": "线条",
    "plaid": "格纹",
    "star": "星星",
    "stars": "星星",
    "hand painted": "手绘",
    "hand-painted": "手绘",
    "dopamine": "多巴胺",
    "black": "黑色",
    "white": "白色",
    "red": "红色",
    "pink": "粉色",
    "silver": "银色",
    "gold": "金色",
    "gray": "灰色",
    "grey": "灰色",
    "blue": "蓝色",
    "purple": "紫色",
    "green": "绿色",
    "transparent": "透明",
    "cream white": "奶油白",
    "rose gold": "玫瑰金",
    "daily": "日常",
    "everyday": "日常",
    "commute": "通勤",
    "work": "通勤",
    "party": "派对",
    "date": "约会",
    "dating": "约会",
    "wedding": "婚礼",
    "holiday": "节日",
    "sweet": "甜美",
    "cute": "可爱",
    "vacation": "度假",
    "advanced": "高级感",
    "premium": "高级感",
    "personality": "个性",
}

VALUE_ALIASES = {
    "short": "短甲",
    "medium": "中长甲",
    "long": "长甲",
    "round": "圆形",
    "square": "方形",
    "squoval": "方圆形",
    "almond": "杏仁形",
    "stiletto": "尖形",
    "oval": "椭圆形",
}


def _filename_from_url(image_url: str) -> str:
    return image_url.rsplit("/", 1)[-1]


DESIGN_UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "designs"
DEFAULT_DESIGN_IMAGE_URL = "/uploads/designs/design_01.jpg"


@lru_cache(maxsize=512)
def _local_design_upload_exists(image_url: str) -> bool:
    prefix = "/uploads/designs/"
    if not image_url.startswith(prefix):
        return True
    filename = Path(image_url.removeprefix(prefix)).name
    return bool(filename) and (DESIGN_UPLOADS_DIR / filename).is_file()


def resolve_design_image_url(image_url: str) -> str:
    if not image_url:
        return DEFAULT_DESIGN_IMAGE_URL
    if _local_design_upload_exists(image_url):
        return image_url
    return DEFAULT_DESIGN_IMAGE_URL


def has_servable_design_image(design: Any) -> bool:
    image_url = _get_attr(design, "image_url") or ""
    return bool(image_url) and _local_design_upload_exists(image_url)


def filter_servable_designs(designs: Iterable[Any]) -> list[Any]:
    return [design for design in designs if has_servable_design_image(design)]


def deduplicate_designs_by_image(designs: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    unique_designs: list[Any] = []
    for design in designs:
        image_url = _get_attr(design, "image_url") or ""
        filename = _filename_from_url(image_url)
        key = filename.lower() if filename else image_url
        if key in seen:
            continue
        seen.add(key)
        unique_designs.append(design)
    return unique_designs


def _get_attr(design: Any, field: str) -> Any:
    if isinstance(design, dict):
        return design.get(field)
    return getattr(design, field, None)


def get_visual_tags_for_design(design: Any) -> Optional[VisualDesignTags]:
    image_url = _get_attr(design, "image_url") or ""
    return VISUAL_TAGS_BY_FILENAME.get(_filename_from_url(image_url))


def _tags_need_visual_default(tags: Any, seed_signatures: set[tuple[str, ...]]) -> bool:
    tag_values = tuple(tags or [])
    return not tag_values or tag_values in seed_signatures


def _value_needs_visual_default(value: Any, seed_values: set[str]) -> bool:
    return not value or value in seed_values


def _normalize_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    return VALUE_ALIASES.get(stripped.lower(), stripped)


def _normalize_tag(tag: Any) -> str:
    stripped = str(tag).strip()
    return TAG_ALIASES.get(stripped.lower(), stripped)


def _normalize_tags(tags: Iterable[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        value = _normalize_tag(tag)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def design_to_effective_tags(design: Any) -> dict[str, Any]:
    data = {
        "description": _get_attr(design, "description"),
        "style_tags": _normalize_tags(_get_attr(design, "style_tags") or []),
        "color_tags": _normalize_tags(_get_attr(design, "color_tags") or []),
        "scene_tags": _normalize_tags(_get_attr(design, "scene_tags") or []),
        "length": _normalize_value(_get_attr(design, "length")),
        "shape": _normalize_value(_get_attr(design, "shape")),
    }

    visual_tags = get_visual_tags_for_design(design)
    if not visual_tags:
        return data

    if _tags_need_visual_default(data["style_tags"], SEED_STYLE_TAG_SIGNATURES):
        data["style_tags"] = _normalize_tags(visual_tags.style_tags)
    if _tags_need_visual_default(data["color_tags"], SEED_COLOR_TAG_SIGNATURES):
        data["color_tags"] = _normalize_tags(visual_tags.color_tags)
    if _tags_need_visual_default(data["scene_tags"], SEED_SCENE_TAG_SIGNATURES):
        data["scene_tags"] = _normalize_tags(visual_tags.scene_tags)
    if _value_needs_visual_default(data["length"], SEED_LENGTH_VALUES):
        data["length"] = _normalize_value(visual_tags.length)
    if _value_needs_visual_default(data["shape"], SEED_SHAPE_VALUES):
        data["shape"] = _normalize_value(visual_tags.shape)
    if not data["description"] or str(data["description"]).startswith("官方样例款式 #"):
        data["description"] = visual_tags.description

    return data


def design_to_response(design: Any) -> dict[str, Any]:
    effective = design_to_effective_tags(design)
    data = {
        "id": _get_attr(design, "id"),
        "name": _get_attr(design, "name"),
        "description": effective["description"],
        "image_url": resolve_design_image_url(_get_attr(design, "image_url") or ""),
        "thumbnail_url": _get_attr(design, "thumbnail_url"),
        "style_tags": effective["style_tags"],
        "color_tags": effective["color_tags"],
        "scene_tags": effective["scene_tags"],
        "length": effective["length"],
        "shape": effective["shape"],
        "status": _get_attr(design, "status"),
        "is_hot": bool(_get_attr(design, "is_hot")),
        "is_new": bool(_get_attr(design, "is_new")),
        "view_count": int(_get_attr(design, "view_count") or 0),
        "try_on_count": int(_get_attr(design, "try_on_count") or 0),
        "favorite_count": int(_get_attr(design, "favorite_count") or 0),
        "booking_count": int(_get_attr(design, "booking_count") or 0),
        "created_at": _get_attr(design, "created_at"),
    }

    return data


def _contains_all(actual: Iterable[str], expected: Optional[Iterable[str]]) -> bool:
    expected_values = _normalize_tags(expected or [])
    if not expected_values:
        return True
    actual_set = set(_normalize_tags(actual or []))
    return all(value in actual_set for value in expected_values)


def _search_blob(design: dict[str, Any]) -> str:
    values = [
        design.get("name"),
        design.get("description"),
        design.get("length"),
        design.get("shape"),
        *(design.get("style_tags") or []),
        *(design.get("color_tags") or []),
        *(design.get("scene_tags") or []),
    ]
    return " ".join(str(value).lower() for value in values if value)


def matches_design_filters(
    design: dict[str, Any],
    style_tags: Optional[list[str]],
    color_tags: Optional[list[str]],
    scene_tags: Optional[list[str]],
    q: Optional[str],
) -> bool:
    if not _contains_all(design.get("style_tags") or [], style_tags):
        return False
    if not _contains_all(design.get("color_tags") or [], color_tags):
        return False
    if not _contains_all(design.get("scene_tags") or [], scene_tags):
        return False

    query = (q or "").strip().lower()
    if not query:
        return True

    keywords = [keyword for keyword in query.split() if keyword]
    blob = _search_blob(design)
    return all(keyword in blob for keyword in keywords)


def collect_visual_tags(designs: Iterable[Any], field: str) -> list[str]:
    tags: set[str] = set()
    for design in designs:
        response = design_to_response(design)
        tags.update(response.get(field) or [])
    return sorted(tags)
