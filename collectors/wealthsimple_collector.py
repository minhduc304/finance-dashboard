"""
Wealthsimple pure data collector
Returns data without database operations
"""

import os
import getpass
import json
from datetime import datetime, timedelta, timezone
from ws_api import WealthsimpleAPI, WSAPISession
from typing import List, Optional, Dict, Any

SESSION_FILE = 'ws_session.json'
CACHE_DURATION = timedelta(hours=6)

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

    def get_accounts(self) -> List[Dict]:
        """Get all account information"""
        if not self.ws_api:
            raise Exception("Not authenticated. Call authenticate() first.")

        accounts = self.ws_api.get_accounts()
        return [
            {
                'id': account['id'],
                'description': account['description'],
                'account_type': account.get('type', 'unknown'),
                'value': float(account.get('value', 0)),
                'cash_balance': float(account.get('cash_balance', 0)),
                'currency': account.get('currency', 'CAD'),
                'status': account.get('status', 'unknown')
            }
            for account in accounts
        ]

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of all portfolios"""
        accounts = self.get_accounts()

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
        accounts = self.get_accounts()

        target_accounts = [acc for acc in accounts if account_id is None or acc['id'] == account_id]

        for account in target_accounts:
            try:
                holdings = self.ws_api.get_holdings(account['id'])

                for holding_data in holdings:
                    security = holding_data.get('security', {})

                    holding = {
                        'account_id': account['id'],
                        'account_name': account['description'],
                        'symbol': security.get('symbol', 'UNKNOWN'),
                        'name': security.get('name', 'Unknown Security'),
                        'quantity': float(holding_data.get('quantity', 0)),
                        'average_cost': float(holding_data.get('average_cost', 0)),
                        'current_price': float(security.get('last_price', 0)),
                        'market_value': float(holding_data.get('market_value', 0)),
                        'currency': security.get('currency', 'CAD'),
                        'security_type': security.get('type', 'stock'),
                        'gain_loss': 0  # Will be calculated
                    }

                    # Calculate gain/loss
                    total_cost = holding['quantity'] * holding['average_cost']
                    holding['gain_loss'] = holding['market_value'] - total_cost
                    holding['gain_loss_percent'] = (holding['gain_loss'] / total_cost * 100) if total_cost > 0 else 0

                    all_holdings.append(holding)

            except Exception as e:
                # Continue with other accounts if one fails
                continue

        return all_holdings

    def get_transactions(self, account_id: str = None, days_back: int = 30) -> List[Dict]:
        """Get recent transactions"""
        if not self.ws_api:
            raise Exception("Not authenticated. Call authenticate() first.")

        all_transactions = []
        accounts = self.get_accounts()

        target_accounts = [acc for acc in accounts if account_id is None or acc['id'] == account_id]
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for account in target_accounts:
            try:
                activities = self.ws_api.get_activities(account['id'], how_many=100)

                for activity in activities:
                    try:
                        # Parse transaction date
                        trans_date = datetime.fromisoformat(activity['occurredAt'].replace('Z', '+00:00'))

                        # Skip old transactions
                        if trans_date < cutoff_date:
                            continue

                        transaction = {
                            'account_id': account['id'],
                            'account_name': account['description'],
                            'transaction_id': activity.get('id'),
                            'type': self._determine_transaction_type(activity),
                            'description': activity.get('description', ''),
                            'symbol': activity.get('symbol'),
                            'quantity': float(activity.get('quantity', 0)),
                            'price': float(activity.get('price', 0)),
                            'total_amount': float(activity.get('amount', 0)),
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