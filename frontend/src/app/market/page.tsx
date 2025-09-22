"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";
import Link from "next/link";
import { marketService } from "@/lib/api/services/market";

interface Stock {
  ticker: string;
  name: string;
  current_price: number;
  market_cap: number;
  sector: string;
  industry: string;
  beta: number;
  trailing_pe: number;
  dividend_yield: number;
}

interface NewsItem {
  title: string;
  publisher: string;
  publish_time: string;
  sentiment_label: string;
  sentiment_score: number;
}

export default function MarketPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMarketData = async () => {
    setLoading(true);
    try {
      // Fetch data for major stocks
      const stockTickers = ["AAPL", "MSFT", "GOOGL", "TSLA"];
      const stockPromises = stockTickers.map(async (ticker) => {
        try {
          const stockInfo = await marketService.getStockInfo(ticker);
          return {
            ticker: stockInfo.ticker,
            name: stockInfo.long_name || stockInfo.name || ticker,
            current_price: stockInfo.current_price || 0,
            market_cap: stockInfo.market_cap || 0,
            sector: stockInfo.sector || "Technology",
            industry: stockInfo.industry || "N/A",
            beta: stockInfo.beta || 0,
            trailing_pe: stockInfo.trailing_pe || 0,
            dividend_yield: stockInfo.dividend_yield || 0
          };
        } catch (error) {
          console.error(`Error fetching data for ${ticker}:`, error);
          return null;
        }
      });

      const stocksData = await Promise.all(stockPromises);
      setStocks(stocksData.filter(stock => stock !== null));

      // Fetch news for the first ticker
      try {
        const newsResponse = await marketService.getStockNews("AAPL", 5);
        if (newsResponse && newsResponse.articles) {
          const transformedNews = newsResponse.articles.map(article => ({
            title: article.title,
            publisher: article.publisher || "Unknown",
            publish_time: article.publish_time || new Date().toISOString(),
            sentiment_label: article.sentiment_label || "neutral",
            sentiment_score: article.sentiment_score || 0
          }));
          setNews(transformedNews);
        } else {
          setNews([]);
        }
      } catch (newsError) {
        console.error("Error fetching news:", newsError);
        setNews([]);
      }
    } catch (error) {
      console.error("Error fetching market data:", error);
      setStocks([]);
      setNews([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMarketData();
  }, []);

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

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market Overview</h1>
          <p className="text-muted-foreground">
            Real-time market data and stock information
          </p>
        </div>
        <Button onClick={fetchMarketData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stocks</CardTitle>
          <CardDescription>
            Current stock prices and key metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Market Cap</TableHead>
                <TableHead>Sector</TableHead>
                <TableHead>P/E Ratio</TableHead>
                <TableHead>Beta</TableHead>
                <TableHead>Dividend Yield</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    Loading market data...
                  </TableCell>
                </TableRow>
              ) : stocks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    No market data available
                  </TableCell>
                </TableRow>
              ) : (
                stocks.map((stock) => (
                  <TableRow key={stock.ticker}>
                    <TableCell>
                      <Link href={`/market/${stock.ticker}`} className="font-medium hover:underline">
                        <Badge variant="secondary">{stock.ticker}</Badge>
                      </Link>
                    </TableCell>
                    <TableCell>{stock.name}</TableCell>
                    <TableCell className="font-medium">
                      {formatCurrency(stock.current_price)}
                    </TableCell>
                    <TableCell>{formatMarketCap(stock.market_cap)}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{stock.sector}</Badge>
                    </TableCell>
                    <TableCell>{stock.trailing_pe?.toFixed(1) || "N/A"}</TableCell>
                    <TableCell>{stock.beta?.toFixed(2) || "N/A"}</TableCell>
                    <TableCell>
                      {stock.dividend_yield ? `${(stock.dividend_yield * 100).toFixed(2)}%` : "0%"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Market News</CardTitle>
          <CardDescription>
            Latest news with sentiment analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading news...</div>
          ) : news.length === 0 ? (
            <div className="text-center py-8">No news available</div>
          ) : (
            <div className="space-y-4">
              {news.map((article, index) => (
                <div key={index} className="flex items-start justify-between p-4 border rounded-lg">
                  <div className="space-y-2">
                    <h3 className="font-medium">{article.title}</h3>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <span>{article.publisher}</span>
                      <span>•</span>
                      <span>{new Date(article.publish_time).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {article.sentiment_label === "positive" && (
                      <Badge variant="default" className="bg-green-100 text-green-800">
                        <TrendingUp className="mr-1 h-3 w-3" />
                        Positive
                      </Badge>
                    )}
                    {article.sentiment_label === "negative" && (
                      <Badge variant="default" className="bg-red-100 text-red-800">
                        <TrendingDown className="mr-1 h-3 w-3" />
                        Negative
                      </Badge>
                    )}
                    {article.sentiment_label === "neutral" && (
                      <Badge variant="outline">Neutral</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}