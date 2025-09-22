"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { TrendingUp, TrendingDown, DollarSign, PieChart } from "lucide-react";
import { usePortfolios, useHoldings, useTransactions } from "@/hooks/usePortfolio";

export default function Home() {
  const { data: portfolios, loading: portfoliosLoading, error: portfoliosError } = usePortfolios();
  const portfolio = portfolios && portfolios.length > 0 ? portfolios[0] : null;

  const { data: holdings, loading: holdingsLoading } = useHoldings(portfolio?.id || null);
  const { data: transactions, loading: transactionsLoading } = useTransactions(portfolio?.id || null, 3);

  const loading = portfoliosLoading || holdingsLoading || transactionsLoading;
  const error = portfoliosError;

  if (loading) {
    return <HomeSkeleton />;
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Finance Dashboard</h1>
          <p className="text-muted-foreground">
            Track your portfolio performance and market insights
          </p>
        </div>
        <Alert variant="destructive">
          <AlertDescription>
            Error loading portfolio data: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Finance Dashboard</h1>
          <p className="text-muted-foreground">
            Track your portfolio performance and market insights
          </p>
        </div>
        <Alert>
          <AlertDescription>
            No portfolios found. Create your first portfolio to get started.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const marketStats = [
    {
      title: "Total Portfolio Value",
      value: `$${portfolio.total_value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: portfolio.total_cost > 0
        ? `${portfolio.total_gain_loss >= 0 ? '+' : ''}$${Math.abs(portfolio.total_gain_loss).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          })}`
        : "N/A",
      changePercent: portfolio.total_cost > 0
        ? `${portfolio.total_gain_loss >= 0 ? '+' : ''}${((portfolio.total_gain_loss / portfolio.total_cost) * 100).toFixed(1)}%`
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
      change: portfolio.total_cost > 0
        ? `${portfolio.total_gain_loss >= 0 ? '+' : ''}${((portfolio.total_gain_loss / portfolio.total_cost) * 100).toFixed(1)}%`
        : "N/A",
      changePercent: "vs initial",
      trending: portfolio.total_gain_loss >= 0 ? "up" : "down",
      icon: TrendingUp,
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
      icon: PieChart,
    },
  ];

  const topStocks = holdings?.slice(0, 4).map(holding => ({
    ticker: holding.ticker,
    name: holding.name || holding.ticker,
    price: `$${(holding.current_price || 0).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`,
    change: holding.unrealized_gain && holding.current_price
      ? `${holding.unrealized_gain >= 0 ? '+' : ''}${((holding.unrealized_gain / (holding.quantity * holding.average_cost)) * 100).toFixed(1)}%`
      : "0.0%"
  })) || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Finance Dashboard</h1>
        <p className="text-muted-foreground">
          Track your portfolio performance and market insights
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {marketStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="flex items-center text-sm text-muted-foreground">
                  {stat.trending === "up" && (
                    <TrendingUp className="mr-1 h-4 w-4 text-green-500" />
                  )}
                  {stat.trending === "down" && (
                    <TrendingDown className="mr-1 h-4 w-4 text-red-500" />
                  )}
                  <span className={
                    stat.trending === "up" ? "text-green-500" : 
                    stat.trending === "down" ? "text-red-500" : ""
                  }>
                    {stat.change}
                  </span>
                  <span className="ml-1">{stat.changePercent}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
            <CardDescription>
              Top performing stocks in your watchlist
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {topStocks.map((stock) => (
              <div key={stock.ticker} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Badge variant="secondary">{stock.ticker}</Badge>
                  <div>
                    <p className="text-sm font-medium">{stock.name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{stock.price}</p>
                  <p className="text-xs text-green-500">{stock.change}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest transactions and updates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {transactions && transactions.length > 0 ? (
              transactions.map((transaction, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {transaction.type.charAt(0).toUpperCase() + transaction.type.slice(1)} {transaction.symbol || 'Cash'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {transaction.symbol
                        ? `${transaction.quantity} shares @ $${transaction.price?.toFixed(2)}`
                        : `$${Math.abs(transaction.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                      }
                    </p>
                  </div>
                  <Badge variant="outline">Completed</Badge>
                </div>
              ))
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">No recent transactions</p>
                <p className="text-xs text-muted-foreground mt-1">Your trading activity will appear here</p>
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
    <div className="space-y-8">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64 mt-2" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-3 w-16 mt-1" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Skeleton className="h-6 w-12" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <div className="text-right">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-3 w-12 mt-1" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between">
                <div>
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-3 w-32 mt-1" />
                </div>
                <Skeleton className="h-6 w-16" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}