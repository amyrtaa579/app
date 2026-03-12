from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
import json
from collections import Counter

from app.models import (
    AdminLog, UserActionLog, SpecialtyStat, DocumentDownloadStat,
    TestStat, DailyStat, Specialty, Document, TestResult, Admin
)
from app.schemas import statistics as schemas

class StatisticsService:
    """Сервис для сбора и анализа статистики"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== ЛОГИРОВАНИЕ ДЕЙСТВИЙ ==========
    
    async def log_admin_action(
        self,
        admin_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        changes: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Логирование действия администратора"""
        log = AdminLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        await self.db.commit()
    
    async def log_user_action(
        self,
        user_id: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ):
        """Логирование действия пользователя"""
        log = UserActionLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            ip_address=ip_address
        )
        self.db.add(log)
        await self.db.commit()
    
    # ========== СТАТИСТИКА СПЕЦИАЛЬНОСТЕЙ ==========
    
    async def track_specialty_view(self, specialty_id: int, user_id: str):
        """Отслеживание просмотра специальности"""
        # Получаем или создаем запись статистики
        result = await self.db.execute(
            select(SpecialtyStat)
            .where(SpecialtyStat.specialty_id == specialty_id)
            .order_by(SpecialtyStat.viewed_at.desc())
            .limit(1)
        )
        stat = result.scalar_one_or_none()
        
        if not stat:
            stat = SpecialtyStat(
                specialty_id=specialty_id,
                views_count=1,
                unique_users=[user_id],
                last_viewed_at=datetime.utcnow()
            )
            self.db.add(stat)
        else:
            stat.views_count += 1
            stat.last_viewed_at = datetime.utcnow()
            
            # Обновляем список уникальных пользователей
            if user_id not in stat.unique_users:
                stat.unique_users.append(user_id)
        
        await self.db.commit()
        
        # Также логируем действие
        await self.log_user_action(
            user_id=user_id,
            action="view",
            entity_type="specialty",
            entity_id=specialty_id
        )
    
    async def get_specialty_stats(
        self,
        specialty_id: int,
        period: str = "all"
    ) -> Dict[str, Any]:
        """Получить статистику по специальности"""
        # Базовая статистика
        result = await self.db.execute(
            select(SpecialtyStat)
            .where(SpecialtyStat.specialty_id == specialty_id)
        )
        stats = result.scalars().all()
        
        total_views = sum(s.views_count for s in stats)
        unique_users = set()
        for s in stats:
            unique_users.update(s.unique_users)
        
        # Статистика за период
        if period != "all":
            days = int(period) if period.isdigit() else 30
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            period_stats = [s for s in stats if s.viewed_at > cutoff]
            period_views = sum(s.views_count for s in period_stats)
        else:
            period_views = total_views
        
        return {
            "specialty_id": specialty_id,
            "total_views": total_views,
            "unique_users": len(unique_users),
            "period_views": period_views,
            "last_viewed": max((s.last_viewed_at for s in stats if s.last_viewed_at), default=None)
        }
    
    # ========== СТАТИСТИКА ДОКУМЕНТОВ ==========
    
    async def track_document_download(self, document_id: int, user_id: str):
        """Отслеживание скачивания документа"""
        result = await self.db.execute(
            select(DocumentDownloadStat)
            .where(DocumentDownloadStat.document_id == document_id)
            .order_by(DocumentDownloadStat.downloaded_at.desc())
            .limit(1)
        )
        stat = result.scalar_one_or_none()
        
        if not stat:
            stat = DocumentDownloadStat(
                document_id=document_id,
                download_count=1,
                unique_users=[user_id],
                last_downloaded_at=datetime.utcnow()
            )
            self.db.add(stat)
        else:
            stat.download_count += 1
            stat.last_downloaded_at = datetime.utcnow()
            
            if user_id not in stat.unique_users:
                stat.unique_users.append(user_id)
        
        await self.db.commit()
        
        await self.log_user_action(
            user_id=user_id,
            action="download",
            entity_type="document",
            entity_id=document_id
        )
    
    async def get_document_stats(
        self,
        document_id: int,
        period: str = "all"
    ) -> Dict[str, Any]:
        """Получить статистику по документу"""
        result = await self.db.execute(
            select(DocumentDownloadStat)
            .where(DocumentDownloadStat.document_id == document_id)
        )
        stats = result.scalars().all()
        
        total_downloads = sum(s.download_count for s in stats)
        unique_users = set()
        for s in stats:
            unique_users.update(s.unique_users)
        
        if period != "all":
            days = int(period) if period.isdigit() else 30
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            period_stats = [s for s in stats if s.downloaded_at > cutoff]
            period_downloads = sum(s.download_count for s in period_stats)
        else:
            period_downloads = total_downloads
        
        return {
            "document_id": document_id,
            "total_downloads": total_downloads,
            "unique_users": len(unique_users),
            "period_downloads": period_downloads,
            "last_downloaded": max((s.last_downloaded_at for s in stats if s.last_downloaded_at), default=None)
        }
    
    # ========== СТАТИСТИКА ТЕСТОВ ==========
    
    async def track_test_completion(
        self,
        user_id: str,
        result_id: int,
        score: int,
        answers: List[Dict],
        time_spent: Optional[int] = None
    ):
        """Отслеживание прохождения теста"""
        stat = TestStat(
            user_id=user_id,
            result_id=result_id,
            score=score,
            answers=answers,
            time_spent=time_spent
        )
        self.db.add(stat)
        await self.db.commit()
        
        await self.log_user_action(
            user_id=user_id,
            action="complete_test",
            entity_type="test",
            entity_id=result_id,
            metadata={"score": score, "time_spent": time_spent}
        )
    
    async def get_test_stats(self, period: str = "30d") -> Dict[str, Any]:
        """Получить общую статистику по тестам"""
        days = int(period.replace('d', '')) if 'd' in period else 30
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Всего прохождений
        total_result = await self.db.execute(
            select(func.count()).select_from(TestStat)
        )
        total_tests = total_result.scalar()
        
        # За период
        period_result = await self.db.execute(
            select(func.count())
            .select_from(TestStat)
            .where(TestStat.completed_at > cutoff)
        )
        period_tests = period_result.scalar()
        
        # Средний балл
        avg_result = await self.db.execute(
            select(func.avg(TestStat.score))
            .where(TestStat.completed_at > cutoff)
        )
        avg_score = avg_result.scalar() or 0
        
        # Распределение результатов
        results_dist = await self.db.execute(
            select(TestResult.id, TestResult.title, func.count(TestStat.id))
            .join(TestStat, TestStat.result_id == TestResult.id)
            .where(TestStat.completed_at > cutoff)
            .group_by(TestResult.id, TestResult.title)
            .order_by(func.count().desc())
            .limit(5)
        )
        popular_results = [
            {"id": r.id, "title": r.title, "count": count}
            for r, count in results_dist
        ]
        
        return {
            "total_tests": total_tests,
            "period_tests": period_tests,
            "average_score": round(avg_score, 2),
            "popular_results": popular_results,
            "unique_users": await self._get_unique_test_users(cutoff)
        }
    
    async def _get_unique_test_users(self, cutoff: datetime) -> int:
        """Получить количество уникальных пользователей теста"""
        result = await self.db.execute(
            select(func.count(func.distinct(TestStat.user_id)))
            .where(TestStat.completed_at > cutoff)
        )
        return result.scalar()
    
    # ========== ОБЩАЯ СТАТИСТИКА ==========
    
    async def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Получить ежедневную статистику за последние N дней"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(DailyStat)
            .where(DailyStat.date > cutoff)
            .order_by(DailyStat.date)
        )
        stats = result.scalars().all()
        
        return [
            {
                "date": stat.date.isoformat(),
                "users": stat.total_users,
                "views": stat.total_views,
                "downloads": stat.total_downloads,
                "tests": stat.total_tests
            }
            for stat in stats
        ]
    
    async def get_popular_content(
        self,
        limit: int = 10,
        period: str = "30d"
    ) -> Dict[str, Any]:
        """Получить популярный контент"""
        days = int(period.replace('d', '')) if 'd' in period else 30
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Популярные специальности
        specialty_views = await self.db.execute(
            select(
                Specialty.id,
                Specialty.name,
                func.count(UserActionLog.id).label('views')
            )
            .join(UserActionLog, and_(
                UserActionLog.entity_type == 'specialty',
                UserActionLog.entity_id == Specialty.id,
                UserActionLog.created_at > cutoff
            ))
            .group_by(Specialty.id, Specialty.name)
            .order_by(desc('views'))
            .limit(limit)
        )
        
        # Популярные документы
        document_downloads = await self.db.execute(
            select(
                Document.id,
                Document.title,
                func.count(UserActionLog.id).label('downloads')
            )
            .join(UserActionLog, and_(
                UserActionLog.entity_type == 'document',
                UserActionLog.entity_id == Document.id,
                UserActionLog.created_at > cutoff
            ))
            .group_by(Document.id, Document.title)
            .order_by(desc('downloads'))
            .limit(limit)
        )
        
        # Популярные результаты тестов
        test_results = await self.db.execute(
            select(
                TestResult.id,
                TestResult.title,
                func.count(TestStat.id).label('completions')
            )
            .join(TestStat, TestStat.result_id == TestResult.id)
            .where(TestStat.completed_at > cutoff)
            .group_by(TestResult.id, TestResult.title)
            .order_by(desc('completions'))
            .limit(limit)
        )
        
        return {
            "popular_specialties": [
                {"id": id, "name": name, "views": views}
                for id, name, views in specialty_views
            ],
            "popular_documents": [
                {"id": id, "title": title, "downloads": downloads}
                for id, title, downloads in document_downloads
            ],
            "popular_test_results": [
                {"id": id, "title": title, "completions": completions}
                for id, title, completions in test_results
            ]
        }
    
    async def get_admin_activity(
        self,
        days: int = 30,
        admin_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Получить активность администраторов"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(AdminLog).where(AdminLog.created_at > cutoff)
        
        if admin_id:
            query = query.where(AdminLog.admin_id == admin_id)
        
        query = query.order_by(AdminLog.created_at.desc()).limit(1000)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "id": log.id,
                "admin": log.admin.full_name if log.admin else "Unknown",
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "changes": log.changes,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    
    # ========== АГРЕГАЦИЯ ЕЖЕДНЕВНОЙ СТАТИСТИКИ ==========
    
    async def aggregate_daily_stats(self, target_date: Optional[date] = None):
        """Агрегирует ежедневную статистику"""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        start_date = datetime.combine(target_date, datetime.min.time())
        end_date = datetime.combine(target_date, datetime.max.time())
        
        # Уникальные пользователи
        users_result = await self.db.execute(
            select(func.count(func.distinct(UserActionLog.user_id)))
            .where(
                UserActionLog.created_at >= start_date,
                UserActionLog.created_at <= end_date
            )
        )
        unique_users = users_result.scalar() or 0
        
        # Всего просмотров
        views_result = await self.db.execute(
            select(func.count())
            .where(
                UserActionLog.action == 'view',
                UserActionLog.created_at >= start_date,
                UserActionLog.created_at <= end_date
            )
        )
        total_views = views_result.scalar() or 0
        
        # Всего скачиваний
        downloads_result = await self.db.execute(
            select(func.count())
            .where(
                UserActionLog.action == 'download',
                UserActionLog.created_at >= start_date,
                UserActionLog.created_at <= end_date
            )
        )
        total_downloads = downloads_result.scalar() or 0
        
        # Всего тестов
        tests_result = await self.db.execute(
            select(func.count())
            .where(
                TestStat.completed_at >= start_date,
                TestStat.completed_at <= end_date
            )
        )
        total_tests = tests_result.scalar() or 0
        
        # Популярные специальности
        popular_spec = await self.db.execute(
            select(
                Specialty.id,
                Specialty.name,
                func.count(UserActionLog.id).label('views')
            )
            .join(UserActionLog, and_(
                UserActionLog.entity_type == 'specialty',
                UserActionLog.entity_id == Specialty.id,
                UserActionLog.created_at >= start_date,
                UserActionLog.created_at <= end_date
            ))
            .group_by(Specialty.id, Specialty.name)
            .order_by(desc('views'))
            .limit(5)
        )
        
        # Популярные документы
        popular_docs = await self.db.execute(
            select(
                Document.id,
                Document.title,
                func.count(UserActionLog.id).label('downloads')
            )
            .join(UserActionLog, and_(
                UserActionLog.entity_type == 'document',
                UserActionLog.entity_id == Document.id,
                UserActionLog.created_at >= start_date,
                UserActionLog.created_at <= end_date
            ))
            .group_by(Document.id, Document.title)
            .order_by(desc('downloads'))
            .limit(5)
        )
        
        # Сохраняем или обновляем
        result = await self.db.execute(
            select(DailyStat).where(DailyStat.date == target_date)
        )
        daily_stat = result.scalar_one_or_none()
        
        if not daily_stat:
            daily_stat = DailyStat(date=target_date)
            self.db.add(daily_stat)
        
        daily_stat.total_users = unique_users
        daily_stat.total_views = total_views
        daily_stat.total_downloads = total_downloads
        daily_stat.total_tests = total_tests
        daily_stat.popular_specialties = [
            {"id": id, "name": name, "views": views}
            for id, name, views in popular_spec
        ]
        daily_stat.popular_documents = [
            {"id": id, "title": title, "downloads": downloads}
            for id, title, downloads in popular_docs
        ]
        
        await self.db.commit()