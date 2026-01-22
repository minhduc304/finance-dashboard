"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, PieChart as PieChartIcon, BarChart3, Layers, Award } from "lucide-react";
import { portfolioService } from "@/lib/api/services/portfolio";
import { marketService } from "@/lib/api/services/market";
import { safePercentage, isValidNumber, formatLargeNumber } from "@/lib/utils/calculations";

interface AllocationData {
  name: string;
  value: number;
  amount: number;
}

interface PerformanceData {
  date: string;
  value: number;
  return: number;
}

interface HoldingWithSector {
  ticker: string;
  name: string;
  market_value: number;
  unrealized_gain: number;
  unrealized_gain_percent: number;
  sector: string;
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [portfolioAllocation, setPortfolioAllocation] = useState<AllocationData[]>([]);
  const [sectorAllocation, setSectorAllocation] = useState<AllocationData[]>([]);
  const [performanceHistory, setPerformanceHistory] = useState<PerformanceData[]>([]);
  const [holdings, setHoldings] = useState<HoldingWithSector[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalGain, setTotalGain] = useState(0);
  const [cashBalance, setCashBalance] = useState(0);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7c43'];

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    setLoading(true);
    try {
      // 1. Fetch portfolios to get overview
      const portfolios = await portfolioService.getAllPortfolios();
      if (!portfolios || portfolios.length === 0) {
        setLoading(false);
        return;
      }

      const firstPortfolio = portfolios[0];
      const portfolioTotalValue = firstPortfolio.total_value || 0;
      const portfolioCash = firstPortfolio.cash_balance || 0;
      const portfolioGain = firstPortfolio.total_gain_loss || 0;

      setTotalValue(portfolioTotalValue);
      setCashBalance(portfolioCash);
      setTotalGain(portfolioGain);

      // 2. Fetch holdings for allocation data
      const holdingsData = await portfolioService.getHoldings(firstPortfolio.id);

      // 3. Enrich holdings with sector info from market data
      const enrichedHoldings: HoldingWithSector[] = await Promise.all(
        holdingsData.map(async (h) => {
          let sector = "Unknown";
          try {
            const stockInfo = await marketService.getStockInfo(h.symbol);
            sector = stockInfo?.sector || "Unknown";
          } catch {
            // If we can't get stock info, use Unknown sector
          }
          return {
            ticker: h.symbol,
            name: h.symbol,
            market_value: h.market_value || 0,
            unrealized_gain: h.gain_loss || 0,
            unrealized_gain_percent: h.gain_loss && h.quantity && h.average_cost
              ? safePercentage(h.gain_loss, h.quantity * h.average_cost, 0)
              : 0,
            sector
          };
        })
      );

      setHoldings(enrichedHoldings);

      // 4. Calculate portfolio allocation (by ticker)
      const totalHoldingsValue = enrichedHoldings.reduce((sum, h) => sum + h.market_value, 0);
      const allocation: AllocationData[] = enrichedHoldings.map(h => ({
        name: h.ticker,
        value: safePercentage(h.market_value, totalHoldingsValue, 0),
        amount: h.market_value
      }));

      // Add cash to allocation if significant
      if (portfolioCash > 0) {
        const cashPercent = safePercentage(portfolioCash, portfolioTotalValue, 0);
        if (cashPercent > 0.5) {
          allocation.push({
            name: 'Cash',
            value: cashPercent,
            amount: portfolioCash
          });
        }
      }

      // Sort by value descending
      allocation.sort((a, b) => b.value - a.value);
      setPortfolioAllocation(allocation);

      // 5. Calculate sector allocation
      const sectorMap = new Map<string, number>();
      enrichedHoldings.forEach(h => {
        const current = sectorMap.get(h.sector) || 0;
        sectorMap.set(h.sector, current + h.market_value);
      });

      // Add cash as a "sector"
      if (portfolioCash > 0) {
        sectorMap.set('Cash', portfolioCash);
      }

      const sectorData: AllocationData[] = Array.from(sectorMap.entries()).map(([name, amount]) => ({
        name,
        value: safePercentage(amount, portfolioTotalValue, 0),
        amount
      }));
      sectorData.sort((a, b) => b.value - a.value);
      setSectorAllocation(sectorData);

      // 6. Fetch performance history
      try {
        const perfData = await portfolioService.getPerformance(firstPortfolio.id, 30);
        if (perfData && Array.isArray(perfData.history)) {
          const performanceData: PerformanceData[] = perfData.history.map((p: { date: string; total_value: number; daily_return?: number }) => ({
            date: new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            value: p.total_value || 0,
            return: p.daily_return || 0
          }));
          setPerformanceHistory(performanceData);
        }
      } catch {
        // Performance data may not be available
        setPerformanceHistory([]);
      }

    } catch (error) {
      console.error("Error fetching analytics data:", error);
    }
    setLoading(false);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  // Find top performer and largest position
  const topPerformer = holdings.reduce((best, h) =>
    h.unrealized_gain_percent > (best?.unrealized_gain_percent || -Infinity) ? h : best
  , holdings[0]);

  const largestPosition = holdings.reduce((largest, h) =>
    h.market_value > (largest?.market_value || 0) ? h : largest
  , holdings[0]);

  // Calculate sector concentration (largest sector %)
  const largestSector = sectorAllocation[0];
  const sectorConcentration = largestSector?.value || 0;

  if (loading) {
    return <AnalyticsSkeleton />;
  }

  if (portfolioAllocation.length === 0 && holdings.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Portfolio performance analysis and insights
          </p>
        </div>
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">No portfolio data available for analysis</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Portfolio performance analysis and insights
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Holdings Count</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{holdings.length}</div>
            <p className="text-xs text-muted-foreground">Active positions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Performer</CardTitle>
            <Award className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{topPerformer?.ticker || "N/A"}</div>
            <p className={`text-xs ${topPerformer?.unrealized_gain_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {topPerformer ? `${topPerformer.unrealized_gain_percent >= 0 ? '+' : ''}${topPerformer.unrealized_gain_percent.toFixed(1)}%` : 'N/A'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Largest Position</CardTitle>
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{largestPosition?.ticker || "N/A"}</div>
            <p className="text-xs text-muted-foreground">
              {largestPosition ? formatCurrency(largestPosition.market_value) : 'N/A'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sector Concentration</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sectorConcentration.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {largestSector?.name || 'N/A'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Allocation Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Allocation</CardTitle>
            <CardDescription>
              Breakdown by individual holdings
            </CardDescription>
          </CardHeader>
          <CardContent>
            {portfolioAllocation.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={portfolioAllocation}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {portfolioAllocation.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Allocation']} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                No allocation data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sector Allocation</CardTitle>
            <CardDescription>
              Breakdown by industry sectors
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sectorAllocation.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={sectorAllocation}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {sectorAllocation.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Allocation']} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                No sector data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart */}
      {performanceHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Performance</CardTitle>
            <CardDescription>
              Historical value over the last 30 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis
                  tickFormatter={(value) => formatLargeNumber(value, '')}
                />
                <Tooltip
                  formatter={(value) => [formatCurrency(Number(value)), 'Portfolio Value']}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#8884d8"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Holdings Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Holdings Performance</CardTitle>
          <CardDescription>
            Individual stock performance comparison
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {holdings
              .sort((a, b) => b.unrealized_gain_percent - a.unrealized_gain_percent)
              .slice(0, 6)
              .map((holding) => (
                <div key={holding.ticker} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Badge variant="secondary">{holding.ticker}</Badge>
                    <div className="text-sm font-medium">{formatCurrency(holding.market_value)}</div>
                  </div>
                  <div className={`flex items-center space-x-1 ${holding.unrealized_gain_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {holding.unrealized_gain_percent >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    <span className="text-sm font-medium">
                      {holding.unrealized_gain_percent >= 0 ? '+' : ''}{holding.unrealized_gain_percent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>

      {/* Diversification Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Diversification Summary</CardTitle>
          <CardDescription>
            Portfolio diversification assessment
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Diversification Score</span>
              <Badge variant={sectorAllocation.length >= 3 ? "default" : "secondary"}>
                {sectorAllocation.length >= 4 ? "Good" : sectorAllocation.length >= 2 ? "Moderate" : "Low"}
              </Badge>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${sectorAllocation.length >= 4 ? 'bg-green-500' : sectorAllocation.length >= 2 ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{ width: `${Math.min(sectorAllocation.length * 20, 100)}%` }}
              />
            </div>
          </div>

          <div className="pt-4 space-y-2">
            <h4 className="text-sm font-medium">Insights</h4>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>You have {holdings.length} position{holdings.length !== 1 ? 's' : ''} across {sectorAllocation.filter(s => s.name !== 'Cash').length} sector{sectorAllocation.filter(s => s.name !== 'Cash').length !== 1 ? 's' : ''}</li>
              {sectorConcentration > 50 && (
                <li>High concentration in {largestSector?.name} ({sectorConcentration.toFixed(1)}%)</li>
              )}
              {cashBalance > 0 && (
                <li>{formatCurrency(cashBalance)} available in cash ({safePercentage(cashBalance, totalValue, 0).toFixed(1)}% of portfolio)</li>
              )}
              <li>Total portfolio gain: {totalGain >= 0 ? '+' : ''}{formatCurrency(totalGain)}</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-5 w-64 mt-2" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-20 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-56" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[300px] w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
