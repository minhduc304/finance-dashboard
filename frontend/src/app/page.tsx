"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { TrendingUp, TrendingDown, DollarSign, Wallet, ArrowUpRight, ArrowDownRight, MessageSquare } from "lucide-react";
import { usePortfolios, useHoldings, useTransactions } from "@/hooks/usePortfolio";
import { useSentimentSummary } from "@/hooks/useSentiment";
import { safePercentage, formatPercentChange, calcGainPercent, isValidNumber } from "@/lib/utils/calculations";

export default function Home() {
  const { data: portfolios, loading: portfoliosLoading, error: portfoliosError } = usePortfolios();
  const { data: sentimentSummary } = useSentimentSummary();

  // Aggregate all portfolios into a single summary view
  const portfolio = portfolios && portfolios.length > 0 ? {
    id: 'all',
    name: 'All Portfolios',
    total_value: portfolios.reduce((sum, p) => sum + (p.total_value || 0), 0),
    total_cost: portfolios.reduce((sum, p) => sum + (p.total_cost || 0), 0),
    total_gain_loss: portfolios.reduce((sum, p) => sum + (p.total_gain_loss || 0), 0),
    cash_balance: portfolios.reduce((sum, p) => sum + (p.cash_balance || 0), 0),
    updated_at: new Date().toISOString()
  } : null;

  // Get holdings and transactions from the first non-empty portfolio for display
  const firstPortfolio = portfolios && portfolios.length > 0 ? portfolios.find(p => p.total_value > 0) || portfolios[0] : null;
  const { data: holdings, loading: holdingsLoading } = useHoldings(firstPortfolio?.id || null);
  const { data: transactions, loading: transactionsLoading } = useTransactions(firstPortfolio?.id || null, 3);

  const loading = portfoliosLoading || holdingsLoading || transactionsLoading;
  const error = portfoliosError;

  if (loading) {
    return <HomeSkeleton />;
  }

  if (error) {
    return (
      <div className="space-y-10">
        <div className="space-y-1">
          <h1 className="font-display text-4xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-base">
            Track your portfolio performance and market insights
          </p>
        </div>
        <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
          <AlertDescription className="text-sm">
            Error loading portfolio data: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="space-y-10">
        <div className="space-y-1">
          <h1 className="font-display text-4xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-base">
            Track your portfolio performance and market insights
          </p>
        </div>
        <Alert className="border-border/50 bg-muted/50">
          <AlertDescription className="text-sm">
            No portfolios found. Create your first portfolio to get started.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const returnPercent = safePercentage(portfolio.total_gain_loss, portfolio.total_cost, 0);
  const returnPercentFormatted = formatPercentChange(returnPercent, "N/A");

  const marketStats = [
    {
      title: "Total Value",
      value: `$${portfolio.total_value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: isValidNumber(portfolio.total_cost) && portfolio.total_cost > 0
        ? `${portfolio.total_gain_loss >= 0 ? '+' : ''}$${Math.abs(portfolio.total_gain_loss).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          })}`
        : "N/A",
      changePercent: isValidNumber(portfolio.total_cost) && portfolio.total_cost > 0
        ? returnPercentFormatted
        : "",
      trending: portfolio.total_gain_loss >= 0 ? "up" : "down",
      icon: DollarSign,
    },
    {
      title: "Total Return",
      value: `${portfolio.total_gain_loss >= 0 ? '+' : ''}$${Math.abs(portfolio.total_gain_loss).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: isValidNumber(portfolio.total_cost) && portfolio.total_cost > 0
        ? returnPercentFormatted
        : "N/A",
      changePercent: "all time",
      trending: portfolio.total_gain_loss >= 0 ? "up" : "down",
      icon: portfolio.total_gain_loss >= 0 ? TrendingUp : TrendingDown,
    },
    {
      title: "Cash Balance",
      value: `$${portfolio.cash_balance.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: "Available",
      changePercent: "to invest",
      trending: "neutral",
      icon: Wallet,
    },
    {
      title: "Market Mood",
      value: sentimentSummary?.market_mood
        ? sentimentSummary.market_mood.charAt(0).toUpperCase() + sentimentSummary.market_mood.slice(1)
        : "Loading...",
      change: sentimentSummary?.total_posts
        ? `${sentimentSummary.total_posts.toLocaleString()} posts`
        : "Fetching data",
      changePercent: "today",
      trending: sentimentSummary?.market_mood === 'bullish' ? "up" :
                sentimentSummary?.market_mood === 'bearish' ? "down" : "neutral",
      icon: MessageSquare,
    },
  ];

  const topStocks = holdings?.slice(0, 4).map(holding => {
    const gainPercent = calcGainPercent(holding.unrealized_gain, holding.quantity, holding.average_cost);
    return {
      ticker: holding.ticker,
      name: holding.name || holding.ticker,
      price: `$${(holding.current_price || 0).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: formatPercentChange(gainPercent, "0.0%", 1)
    };
  }) || [];

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="space-y-1 animate-fadeInUp opacity-0 stagger-1">
        <h1 className="font-display text-4xl font-semibold tracking-tight">
          Dashboard
        </h1>
        <p className="text-muted-foreground text-base">
          Track your portfolio performance and market insights
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {marketStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card
              key={index}
              className="group relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20 animate-fadeInUp opacity-0"
              style={{ animationDelay: `${0.2 + index * 0.1}s` }}
            >
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <div className="rounded-lg bg-primary/10 p-2 ring-1 ring-primary/20">
                  <Icon className="h-4 w-4 text-primary" strokeWidth={2} />
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="font-display text-3xl font-semibold tracking-tight">
                  {stat.value}
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {stat.trending === "up" && (
                    <div className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-600 dark:text-emerald-400">
                      <ArrowUpRight className="h-3 w-3" strokeWidth={2.5} />
                      <span className="font-medium">{stat.change}</span>
                    </div>
                  )}
                  {stat.trending === "down" && (
                    <div className="flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-red-600 dark:text-red-400">
                      <ArrowDownRight className="h-3 w-3" strokeWidth={2.5} />
                      <span className="font-medium">{stat.change}</span>
                    </div>
                  )}
                  {stat.trending === "neutral" && (
                    <span className="text-muted-foreground font-medium">{stat.change}</span>
                  )}
                  <span className="text-muted-foreground">{stat.changePercent}</span>
                </div>
              </CardContent>
              {/* Subtle gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/0 to-primary/5 opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none" />
            </Card>
          );
        })}
      </div>

      {/* Content Grid */}
      <div className="grid gap-5 md:grid-cols-2">
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-4">
          <CardHeader className="space-y-1">
            <CardTitle className="font-display text-xl font-semibold">
              Holdings
            </CardTitle>
            <CardDescription className="text-sm">
              Your top performing positions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {topStocks.length > 0 ? (
              topStocks.map((stock, idx) => (
                <div
                  key={stock.ticker}
                  className="group flex items-center justify-between rounded-lg border border-border/50 bg-accent/30 p-3 transition-all hover:bg-accent/50 hover:border-primary/20"
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant="secondary"
                      className="font-mono text-xs font-semibold"
                    >
                      {stock.ticker}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">{stock.name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{stock.price}</p>
                    <p className={`text-xs font-medium ${
                      stock.change.startsWith('+')
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : stock.change.startsWith('-')
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-muted-foreground'
                    }`}>
                      {stock.change}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <p className="text-sm text-muted-foreground">No holdings available</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-fadeInUp opacity-0 stagger-5">
          <CardHeader className="space-y-1">
            <CardTitle className="font-display text-xl font-semibold">
              Recent Activity
            </CardTitle>
            <CardDescription className="text-sm">
              Latest transactions and updates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {transactions && transactions.length > 0 ? (
              transactions.map((transaction, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-accent/30 p-3 transition-all hover:bg-accent/50"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {transaction.type.charAt(0).toUpperCase() + transaction.type.slice(1)}{' '}
                      {transaction.symbol || 'Cash'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {transaction.symbol
                        ? `${transaction.quantity} shares @ $${transaction.price?.toFixed(2)}`
                        : `$${Math.abs(transaction.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                      }
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className="border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  >
                    Completed
                  </Badge>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <p className="text-sm text-muted-foreground">No recent transactions</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Your trading activity will appear here
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-10">
      <div className="space-y-1">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-5 w-72 mt-2" />
      </div>

      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="border-border/50 bg-card/50">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-8 w-8 rounded-lg" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Skeleton className="h-9 w-32" />
              <Skeleton className="h-5 w-24" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="space-y-1">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-border/50 bg-accent/30 p-3"
              >
                <div className="flex items-center gap-3">
                  <Skeleton className="h-6 w-12" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <div className="text-right space-y-1">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-3 w-12" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="space-y-1">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-border/50 bg-accent/30 p-3"
              >
                <div className="space-y-1">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="h-6 w-20" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}