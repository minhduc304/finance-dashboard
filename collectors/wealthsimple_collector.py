"""
Wealthsimple pure data collector
Returns data without database operations
"""

import os
import getpass
from datetime import datetime, timedelta, timezone
from ws_api import WealthsimpleAPI, WSAPISession
from typing import List, Optional, Dict, Any

# Use absolute path for session file to ensure consistency across different working directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(PROJECT_ROOT, 'ws_session.json')
CACHE_DURATION = timedelta(hours=12)

class WealthsimpleCollector:
    """Pure data collector for Wealthsimple - no database operations"""

    def __init__(self):
        """Initialize Wealthsimple collector"""
        self.ws_api = None
        self.user_email = None

    def persist_session(self, session_json) -> None:
        """Persist session to file"""
        with open(SESSION_FILE, 'w') as f:
            f.write(session_json)

    def load_session(self) -> Optional[WSAPISession]:
        """Load session from file"""
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                return WSAPISession.from_json(f.read())
        return None

    def authenticate(self, email: str = None, password: str = None, otp: str = None) -> bool:
        """Authenticate with Wealthsimple"""
        session = self.load_session()

        if session:
            try:
                self.ws_api = WealthsimpleAPI.from_token(session, self.persist_session)
                return True
            except Exception:
                self.ws_api = None

        if not self.ws_api:
            if not email:
                email = input("Enter your Wealthsimple email: ")
            if not password:
                password = getpass.getpass("Enter your Wealthsimple password: ")

            self.user_email = email

            try:
                session_obj = WealthsimpleAPI.login(email, password, persist_session_fct=self.persist_session)
                self.ws_api = WealthsimpleAPI.from_token(session_obj, self.persist_session)
            except Exception as e:
                if "2FA code required" in str(e):
                    if not otp:
                        otp = input("Enter your 2FA code: ")
                    session_obj = WealthsimpleAPI.login(email, password, otp_answer=otp, persist_session_fct=self.persist_session)
                    self.ws_api = WealthsimpleAPI.from_token(session_obj, self.persist_session)
                else:
                    raise e

        return True

    def _get_accounts(self) -> List[Dict]:
        """Get all account information"""
        if not self.ws_api:
            raise Exception("Not authenticated. Call authenticate() first.")

        accounts = self.ws_api.get_accounts()
        parsed_accounts = []

        for account in accounts:
            # Extract nested financial values
            financials = account.get('financials', {})
            current_combined = financials.get('currentCombined', {})
            net_liquidation = current_combined.get('netLiquidationValue', {})

            # Get the value in dollars (amount field is string)
            value_str = net_liquidation.get('amount', '0')
            value = float(value_str) if value_str else 0.0

            # Note: There's no direct cash_balance field, using netLiquidationValue for now
            # Could potentially calculate from deposits - withdrawals

            parsed_account = {
                'id': account['id'],
                'description': account.get('description', account.get('nickname', 'Unknown')),
                'account_type': account.get('type', 'unknown'),
                'value': value,
                'cash_balance': value,  # Using total value as cash for now
                'currency': account.get('currency', 'CAD'),
                'status': account.get('status', 'unknown')
            }
            parsed_accounts.append(parsed_account)

        return parsed_accounts

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of all portfolios"""
        accounts = self._get_accounts()

        total_value = sum(acc['value'] for acc in accounts)
        total_cash = sum(acc['cash_balance'] for acc in accounts)

        return {
            'user_email': self.user_email,
            'total_accounts': len(accounts),
            'total_portfolio_value': total_value,
            'total_cash_balance': total_cash,
            'currency': 'CAD',  # Assume CAD for Wealthsimple
            'accounts': accounts,
            'collected_at': datetime.now(timezone.utc)
        }

    def get_holdings(self, account_id: str = None) -> List[Dict]:
        """Get holdings for specific account or all accounts"""
        if not self.ws_api:
            raise Exception("Not authenticated. Call authenticate() first.")

        all_holdings = []
        accounts = self._get_accounts()

        target_accounts = [acc for acc in accounts if account_id is None or acc['id'] == account_id]

        for account in target_accounts:
            try:
                # Get account balances returns {security_id: quantity}
                balances = self.ws_api.get_account_balances(account['id'])

                if not balances:
                    continue

                for security_id, quantity in balances.items():
                    if quantity == 0:
                        continue

                    symbol = security_id
                    name = security_id
                    current_price = 0
                    currency = 'CAD'
                    security_type = 'unknown'
                    market_value = 0

                    try:
                        # Try to get market data for the security
                        market_data = self.ws_api.get_security_market_data(security_id)

                        # Extract relevant fields from market data
                        symbol = market_data.get('symbol', security_id)
                        name = market_data.get('name', security_id)

                        # Try different fields for price
                        quote = market_data.get('quote', {})
                        current_price = float(quote.get('last', 0) or quote.get('price', 0) or quote.get('amount', 0))

                        # If still no price, check top level
                        if current_price == 0:
                            current_price = float(market_data.get('last_price', 0) or market_data.get('price', 0))

                        currency = market_data.get('currency', 'CAD')
                        security_type = market_data.get('type', 'stock')

                    except Exception:
                        # For crypto or special securities, parse the ID
                        if ' - ' in security_id:
                            parts = security_id.split(' - ')
                            symbol = parts[0]
                            name = parts[1] if len(parts) > 1 else security_id
                            security_type = 'crypto'
                        elif security_id.startswith('sec-'):
                            # Cash or special security
                            symbol = security_id
                            name = 'Cash' if 'cad' in security_id.lower() else security_id
                            current_price = 1.0 if 'cad' in security_id.lower() else 0
                            security_type = 'cash'

                    # Calculate market value
                    market_value = float(quantity) * float(current_price)

                    holding = {
                        'account_id': account['id'],
                        'account_name': account['description'],
                        'symbol': symbol,
                        'name': name,
                        'quantity': float(quantity),
                        'average_cost': 0,  # Will need to calculate from activities
                        'current_price': float(current_price),
                        'market_value': float(market_value),
                        'currency': currency,
                        'security_type': security_type,
                        'gain_loss': 0,  # Cannot calculate without average cost
                        'gain_loss_percent': 0  # Cannot calculate without average cost
                    }

                    all_holdings.append(holding)

            except Exception:
                # Continue with other accounts if one fails
                continue

        return all_holdings

    def get_transactions(self, account_id: str = None, days_back: int = 30) -> List[Dict]:
        """Get recent transactions"""
        if not self.ws_api:
            raise Exception("Not authenticated. Call authenticate() first.")

        all_transactions = []
        accounts = self._get_accounts()

        target_accounts = [acc for acc in accounts if account_id is None or acc['id'] == account_id]
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for account in target_accounts:
            try:
                activities = self.ws_api.get_activities(account['id'], how_many=100)

                for activity in activities:
                    try:
                        # Parse transaction date - try different field names
                        date_str = activity.get('occurredAt') or activity.get('occurred_at') or activity.get('createdAt')
                        if not date_str:
                            continue

                        trans_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                        # Skip old transactions
                        if trans_date.replace(tzinfo=None) < cutoff_date:
                            continue

                        # Get symbol - might be in different fields
                        symbol = activity.get('symbol')
                        if not symbol and 'security_id' in activity:
                            symbol = self.ws_api.security_id_to_symbol(activity['security_id'])

                        transaction = {
                            'account_id': account['id'],
                            'account_name': account['description'],
                            'transaction_id': activity.get('id'),
                            'type': self._determine_transaction_type(activity),
                            'description': activity.get('description', ''),
                            'symbol': symbol,
                            'quantity': float(activity.get('quantity', 0)),
                            'price': float(activity.get('price', 0)),
                            'total_amount': float(activity.get('amount', 0) or activity.get('net_amount', 0)),
                            'currency': activity.get('currency', 'CAD'),
                            'transaction_date': trans_date,
                            'status': activity.get('status', 'unknown')
                        }

                        all_transactions.append(transaction)

                    except Exception:
                        continue

            except Exception:
                continue

        # Sort by date, newest first
        all_transactions.sort(key=lambda x: x['transaction_date'], reverse=True)
        return all_transactions

    def get_performance_data(self, account_id: str = None, days_back: int = 30) -> Dict[str, Any]:
        """Get performance data for accounts"""
        holdings = self.get_holdings(account_id)
        transactions = self.get_transactions(account_id, days_back)

        # Calculate performance metrics
        total_market_value = sum(h['market_value'] for h in holdings)
        total_cost = sum(h['quantity'] * h['average_cost'] for h in holdings)
        total_gain_loss = total_market_value - total_cost

        # Group by symbol for analysis
        holdings_by_symbol = {}
        for holding in holdings:
            symbol = holding['symbol']
            if symbol not in holdings_by_symbol:
                holdings_by_symbol[symbol] = {
                    'symbol': symbol,
                    'name': holding['name'],
                    'total_quantity': 0,
                    'total_market_value': 0,
                    'total_cost': 0,
                    'accounts': []
                }

            holdings_by_symbol[symbol]['total_quantity'] += holding['quantity']
            holdings_by_symbol[symbol]['total_market_value'] += holding['market_value']
            holdings_by_symbol[symbol]['total_cost'] += (holding['quantity'] * holding['average_cost'])
            holdings_by_symbol[symbol]['accounts'].append(holding['account_name'])

        # Calculate performance for each holding
        top_performers = []
        worst_performers = []

        for symbol_data in holdings_by_symbol.values():
            gain_loss = symbol_data['total_market_value'] - symbol_data['total_cost']
            gain_loss_percent = (gain_loss / symbol_data['total_cost'] * 100) if symbol_data['total_cost'] > 0 else 0

            performance = {
                'symbol': symbol_data['symbol'],
                'name': symbol_data['name'],
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent,
                'market_value': symbol_data['total_market_value']
            }

            if gain_loss_percent > 0:
                top_performers.append(performance)
            else:
                worst_performers.append(performance)

        # Sort performers
        top_performers.sort(key=lambda x: x['gain_loss_percent'], reverse=True)
        worst_performers.sort(key=lambda x: x['gain_loss_percent'])

        return {
            'summary': {
                'total_market_value': total_market_value,
                'total_cost': total_cost,
                'total_gain_loss': total_gain_loss,
                'total_gain_loss_percent': (total_gain_loss / total_cost * 100) if total_cost > 0 else 0,
                'number_of_holdings': len(holdings),
                'number_of_transactions': len(transactions)
            },
            'top_performers': top_performers[:5],
            'worst_performers': worst_performers[:5],
            'holdings_by_symbol': list(holdings_by_symbol.values()),
            'recent_transactions': transactions[:10],
            'collected_at': datetime.now(timezone.utc)
        }

    def _determine_transaction_type(self, activity: Dict) -> str:
        """Determine transaction type from activity description"""
        description = activity.get('description', '').lower()
        activity_type = activity.get('type', '').lower()
        sub_type = activity.get('sub_type', '').lower()

        # Check type field first
        if 'buy' in activity_type or 'bought' in activity_type:
            return 'buy'
        elif 'sell' in activity_type or 'sold' in activity_type:
            return 'sell'
        elif 'dividend' in activity_type:
            return 'dividend'
        elif 'deposit' in activity_type or 'funding' in activity_type:
            return 'deposit'
        elif 'withdrawal' in activity_type or 'redeem' in activity_type:
            return 'withdrawal'

        # Check sub_type
        if 'buy' in sub_type:
            return 'buy'
        elif 'sell' in sub_type:
            return 'sell'

        # Check description
        if 'buy' in description or 'bought' in description:
            return 'buy'
        elif 'sell' in description or 'sold' in description:
            return 'sell'
        elif 'dividend' in description:
            return 'dividend'
        elif 'deposit' in description:
            return 'deposit'
        elif 'withdrawal' in description:
            return 'withdrawal'
        elif 'fee' in description:
            return 'fee'
        else:
            return 'other'

    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all available data"""
        return {
            'portfolio_summary': self.get_portfolio_summary(),
            'holdings': self.get_holdings(),
            'transactions': self.get_transactions(days_back=30),
            'performance': self.get_performance_data(days_back=30)
        }