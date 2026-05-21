"""
Analytics aggregation service.

Builds HTTP-facing analytics DTOs for both durable sessions (loaded from the
configured persistence driver) and development-only ephemeral sessions (loaded
from Redis). Route modules should delegate aggregation and DTO construction here
so they remain focused on authentication, validation and HTTP concerns.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone

from src.domain.conversation import HistoryMessage, ScoreData, SessionMeta, SessionRecord
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.persistence.factory import get_driver
from src.interfaces.http.schemas.chat import ConversationEntry, Message
from src.interfaces.http.schemas.data import (
    AnalyticsPatterns,
    AnalyticsPeriod,
    AnalyticsResponse,
    AnalyticsSentiment,
    AnalyticsSummary,
    AnalyticsUsers,
    ChatSummary,
    MetricsData,
    PeakHour,
    SentimentData,
    SentimentDistribution,
    SentimentPoint,
    TimelineEntry,
    TopicPattern,
    TopicsData,
    UserSegment,
)


EphemeralRecord = tuple[SessionMeta, ScoreData | None, list[HistoryMessage]]


class AnalyticsService:
    def __init__(self):
        self.cache = CacheClient()

    def chat_summary(self, session: SessionMeta | SessionRecord) -> ChatSummary:
        return ChatSummary(
            session_id=session.session_id,
            agent_id=session.agent_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_messages=session.total_messages,
            total_tokens=session.total_tokens,
            resolved=session.resolved,
            escalated=session.escalated,
        )

    def conversation_from_history(self, history: list[HistoryMessage]) -> list[ConversationEntry]:
        return [
            ConversationEntry(message=Message(
                id=m.message_id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                status=m.status,
                tokens=m.tokens,
                response_time_ms=m.response_time_ms,
            ))
            for m in history
        ]

    def sentiment_from_scores(self, scores: ScoreData | None) -> SentimentData:
        if not scores:
            return SentimentData(score=0.0, label="neutral", progression=[])
        progression = [
            SentimentPoint(message_id=m.message_id, score=m.sentiment_score or 0.0)
            for m in scores.messages
            if m.role == "user" and m.sentiment_score is not None
        ]
        return SentimentData(
            score=scores.avg_sentiment_score or 0.0,
            label=scores.sentiment_label or "neutral",
            progression=progression,
        )

    def topics_from_scores(self, scores: ScoreData | None) -> TopicsData:
        if not scores:
            return TopicsData(detected=[], main_topic="", intent=None)
        return TopicsData(
            detected=scores.all_topics,
            main_topic=scores.main_topic or "",
            intent=scores.intent,
        )

    def resolution(self, session: SessionMeta | SessionRecord) -> str:
        if session.resolved:
            return "resolved"
        if session.escalated:
            return "escalated"
        return "open"

    def metrics_from_session(
        self,
        session: SessionMeta | SessionRecord,
        scores: ScoreData | None,
        history: list[HistoryMessage],
    ) -> MetricsData:
        response_times = [m.response_time_ms for m in history if m.role == "assistant" and m.response_time_ms]
        avg_rt = round(sum(response_times) / len(response_times), 1) if response_times else 0.0
        time_to_escalation = None
        if session.escalated and session.ended_at:
            try:
                start = datetime.fromisoformat(session.started_at)
                end = datetime.fromisoformat(session.ended_at)
                time_to_escalation = int((end - start).total_seconds())
            except Exception:
                pass
        return MetricsData(
            total_messages=session.total_messages,
            total_tokens=session.total_tokens,
            avg_user_message_length=scores.avg_user_message_length or 0.0 if scores else 0.0,
            avg_response_time_ms=avg_rt,
            time_to_escalation_seconds=time_to_escalation,
            resolution=self.resolution(session),
        )

    def ephemeral_records(self, agent_id: str) -> list[EphemeralRecord]:
        records = []
        for session_id in self.cache.list_ephemeral_sessions(agent_id):
            meta = self.cache.get_session_meta(session_id)
            if not meta or meta.agent_id != agent_id:
                continue
            records.append((meta, self.cache.get_scores(session_id), self.cache.get_history(session_id)))
        return sorted(records, key=lambda item: item[0].started_at, reverse=True)

    def build_persistent_analytics(self, agent_id: str, from_: str | None, to: str | None) -> AnalyticsResponse:
        driver = get_driver()
        sessions = driver.list_sessions(agent_id)

        if from_:
            sessions = [s for s in sessions if s.started_at >= from_]
        if to:
            sessions = [s for s in sessions if s.started_at <= to]

        session_ids = {s.session_id for s in sessions}
        scores = [sc for sc in driver.load_all_scores(agent_id) if sc.session_id in session_ids]
        users = {s.user_id for s in sessions if s.user_id}
        return self._build_analytics(
            sessions=sessions,
            scores=scores,
            unique_users=users,
            period=AnalyticsPeriod(from_=from_, to=to),
            segments=self._build_segments(driver, agent_id, sessions, users),
        )

    def build_ephemeral_analytics(self, agent_id: str) -> AnalyticsResponse:
        records = self.ephemeral_records(agent_id)
        sessions = [meta for meta, _, _ in records]
        scores = [score for _, score, _ in records if score]
        users = {s.user_id for s in sessions if s.user_id}
        return self._build_analytics(
            sessions=sessions,
            scores=scores,
            unique_users=users,
            period=AnalyticsPeriod(from_=None, to=None),
            segments=[],
        )

    def _build_segments(self, driver, agent_id: str, sessions, unique_users: set) -> list[UserSegment]:
        user_contexts = driver.list_user_contexts(agent_id)
        relevant = [uc for uc in user_contexts if uc.user_id in unique_users and uc.segment]
        seg_counts: Counter = Counter(uc.segment for uc in relevant)
        seg_users: dict[str, set] = {}
        for uc in relevant:
            seg_users.setdefault(uc.segment, set()).add(uc.user_id)
        result = []
        for seg, count in seg_counts.most_common():
            seg_session_ids = {s.session_id for s in sessions if s.user_id in seg_users.get(seg, set())}
            seg_sessions = [s for s in sessions if s.session_id in seg_session_ids]
            resolved_count = sum(1 for s in seg_sessions if s.resolved)
            resolution_rate = round(resolved_count / len(seg_sessions), 4) if seg_sessions else 0.0
            result.append(UserSegment(segment=seg, total_users=count, resolution_rate=resolution_rate))
        return result

    def _empty_analytics(self, period: AnalyticsPeriod) -> AnalyticsResponse:
        return AnalyticsResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            period=period,
            summary=AnalyticsSummary(
                total_chats=0, total_messages=0, total_users=0,
                avg_messages_per_chat=0.0, avg_chat_duration_seconds=0.0,
                avg_response_time_ms=0.0, resolution_rate=0.0, escalation_rate=0.0,
                total_tokens_used=0, avg_tokens_per_chat=0.0,
            ),
            patterns=AnalyticsPatterns(
                most_common_topics=[], most_common_unresolved_topics=[],
                peak_hours=[], peak_days=[], avg_messages_to_resolution=0.0,
                avg_messages_to_escalation=0.0,
            ),
            sentiment=AnalyticsSentiment(
                avg_score=0.0,
                distribution=SentimentDistribution(positive=0.0, neutral=1.0, negative=0.0),
            ),
            users=AnalyticsUsers(new_users=0, returning_users=0, avg_chats_per_user=0.0, segments=[]),
            timeline=[],
        )

    def _build_analytics(
        self,
        sessions: list[SessionMeta | SessionRecord],
        scores: list[ScoreData],
        unique_users: set,
        period: AnalyticsPeriod,
        segments: list[UserSegment],
    ) -> AnalyticsResponse:
        total = len(sessions)
        if total == 0:
            return self._empty_analytics(period)

        total_msgs = sum(s.total_messages for s in sessions)
        total_tokens = sum(s.total_tokens for s in sessions)
        resolved = sum(1 for s in sessions if s.resolved)
        escalated = sum(1 for s in sessions if s.escalated)
        returning = {uid for uid in unique_users if sum(1 for s in sessions if s.user_id == uid) > 1}

        durations = []
        for session in sessions:
            if session.started_at and session.ended_at:
                try:
                    start = datetime.fromisoformat(session.started_at)
                    end = datetime.fromisoformat(session.ended_at)
                    durations.append((end - start).total_seconds())
                except Exception:
                    pass
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

        resolved_map = {s.session_id: s.resolved for s in sessions}
        topic_counts: Counter = Counter()
        unresolved_topic_counts: Counter = Counter()
        for score in scores:
            for topic in score.all_topics:
                topic_counts[topic] += 1
                if not resolved_map.get(score.session_id, True):
                    unresolved_topic_counts[topic] += 1

        sentiment_values = [s.avg_sentiment_score for s in scores if s.avg_sentiment_score is not None]
        avg_sentiment = round(sum(sentiment_values) / len(sentiment_values), 4) if sentiment_values else 0.0

        rt_values = [s.avg_response_time_ms for s in scores if s.avg_response_time_ms > 0]
        avg_rt = round(sum(rt_values) / len(rt_values), 1) if rt_values else 0.0

        labels = [s.sentiment_label for s in scores if s.sentiment_label]
        label_counter = Counter(labels)
        label_total = len(labels) or 1

        hour_counts: Counter = Counter()
        day_counts: Counter = Counter()
        daily = defaultdict(lambda: {
            "total_chats": 0, "resolved": 0, "escalated": 0, "users": set(),
            "tokens": 0, "sentiments": [], "response_times": [],
        })
        for session in sessions:
            try:
                dt = datetime.fromisoformat(session.started_at)
                hour_counts[f"{dt.hour:02d}:00"] += 1
                day_counts[dt.strftime("%A")] += 1
                date = dt.strftime("%Y-%m-%d")
                daily[date]["total_chats"] += 1
                daily[date]["resolved"] += int(session.resolved)
                daily[date]["escalated"] += int(session.escalated)
                if session.user_id:
                    daily[date]["users"].add(session.user_id)
                daily[date]["tokens"] += session.total_tokens
            except Exception:
                pass

        for score in scores:
            if not score.updated_at:
                continue
            try:
                date = datetime.fromisoformat(score.updated_at).strftime("%Y-%m-%d")
                if score.avg_sentiment_score is not None:
                    daily[date]["sentiments"].append(score.avg_sentiment_score)
                if score.avg_response_time_ms > 0:
                    daily[date]["response_times"].append(score.avg_response_time_ms)
            except Exception:
                pass

        timeline = []
        for date in sorted(daily.keys()):
            item = daily[date]
            sentiments = item["sentiments"]
            response_times = item["response_times"]
            timeline.append(TimelineEntry(
                date=date,
                total_chats=item["total_chats"],
                resolved=item["resolved"],
                escalated=item["escalated"],
                new_users=len(item["users"]),
                total_tokens=item["tokens"],
                avg_response_time_ms=round(sum(response_times) / len(response_times), 1) if response_times else 0.0,
                avg_sentiment_score=round(sum(sentiments) / len(sentiments), 4) if sentiments else 0.0,
            ))

        resolved_msgs = [s.total_messages for s in sessions if s.resolved]
        escalated_msgs = [s.total_messages for s in sessions if s.escalated]
        return AnalyticsResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            period=period,
            summary=AnalyticsSummary(
                total_chats=total,
                total_messages=total_msgs,
                total_users=len(unique_users),
                avg_messages_per_chat=round(total_msgs / total, 1),
                avg_chat_duration_seconds=avg_duration,
                avg_response_time_ms=avg_rt,
                resolution_rate=round(resolved / total, 4),
                escalation_rate=round(escalated / total, 4),
                total_tokens_used=total_tokens,
                avg_tokens_per_chat=round(total_tokens / total, 1),
            ),
            patterns=AnalyticsPatterns(
                most_common_topics=[TopicPattern(topic=t, count=c) for t, c in topic_counts.most_common(10)],
                most_common_unresolved_topics=[
                    TopicPattern(topic=t, count=c) for t, c in unresolved_topic_counts.most_common(5)
                ],
                peak_hours=[PeakHour(hour=h, avg_chats=c) for h, c in hour_counts.most_common(3)],
                peak_days=[d for d, _ in day_counts.most_common(3)],
                avg_messages_to_resolution=round(sum(resolved_msgs) / len(resolved_msgs), 1) if resolved_msgs else 0.0,
                avg_messages_to_escalation=round(sum(escalated_msgs) / len(escalated_msgs), 1) if escalated_msgs else 0.0,
            ),
            sentiment=AnalyticsSentiment(
                avg_score=avg_sentiment,
                distribution=SentimentDistribution(
                    positive=round(label_counter.get("positive", 0) / label_total, 4),
                    neutral=round(label_counter.get("neutral", 0) / label_total, 4),
                    negative=round(label_counter.get("negative", 0) / label_total, 4),
                ),
            ),
            users=AnalyticsUsers(
                new_users=len(unique_users) - len(returning),
                returning_users=len(returning),
                avg_chats_per_user=round(total / len(unique_users), 1) if unique_users else 0.0,
                segments=segments,
            ),
            timeline=timeline,
        )
