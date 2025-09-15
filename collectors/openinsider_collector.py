"""
OpenInsider pure data collector
Returns data without database operations
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import random
import logging

class OpenInsiderCollector:
    """Pure data collector for OpenInsider - no database operations"""

    def __init__(self):
        """Initialize OpenInsider collector"""
        self.base_url = "http://openinsider.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def scrape_latest_trades(self, pages: int = 5) -> List[Dict]:
        """Scrape latest insider trades and return as list of dicts"""
        trades = []

        for page in range(1, pages + 1):
            try:
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(1, 3))

                url = f"{self.base_url}/latest"
                if page > 1:
                    url += f"?p={page}"

                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                page_trades = self._parse_trades_table(soup)
                trades.extend(page_trades)

            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                continue

        return trades

    def _parse_trades_table(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse trades table from soup"""
        trades = []
        table = soup.find('table', {'class': 'tinytable'})

        if not table:
            return trades

        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []

        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 11:
                    continue

                trade = {
                    'filing_date': self._parse_date(cells[1].text.strip()),
                    'trade_date': self._parse_date(cells[2].text.strip()),
                    'ticker': cells[3].text.strip(),
                    'company_name': cells[4].text.strip(),
                    'insider_name': cells[5].text.strip(),
                    'insider_title': cells[6].text.strip(),
                    'trade_type': cells[7].text.strip(),
                    'price': self._parse_float(cells[8].text.strip()),
                    'quantity': self._parse_int(cells[9].text.strip()),
                    'shares_owned': self._parse_int(cells[10].text.strip()),
                    'delta_owned': self._parse_float(cells[11].text.strip()) if len(cells) > 11 else 0.0,
                    'value': self._parse_float(cells[12].text.strip()) if len(cells) > 12 else 0.0
                }

                trades.append(trade)

            except Exception as e:
                self.logger.error(f"Error parsing trade row: {e}")
                continue

        return trades

    def scrape_company_trades(self, ticker: str, days: int = 30) -> List[Dict]:
        """Scrape trades for a specific company"""
        url = f"{self.base_url}/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=730&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysback=&xp=1"

        try:
            time.sleep(random.uniform(1, 3))
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            trades = self._parse_trades_table(soup)

            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_trades = []
            for t in trades:
                if t['trade_date'] and isinstance(t['trade_date'], datetime):
                    if t['trade_date'] >= cutoff_date:
                        recent_trades.append(t)

            return recent_trades

        except Exception as e:
            self.logger.error(f"Error scraping trades for {ticker}: {e}")
            return []

    def get_top_insider_buys(self, limit: int = 20) -> List[Dict]:
        """Get top insider buying activity"""
        try:
            time.sleep(random.uniform(1, 3))
            url = f"{self.base_url}/top-insider-buying"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            trades = self._parse_trades_table(soup)
            return trades[:limit]
        except Exception:
            return []

    def get_top_insider_sales(self, limit: int = 20) -> List[Dict]:
        """Get top insider selling activity"""
        try:
            time.sleep(random.uniform(1, 3))
            url = f"{self.base_url}/top-insider-sales"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            trades = self._parse_trades_table(soup)
            return trades[:limit]
        except Exception:
            return []

    def calculate_insider_summary(self, trades: List[Dict], ticker: Optional[str] = None) -> Dict:
        """Calculate summary statistics from trades data"""
        if ticker:
            trades = [t for t in trades if t.get('ticker') == ticker]

        if not trades:
            return {}

        # Filter recent trades (last 30 days)
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_trades = []
        for t in trades:
            if t.get('trade_date') and isinstance(t['trade_date'], datetime):
                if t['trade_date'] >= recent_cutoff:
                    recent_trades.append(t)

        if not recent_trades:
            return {}

        buy_trades = [t for t in recent_trades if 'buy' in t.get('trade_type', '').lower()]
        sell_trades = [t for t in recent_trades if 'sell' in t.get('trade_type', '').lower()]

        total_buy_value = sum(t.get('value', 0) for t in buy_trades)
        total_sell_value = sum(abs(t.get('value', 0)) for t in sell_trades)
        net_activity = total_buy_value - total_sell_value

        return {
            'ticker': ticker,
            'period_days': 30,
            'total_trades': len(recent_trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'net_activity': net_activity,
            'sentiment': 'bullish' if net_activity > 0 else 'bearish' if net_activity < 0 else 'neutral',
            'top_buyers': self._get_top_insiders(buy_trades, 'buy'),
            'top_sellers': self._get_top_insiders(sell_trades, 'sell')
        }

    def _get_top_insiders(self, trades: List[Dict], trade_type: str) -> List[Dict]:
        """Get top insiders by trade value"""
        insider_totals = {}

        for trade in trades:
            insider = trade.get('insider_name', 'Unknown')
            value = abs(trade.get('value', 0))

            if insider not in insider_totals:
                insider_totals[insider] = {
                    'name': insider,
                    'title': trade.get('insider_title', ''),
                    'total_value': 0,
                    'trade_count': 0
                }

            insider_totals[insider]['total_value'] += value
            insider_totals[insider]['trade_count'] += 1

        # Sort by total value
        sorted_insiders = sorted(insider_totals.values(),
                                key=lambda x: x['total_value'],
                                reverse=True)

        return sorted_insiders[:5]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str or date_str.strip() == '':
            return None

        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _parse_float(self, value_str: str) -> float:
        """Parse string to float, handling currency symbols"""
        if not value_str:
            return 0.0

        cleaned = value_str.replace('$', '').replace(',', '').replace('+', '').strip()

        # Handle millions (M) and thousands (K)
        if 'M' in cleaned:
            cleaned = cleaned.replace('M', '')
            try:
                return float(cleaned) * 1000000
            except:
                return 0.0
        elif 'K' in cleaned:
            cleaned = cleaned.replace('K', '')
            try:
                return float(cleaned) * 1000
            except:
                return 0.0

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    def _parse_int(self, value_str: str) -> int:
        """Parse string to integer"""
        if not value_str:
            return 0

        cleaned = value_str.replace(',', '').strip()
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return 0