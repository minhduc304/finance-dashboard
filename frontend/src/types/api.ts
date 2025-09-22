// Portfolio types
export interface PortfolioSummary {
  id: number;
  name: string;
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  cash_balance: number;
  updated_at: string;
}

export interface Holding {
  id: number;
  symbol: string;
  quantity: number;
  average_cost: number;
  current_price?: number;
  market_value?: number;
  gain_loss?: number;
}

export interface Transaction {
  id: number;
  type: string;
  symbol?: string;
  quantity?: number;
  price?: number;
  total_amount: number;
  transaction_date: string;
}

// Market types
export interface StockInfo {
  ticker: string;
  name?: string;
  long_name?: string;
  sector?: string;
  industry?: string;
  exchange?: string;
  market_cap?: number;
  beta?: number;
  trailing_pe?: number;
  dividend_yield?: number;
  updated_at?: string;
}

export interface PricePoint {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
  daily_return?: number;
}

export interface StockPriceResponse {
  ticker: string;
  period_days: number;
  data_points: number;
  prices: PricePoint[];
}

export interface NewsArticle {
  title: string;
  link?: string;
  publisher?: string;
  publish_time?: string;
  related_tickers?: string[];
  sentiment_score?: number;
  sentiment_label?: string;
}

export interface StockNewsResponse {
  ticker: string;
  count: number;
  articles: NewsArticle[];
}

export interface TrendingStock {
  ticker: string;
  mentions: number;
  avg_sentiment: number;
}

export interface TrendingResponse {
  period: string;
  count: number;
  stocks: TrendingStock[];
}

// Insider trading types
export interface InsiderTrade {
  transaction_date?: string;
  trade_date?: string;
  company_name?: string;
  owner_name?: string;
  title?: string;
  transaction_type?: string;
  last_price?: number;
  quantity?: number;
  shares_held?: number;
  ownership_percentage?: number;
  value?: number;
}

export interface StockInsiderTradesResponse {
  ticker: string;
  period_days: number;
  transaction_type_filter?: string;
  total_trades: number;
  trades: InsiderTrade[];
}

export interface InsiderAlert {
  alert_type?: string;
  ticker?: string;
  company_name?: string;
  severity?: string;
  description?: string;
  total_value?: number;
  num_insiders?: number;
  alert_date?: string;
}

export interface InsiderAlertsResponse {
  count: number;
  severity_filter?: string;
  alerts: InsiderAlert[];
}

export interface InsiderSummaryResponse {
  ticker: string;
  summary_exists: boolean;
  company_name?: string;
  purchases?: {
    total_purchases?: number;
    total_purchase_value?: number;
    total_purchase_shares?: number;
    avg_purchase_price?: number;
    last_purchase_date?: string;
  };
  sales?: {
    total_sales?: number;
    total_sale_value?: number;
    total_sale_shares?: number;
    avg_sale_price?: number;
    last_sale_date?: string;
  };
  net_activity?: {
    net_insider_activity?: number;
    net_shares_traded?: number;
    last_activity_date?: string;
  };
  participants?: {
    unique_buyers?: number;
    unique_sellers?: number;
  };
  updated_at?: string;
}

export interface TopTrader {
  owner_name?: string;
  most_common_title?: string;
  total_trades?: number;
  total_purchases?: number;
  total_sales?: number;
  total_value_traded?: number;
  total_purchase_value?: number;
  total_sale_value?: number;
  primary_company?: string;
  last_trade_date?: string;
  last_trade_ticker?: string;
  last_trade_type?: string;
  performance?: {
    avg_return_30d?: number;
    avg_return_90d?: number;
    win_rate?: number;
  };
}

export interface TopTradersResponse {
  count: number;
  sort_by: string;
  traders: TopTrader[];
}

// Sentiment types
export interface SentimentData {
  date: string;
  total_mentions: number;
  total_posts: number;
  total_comments: number;
  avg_sentiment: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface StockSentimentResponse {
  ticker: string;
  period_days: number;
  data_points: number;
  sentiment: SentimentData[];
}

export interface TrendingSentimentStock {
  ticker: string;
  total_mentions: number;
  avg_sentiment: number;
  positive_mentions: number;
  negative_mentions: number;
  sentiment_ratio?: number;
}

export interface TrendingSentimentResponse {
  period: string;
  count: number;
  stocks: TrendingSentimentStock[];
}

export interface RedditPost {
  id: string;
  title: string;
  subreddit: string;
  author: string;
  score: number;
  num_comments: number;
  content_preview?: string;
  mentioned_tickers?: string[];
  sentiment_score?: number;
  sentiment_label?: string;
  created_utc?: string;
}

export interface StockPostsResponse {
  ticker: string;
  count: number;
  sentiment_filter?: string;
  posts: RedditPost[];
}

export interface SentimentSummaryResponse {
  date: string;
  total_mentions: number;
  total_posts: number;
  sentiment_breakdown: {
    positive: number;
    negative: number;
    neutral: number;
  };
  avg_sentiment: number;
  market_mood: string;
}