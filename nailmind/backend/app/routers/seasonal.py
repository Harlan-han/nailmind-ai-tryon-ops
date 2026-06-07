"""Seasonal and festival nail recommendations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel

from app.database import get_db
from app import models
from app.auth import require_operator
from app.services.design_visual_tags import design_to_effective_tags

router = APIRouter()


# ============== Pydantic Schemas ==============

class SeasonalThemeCreate(BaseModel):
    name: str
    description: str
    icon: str
    keywords: List[str]
    colors: List[str]
    months: List[int]


class SeasonalThemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    keywords: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    months: Optional[List[int]] = None


class FestivalThemeCreate(BaseModel):
    name: str
    description: str
    icon: str
    keywords: List[str]
    colors: List[str]
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    priority: int = 5


class FestivalThemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    keywords: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    start_month: Optional[int] = None
    start_day: Optional[int] = None
    end_month: Optional[int] = None
    end_day: Optional[int] = None
    priority: Optional[int] = None


# ============== In-memory storage (replace with DB in production) ==============

_seasonal_themes: Dict[str, dict] = {
    'spring': {
        'id': 'spring',
        'name': '春日清新',
        'months': [3, 4, 5],
        'keywords': ['裸色', '粉色', '渐变', '花朵', '法式'],
        'colors': ['裸色', '粉色', '浅紫', '薄荷绿'],
        'description': '春光明媚，清新淡雅',
        'icon': '🌸',
        'is_active': False,
        'start_date': '2026-03-01',
        'end_date': '2026-05-31',
    },
    'summer': {
        'id': 'summer',
        'name': '夏日活力',
        'months': [6, 7, 8],
        'keywords': ['猫眼', '闪粉', '渐变', '蓝色', '橙色'],
        'colors': ['蓝色', '橙色', '粉色', '紫色'],
        'description': '活力夏日，炫彩夺目',
        'icon': '☀️',
        'is_active': False,
        'start_date': '2026-06-01',
        'end_date': '2026-08-31',
    },
    'autumn': {
        'id': 'autumn',
        'name': '秋日暖调',
        'months': [9, 10, 11],
        'keywords': ['红色', '棕色', '金色', '猫眼', '磨砂'],
        'colors': ['红色', '棕色', '橙色', '金色'],
        'description': '温暖秋日，优雅沉稳',
        'icon': '🍁',
        'is_active': False,
        'start_date': '2026-09-01',
        'end_date': '2026-11-30',
    },
    'winter': {
        'id': 'winter',
        'name': '冬日闪耀',
        'months': [12, 1, 2],
        'keywords': ['闪粉', '银色', '红色', '猫眼', '法式'],
        'colors': ['银色', '红色', '白色', '蓝色'],
        'description': '冬日闪耀，节日氛围',
        'icon': '❄️',
        'is_active': False,
        'start_date': '2025-12-01',
        'end_date': '2026-02-28',
    }
}

_festival_themes: Dict[str, dict] = {
    'new_year': {
        'id': 'new_year',
        'name': '新年开运',
        'start_month': 1, 'start_day': 1,
        'end_month': 2, 'end_day': 15,
        'keywords': ['红色', '金色', '闪粉', '猫眼'],
        'colors': ['红色', '金色', '粉色'],
        'description': '新年新气象，红红火火',
        'icon': '🧧',
        'priority': 10,
        'is_active': False,
    },
    'valentine': {
        'id': 'valentine',
        'name': '情人节限定',
        'start_month': 2, 'start_day': 1,
        'end_month': 2, 'end_day': 20,
        'keywords': ['爱心', '粉色', '红色', '闪粉'],
        'colors': ['粉色', '红色', '白色'],
        'description': '浪漫甜蜜，示爱首选',
        'icon': '💕',
        'priority': 9,
        'is_active': False,
    },
    'wedding_season': {
        'id': 'wedding_season',
        'name': '婚礼季',
        'start_month': 3, 'start_day': 1,
        'end_month': 5, 'end_day': 31,
        'keywords': ['法式', '裸色', '闪粉', '珍珠'],
        'colors': ['裸色', '白色', '粉色', '香槟'],
        'description': '优雅精致，最美新娘',
        'icon': '💍',
        'priority': 8,
        'is_active': False,
    },
    'summer_vacation': {
        'id': 'summer_vacation',
        'name': '夏日度假',
        'start_month': 6, 'start_day': 1,
        'end_month': 8, 'end_day': 31,
        'keywords': ['蓝色', '渐变', '闪粉', '猫眼'],
        'colors': ['蓝色', '橙色', '紫色'],
        'description': '度假风情，清凉一夏',
        'icon': '🏖️',
        'priority': 7,
        'is_active': False,
    },
    'mid_autumn': {
        'id': 'mid_autumn',
        'name': '中秋月圆',
        'start_month': 9, 'start_day': 1,
        'end_month': 9, 'end_day': 30,
        'keywords': ['金色', '红色', '闪粉', '花朵'],
        'colors': ['金色', '红色', '橙色'],
        'description': '月圆人团圆',
        'icon': '🥮',
        'priority': 8,
        'is_active': False,
    },
    'halloween': {
        'id': 'halloween',
        'name': '万圣节狂欢',
        'start_month': 10, 'start_day': 15,
        'end_month': 11, 'end_day': 5,
        'keywords': ['黑色', '紫色', '橙色', '闪粉'],
        'colors': ['黑色', '紫色', '橙色'],
        'description': '神秘搞怪，个性十足',
        'icon': '🎃',
        'priority': 7,
        'is_active': False,
    },
    'christmas': {
        'id': 'christmas',
        'name': '圣诞限定',
        'start_month': 12, 'start_day': 1,
        'end_month': 12, 'end_day': 31,
        'keywords': ['红色', '绿色', '金色', '闪粉'],
        'colors': ['红色', '绿色', '金色'],
        'description': '圣诞氛围，闪耀冬日',
        'icon': '🎄',
        'priority': 10,
        'is_active': False,
    }
}


# ============== Helper Functions ==============

def get_current_season() -> str:
    """Get current season based on month."""
    month = datetime.now().month
    for season_id, info in _seasonal_themes.items():
        if month in info['months']:
            return season_id
    return 'spring'


def count_matching_designs(theme: dict, db: Session) -> int:
    """Count designs matching theme keywords/colors."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()
    count = 0
    for design in designs:
        if theme_match_score(design, theme) > 0:
            count += 1
    return count


def theme_match_score(design: models.NailDesign, theme: dict) -> int:
    effective = design_to_effective_tags(design)
    score = 0
    for tag in effective.get('style_tags') or []:
        if tag in theme.get('keywords', []):
            score += 10
    for color in effective.get('color_tags') or []:
        if color in theme.get('colors', []):
            score += 15
    return score


def update_active_status():
    """Update is_active based on current date."""
    now = datetime.now()
    current_month = now.month
    current_day = now.day
    year = now.year

    # Update seasons
    for season_id, theme in _seasonal_themes.items():
        theme['is_active'] = current_month in theme['months']

    # Update festivals
    for festival_id, theme in _festival_themes.items():
        start_date = datetime(year, theme['start_month'], theme['start_day'])
        end_date = datetime(year, theme['end_month'], theme['end_day'])
        current_date = datetime(year, current_month, current_day)

        if end_date < start_date:
            end_date = datetime(year + 1, theme['end_month'], theme['end_day'])

        theme['is_active'] = start_date <= current_date <= end_date


# ============== API Endpoints ==============

@router.get("/current")
def get_current_themes(db: Session = Depends(get_db)):
    """Get current seasonal and festival themes."""
    update_active_status()
    season_id = get_current_season()
    season_info = _seasonal_themes[season_id]

    all_designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()

    # Seasonal designs
    seasonal_designs = []
    for design in all_designs:
        score = theme_match_score(design, season_info)
        if score > 0:
            seasonal_designs.append({
                'design': design,
                'score': score
            })

    seasonal_designs.sort(key=lambda x: x['score'], reverse=True)

    # Active festivals
    active_festivals = [
        f for f in _festival_themes.values() if f['is_active']
    ]
    active_festivals.sort(key=lambda x: x['priority'], reverse=True)

    # Festival designs
    festival_results = []
    for festival in active_festivals:
        festival_designs = []
        for design in all_designs:
            score = theme_match_score(design, festival)
            if score > 0:
                festival_designs.append({
                    'design': design,
                    'score': score
                })

        festival_designs.sort(key=lambda x: x['score'], reverse=True)
        festival_results.append({
            'festival': festival,
            'designs': festival_designs[:6]
        })

    return {
        'season': {
            'id': season_id,
            'name': season_info['name'],
            'description': season_info['description'],
            'icon': season_info['icon'],
            'keywords': season_info['keywords'],
            'colors': season_info['colors'],
            'designs': [
                {'design': d['design'], 'match_score': d['score']}
                for d in seasonal_designs[:6]
            ]
        },
        'festivals': festival_results
    }


@router.get("/upcoming")
def get_upcoming_themes(days: int = 30):
    """Get upcoming seasonal/festival themes."""
    now = datetime.now()
    upcoming = []

    for theme in _festival_themes.values():
        start_date = datetime(now.year, theme['start_month'], theme['start_day'])
        if start_date > now and (start_date - now).days <= days:
            upcoming.append({
                'id': theme['id'],
                'name': theme['name'],
                'description': theme['description'],
                'icon': theme['icon'],
                'days_until': (start_date - now).days
            })

    upcoming.sort(key=lambda x: x['days_until'])
    return upcoming


@router.get("/all")
def get_all_themes(db: Session = Depends(get_db)):
    """Get all seasonal and festival themes with counts."""
    update_active_status()

    seasons = []
    for theme in _seasonal_themes.values():
        seasons.append({
            'id': theme['id'],
            'name': theme['name'],
            'description': theme['description'],
            'icon': theme['icon'],
            'keywords': theme['keywords'],
            'colors': theme['colors'],
            'start_date': theme['start_date'],
            'end_date': theme['end_date'],
            'is_active': theme['is_active'],
            'designs_count': count_matching_designs(theme, db)
        })

    festivals = []
    for theme in _festival_themes.values():
        festivals.append({
            'id': theme['id'],
            'name': theme['name'],
            'description': theme['description'],
            'icon': theme['icon'],
            'start_date': f"2026-{theme['start_month']:02d}-{theme['start_day']:02d}",
            'end_date': f"2026-{theme['end_month']:02d}-{theme['end_day']:02d}",
            'is_active': theme['is_active'],
            'designs_count': count_matching_designs(theme, db),
            'match_rules': {
                'style_tags': theme['keywords'],
                'color_tags': theme['colors'],
                'scene_tags': []
            }
        })

    return {
        'seasons': seasons,
        'festivals': festivals
    }


# ============== Season CRUD ==============

@router.post("/seasons")
def create_season(
    data: SeasonalThemeCreate,
    _operator: models.User = Depends(require_operator),
):
    """Create a new seasonal theme."""
    season_id = data.name.lower().replace(' ', '_')
    _seasonal_themes[season_id] = {
        'id': season_id,
        **data.dict(),
        'is_active': False,
        'start_date': f"2026-{data.months[0]:02d}-01",
        'end_date': f"2026-{data.months[-1]:02d}-{28 if data.months[-1] == 2 else 30}",
    }
    return _seasonal_themes[season_id]


@router.put("/seasons/{season_id}")
def update_season(
    season_id: str,
    data: SeasonalThemeUpdate,
    _operator: models.User = Depends(require_operator),
):
    """Update a seasonal theme."""
    if season_id not in _seasonal_themes:
        raise HTTPException(status_code=404, detail="Season not found")

    theme = _seasonal_themes[season_id]
    for key, value in data.dict(exclude_unset=True).items():
        theme[key] = value

    return theme


@router.delete("/seasons/{season_id}")
def delete_season(
    season_id: str,
    _operator: models.User = Depends(require_operator),
):
    """Delete a seasonal theme."""
    if season_id not in _seasonal_themes:
        raise HTTPException(status_code=404, detail="Season not found")

    del _seasonal_themes[season_id]
    return {"message": "Season deleted"}


# ============== Festival CRUD ==============

@router.post("/festivals")
def create_festival(
    data: FestivalThemeCreate,
    _operator: models.User = Depends(require_operator),
):
    """Create a new festival theme."""
    festival_id = data.name.lower().replace(' ', '_')
    _festival_themes[festival_id] = {
        'id': festival_id,
        **data.dict(),
        'is_active': False,
    }
    return _festival_themes[festival_id]


@router.put("/festivals/{festival_id}")
def update_festival(
    festival_id: str,
    data: FestivalThemeUpdate,
    _operator: models.User = Depends(require_operator),
):
    """Update a festival theme."""
    if festival_id not in _festival_themes:
        raise HTTPException(status_code=404, detail="Festival not found")

    theme = _festival_themes[festival_id]
    for key, value in data.dict(exclude_unset=True).items():
        theme[key] = value

    return theme


@router.delete("/festivals/{festival_id}")
def delete_festival(
    festival_id: str,
    _operator: models.User = Depends(require_operator),
):
    """Delete a festival theme."""
    if festival_id not in _festival_themes:
        raise HTTPException(status_code=404, detail="Festival not found")

    del _festival_themes[festival_id]
    return {"message": "Festival deleted"}


@router.patch("/festivals/{festival_id}/toggle")
def toggle_festival(
    festival_id: str,
    _operator: models.User = Depends(require_operator),
):
    """Toggle festival active status."""
    if festival_id not in _festival_themes:
        raise HTTPException(status_code=404, detail="Festival not found")

    _festival_themes[festival_id]['is_active'] = not _festival_themes[festival_id]['is_active']
    return _festival_themes[festival_id]
