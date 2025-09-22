'use client';

import { usePortfolios } from '@/hooks/usePortfolio';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DollarSign, TrendingUp, Wallet, Activity } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function PortfolioOverview() {
  const { data: portfolios, loading, error } = usePortfolios();

  if (loading) {
    return <PortfolioSkeleton />;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Error loading portfolio data: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (!portfolios || portfolios.length === 0) {
    return (
      <Alert>
        <AlertDescription>
          No portfolios found. Create your first portfolio to get started.
        </AlertDescription>
      </Alert>
    );
  }

  // For now, show the first portfolio
  const portfolio = portfolios[0];

  const stats = [
    {
      title: 'Total Portfolio Value',
      value: `$${portfolio.total_value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      icon: DollarSign,
      change: null,
    },
    {
      title: 'Total Gain/Loss',
      value: `$${portfolio.total_gain_loss.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      change: portfolio.total_cost > 0
        ? `${((portfolio.total_gain_loss / portfolio.total_cost) * 100).toFixed(2)}%`
        : '0%',
      icon: TrendingUp,
      positive: portfolio.total_gain_loss >= 0,
    },
    {
      title: 'Cash Balance',
      value: `$${portfolio.cash_balance.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`,
      icon: Wallet,
      change: null,
    },
    {
      title: 'Portfolio',
      value: portfolio.name,
      icon: Activity,
      change: null,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => {
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
              {stat.change && (
                <p className={`text-xs ${
                  stat.positive === undefined
                    ? 'text-muted-foreground'
                    : stat.positive
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {stat.change}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function PortfolioSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
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
  );
}