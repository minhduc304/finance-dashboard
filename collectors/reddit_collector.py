import praw
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv
from collectors.sentiment_analyzer import FinancialSentimentAnalyzer

load_dotenv()

class RedditCollector:
    """Pure data collector for Reddit - returns data without database operations"""

    def __init__(self):
        """Initialize Reddit collector with PRAW"""
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="FinanceDashboard/1.0 (Stock Sentiment Analyzer)",
        )

        self.sentiment_analyzer = FinancialSentimentAnalyzer()

        self.subreddits = [
            "wallstreetbets", "stocks", "investing",
            "StockMarket", "pennystocks", "options",
            "SecurityAnalysis", "ValueInvesting",
            "dividends", "Bogleheads"
        ]

        self.ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')

        self.ticker_blacklist = {
            'I', 'A', 'THE', 'AND', 'OR', 'BUT', 'FOR', 'TO', 'AT', 'BY',
            'UP', 'DOWN', 'IN', 'OUT', 'ON', 'OFF', 'ALL', 'NEW', 'OLD',
            'BUY', 'SELL', 'HOLD', 'LONG', 'SHORT', 'PUT', 'CALL', 'DD',
            'ETF', 'IPO', 'CEO', 'CFO', 'COO', 'USA', 'USD', 'GDP', 'EPS',
            'PE', 'PEG', 'RSI', 'MACD', 'EMA', 'SMA', 'ATH', 'LOL', 'IMO',
            'TLDR', 'YOLO', 'FOMO', 'FUD', 'HODL', 'WSB', 'SEC', 'FDA',
            'NYSE', 'NASDAQ', 'SP', 'DOW', 'QQQ', 'SPY', 'VOO', 'VTI'
        }

    def extract_tickers(self, text: str) -> List[str]:
        """Extract potential stock tickers from text"""
        if not text:
            return []

        potential_tickers = self.ticker_pattern.findall(text)
        tickers = []

        for ticker in potential_tickers:
            if ticker not in self.ticker_blacklist and (len(ticker) > 1 or ticker == 'I'):
                if f'${ticker}' in text or f'${ticker.lower()}' in text.lower():
                    tickers.append(ticker)
                elif text.count(ticker) > 1 or any(phrase in text.lower() for phrase in [
                    f'{ticker.lower()} stock',
                    f'{ticker.lower()} shares',
                    f'{ticker.lower()} calls',
                    f'{ticker.lower()} puts',
                    f'buying {ticker.lower()}',
                    f'selling {ticker.lower()}',
                    f'holding {ticker.lower()}'
                ]):
                    tickers.append(ticker)

        return list(set(tickers))

    def collect_posts(self, subreddit_name: str, limit: int = 100, time_filter: str = "day") -> List[Dict]:
        """
        Collect posts from a specific subreddit and return as list of dicts
        """
        collected_posts = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Get hot posts
            for submission in subreddit.hot(limit=limit//2):
                post_data = self._process_submission(submission, subreddit_name)
                if post_data:
                    collected_posts.append(post_data)

            # Get top posts
            for submission in subreddit.top(time_filter=time_filter, limit=limit//2):
                post_data = self._process_submission(submission, subreddit_name)
                if post_data and post_data['reddit_id'] not in [p['reddit_id'] for p in collected_posts]:
                    collected_posts.append(post_data)
        except Exception:
            pass  # Error collecting posts

        return collected_posts

    def _process_submission(self, submission, subreddit_name: str) -> Optional[Dict]:
        """Process a single Reddit submission into a dictionary"""
        try:
            full_text = f"{submission.title} {submission.selftext}"
            tickers = self.extract_tickers(full_text)
            sentiment = self.sentiment_analyzer.calculate_sentiment(full_text, subreddit_name)

            return {
                'reddit_id': submission.id,
                'subreddit': subreddit_name,
                'title': submission.title[:500],
                'content': submission.selftext[:10000] if submission.selftext else None,
                'author': str(submission.author) if submission.author else "[deleted]",
                'score': submission.score,
                'num_comments': submission.num_comments,
                'mentioned_tickers': tickers if tickers else None,
                'sentiment_score': sentiment.get("score", 0),
                'sentiment_label': sentiment.get("label", "neutral"),
                'created_utc': datetime.fromtimestamp(submission.created_utc),
                'scraped_at': datetime.now(timezone.utc)
            }
        except Exception:
            return None

    def collect_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        Collect comments for a specific post and return as list of dicts
        """
        collected_comments = []

        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            all_comments = submission.comments.list()[:limit]

            for comment in all_comments:
                comment_data = self._process_comment(comment, post_id, submission.subreddit.display_name)
                if comment_data:
                    collected_comments.append(comment_data)
        except Exception:
            pass  # Error collecting comments

        return collected_comments

    def _process_comment(self, comment, post_id: str, subreddit: str) -> Optional[Dict]:
        """Process a single Reddit comment into a dictionary"""
        try:
            if not hasattr(comment, 'body'):
                return None

            tickers = self.extract_tickers(comment.body)
            sentiment = self.sentiment_analyzer.calculate_sentiment(comment.body, subreddit)

            return {
                'reddit_id': comment.id,
                'post_reddit_id': post_id,
                'author': str(comment.author) if comment.author else "[deleted]",
                'content': comment.body[:10000],
                'score': comment.score,
                'mentioned_tickers': tickers if tickers else None,
                'sentiment_score': sentiment.get("score", 0),
                'sentiment_label': sentiment.get("label", "neutral"),
                'created_utc': datetime.fromtimestamp(comment.created_utc),
                'scraped_at': datetime.now(timezone.utc)
            }
        except Exception:
            return None

    def collect_trending_stocks(self, posts_per_sub: int = 25) -> Dict[str, any]:
        """
        Collect trending stocks across all subreddits
        Returns dict with trending data
        """
        all_posts = []
        ticker_mentions = {}
        sentiment_by_ticker = {}

        for subreddit_name in self.subreddits:
            posts = self.collect_posts(subreddit_name, limit=posts_per_sub)
            all_posts.extend(posts)

            for post in posts:
                if post['mentioned_tickers']:
                    for ticker in post['mentioned_tickers']:
                        ticker_mentions[ticker] = ticker_mentions.get(ticker, 0) + 1

                        if ticker not in sentiment_by_ticker:
                            sentiment_by_ticker[ticker] = []
                        sentiment_by_ticker[ticker].append(post['sentiment_score'])

        # Calculate average sentiment per ticker
        ticker_sentiment_avg = {}
        for ticker, scores in sentiment_by_ticker.items():
            ticker_sentiment_avg[ticker] = sum(scores) / len(scores) if scores else 0

        # Sort by mentions
        trending_tickers = dict(sorted(ticker_mentions.items(), key=lambda x: x[1], reverse=True)[:20])

        return {
            'trending_tickers': trending_tickers,
            'ticker_sentiment': ticker_sentiment_avg,
            'total_posts_analyzed': len(all_posts),
            'timestamp': datetime.now(timezone.utc)
        }