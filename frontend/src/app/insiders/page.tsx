"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, RefreshCw, Users } from "lucide-react";
import { insidersService } from "@/lib/api/services/insiders";

interface InsiderTrade {
  transaction_date: string;
  trade_date: string;
  ticker: string;
  company_name: string;
  owner_name: string;
  title: string;
  transaction_type: string;
  last_price: number;
  quantity: number;
  value: number;
  shares_held: number;
  ownership_percentage: number;
}

export default function InsidersPage() {
  const [trades, setTrades] = useState<InsiderTrade[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchInsiderData = async () => {
    setLoading(true);
    try {
      // Fetch insider trades for major stocks
      const stockTickers = ["AAPL", "MSFT", "TSLA", "GOOGL", "NVDA"];
      const tradePromises = stockTickers.map(async (ticker) => {
        try {
          const response = await insidersService.getStockInsiderTrades(ticker, 90);
          // Transform the API response to match our interface
          if (response && response.trades) {
            return response.trades.map((trade) => ({
              transaction_date: trade.transaction_date || "",
              trade_date: trade.trade_date || trade.transaction_date || "",
              ticker: ticker,
              company_name: trade.company_name || ticker,
              owner_name: trade.owner_name || "Unknown",
              title: trade.title || "Insider",
              transaction_type: trade.transaction_type || "Unknown",
              last_price: trade.last_price || 0,
              quantity: trade.quantity || 0,
              value: trade.value || 0,
              shares_held: trade.shares_held || 0,
              ownership_percentage: trade.ownership_percentage || 0
            }));
          }
          return [];
        } catch (err) {
          console.warn(`Error fetching ${ticker} insider data:`, err);
          return [];
        }
      });

      const tradesData = await Promise.all(tradePromises);
      const allTrades = tradesData.flat();

      // Sort by transaction date descending
      allTrades.sort((a, b) => {
        const dateA = new Date(a.transaction_date).getTime();
        const dateB = new Date(b.transaction_date).getTime();
        return dateB - dateA;
      });

      setTrades(allTrades.slice(0, 50)); // Limit to 50 most recent trades
    } catch (error) {
      console.error("Error fetching insider data:", error);
      setTrades([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchInsiderData();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  const getTransactionTypeInfo = (type: string) => {
    switch (type.toLowerCase()) {
      case 'p':
      case 'purchase':
        return { label: 'Purchase', color: 'text-green-600', icon: TrendingUp };
      case 's':
      case 'sale':
        return { label: 'Sale', color: 'text-red-600', icon: TrendingDown };
      default:
        return { label: type, color: 'text-gray-600', icon: Users };
    }
  };

  const getInsiderSummary = () => {
    const purchaseCount = trades.filter(t => t.transaction_type.toLowerCase() === 'p').length;
    const saleCount = trades.filter(t => t.transaction_type.toLowerCase() === 's').length;
    const totalValue = trades.reduce((sum, trade) => sum + trade.value, 0);
    
    return { purchaseCount, saleCount, totalValue, totalTrades: trades.length };
  };

  const summary = getInsiderSummary();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Insider Trading</h1>
          <p className="text-muted-foreground">
            Track insider trading activity from company executives and directors
          </p>
        </div>
        <Button onClick={fetchInsiderData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.totalTrades}</div>
            <p className="text-xs text-muted-foreground">Recent insider activities</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Purchases</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{summary.purchaseCount}</div>
            <p className="text-xs text-muted-foreground">Insider buy signals</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sales</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary.saleCount}</div>
            <p className="text-xs text-muted-foreground">Insider sell activities</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summary.totalValue)}</div>
            <p className="text-xs text-muted-foreground">Combined trade value</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Insider Trades</CardTitle>
          <CardDescription>
            Latest insider trading activities from company executives and directors
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Insider</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Transaction</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Shares</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Ownership</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    Loading insider trades...
                  </TableCell>
                </TableRow>
              ) : trades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    No insider trading data available
                  </TableCell>
                </TableRow>
              ) : (
                trades.map((trade, index) => {
                  const transactionInfo = getTransactionTypeInfo(trade.transaction_type);
                  const TransactionIcon = transactionInfo.icon;
                  
                  return (
                    <TableRow key={index}>
                      <TableCell>
                        {new Date(trade.transaction_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div>
                          <Badge variant="secondary">{trade.ticker}</Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            {trade.company_name}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">
                        {trade.owner_name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{trade.title}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className={`flex items-center ${transactionInfo.color}`}>
                          <TransactionIcon className="mr-1 h-4 w-4" />
                          {transactionInfo.label}
                        </div>
                      </TableCell>
                      <TableCell>{formatCurrency(trade.last_price)}</TableCell>
                      <TableCell>
                        {trade.quantity.toLocaleString()}
                      </TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(trade.value)}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">
                            {trade.shares_held.toLocaleString()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {trade.ownership_percentage.toFixed(2)}%
                          </p>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Insider Trading Insights</CardTitle>
          <CardDescription>
            Key insights from recent insider trading activity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h4 className="font-medium">Purchase vs Sale Ratio</h4>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-sm">Purchases: {summary.purchaseCount}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-sm">Sales: {summary.saleCount}</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Most Active Companies</h4>
              <div className="space-y-1">
                {trades.slice(0, 3).map((trade, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <Badge variant="outline">{trade.ticker}</Badge>
                    <span className="text-sm text-muted-foreground">
                      {formatCurrency(trade.value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}