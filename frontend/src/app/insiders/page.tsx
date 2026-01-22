"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, RefreshCw, Users, ArrowUpRight, ArrowDownRight, Activity } from "lucide-react";
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
      // Fetch recent insider trades from all stocks in the database
      const response = await insidersService.getRecentInsiderTrades(90, 100);

      // Transform the API response to match our interface
      if (response && response.trades) {
        const formattedTrades = response.trades.map((trade) => ({
          transaction_date: trade.transaction_date || "",
          trade_date: trade.trade_date || trade.transaction_date || "",
          ticker: trade.ticker || "N/A",
          company_name: trade.company_name || trade.ticker || "Unknown",
          owner_name: trade.owner_name || "Unknown",
          title: trade.title || "Insider",
          transaction_type: trade.transaction_type || "Unknown",
          last_price: trade.last_price || 0,
          quantity: trade.quantity || 0,
          value: trade.value || 0,
          shares_held: trade.shares_held || 0,
          ownership_percentage: trade.ownership_percentage || 0
        }));

        setTrades(formattedTrades);
      } else {
        setTrades([]);
      }
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
    const lowerType = type.toLowerCase();
    // Handle various formats: "P", "P - Purchase", "Purchase", "P - Open Market Purchase", etc.
    if (lowerType.startsWith('p') || lowerType.includes('purchase') || lowerType.includes('buy')) {
      return { label: 'Purchase', color: 'text-green-600', icon: TrendingUp };
    }
    // Handle various formats: "S", "S - Sale", "Sale", "S - Open Market Sale", etc.
    if (lowerType.startsWith('s') || lowerType.includes('sale') || lowerType.includes('sell')) {
      return { label: 'Sale', color: 'text-red-600', icon: TrendingDown };
    }
    return { label: type, color: 'text-gray-600', icon: Users };
  };

  const getInsiderSummary = () => {
    // Check if transaction_type starts with 'p' (handles "P", "P - Purchase", "Purchase", etc.)
    const purchaseCount = trades.filter(t => {
      const type = t.transaction_type.toLowerCase();
      return type.startsWith('p') || type.includes('purchase') || type.includes('buy');
    }).length;
    // Check if transaction_type starts with 's' (handles "S", "S - Sale", "Sale", etc.)
    const saleCount = trades.filter(t => {
      const type = t.transaction_type.toLowerCase();
      return type.startsWith('s') || type.includes('sale') || type.includes('sell');
    }).length;
    const totalValue = trades.reduce((sum, trade) => sum + trade.value, 0);

    return { purchaseCount, saleCount, totalValue, totalTrades: trades.length };
  };

  const summary = getInsiderSummary();

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between animate-fadeInUp opacity-0 stagger-1">
        <div className="space-y-1">
          <h1 className="font-display text-4xl font-semibold tracking-tight">
            Insider Trading
          </h1>
          <p className="text-muted-foreground text-base">
            Track insider trading activity from company executives and directors
          </p>
        </div>
        <Button
          onClick={fetchInsiderData}
          disabled={loading}
          variant="outline"
          className="gap-2 transition-all hover:bg-accent"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Refresh</span>
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-2">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Trades
            </CardTitle>
            <div className="rounded-lg bg-primary/10 p-2 ring-1 ring-primary/20">
              <Activity className="h-4 w-4 text-primary" strokeWidth={2} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tracking-tight">
              {summary.totalTrades}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Recent activities</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-3">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Purchases
            </CardTitle>
            <div className="rounded-lg bg-emerald-500/10 p-2 ring-1 ring-emerald-500/20">
              <ArrowUpRight className="h-4 w-4 text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tracking-tight text-emerald-600 dark:text-emerald-400">
              {summary.purchaseCount}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Buy signals</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-4">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Sales
            </CardTitle>
            <div className="rounded-lg bg-red-500/10 p-2 ring-1 ring-red-500/20">
              <ArrowDownRight className="h-4 w-4 text-red-600 dark:text-red-400" strokeWidth={2.5} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tracking-tight text-red-600 dark:text-red-400">
              {summary.saleCount}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Sell activities</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-5">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Value
            </CardTitle>
            <div className="rounded-lg bg-primary/10 p-2 ring-1 ring-primary/20">
              <Users className="h-4 w-4 text-primary" strokeWidth={2} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tracking-tight">
              {formatCurrency(summary.totalValue)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Combined value</p>
          </CardContent>
        </Card>
      </div>

      {/* Trades Table */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-6">
        <CardHeader className="space-y-1">
          <CardTitle className="font-display text-xl font-semibold">
            Recent Trades
          </CardTitle>
          <CardDescription className="text-sm">
            Latest insider trading activities from company executives and directors
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border/50 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent border-border/50 bg-muted/30">
                  <TableHead className="font-semibold">Date</TableHead>
                  <TableHead className="font-semibold">Company</TableHead>
                  <TableHead className="font-semibold">Insider</TableHead>
                  <TableHead className="font-semibold">Title</TableHead>
                  <TableHead className="font-semibold">Type</TableHead>
                  <TableHead className="font-semibold">Price</TableHead>
                  <TableHead className="font-semibold">Shares</TableHead>
                  <TableHead className="font-semibold">Value</TableHead>
                  <TableHead className="font-semibold">Ownership</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                      Loading insider trades...
                    </TableCell>
                  </TableRow>
                ) : trades.length === 0 ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                      No insider trading data available
                    </TableCell>
                  </TableRow>
                ) : (
                  trades.map((trade, index) => {
                    const transactionInfo = getTransactionTypeInfo(trade.transaction_type);
                    const TransactionIcon = transactionInfo.icon;

                    return (
                      <TableRow
                        key={index}
                        className="border-border/50 transition-colors hover:bg-accent/30"
                      >
                        <TableCell className="font-medium">
                          {new Date(trade.transaction_date).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <Badge
                              variant="secondary"
                              className="font-mono text-xs font-semibold"
                            >
                              {trade.ticker}
                            </Badge>
                            <p className="text-xs text-muted-foreground">
                              {trade.company_name}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          {trade.owner_name}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-medium">
                            {trade.title}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className={`flex items-center gap-1.5 ${transactionInfo.color}`}>
                            <TransactionIcon className="h-4 w-4" strokeWidth={2} />
                            <span className="font-medium">{transactionInfo.label}</span>
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          {formatCurrency(trade.last_price)}
                        </TableCell>
                        <TableCell className="font-medium">
                          {trade.quantity.toLocaleString()}
                        </TableCell>
                        <TableCell className="font-semibold">
                          {formatCurrency(trade.value)}
                        </TableCell>
                        <TableCell>
                          {trade.shares_held > 0 || trade.ownership_percentage > 0 ? (
                            <div className="space-y-0.5">
                              <p className="font-medium text-sm">
                                {trade.shares_held > 0 ? trade.shares_held.toLocaleString() : '—'}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {trade.ownership_percentage > 0 ? `${trade.ownership_percentage.toFixed(2)}%` : '—'}
                              </p>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">N/A</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Insights */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="font-display text-xl font-semibold">
            Insights
          </CardTitle>
          <CardDescription className="text-sm">
            Key metrics from recent insider trading activity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
                Purchase vs Sale Ratio
              </h4>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20"></div>
                  <span className="text-sm font-medium">
                    Purchases: <span className="font-semibold">{summary.purchaseCount}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500 ring-2 ring-red-500/20"></div>
                  <span className="text-sm font-medium">
                    Sales: <span className="font-semibold">{summary.saleCount}</span>
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
                Most Active Companies
              </h4>
              <div className="space-y-2">
                {trades.slice(0, 3).map((trade, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-lg border border-border/50 bg-accent/30 p-2.5"
                  >
                    <Badge variant="outline" className="font-mono text-xs font-semibold">
                      {trade.ticker}
                    </Badge>
                    <span className="text-sm font-semibold">
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