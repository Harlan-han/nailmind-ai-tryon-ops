"""Enhanced AI Operations Agent with predictive capabilities."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import defaultdict

from app import models
from app.services.design_visual_tags import design_to_effective_tags, filter_servable_designs

BUSINESS_TRY_ON_STATUSES = ("completed",)


class AIOperationsAgent:
    """AI agent for operations intelligence and predictions."""

    def __init__(self, db: Session):
        self.db = db

    def _style_tags(self, design: models.NailDesign) -> list[str]:
        return list(design_to_effective_tags(design).get("style_tags") or [])

    def _business_try_on_query(self):
        return self.db.query(models.TryOnRecord).filter(
            models.TryOnRecord.status.in_(BUSINESS_TRY_ON_STATUSES)
        )

    def predict_trend(self, days_ahead: int = 7) -> Dict:
        """Predict future trends based on historical data."""
        # Get last 30 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        daily_stats = self._business_try_on_query().with_entities(
            func.date(models.TryOnRecord.created_at).label('date'),
            func.count(models.TryOnRecord.id).label('count')
        ).filter(
            models.TryOnRecord.created_at >= start_date
        ).group_by(
            func.date(models.TryOnRecord.created_at)
        ).order_by('date').all()

        if len(daily_stats) < 7:
            return {
                'trend_direction': 'insufficient_data',
                'prediction': None,
                'confidence': 0
            }

        # Calculate trend using simple linear regression
        x = np.arange(len(daily_stats))
        y = np.array([s.count for s in daily_stats])

        # Linear regression
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        intercept = (np.sum(y) - slope * np.sum(x)) / n

        # Predict next 7 days
        predictions = []
        for i in range(1, days_ahead + 1):
            pred = slope * (n + i - 1) + intercept
            predictions.append(max(0, int(pred)))

        # Calculate confidence (R-squared)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        trend_direction = 'up' if slope > 0.5 else 'down' if slope < -0.5 else 'stable'

        return {
            'trend_direction': trend_direction,
            'slope': round(slope, 2),
            'predictions': predictions,
            'confidence': round(r_squared, 2),
            'average_last_7_days': round(np.mean(y[-7:]), 1),
            'prediction_next_7_days': round(np.mean(predictions), 1)
        }

    def identify_emerging_styles(self, days: int = 14) -> List[Dict]:
        """Identify emerging/new trending styles."""
        recent_date = datetime.now() - timedelta(days=days)

        # Get recent try-ons
        recent_records = self._business_try_on_query().filter(
            models.TryOnRecord.created_at >= recent_date
        ).all()

        # Calculate current period stats
        style_stats = defaultdict(lambda: {'try_ons': 0, 'favorites': 0, 'unique_users': set()})

        for record in recent_records:
            design = record.nail_design
            if design:
                for style in self._style_tags(design):
                    style_stats[style]['try_ons'] += 1
                    style_stats[style]['unique_users'].add(record.user_id)
                    if record.is_favorite:
                        style_stats[style]['favorites'] += 1

        # Get previous period for comparison
        previous_start = recent_date - timedelta(days=days)
        previous_records = self._business_try_on_query().filter(
            models.TryOnRecord.created_at >= previous_start,
            models.TryOnRecord.created_at < recent_date
        ).all()

        previous_stats = defaultdict(int)
        for record in previous_records:
            design = record.nail_design
            if design:
                for style in self._style_tags(design):
                    previous_stats[style] += 1

        # Calculate growth rates
        emerging = []
        for style, stats in style_stats.items():
            current_count = stats['try_ons']
            previous_count = previous_stats.get(style, 0)

            if current_count >= 5:  # Minimum threshold
                if previous_count > 0:
                    growth_rate = (current_count - previous_count) / previous_count
                else:
                    growth_rate = float(current_count)

                favorite_rate = stats['favorites'] / current_count if current_count > 0 else 0

                emerging.append({
                    'style': style,
                    'try_ons': current_count,
                    'favorites': stats['favorites'],
                    'unique_users': len(stats['unique_users']),
                    'growth_rate': round(growth_rate, 2),
                    'favorite_rate': round(favorite_rate, 2),
                    'is_emerging': growth_rate > 0.5 and favorite_rate > 0.2
                })

        # Sort by growth rate
        emerging.sort(key=lambda x: x['growth_rate'], reverse=True)
        return emerging[:10]

    def generate_inventory_recommendations(self) -> List[Dict]:
        """Generate inventory/stocking recommendations."""
        # Analyze demand vs supply

        # Get designs with high try-on but low "stock" (represented by active status)
        popular_designs = self.db.query(models.NailDesign).filter(
            models.NailDesign.status == 'active',
            models.NailDesign.try_on_count >= 10
        ).order_by(
            models.NailDesign.try_on_count.desc()
        ).limit(40).all()
        popular_designs = filter_servable_designs(popular_designs)

        recommendations = []

        for design in popular_designs:
            # Calculate metrics
            try_on_rate = design.try_on_count
            favorite_rate = design.favorite_count / design.try_on_count if design.try_on_count > 0 else 0
            booking_rate = design.booking_count / design.favorite_count if design.favorite_count > 0 else 0

            # Determine recommendation
            if favorite_rate > 0.3 and booking_rate > 0.3:
                status = 'high_demand'
                action = 'ensure_stock'
                reason = '高转化率款式，确保库存充足'
            elif favorite_rate > 0.3:
                status = 'potential'
                action = 'promote'
                reason = '收藏率高但预约转化可提升'
            elif try_on_rate > 50:
                status = 'high_exposure'
                action = 'review'
                reason = '试戴多但转化需优化'
            else:
                continue

            recommendations.append({
                'design_id': design.id,
                'design_name': design.name,
                'image_url': design.image_url,
                'status': status,
                'action': action,
                'reason': reason,
                'metrics': {
                    'try_ons': try_on_rate,
                    'favorites': design.favorite_count,
                    'bookings': design.booking_count,
                    'favorite_rate': round(favorite_rate, 2),
                    'booking_rate': round(booking_rate, 2)
                }
            })

        return recommendations[:10]

    def detect_anomalies(self, days: int = 7) -> List[Dict]:
        """Detect unusual patterns in data."""
        start_date = datetime.now() - timedelta(days=days)

        # Get daily stats
        daily_data = self._business_try_on_query().with_entities(
            func.date(models.TryOnRecord.created_at).label('date'),
            func.count(models.TryOnRecord.id).label('count')
        ).filter(
            models.TryOnRecord.created_at >= start_date
        ).group_by(
            func.date(models.TryOnRecord.created_at)
        ).all()

        if len(daily_data) < 3:
            return []

        counts = [d.count for d in daily_data]
        mean = np.mean(counts)
        std = np.std(counts)

        anomalies = []
        for i, day_data in enumerate(daily_data):
            z_score = (day_data.count - mean) / std if std > 0 else 0

            if abs(z_score) > 2:  # More than 2 standard deviations
                anomalies.append({
                    'date': str(day_data.date),
                    'value': day_data.count,
                    'expected': round(mean, 1),
                    'z_score': round(z_score, 2),
                    'type': 'spike' if z_score > 0 else 'drop',
                    'severity': 'high' if abs(z_score) > 3 else 'medium'
                })

        return anomalies

    def generate_action_plan(self) -> Dict:
        """Generate comprehensive action plan."""
        plan = {
            'generated_at': datetime.now().isoformat(),
            'summary': '',
            'immediate_actions': [],
            'short_term': [],
            'long_term': []
        }

        # Trend prediction
        trend = self.predict_trend(7)

        if trend['trend_direction'] == 'up':
            plan['summary'] = f'预计接下来7天试戴量将增长约 {trend["slope"]:.1f}/天'
            plan['immediate_actions'].append({
                'action': '准备服务器资源',
                'reason': '预计流量增长',
                'priority': 'high'
            })
        elif trend['trend_direction'] == 'down':
            plan['summary'] = f'注意：试戴量呈下降趋势，建议加强推广'
            plan['immediate_actions'].append({
                'action': '推出促销活动',
                'reason': '试戴量下滑',
                'priority': 'high'
            })

        # Emerging styles
        emerging = self.identify_emerging_styles(14)
        top_emerging = [e for e in emerging if e['is_emerging']][:3]

        if top_emerging:
            plan['short_term'].append({
                'action': f'重点推广新兴风格：{", ".join([e["style"] for e in top_emerging])}',
                'reason': '这些风格增长迅速，收藏转化好',
                'priority': 'medium'
            })

        # Anomalies
        anomalies = self.detect_anomalies(7)
        if anomalies:
            latest = anomalies[-1]
            plan['immediate_actions'].append({
                'action': f'关注{latest["date"]}数据{latest["type"]}',
                'reason': f'较预期{"高" if latest["type"] == "spike" else "低"}了 {abs(latest["z_score"]):.1f} 个标准差',
                'priority': 'high' if latest['severity'] == 'high' else 'medium'
            })

        # Inventory
        inventory = self.generate_inventory_recommendations()
        high_demand = [i for i in inventory if i['status'] == 'high_demand'][:3]

        if high_demand:
            plan['short_term'].append({
                'action': f'确保高需求款式库存：{", ".join([i["design_name"] for i in high_demand])}',
                'reason': '收藏和预约转化率都很高',
                'priority': 'medium'
            })

        return plan

    def get_insights_report(self) -> Dict:
        """Get comprehensive AI insights report."""
        return {
            'predictions': self.predict_trend(7),
            'emerging_styles': self.identify_emerging_styles(14),
            'inventory_recommendations': self.generate_inventory_recommendations(),
            'anomalies': self.detect_anomalies(7),
            'action_plan': self.generate_action_plan()
        }
