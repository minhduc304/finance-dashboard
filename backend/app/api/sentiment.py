"""
Sentiment analysis API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models import StockSentiment, RedditPost

router = APIRouter()

# Response models
class SentimentData(BaseModel):
    date: datetime
    total_mentions: int
    total_posts: int
    total_comments: int
    avg_sentiment: float
    positive_count: int
    negative_count: int
    neutral_count: int

class StockSentimentResponse(BaseModel):
    ticker: str
    period_days: int
    data_points: int
    sentiment: List[SentimentData]

class TrendingSentimentStock(BaseModel):
    ticker: str
    total_mentions: int
    avg_sentiment: float
    positive_mentions: int
    negative_mentions: int
    sentiment_ratio: Optional[float]

class TrendingSentimentResponse(BaseModel):
    period: str
    count: int
    stocks: List[TrendingSentimentStock]

class RedditPostResponse(BaseModel):
    id: str
    title: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    content_preview: Optional[str]
    mentioned_tickers: Optional[List[str]]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    created_utc: Optional[datetime]

class StockPostsResponse(BaseModel):
    ticker: str
    count: int
    sentiment_filter: Optional[str]
    posts: List[RedditPostResponse]

class SentimentBreakdown(BaseModel):
    positive: int
    negative: int
    neutral: int

class SentimentSummaryResponse(BaseModel):
    date: str
    total_mentions: int
    total_posts: int
    sentiment_breakdown: SentimentBreakdown
    avg_sentiment: float
    market_mood: str


@router.get("/stock/{ticker}", response_model=StockSentimentResponse)
async def get_stock_sentiment(
    ticker: str,
    days: int = Query(default=7, description="Number of days of sentiment history"),
    db: Session = Depends(get_db)
):
    """Get sentiment data for a specific stock"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    sentiment_data = db.query(StockSentiment).filter(
        StockSentiment.ticker == ticker.upper(),
        StockSentiment.date >= cutoff_date
    ).order_by(StockSentiment.date.desc()).all()

    return StockSentimentResponse(
        ticker=ticker.upper(),
        period_days=days,
        data_points=len(sentiment_data),
        sentiment=sentiment_data
    )


@router.get("/trending", response_model=TrendingSentimentResponse)
async def get_trending_sentiment(
    limit: int = Query(default=10, description="Number of trending stocks to return"),
    period: str = Query(default="24h", description="Time period: 24h, 7d, 30d"),
    db: Session = Depends(get_db)
):
    """Get trending stocks by sentiment mentions"""
    try:
        from sqlalchemy import func, desc

        period_days = {"24h": 1, "7d": 7, "30d": 30}.get(period, 1)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        trending = db.query(
            StockSentiment.ticker,
            func.sum(StockSentiment.total_mentions).label('total_mentions'),
            func.avg(StockSentiment.avg_sentiment).label('avg_sentiment'),
            func.sum(StockSentiment.positive_count).label('positive_total'),
            func.sum(StockSentiment.negative_count).label('negative_total')
        ).filter(
            StockSentiment.date >= cutoff_date
        ).group_by(
            StockSentiment.ticker
        ).order_by(
            desc('total_mentions')
        ).limit(limit).all()

        stocks = [
            TrendingSentimentStock(
                ticker=stock.ticker,
                total_mentions=int(stock.total_mentions),
                avg_sentiment=float(stock.avg_sentiment) if stock.avg_sentiment else 0,
                positive_mentions=int(stock.positive_total),
                negative_mentions=int(stock.negative_total),
                sentiment_ratio=(
                    float(stock.positive_total) / float(stock.negative_total)
                    if stock.negative_total and stock.negative_total > 0
                    else None
                )
            )
            for stock in trending
        ]

        return TrendingSentimentResponse(
            period=period,
            count=len(stocks),
            stocks=stocks
        )

    except Exception:
        return TrendingSentimentResponse(
            period=period,
            count=0,
            stocks=[]
        )


@router.get("/posts/{ticker}", response_model=StockPostsResponse)
async def get_stock_posts(
    ticker: str,
    limit: int = Query(default=20, description="Number of posts to return"),
    sentiment_filter: Optional[str] = Query(default=None, description="Filter by sentiment: positive, negative, neutral"),
    db: Session = Depends(get_db)
):
    """Get recent Reddit posts mentioning a specific stock"""
    from sqlalchemy import or_

    query = db.query(RedditPost).filter(
        or_(
            RedditPost.mentioned_tickers.contains([ticker.upper()]),
            RedditPost.title.contains(ticker.upper()),
            RedditPost.content.contains(ticker.upper())
        )
    )

    if sentiment_filter:
        query = query.filter(RedditPost.sentiment_label == sentiment_filter)

    posts = query.order_by(RedditPost.created_utc.desc()).limit(limit).all()

    post_responses = [
        RedditPostResponse(
            id=post.reddit_id,
            title=post.title,
            subreddit=post.subreddit,
            author=post.author,
            score=post.score,
            num_comments=post.num_comments,
            content_preview=post.content[:200] + "..." if post.content and len(post.content) > 200 else post.content,
            mentioned_tickers=post.mentioned_tickers,
            sentiment_score=post.sentiment_score,
            sentiment_label=post.sentiment_label,
            created_utc=post.created_utc
        )
        for post in posts
    ]

    return StockPostsResponse(
        ticker=ticker.upper(),
        count=len(posts),
        sentiment_filter=sentiment_filter,
        posts=post_responses
    )


@router.get("/summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    db: Session = Depends(get_db)
):
    """Get overall sentiment summary across all stocks"""
    try:
        from sqlalchemy import func

        today = datetime.now(timezone.utc).date()

        today_sentiment = db.query(
            func.sum(StockSentiment.total_mentions).label('total_mentions'),
            func.sum(StockSentiment.positive_count).label('positive'),
            func.sum(StockSentiment.negative_count).label('negative'),
            func.sum(StockSentiment.neutral_count).label('neutral'),
            func.avg(StockSentiment.avg_sentiment).label('avg_sentiment')
        ).filter(
            func.date(StockSentiment.date) == today
        ).first()

        posts_today = db.query(func.count(RedditPost.id)).filter(
            func.date(RedditPost.created_utc) == today
        ).scalar() or 0

        avg_sentiment = float(today_sentiment.avg_sentiment) if today_sentiment.avg_sentiment else 0

        return SentimentSummaryResponse(
            date=today.isoformat(),
            total_mentions=int(today_sentiment.total_mentions) if today_sentiment.total_mentions else 0,
            total_posts=posts_today,
            sentiment_breakdown=SentimentBreakdown(
                positive=int(today_sentiment.positive) if today_sentiment.positive else 0,
                negative=int(today_sentiment.negative) if today_sentiment.negative else 0,
                neutral=int(today_sentiment.neutral) if today_sentiment.neutral else 0
            ),
            avg_sentiment=avg_sentiment,
            market_mood=(
                "bullish" if avg_sentiment > 0.1
                else "bearish" if avg_sentiment < -0.1
                else "neutral"
            )
        )

    except Exception:
        return SentimentSummaryResponse(
            date=datetime.now(timezone.utc).date().isoformat(),
            total_mentions=0,
            total_posts=0,
            sentiment_breakdown=SentimentBreakdown(positive=0, negative=0, neutral=0),
            avg_sentiment=0,
            market_mood="neutral"
        )


class DailyCollectionMetric(BaseModel):
    date: str
    posts_collected: int
    comments_collected: int

class CollectionMetricsResponse(BaseModel):
    total_posts: int
    total_comments: int
    daily_average_posts: float
    daily_average_comments: float
    last_7_days: List[DailyCollectionMetric]
    target_met: bool  # True if averaging 1,000+ posts/day
    last_collection_time: Optional[datetime]


@router.get("/metrics/collection", response_model=CollectionMetricsResponse)
async def get_collection_metrics(
    db: Session = Depends(get_db)
):
    """
    Get Reddit data collection metrics to validate 1,000+ posts/day claim

    Shows:
    - Total posts and comments collected
    - Daily collection metrics for last 7 days
    - Average daily collection rate
    - Validation against 1,000+ posts/day target
    """
    try:
        from sqlalchemy import func
        from app.models import RedditComment

        # Get total counts
        total_posts = db.query(func.count(RedditPost.id)).scalar() or 0
        total_comments = db.query(func.count(RedditComment.id)).scalar() or 0

        # Get last collection time
        last_collection = db.query(RedditPost.scraped_at).order_by(
            RedditPost.scraped_at.desc()
        ).first()
        last_collection_time = last_collection[0] if last_collection else None

        # Get daily metrics for last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        daily_metrics = []

        for i in range(7):
            day_start = datetime.now(timezone.utc) - timedelta(days=6-i)
            day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            posts_count = db.query(func.count(RedditPost.id)).filter(
                RedditPost.scraped_at >= day_start,
                RedditPost.scraped_at < day_end
            ).scalar() or 0

            comments_count = db.query(func.count(RedditComment.id)).filter(
                RedditComment.scraped_at >= day_start,
                RedditComment.scraped_at < day_end
            ).scalar() or 0

            daily_metrics.append(DailyCollectionMetric(
                date=day_start.date().isoformat(),
                posts_collected=posts_count,
                comments_collected=comments_count
            ))

        # Calculate averages
        total_posts_7d = sum(m.posts_collected for m in daily_metrics)
        total_comments_7d = sum(m.comments_collected for m in daily_metrics)
        avg_posts_per_day = total_posts_7d / 7
        avg_comments_per_day = total_comments_7d / 7

        # Check if target is met (1,000+ posts/day)
        target_met = avg_posts_per_day >= 1000

        return CollectionMetricsResponse(
            total_posts=total_posts,
            total_comments=total_comments,
            daily_average_posts=round(avg_posts_per_day, 2),
            daily_average_comments=round(avg_comments_per_day, 2),
            last_7_days=daily_metrics,
            target_met=target_met,
            last_collection_time=last_collection_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collection metrics: {str(e)}"
        )


# ========== Sentiment Accuracy Validation ==========

class ValidationSampleCreate(BaseModel):
    text: str
    true_label: str
    source_type: Optional[str] = "synthetic"
    source_id: Optional[str] = None
    subreddit: Optional[str] = None
    true_score: Optional[float] = None
    notes: Optional[str] = None

class ValidationSampleResponse(BaseModel):
    id: int
    text: str
    true_label: str
    predicted_label: Optional[str]
    predicted_score: Optional[float]
    source_type: Optional[str]
    created_at: datetime

class AccuracyMetrics(BaseModel):
    total_samples: int
    accuracy: float
    precision_positive: float
    precision_negative: float
    precision_neutral: float
    recall_positive: float
    recall_negative: float
    recall_neutral: float
    f1_positive: float
    f1_negative: float
    f1_neutral: float
    macro_f1: float
    confusion_matrix: dict
    last_validated: Optional[datetime]

class ValidationResultsResponse(BaseModel):
    message: str
    samples_validated: int
    accuracy_metrics: AccuracyMetrics


@router.post("/validation/samples", response_model=ValidationSampleResponse)
async def add_validation_sample(
    sample: ValidationSampleCreate,
    db: Session = Depends(get_db)
):
    """
    Add a manually labeled sample for sentiment validation

    This is used to build a ground-truth dataset for accuracy testing.
    Each sample should have a human-verified sentiment label.
    """
    from app.models import SentimentValidationSample

    # Validate label
    if sample.true_label not in ["positive", "negative", "neutral"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="true_label must be 'positive', 'negative', or 'neutral'"
        )

    # Create validation sample
    validation_sample = SentimentValidationSample(
        text=sample.text,
        true_label=sample.true_label,
        source_type=sample.source_type,
        source_id=sample.source_id,
        subreddit=sample.subreddit,
        true_score=sample.true_score,
        notes=sample.notes
    )

    db.add(validation_sample)
    db.commit()
    db.refresh(validation_sample)

    return validation_sample


@router.post("/validation/run", response_model=ValidationResultsResponse)
async def run_validation(
    db: Session = Depends(get_db)
):
    """
    Run sentiment analysis on all validation samples and calculate accuracy metrics

    This endpoint:
    1. Fetches all validation samples
    2. Runs sentiment prediction on each
    3. Compares predictions to ground truth labels
    4. Calculates precision, recall, F1-score for each class
    5. Returns overall accuracy metrics
    """
    from app.models import SentimentValidationSample
    from collectors.sentiment_analyzer import FinancialSentimentAnalyzer

    try:
        # Get all validation samples
        samples = db.query(SentimentValidationSample).all()

        if not samples:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No validation samples found. Add samples first using POST /validation/samples"
            )

        # Initialize sentiment analyzer
        analyzer = FinancialSentimentAnalyzer()

        # Run predictions on all samples
        for sample in samples:
            sentiment_result = analyzer.calculate_sentiment(
                sample.text,
                subreddit=sample.subreddit
            )

            sample.predicted_label = sentiment_result['label']
            sample.predicted_score = sentiment_result['score']
            sample.prediction_confidence = sentiment_result.get('confidence', 0.0)
            sample.validated_at = datetime.now(timezone.utc)

        db.commit()

        # Calculate accuracy metrics
        metrics = _calculate_accuracy_metrics(samples)

        return ValidationResultsResponse(
            message="Validation completed successfully",
            samples_validated=len(samples),
            accuracy_metrics=metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running validation: {str(e)}"
        )


@router.get("/validation/accuracy", response_model=AccuracyMetrics)
async def get_validation_accuracy(
    db: Session = Depends(get_db)
):
    """
    Get current sentiment accuracy metrics

    Returns precision, recall, and F1-scores for each sentiment class,
    plus overall accuracy. Used to validate the 80%+ accuracy claim.
    """
    from app.models import SentimentValidationSample

    # Get all validated samples
    samples = db.query(SentimentValidationSample).filter(
        SentimentValidationSample.predicted_label.isnot(None)
    ).all()

    if not samples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validated samples found. Run POST /validation/run first."
        )

    metrics = _calculate_accuracy_metrics(samples)
    return metrics


@router.get("/validation/samples", response_model=List[ValidationSampleResponse])
async def get_validation_samples(
    limit: int = Query(default=50, description="Number of samples to return"),
    db: Session = Depends(get_db)
):
    """Get all validation samples"""
    from app.models import SentimentValidationSample

    samples = db.query(SentimentValidationSample).order_by(
        SentimentValidationSample.created_at.desc()
    ).limit(limit).all()

    return samples


def _calculate_accuracy_metrics(samples: list) -> AccuracyMetrics:
    """
    Calculate comprehensive accuracy metrics from validation samples

    Returns:
        AccuracyMetrics with precision, recall, F1 for each class
    """
    from collections import defaultdict

    # Initialize counters
    true_positives = defaultdict(int)
    false_positives = defaultdict(int)
    false_negatives = defaultdict(int)
    true_negatives = defaultdict(int)

    # Confusion matrix
    confusion = {
        "positive": {"positive": 0, "negative": 0, "neutral": 0},
        "negative": {"positive": 0, "negative": 0, "neutral": 0},
        "neutral": {"positive": 0, "negative": 0, "neutral": 0}
    }

    # Count predictions
    total_correct = 0
    labels = ["positive", "negative", "neutral"]

    for sample in samples:
        true_label = sample.true_label
        pred_label = sample.predicted_label

        # Update confusion matrix
        confusion[true_label][pred_label] += 1

        # Count correct predictions
        if true_label == pred_label:
            total_correct += 1

        # Calculate TP, FP, FN for each class
        for label in labels:
            if true_label == label and pred_label == label:
                true_positives[label] += 1
            elif true_label != label and pred_label == label:
                false_positives[label] += 1
            elif true_label == label and pred_label != label:
                false_negatives[label] += 1
            elif true_label != label and pred_label != label:
                true_negatives[label] += 1

    # Calculate metrics for each class
    precision = {}
    recall = {}
    f1 = {}

    for label in labels:
        tp = true_positives[label]
        fp = false_positives[label]
        fn = false_negatives[label]

        # Precision = TP / (TP + FP)
        precision[label] = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        # Recall = TP / (TP + FN)
        recall[label] = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # F1 = 2 * (Precision * Recall) / (Precision + Recall)
        if precision[label] + recall[label] > 0:
            f1[label] = 2 * (precision[label] * recall[label]) / (precision[label] + recall[label])
        else:
            f1[label] = 0.0

    # Overall accuracy
    accuracy = total_correct / len(samples) if samples else 0.0

    # Macro F1 (average of F1 scores)
    macro_f1 = sum(f1.values()) / len(f1) if f1 else 0.0

    # Get latest validation timestamp
    last_validated = max((s.validated_at for s in samples if s.validated_at), default=None)

    return AccuracyMetrics(
        total_samples=len(samples),
        accuracy=round(accuracy, 4),
        precision_positive=round(precision["positive"], 4),
        precision_negative=round(precision["negative"], 4),
        precision_neutral=round(precision["neutral"], 4),
        recall_positive=round(recall["positive"], 4),
        recall_negative=round(recall["negative"], 4),
        recall_neutral=round(recall["neutral"], 4),
        f1_positive=round(f1["positive"], 4),
        f1_negative=round(f1["negative"], 4),
        f1_neutral=round(f1["neutral"], 4),
        macro_f1=round(macro_f1, 4),
        confusion_matrix=confusion,
        last_validated=last_validated
    )