"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, PieChart as PieChartIcon } from "lucide-react";

export default function AnalyticsPage() {
  // Mock data for analytics
  const portfolioAllocation = [
    { name: 'AAPL', value: 37.1, amount: 19500 },
    { name: 'MSFT', value: 36.2, amount: 19000 },
    { name: 'TSLA', value: 11.7, amount: 6125 },
    { name: 'GOOGL', value: 11.4, amount: 6000 },
    { name: 'Cash', value: 4.8, amount: 2500 },
  ];

  const sectorAllocation = [
    { name: 'Technology', value: 84.7, amount: 44500 },
    { name: 'Consumer Cyclical', value: 11.7, amount: 6125 },
    { name: 'Cash', value: 4.8, amount: 2500 },
  ];

  const performanceHistory = [
    { month: 'Jan', value: 45000, return: 0 },
    { month: 'Feb', value: 47000, return: 4.4 },
    { month: 'Mar', value: 49000, return: 8.9 },
    { month: 'Apr', value: 51000, return: 13.3 },
    { month: 'May', value: 52500, return: 16.7 },
  ];

  const riskMetrics = [
    { metric: 'Beta', value: 1.15, description: 'Portfolio volatility vs market' },
    { metric: 'Sharpe Ratio', value: 1.45, description: 'Risk-adjusted return' },
    { metric: 'Max Drawdown', value: -5.2, description: 'Maximum loss from peak' },
    { metric: 'Volatility', value: 18.3, description: 'Annualized volatility %' },
  ];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Portfolio performance analysis and insights
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {riskMetrics.map((metric) => (
          <Card key={metric.metric}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.metric}</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {typeof metric.value === 'number' ? (
                  metric.value < 0 ? `${metric.value.toFixed(1)}%` : metric.value.toFixed(2)
                ) : metric.value}
              </div>
              <p className="text-xs text-muted-foreground">{metric.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Allocation</CardTitle>
            <CardDescription>
              Breakdown by individual holdings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={portfolioAllocation}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {portfolioAllocation.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value}%`, name]} />
              </PieChart>
            </ResponsiveContainer>
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
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sectorAllocation}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {sectorAllocation.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value}%`, name]} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
          <CardDescription>
            Historical value and returns over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis 
                yAxisId="left"
                tickFormatter={(value) => formatCurrency(value)}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right"
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip 
                formatter={(value, name) => [
                  name === 'Portfolio Value' ? formatCurrency(Number(value)) : `${Number(value).toFixed(1)}%`,
                  name
                ]}
              />
              <Bar yAxisId="left" dataKey="value" fill="#8884d8" name="Portfolio Value" />
              <Line yAxisId="right" type="monotone" dataKey="return" stroke="#ff7300" name="Return %" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Holdings Performance</CardTitle>
            <CardDescription>
              Individual stock performance comparison
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { ticker: 'MSFT', gain: 18.75, value: 19000 },
                { ticker: 'AAPL', gain: 11.43, value: 19500 },
                { ticker: 'TSLA', gain: 11.36, value: 6125 },
                { ticker: 'GOOGL', gain: 7.14, value: 6000 },
              ].map((holding) => (
                <div key={holding.ticker} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Badge variant="secondary">{holding.ticker}</Badge>
                    <div className="text-sm font-medium">{formatCurrency(holding.value)}</div>
                  </div>
                  <div className={`flex items-center space-x-1 ${holding.gain >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {holding.gain >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    <span className="text-sm font-medium">
                      {holding.gain >= 0 ? '+' : ''}{holding.gain.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk Analysis</CardTitle>
            <CardDescription>
              Portfolio risk assessment and recommendations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Diversification Score</span>
                <Badge variant="default">Good</Badge>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-500 h-2 rounded-full" style={{ width: '75%' }}></div>
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Risk Level</span>
                <Badge variant="secondary">Moderate</Badge>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '60%' }}></div>
              </div>
            </div>

            <div className="pt-4 space-y-2">
              <h4 className="text-sm font-medium">Recommendations</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Consider adding bonds or REITs for diversification</li>
                <li>• High concentration in technology sector (84.7%)</li>
                <li>• Portfolio shows strong growth potential</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}