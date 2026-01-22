"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  TrendingUp,
  TrendingDown,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Minus,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import { useSentimentSummary, useTrendingSentiment, useStockPosts } from "@/hooks/useSentiment";
import type { RedditPost, TrendingSentimentStock } from "@/types/api";

export default function SentimentPage() {
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h');
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [postFilter, setPostFilter] = useState<'all' | 'positive' | 'negative' | 'neutral'>('all');

  const { data: summary, loading: summaryLoading, refetch: refetchSummary } = useSentimentSummary();
  const { data: trending, loading: trendingLoading, refetch: refetchTrending } = useTrendingSentiment(10, period);
  const { data: posts, loading: postsLoading, error: postsError } = useStockPosts(
    selectedTicker,
    20,
    postFilter === 'all' ? undefined : postFilter
  );

  const handleRefresh = () => {
    refetchSummary();
    refetchTrending();
  };

  const getMoodColor = (mood: string | undefined) => {
    if (!mood) return 'text-muted-foreground';
    switch (mood.toLowerCase()) {
      case 'bullish':
        return 'text-green-600';
      case 'bearish':
        return 'text-red-600';
      default:
        return 'text-yellow-600';
    }
  };

  const getMoodIcon = (mood: string | undefined) => {
    if (!mood) return <Minus className="h-8 w-8" />;
    switch (mood.toLowerCase()) {
      case 'bullish':
        return <TrendingUp className="h-8 w-8 text-green-600" />;
      case 'bearish':
        return <TrendingDown className="h-8 w-8 text-red-600" />;
      default:
        return <Minus className="h-8 w-8 text-yellow-600" />;
    }
  };

  const getSentimentBadge = (label: string | undefined) => {
    if (!label) return <Badge variant="outline">Unknown</Badge>;
    switch (label.toLowerCase()) {
      case 'positive':
        return <Badge className="bg-green-500/10 text-green-600 border-green-500/20">Positive</Badge>;
      case 'negative':
        return <Badge className="bg-red-500/10 text-red-600 border-red-500/20">Negative</Badge>;
      default:
        return <Badge variant="outline">Neutral</Badge>;
    }
  };

  const formatScore = (score: number | undefined) => {
    if (score === undefined) return 'N/A';
    return score >= 0 ? `+${score.toFixed(2)}` : score.toFixed(2);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Social Sentiment</h1>
          <p className="text-muted-foreground">
            Market sentiment from Reddit and social media
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={summaryLoading || trendingLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${(summaryLoading || trendingLoading) ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Market Mood Section */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Main Mood Card */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Market Mood
            </CardTitle>
            <CardDescription>Overall social media sentiment</CardDescription>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-4 w-32" />
              </div>
            ) : summary ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  {getMoodIcon(summary.market_mood)}
                  <div>
                    <div className={`text-3xl font-bold capitalize ${getMoodColor(summary.market_mood)}`}>
                      {summary.market_mood || 'Unknown'}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Avg Score: {formatScore(summary.avg_sentiment)}
                    </div>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  Based on {summary.total_posts?.toLocaleString() || 0} posts today
                </div>
              </div>
            ) : (
              <div className="text-muted-foreground">No sentiment data available</div>
            )}
          </CardContent>
        </Card>

        {/* Sentiment Breakdown */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Sentiment Breakdown</CardTitle>
            <CardDescription>Distribution of positive, negative, and neutral posts</CardDescription>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : summary?.sentiment_breakdown ? (
              <div className="space-y-4">
                {/* Positive */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <ThumbsUp className="h-4 w-4 text-green-600" />
                      <span>Positive</span>
                    </div>
                    <span className="font-medium">{summary.sentiment_breakdown.positive || 0}</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full"
                      style={{
                        width: `${summary.total_posts > 0
                          ? (summary.sentiment_breakdown.positive / summary.total_posts) * 100
                          : 0}%`
                      }}
                    />
                  </div>
                </div>

                {/* Neutral */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <Minus className="h-4 w-4 text-yellow-600" />
                      <span>Neutral</span>
                    </div>
                    <span className="font-medium">{summary.sentiment_breakdown.neutral || 0}</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-yellow-500 h-2 rounded-full"
                      style={{
                        width: `${summary.total_posts > 0
                          ? (summary.sentiment_breakdown.neutral / summary.total_posts) * 100
                          : 0}%`
                      }}
                    />
                  </div>
                </div>

                {/* Negative */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <ThumbsDown className="h-4 w-4 text-red-600" />
                      <span>Negative</span>
                    </div>
                    <span className="font-medium">{summary.sentiment_breakdown.negative || 0}</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-red-500 h-2 rounded-full"
                      style={{
                        width: `${summary.total_posts > 0
                          ? (summary.sentiment_breakdown.negative / summary.total_posts) * 100
                          : 0}%`
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-muted-foreground">No breakdown data available</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trending Stocks by Mentions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Trending Stocks</CardTitle>
              <CardDescription>Most mentioned stocks on social media</CardDescription>
            </div>
            <div className="flex gap-1 rounded-lg bg-muted p-1">
              <Button
                variant={period === '24h' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setPeriod('24h')}
              >
                24h
              </Button>
              <Button
                variant={period === '7d' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setPeriod('7d')}
              >
                7 Days
              </Button>
              <Button
                variant={period === '30d' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setPeriod('30d')}
              >
                30 Days
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {trendingLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
                  <Skeleton className="h-6 w-16" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          ) : trending?.stocks && trending.stocks.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead className="text-right">Mentions</TableHead>
                  <TableHead className="text-right">Positive</TableHead>
                  <TableHead className="text-right">Negative</TableHead>
                  <TableHead className="text-right">Avg Sentiment</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trending.stocks.map((stock: TrendingSentimentStock) => (
                  <TableRow
                    key={stock.ticker}
                    className={selectedTicker === stock.ticker ? 'bg-muted/50' : ''}
                  >
                    <TableCell>
                      <Badge variant="secondary" className="font-mono">
                        {stock.ticker}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {stock.total_mentions?.toLocaleString() || 0}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      {stock.positive_mentions || 0}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      {stock.negative_mentions || 0}
                    </TableCell>
                    <TableCell className={`text-right ${
                      stock.avg_sentiment > 0.1 ? 'text-green-600' :
                      stock.avg_sentiment < -0.1 ? 'text-red-600' : ''
                    }`}>
                      {formatScore(stock.avg_sentiment)}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedTicker(
                          selectedTicker === stock.ticker ? null : stock.ticker
                        )}
                      >
                        {selectedTicker === stock.ticker ? 'Hide Posts' : 'View Posts'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No trending stocks data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reddit Posts Section - Shows when a ticker is selected */}
      {selectedTicker && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Reddit Posts for {selectedTicker}</CardTitle>
                <CardDescription>Recent discussions mentioning {selectedTicker}</CardDescription>
              </div>
              <div className="flex gap-1 rounded-lg bg-muted p-1">
                <Button
                  variant={postFilter === 'all' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPostFilter('all')}
                >
                  All
                </Button>
                <Button
                  variant={postFilter === 'positive' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPostFilter('positive')}
                >
                  Positive
                </Button>
                <Button
                  variant={postFilter === 'neutral' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPostFilter('neutral')}
                >
                  Neutral
                </Button>
                <Button
                  variant={postFilter === 'negative' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPostFilter('negative')}
                >
                  Negative
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {postsLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-4 border rounded-lg space-y-2">
                    <Skeleton className="h-5 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                ))}
              </div>
            ) : postsError ? (
              <div className="text-center py-8">
                <p className="text-red-600 dark:text-red-400 font-medium">
                  Failed to load posts
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {postsError.message || 'Please check if the backend server is running'}
                </p>
              </div>
            ) : posts?.posts && posts.posts.length > 0 ? (
              <div className="space-y-4">
                {posts.posts.map((post: RedditPost) => (
                  <div
                    key={post.id}
                    className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <h4 className="font-medium leading-tight">{post.title}</h4>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <Badge variant="outline" className="text-xs">
                            r/{post.subreddit}
                          </Badge>
                          <span>by u/{post.author}</span>
                          <span>{post.score} points</span>
                          <span>{post.num_comments} comments</span>
                        </div>
                        {post.content_preview && (
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {post.content_preview}
                          </p>
                        )}
                        {post.mentioned_tickers && post.mentioned_tickers.length > 0 && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">Mentions:</span>
                            {post.mentioned_tickers.slice(0, 5).map((ticker) => (
                              <Badge key={ticker} variant="secondary" className="text-xs">
                                {ticker}
                              </Badge>
                            ))}
                            {post.mentioned_tickers.length > 5 && (
                              <span className="text-xs text-muted-foreground">
                                +{post.mentioned_tickers.length - 5} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        {getSentimentBadge(post.sentiment_label)}
                        {post.sentiment_score !== undefined && (
                          <span className="text-xs text-muted-foreground">
                            Score: {formatScore(post.sentiment_score)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No posts found for {selectedTicker}
                {postFilter !== 'all' && ` with ${postFilter} sentiment`}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
