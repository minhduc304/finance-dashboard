import praw
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.social_sentiment import Base, RedditPost, RedditComment

load_dotenv()

class RedditCollector:
    def __init__(self, database_url: Optional[str] = None):
        """Initialize Reddit collector with PRAW and database connection"""
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="FinanceDashboard/1.0 (Stock Sentiment Analyzer)",
        )
        
        # Database setup
        if database_url:
            self.engine = create_engine(database_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        else:
            self.session = None
        
        # Finance/stock subreddits to monitor
        self.subreddits = [
            "wallstreetbets",
            "stocks", 
            "investing",
            "StockMarket",
            "pennystocks",
            "options",
            "SecurityAnalysis",
            "ValueInvesting",
            "dividends",
            "Bogleheads"
        ]
        
        # Common stock ticker pattern (basic version)
        self.ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        
        # Common ticker blacklist (words that match pattern but aren't tickers)
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
        
        # Find all potential tickers
        potential_tickers = self.ticker_pattern.findall(text)
        
        # Filter out blacklisted words and single letters (except I for Intel)
        tickers = []
        for ticker in potential_tickers:
            if ticker not in self.ticker_blacklist and (len(ticker) > 1 or ticker == 'I'):
                # Look for $ prefix which often indicates a ticker
                if f'${ticker}' in text or f'${ticker.lower()}' in text.lower():
                    tickers.append(ticker)
                # Or if it appears multiple times or in specific contexts
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
        
        return list(set(tickers))  # Remove duplicates
    
    def calculate_sentiment(self, text: str) -> Dict[str, any]:
        """
        Basic sentiment calculation (placeholder for actual sentiment analysis)
        In production, you'd use TextBlob, VADER, or a financial-specific model
        """
        # Placeholder implementation - returns neutral sentiment
        # You should replace this with actual sentiment analysis
        bullish_words = {'buy', 'long', 'bullish', 'moon', 'rocket', 'gain', 'up', 'calls', 'green', 'profit'}
        bearish_words = {'sell', 'short', 'bearish', 'crash', 'down', 'puts', 'red', 'loss', 'dump'}
        
        text_lower = text.lower() if text else ""
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        if bullish_count > bearish_count:
            return {"score": 0.5, "label": "positive"}
        elif bearish_count > bullish_count:
            return {"score": -0.5, "label": "negative"}
        else:
            return {"score": 0.0, "label": "neutral"}
    
    def collect_posts(self, subreddit_name: str, limit: int = 100, time_filter: str = "day") -> List[RedditPost]:
        """
        Collect posts from a specific subreddit
        
        Args:
            subreddit_name: Name of the subreddit
            limit: Number of posts to collect
            time_filter: Time filter for top posts ('hour', 'day', 'week', 'month', 'year', 'all')
        """
        collected_posts = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get hot posts and top posts
            for submission in subreddit.hot(limit=limit//2):
                post = self._process_submission(submission, subreddit_name)
                if post:
                    collected_posts.append(post)
            
            for submission in subreddit.top(time_filter=time_filter, limit=limit//2):
                post = self._process_submission(submission, subreddit_name)
                if post and post.reddit_id not in [p.reddit_id for p in collected_posts]:
                    collected_posts.append(post)
            
            print(f"Collected {len(collected_posts)} posts from r/{subreddit_name}")
            
        except Exception as e:
            print(f"Error collecting posts from r/{subreddit_name}: {e}")
        
        return collected_posts
    
    def _process_submission(self, submission, subreddit_name: str) -> Optional[RedditPost]:
        """Process a single Reddit submission into a RedditPost object"""
        try:
            # Combine title and selftext for ticker extraction and sentiment
            full_text = f"{submission.title} {submission.selftext}"
            tickers = self.extract_tickers(full_text)
            sentiment = self.calculate_sentiment(full_text)
            
            post = RedditPost(
                reddit_id=submission.id,
                subreddit=subreddit_name,
                title=submission.title[:500],  # Limit to 500 chars as per model
                content=submission.selftext[:10000] if submission.selftext else None,  # Reasonable limit
                author=str(submission.author) if submission.author else "[deleted]",
                score=submission.score,
                num_comments=submission.num_comments,
                mentioned_tickers=tickers if tickers else None,
                sentiment_score=sentiment["score"],
                sentiment_label=sentiment["label"],
                created_utc=datetime.fromtimestamp(submission.created_utc),
                scraped_at=datetime.utcnow()
            )
            
            return post
            
        except Exception as e:
            print(f"Error processing submission {submission.id}: {e}")
            return None
    
    def collect_comments(self, post: RedditPost, limit: int = 50) -> List[RedditComment]:
        """
        Collect comments for a specific post
        
        Args:
            post: RedditPost object to collect comments for
            limit: Maximum number of comments to collect
        """
        collected_comments = []
        
        try:
            submission = self.reddit.submission(id=post.reddit_id)
            
            # Replace "More Comments" with actual comments (limited)
            submission.comments.replace_more(limit=0)
            
            # Flatten comment tree and get top comments
            all_comments = submission.comments.list()[:limit]
            
            for comment in all_comments:
                processed_comment = self._process_comment(comment, post)
                if processed_comment:
                    collected_comments.append(processed_comment)
            
            print(f"Collected {len(collected_comments)} comments for post {post.reddit_id}")
            
        except Exception as e:
            print(f"Error collecting comments for post {post.reddit_id}: {e}")
        
        return collected_comments
    
    def _process_comment(self, comment, post: RedditPost) -> Optional[RedditComment]:
        """Process a single Reddit comment into a RedditComment object"""
        try:
            if not hasattr(comment, 'body'):
                return None
            
            tickers = self.extract_tickers(comment.body)
            sentiment = self.calculate_sentiment(comment.body)
            
            reddit_comment = RedditComment(
                reddit_id=comment.id,
                post_id=post.id if post.id else None,
                author=str(comment.author) if comment.author else "[deleted]",
                content=comment.body[:10000],  # Reasonable limit
                score=comment.score,
                mentioned_tickers=tickers if tickers else None,
                sentiment_score=sentiment["score"],
                sentiment_label=sentiment["label"],
                created_utc=datetime.fromtimestamp(comment.created_utc),
                scraped_at=datetime.utcnow()
            )
            
            return reddit_comment
            
        except Exception as e:
            print(f"Error processing comment {comment.id}: {e}")
            return None
    
    def collect_from_all_subreddits(self, posts_per_sub: int = 25, comments_per_post: int = 10):
        """
        Collect posts and comments from all configured subreddits
        
        Args:
            posts_per_sub: Number of posts to collect per subreddit
            comments_per_post: Number of comments to collect per post
        """
        all_posts = []
        all_comments = []
        
        for subreddit_name in self.subreddits:
            print(f"\nCollecting from r/{subreddit_name}...")
            
            # Collect posts
            posts = self.collect_posts(subreddit_name, limit=posts_per_sub)
            all_posts.extend(posts)
            
            # Save posts to database if session exists
            if self.session:
                for post in posts:
                    existing = self.session.query(RedditPost).filter_by(reddit_id=post.reddit_id).first()
                    if not existing:
                        self.session.add(post)
                        self.session.commit()
                        
                        # Collect comments for this post
                        comments = self.collect_comments(post, limit=comments_per_post)
                        all_comments.extend(comments)
                        
                        # Save comments
                        for comment in comments:
                            comment.post_id = post.id
                            existing_comment = self.session.query(RedditComment).filter_by(reddit_id=comment.reddit_id).first()
                            if not existing_comment:
                                self.session.add(comment)
                
                self.session.commit()
        
        print(f"\n=== Collection Summary ===")
        print(f"Total posts collected: {len(all_posts)}")
        print(f"Total comments collected: {len(all_comments)}")
        
        # Print ticker summary
        all_tickers = set()
        for post in all_posts:
            if post.mentioned_tickers:
                all_tickers.update(post.mentioned_tickers)
        for comment in all_comments:
            if comment.mentioned_tickers:
                all_tickers.update(comment.mentioned_tickers)
        
        print(f"Unique tickers mentioned: {len(all_tickers)}")
        if all_tickers:
            print(f"Top tickers: {', '.join(list(all_tickers)[:10])}")
        
        return all_posts, all_comments


# Example usage
if __name__ == "__main__":
    # Initialize collector with database URL (update with your actual database URL)
    # For PostgreSQL: "postgresql://username:password@localhost/dbname"
    # For SQLite: "sqlite:///reddit_data.db"
    
    collector = RedditCollector(database_url="sqlite:///reddit_sentiment.db")
    
    # Collect data from all subreddits
    posts, comments = collector.collect_from_all_subreddits(
        posts_per_sub=10,  # Collect 10 posts per subreddit
        comments_per_post=5  # Collect 5 comments per post
    )
    
    print("\nData collection complete!")




