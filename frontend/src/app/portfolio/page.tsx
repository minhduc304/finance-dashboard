"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, RefreshCw, DollarSign, PieChart } from "lucide-react";
import { portfolioService } from "@/lib/api/services/portfolio";

interface Portfolio {
  id: number;
  name: string;
  currency: string;
  total_value: number;
  cash_balance: number;
  invested_value: number;
  total_return: number;
  total_return_percent: number;
  daily_return: number;
  daily_return_percent: number;
}

interface Holding {
  ticker: string;
  name: string;
  quantity: number;
  average_cost: number;
  current_price: number;
  market_value: number;
  unrealized_gain: number;
  unrealized_gain_percent: number;
  portfolio_percent: number;
}

interface Transaction {
  id: number;
  transaction_type: string;
  ticker: string;
  quantity: number;
  price: number;
  amount: number;
  fees: number;
  transaction_date: string;
  status: string;
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      // Fetch all portfolios for the user
      const portfolios = await portfolioService.getAllPortfolios();

      if (portfolios && portfolios.length > 0) {
        // Use the first portfolio
        const firstPortfolio = portfolios[0];

        // Transform the data to match our interface
        setPortfolio({
          id: firstPortfolio.id,
          name: firstPortfolio.name,
          currency: "USD",
          total_value: firstPortfolio.total_value,
          cash_balance: firstPortfolio.cash_balance,
          invested_value: firstPortfolio.total_cost || firstPortfolio.total_value - firstPortfolio.cash_balance,
          total_return: firstPortfolio.total_gain_loss || 0,
          total_return_percent: firstPortfolio.total_gain_loss && firstPortfolio.total_cost
            ? (firstPortfolio.total_gain_loss / firstPortfolio.total_cost * 100)
            : 0,
          daily_return: 0, // This would need to be calculated from historical data
          daily_return_percent: 0
        });

        // Fetch holdings for this portfolio
        try {
          const holdingsData = await portfolioService.getHoldings(firstPortfolio.id);
          const transformedHoldings = holdingsData.map(h => ({
            ticker: h.symbol,
            name: h.symbol, // We'll use symbol as name for now
            quantity: h.quantity,
            average_cost: h.average_cost,
            current_price: h.current_price || h.average_cost,
            market_value: h.market_value || (h.quantity * (h.current_price || h.average_cost)),
            unrealized_gain: h.gain_loss || 0,
            unrealized_gain_percent: h.gain_loss && (h.quantity * h.average_cost)
              ? (h.gain_loss / (h.quantity * h.average_cost) * 100)
              : 0,
            portfolio_percent: h.market_value && firstPortfolio.total_value
              ? ((h.market_value / firstPortfolio.total_value) * 100)
              : 0
          }));
          setHoldings(transformedHoldings);
        } catch (holdingsError) {
          console.error("Error fetching holdings:", holdingsError);
          setHoldings([]);
        }

        // Fetch transactions for this portfolio
        try {
          const transactionsData = await portfolioService.getTransactions(firstPortfolio.id, 10);
          const transformedTransactions = transactionsData.map(t => ({
            id: t.id,
            transaction_type: t.type,
            ticker: t.symbol || "CASH",
            quantity: t.quantity || 0,
            price: t.price || 0,
            amount: t.total_amount,
            fees: 0, // Not provided by API
            transaction_date: t.transaction_date,
            status: "completed"
          }));
          setTransactions(transformedTransactions);
        } catch (transError) {
          console.error("Error fetching transactions:", transError);
          setTransactions([]);
        }
      } else {
        // No portfolios found
        console.log("No portfolios found for user");
        setPortfolio(null);
        setHoldings([]);
        setTransactions([]);
      }
    } catch (error) {
      console.error("Error fetching portfolio data:", error);
      // Set empty state on error
      setPortfolio(null);
      setHoldings([]);
      setTransactions([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div>Loading portfolio...</div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-lg text-muted-foreground">No portfolio data available</div>
        <Button onClick={fetchPortfolioData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
          <p className="text-muted-foreground">
            Track your investment performance and holdings
          </p>
        </div>
        <Button onClick={fetchPortfolioData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {portfolio && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</div>
              <div className="flex items-center text-sm text-green-500">
                <TrendingUp className="mr-1 h-4 w-4" />
                {formatCurrency(portfolio.daily_return)} ({portfolio.daily_return_percent.toFixed(2)}%)
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Return</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.total_return)}</div>
              <div className="text-sm text-green-500">
                +{portfolio.total_return_percent.toFixed(1)}% overall
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Invested</CardTitle>
              <PieChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.invested_value)}</div>
              <div className="text-sm text-muted-foreground">
                {((portfolio.invested_value / portfolio.total_value) * 100).toFixed(1)}% invested
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.cash_balance)}</div>
              <div className="text-sm text-muted-foreground">
                Available to invest
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Holdings</CardTitle>
          <CardDescription>
            Your current stock positions and performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Shares</TableHead>
                <TableHead>Avg Cost</TableHead>
                <TableHead>Current Price</TableHead>
                <TableHead>Market Value</TableHead>
                <TableHead>Gain/Loss</TableHead>
                <TableHead>% Return</TableHead>
                <TableHead>% of Portfolio</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {holdings.map((holding) => (
                <TableRow key={holding.ticker}>
                  <TableCell>
                    <Badge variant="secondary">{holding.ticker}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">{holding.name}</TableCell>
                  <TableCell>{holding.quantity}</TableCell>
                  <TableCell>{formatCurrency(holding.average_cost)}</TableCell>
                  <TableCell>{formatCurrency(holding.current_price)}</TableCell>
                  <TableCell className="font-medium">{formatCurrency(holding.market_value)}</TableCell>
                  <TableCell className={holding.unrealized_gain >= 0 ? "text-green-600" : "text-red-600"}>
                    {holding.unrealized_gain >= 0 ? "+" : ""}{formatCurrency(holding.unrealized_gain)}
                  </TableCell>
                  <TableCell className={holding.unrealized_gain_percent >= 0 ? "text-green-600" : "text-red-600"}>
                    {holding.unrealized_gain_percent >= 0 ? "+" : ""}{holding.unrealized_gain_percent.toFixed(2)}%
                  </TableCell>
                  <TableCell>{holding.portfolio_percent.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
          <CardDescription>
            Your latest trading activity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Shares</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((transaction) => (
                <TableRow key={transaction.id}>
                  <TableCell>
                    {new Date(transaction.transaction_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Badge variant={transaction.transaction_type === "buy" ? "default" : "secondary"}>
                      {transaction.transaction_type.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{transaction.ticker}</Badge>
                  </TableCell>
                  <TableCell>{transaction.quantity}</TableCell>
                  <TableCell>{formatCurrency(transaction.price)}</TableCell>
                  <TableCell>{formatCurrency(transaction.amount)}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize">
                      {transaction.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}