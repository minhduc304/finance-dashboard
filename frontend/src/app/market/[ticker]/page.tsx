"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, TrendingDown, RefreshCw, DollarSign } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

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

export default function StockDetailPage() {
  const params = useParams();
  const ticker = params.ticker as string;
  
  const [stock, setStock] = useState<Stock | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStockData = async () => {
    setLoading(true);
    try {
      // Fetch stock info
      const stockResponse = await fetch(`http://localhost:8000/api/v1/market/stocks/${ticker}`);
      const stockData = await stockResponse.json();
      if (!stockData.detail) {
        setStock(stockData);
      }

      // Fetch price history
      const priceResponse = await fetch(`http://localhost:8000/api/v1/market/stocks/${ticker}/price?days=10`);
      const priceData = await priceResponse.json();
      if (Array.isArray(priceData)) {
        // Sort by date ascending for the chart
        const sortedPrices = priceData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        setPriceHistory(sortedPrices);
      }

      // Fetch news
      const newsResponse = await fetch(`http://localhost:8000/api/v1/market/stocks/${ticker}/news`);
      const newsData = await newsResponse.json();
      if (Array.isArray(newsData)) {
        setNews(newsData);
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

  const latestPrice = priceHistory[priceHistory.length - 1];
  const previousPrice = priceHistory[priceHistory.length - 2];
  const priceChange = latestPrice && previousPrice ? latestPrice.close - previousPrice.close : 0;
  const priceChangePercent = latestPrice && previousPrice ? ((priceChange / previousPrice.close) * 100) : 0;

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
    </div>
  );
}