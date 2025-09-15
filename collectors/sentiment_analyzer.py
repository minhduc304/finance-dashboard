"""
Advanced Sentiment Analyzer for Financial Reddit Content
Implements Priority 1 & 2 improvements from sentiment analysis report
"""

import re
from typing import Dict, List, Optional, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import nltk
from datetime import datetime

class FinancialSentimentAnalyzer:
    """
    Sentiment analyzer specifically tuned for financial Reddit content.
    Uses VADER as primary analyzer with financial lexicon updates and context awareness.
    """

    def __init__(self):
        """Initialize sentiment analyzer with financial context"""
        # Download required NLTK data (run once)
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)

        # Initialize VADER analyzer
        self.vader = SentimentIntensityAnalyzer()

        # Update VADER lexicon with financial terms
        self._update_financial_lexicon()

        # Bot patterns to filter out
        self.bot_patterns = [
            r'\*\*User Report\*\*',
            r'Total Submissions.*First Seen In WSB',
            r'\[AutoModerator\]',
            r'I am a bot',
            r'This is an automated',
            r'beep boop',
            r'Join WSB Discord'
        ]

        # Meta content patterns to filter
        self.meta_patterns = [
            r'^Rate My Portfolio',
            r'^Daily Discussion',
            r'^Weekend Discussion',
            r'^What Are Your Moves',
            r'Options Questions Safe Haven',
            r'Please use this thread',
            r'This thread is for'
        ]

        # Negation patterns for context awareness
        self.negation_patterns = [
            r"not\s+", r"n't\s+", r"no\s+", r"never\s+",
            r"neither\s+", r"nor\s+", r"hardly\s+", r"barely\s+"
        ]

        # Sarcasm indicators (especially for WSB)
        self.sarcasm_indicators = [
            r'/s\b', r'\bkek\b', r'\blmao\b', r'\blmfao\b',
            r'🤡', r'🤣', r'😂', r'sure buddy', r'totally',
            r'definitely not', r'yeah right'
        ]

    def _update_financial_lexicon(self):
        """Update VADER lexicon with financial-specific terms"""
        financial_updates = {
            # Bullish terms
            'bullish': 2.5,
            'moon': 3.0,
            'mooning': 3.0,
            'squeeze': 2.5,
            'breakout': 2.0,
            'rally': 2.0,
            'pump': 2.0,
            'tendies': 2.5,
            'lambo': 2.5,
            'gains': 2.0,
            'profit': 1.5,
            'green': 1.5,
            'calls': 1.5,
            'diamond hands': 2.5,
            '💎🙌': 2.5,
            'to the moon': 3.0,
            '🚀': 2.5,
            'rocket': 2.5,
            'undervalued': 2.0,
            'oversold': 1.5,

            # Bearish terms
            'bearish': -2.5,
            'crash': -3.0,
            'dump': -3.0,
            'dumping': -3.0,
            'tank': -2.5,
            'tanking': -2.5,
            'drill': -2.5,
            'drilling': -2.5,
            'puts': -1.5,
            'short': -1.5,
            'red': -1.5,
            'loss': -2.0,
            'losses': -2.0,
            'bagholder': -2.5,
            'bagholding': -2.5,
            'overvalued': -2.0,
            'overbought': -1.5,
            'rug pull': -3.0,
            'paper hands': -2.0,
            '📉': -2.0,
            'bleeding': -2.5,
            'bloodbath': -3.0,

            # Neutral/Context terms
            'hold': 0.0,
            'holding': 0.0,
            'hodl': 0.5,  # Slightly positive as it implies confidence
            'DD': 0.5,    # Due diligence is slightly positive
            'YOLO': 0.0,  # Neutral - could go either way
            'FD': -0.5,   # Financial derivatives (risky)
            'theta': -0.5, # Time decay is generally negative
            'IV': 0.0,    # Implied volatility is neutral
        }

        # Update VADER's lexicon
        self.vader.lexicon.update(financial_updates)

    def _is_bot_or_meta_content(self, text: str) -> bool:
        """Check if text is bot-generated or meta content"""
        # Check for bot patterns
        for pattern in self.bot_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check for meta content patterns
        for pattern in self.meta_patterns:
            if re.search(pattern, text[:200], re.IGNORECASE):  # Check beginning of text
                return True

        return False

    def _detect_sarcasm(self, text: str) -> float:
        """
        Detect sarcasm in text and return confidence score
        Returns: 0.0 (no sarcasm) to 1.0 (definitely sarcastic)
        """
        sarcasm_score = 0.0
        text_lower = text.lower()

        # Check for explicit sarcasm indicators
        for indicator in self.sarcasm_indicators:
            if re.search(indicator, text_lower):
                sarcasm_score += 0.3

        # Check for contradiction patterns (e.g., "great job losing money")
        positive_words = ['great', 'amazing', 'awesome', 'fantastic', 'brilliant']
        negative_context = ['loss', 'crash', 'down', 'red', 'dump']

        for pos in positive_words:
            if pos in text_lower:
                for neg in negative_context:
                    if neg in text_lower:
                        sarcasm_score += 0.4
                        break

        return min(sarcasm_score, 1.0)

    def _apply_negation_handling(self, text: str, base_score: float) -> float:
        """
        Adjust sentiment score based on negation patterns
        """
        # Look for negation patterns before sentiment words
        negation_adjustment = 0.0

        for pattern in self.negation_patterns:
            # Find all negations in text
            negations = re.finditer(pattern, text.lower())
            for neg in negations:
                # Check if negation precedes a sentiment word within 3 words
                following_text = text[neg.end():neg.end()+30].lower()

                # Strong sentiment words that would be reversed by negation
                if any(word in following_text for word in ['bullish', 'bearish', 'good', 'bad', 'great', 'terrible']):
                    # Flip sentiment influence
                    negation_adjustment = -base_score * 0.5

        return base_score + negation_adjustment

    def _get_subreddit_adjustment(self, subreddit: str, base_score: float) -> float:
        """
        Adjust sentiment based on subreddit culture
        """
        subreddit_lower = subreddit.lower()

        if subreddit_lower == 'wallstreetbets':
            # WSB tends to be more extreme and ironic
            # Dampen extreme sentiments slightly
            if abs(base_score) > 0.5:
                return base_score * 0.8
            return base_score

        elif subreddit_lower in ['investing', 'securityanalysis', 'valueinvesting']:
            # More conservative subreddits - slight boost to moderate sentiments
            if abs(base_score) < 0.3:
                return base_score * 1.2
            return base_score

        elif subreddit_lower == 'pennystocks':
            # Penny stocks tend to have more extreme sentiment
            return base_score * 1.1

        return base_score

    def calculate_sentiment(self, text: str, subreddit: Optional[str] = None) -> Dict[str, any]:
        """
        Calculate sentiment with enhanced financial context

        Args:
            text: Text to analyze
            subreddit: Optional subreddit name for context-specific adjustments

        Returns:
            Dictionary with sentiment scores and metadata
        """
        # Check for bot or meta content
        if self._is_bot_or_meta_content(text):
            return {
                "score": 0.0,
                "label": "neutral",
                "confidence": 0.0,
                "is_bot_or_meta": True,
                "method": "filtered"
            }

        # Get VADER scores
        vader_scores = self.vader.polarity_scores(text)

        # Get TextBlob scores for comparison
        try:
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            textblob_subjectivity = blob.sentiment.subjectivity
        except:
            textblob_polarity = 0.0
            textblob_subjectivity = 0.5

        # Primary score from VADER (better for social media)
        compound_score = vader_scores['compound']

        # Apply negation handling
        compound_score = self._apply_negation_handling(text, compound_score)

        # Check for sarcasm
        sarcasm_confidence = self._detect_sarcasm(text)
        if sarcasm_confidence > 0.5:
            # High sarcasm - reduce or flip sentiment
            compound_score = compound_score * (1 - sarcasm_confidence)

        # Apply subreddit-specific adjustments
        if subreddit:
            compound_score = self._get_subreddit_adjustment(subreddit, compound_score)

        # Weighted average with TextBlob (80% VADER, 20% TextBlob)
        final_score = (compound_score * 0.8) + (textblob_polarity * 0.2)

        # Ensure score is within bounds
        final_score = max(-1.0, min(1.0, final_score))

        # Determine label with better thresholds
        if final_score >= 0.1:
            label = "positive"
        elif final_score <= -0.1:
            label = "negative"
        else:
            label = "neutral"

        # Calculate confidence based on agreement and strength
        confidence = abs(final_score)
        if abs(compound_score - textblob_polarity) > 0.5:
            # Disagreement between methods - lower confidence
            confidence *= 0.7

        # Adjust confidence based on subjectivity
        # More subjective text = higher confidence in sentiment
        confidence = confidence * (0.5 + textblob_subjectivity * 0.5)

        return {
            "score": round(final_score, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "vader_compound": round(compound_score, 4),
            "textblob_polarity": round(textblob_polarity, 4),
            "subjectivity": round(textblob_subjectivity, 4),
            "sarcasm_detected": sarcasm_confidence > 0.5,
            "pos": round(vader_scores['pos'], 4),
            "neg": round(vader_scores['neg'], 4),
            "neu": round(vader_scores['neu'], 4),
            "is_bot_or_meta": False,
            "method": "enhanced_vader_textblob"
        }

    def calculate_aggregate_sentiment(self, sentiments: List[Dict]) -> Dict[str, any]:
        """
        Calculate aggregate sentiment from multiple sentiment scores
        Useful for getting overall sentiment for a stock from multiple posts/comments
        """
        if not sentiments:
            return {
                "aggregate_score": 0.0,
                "aggregate_label": "neutral",
                "total_items": 0,
                "confidence": 0.0
            }

        # Filter out bot/meta content
        valid_sentiments = [s for s in sentiments if not s.get('is_bot_or_meta', False)]

        if not valid_sentiments:
            return {
                "aggregate_score": 0.0,
                "aggregate_label": "neutral",
                "total_items": 0,
                "confidence": 0.0
            }

        # Weighted average based on confidence
        total_weight = sum(s.get('confidence', 0.5) for s in valid_sentiments)
        if total_weight == 0:
            total_weight = 1

        weighted_score = sum(
            s['score'] * s.get('confidence', 0.5)
            for s in valid_sentiments
        ) / total_weight

        # Determine aggregate label
        if weighted_score >= 0.1:
            label = "positive"
        elif weighted_score <= -0.1:
            label = "negative"
        else:
            label = "neutral"

        # Calculate confidence metrics
        avg_confidence = sum(s.get('confidence', 0.5) for s in valid_sentiments) / len(valid_sentiments)

        # Count distribution
        positive_count = sum(1 for s in valid_sentiments if s['label'] == 'positive')
        negative_count = sum(1 for s in valid_sentiments if s['label'] == 'negative')
        neutral_count = sum(1 for s in valid_sentiments if s['label'] == 'neutral')

        return {
            "aggregate_score": round(weighted_score, 4),
            "aggregate_label": label,
            "total_items": len(valid_sentiments),
            "confidence": round(avg_confidence, 4),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "positive_pct": round(positive_count / len(valid_sentiments), 4),
            "negative_pct": round(negative_count / len(valid_sentiments), 4),
            "neutral_pct": round(neutral_count / len(valid_sentiments), 4)
        }


if __name__ == "__main__":
    # Test the sentiment analyzer
    analyzer = FinancialSentimentAnalyzer()

    # Test cases from the database analysis
    test_cases = [
        {
            "text": "TSLA saved my account from $3k → $21k 💎🙌",
            "subreddit": "wallstreetbets"
        },
        {
            "text": "How Tesla Stocks rises",
            "subreddit": "stocks"
        },
        {
            "text": "Rate My Portfolio - r/Stocks Quarterly Thread September 2025",
            "subreddit": "stocks"
        },
        {
            "text": "The market is going to crash hard. Sell everything now!",
            "subreddit": "investing"
        },
        {
            "text": "Not bullish on this stock anymore",
            "subreddit": "stocks"
        },
        {
            "text": "Great job losing all your money! /s",
            "subreddit": "wallstreetbets"
        }
    ]

    # Test sentiment analyzer
    for test in test_cases:
        result = analyzer.calculate_sentiment(test["text"], test["subreddit"])
        # Test results available in result dict