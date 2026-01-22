"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, TrendingDown, RefreshCw, DollarSign } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { marketService } from "@/lib/api/services/market";
import { sentimentService } from "@/lib/api/services/sentiment";
import { safePercentageChange, safeDivide, isValidNumber } from "@/lib/utils/calculations";

interface Stock {
  ticker: string;
  name: string;
  long_name: string;
  sector: string;
  industry: string;
  exchange: string;
  current_price: number;
  market_cap: number;
  beta: number;
  trailing_pe: number;
  dividend_yield: number;
}

interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  daily_return: number;
}

interface NewsItem {
  title: string;
  publisher: string;
  publish_time: string;
  sentiment_label: string;
  sentiment_score: number;
}

interface SentimentSummary {
  total_mentions: number;
  avg_sentiment: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export default function StockDetailPage() {
  const params = useParams();
  const ticker = params.ticker as string;
  
  const [stock, setStock] = useState<Stock | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStockData = async () => {
    setLoading(true);
    try {
      // Fetch stock info using marketService
      const stockData = await marketService.getStockInfo(ticker);
      if (stockData && !('detail' in stockData)) {
        setStock(stockData as unknown as Stock);
      }

      // Fetch price history using marketService
      const priceData = await marketService.getStockPrice(ticker, 10);
      if (Array.isArray(priceData)) {
        // Sort by date ascending for the chart
        const sortedPrices = priceData.sort((a: PriceData, b: PriceData) =>
          new Date(a.date).getTime() - new Date(b.date).getTime()
        );
        setPriceHistory(sortedPrices);
      }

      // Fetch news using marketService
      const newsData = await marketService.getStockNews(ticker, 10);
      if (Array.isArray(newsData)) {
        setNews(newsData as unknown as NewsItem[]);
      }

      // Fetch sentiment data
      try {
        const sentimentData = await sentimentService.getStockSentiment(ticker, 7);
        if (sentimentData?.sentiment?.length > 0) {
          // Aggregate sentiment data
          const summary: SentimentSummary = {
            total_mentions: sentimentData.sentiment.reduce((sum, s) => sum + (s.total_mentions || 0), 0),
            avg_sentiment: sentimentData.sentiment.reduce((sum, s) => sum + (s.avg_sentiment || 0), 0) / sentimentData.sentiment.length,
            positive_count: sentimentData.sentiment.reduce((sum, s) => sum + (s.positive_count || 0), 0),
            negative_count: sentimentData.sentiment.reduce((sum, s) => sum + (s.negative_count || 0), 0),
            neutral_count: sentimentData.sentiment.reduce((sum, s) => sum + (s.neutral_count || 0), 0),
          };
          setSentiment(summary);
        }
      } catch {
        // Sentiment data may not be available
      }
    } catch (error) {
      console.error("Error fetching stock data:", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (ticker) {
      fetchStockData();
    }
  }, [ticker]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  const formatMarketCap = (value: number) => {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return formatCurrency(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div>Loading stock data...</div>
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="flex items-center justify-center h-64">
        <div>Stock not found</div>
      </div>
    );
  }

  // Safe array access with bounds checking
  const latestPrice = priceHistory.length > 0 ? priceHistory[priceHistory.length - 1] : null;
  const previousPrice = priceHistory.length > 1 ? priceHistory[priceHistory.length - 2] : null;

  // Safe price change calculation
  const priceChange = latestPrice && previousPrice
    ? latestPrice.close - previousPrice.close
    : 0;
  const priceChangePercent = latestPrice && previousPrice && isValidNumber(previousPrice.close) && previousPrice.close !== 0
    ? safePercentageChange(latestPrice.close, previousPrice.close, 0)
    : 0;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{stock.ticker}</h1>
          <p className="text-muted-foreground">{stock.long_name}</p>
        </div>
        <Button onClick={fetchStockData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Price</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stock.current_price)}</div>
            {latestPrice && previousPrice && (
              <div className={`flex items-center text-sm ${priceChange >= 0 ? "text-green-500" : "text-red-500"}`}>
                {priceChange >= 0 ? (
                  <TrendingUp className="mr-1 h-4 w-4" />
                ) : (
                  <TrendingDown className="mr-1 h-4 w-4" />
                )}
                {priceChange >= 0 ? "+" : ""}{formatCurrency(priceChange)} ({priceChangePercent >= 0 ? "+" : ""}{priceChangePercent.toFixed(2)}%)
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Market Cap</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatMarketCap(stock.market_cap)}</div>
            <p className="text-xs text-muted-foreground">{stock.exchange}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">P/E Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stock.trailing_pe?.toFixed(1) || "N/A"}</div>
            <p className="text-xs text-muted-foreground">Beta: {stock.beta?.toFixed(2) || "N/A"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Dividend Yield</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stock.dividend_yield ? `${(stock.dividend_yield * 100).toFixed(2)}%` : "0%"}
            </div>
            <div className="text-sm">
              <Badge variant="outline">{stock.sector}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Price Chart (10 Days)</CardTitle>
          <CardDescription>Historical price movement</CardDescription>
        </CardHeader>
        <CardContent>
          {priceHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={priceHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  domain={['dataMin - 5', 'dataMax + 5']}
                  tickFormatter={(value) => `$${value.toFixed(0)}`}
                />
                <Tooltip 
                  formatter={(value, name) => [`$${Number(value).toFixed(2)}`, name]}
                  labelFormatter={(label) => new Date(label).toLocaleDateString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="close" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }}
                  name="Close Price"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No price data available
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Company Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Industry</p>
              <p>{stock.industry}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Sector</p>
              <Badge variant="outline">{stock.sector}</Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Exchange</p>
              <p>{stock.exchange}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent News</CardTitle>
            <CardDescription>Latest news for {stock.ticker}</CardDescription>
          </CardHeader>
          <CardContent>
            {news.length > 0 ? (
              <div className="space-y-4">
                {news.slice(0, 3).map((article, index) => (
                  <div key={index} className="space-y-2">
                    <h4 className="text-sm font-medium leading-none">{article.title}</h4>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{article.publisher}</span>
                      <Badge 
                        variant={article.sentiment_label === "positive" ? "default" : 
                                article.sentiment_label === "negative" ? "destructive" : "outline"}
                        className="capitalize"
                      >
                        {article.sentiment_label}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                No news available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Social Sentiment Section */}
      {sentiment && (
        <Card>
          <CardHeader>
            <CardTitle>Social Sentiment (Last 7 Days)</CardTitle>
            <CardDescription>Reddit and social media sentiment for {stock.ticker}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">Total Mentions</p>
                <p className="text-2xl font-bold">{sentiment.total_mentions.toLocaleString()}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">Avg Sentiment</p>
                <p className={`text-2xl font-bold ${
                  sentiment.avg_sentiment > 0.1 ? 'text-green-600' :
                  sentiment.avg_sentiment < -0.1 ? 'text-red-600' : ''
                }`}>
                  {sentiment.avg_sentiment >= 0 ? '+' : ''}{sentiment.avg_sentiment.toFixed(2)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">Positive</p>
                <p className="text-2xl font-bold text-green-600">{sentiment.positive_count}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">Negative</p>
                <p className="text-2xl font-bold text-red-600">{sentiment.negative_count}</p>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Sentiment Distribution</p>
              <div className="flex h-4 w-full overflow-hidden rounded-full">
                {sentiment.total_mentions > 0 ? (
                  <>
                    <div
                      className="bg-green-500"
                      style={{ width: `${(sentiment.positive_count / sentiment.total_mentions) * 100}%` }}
                    />
                    <div
                      className="bg-gray-400"
                      style={{ width: `${(sentiment.neutral_count / sentiment.total_mentions) * 100}%` }}
                    />
                    <div
                      className="bg-red-500"
                      style={{ width: `${(sentiment.negative_count / sentiment.total_mentions) * 100}%` }}
                    />
                  </>
                ) : (
                  <div className="bg-gray-200 w-full" />
                )}
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Positive ({sentiment.positive_count})</span>
                <span>Neutral ({sentiment.neutral_count})</span>
                <span>Negative ({sentiment.negative_count})</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}