import requests
from datetime import datetime
from typing import List, Dict, Optional

class RobloxAPI:
    def __init__(self, cookie: str):
        self.cookie = cookie
        self.session = requests.Session()
        self.session.cookies.set('.ROBLOSECURITY', cookie)
        self.user_id = None
        self.username = None
        
    def get_user_info(self) -> Optional[Dict]:
        try:
            response = self.session.get('https://users.roblox.com/v1/users/authenticated')
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get('id')
                self.username = data.get('name')
                return data
            return None
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return None
    
    def get_transactions(self, limit: int = 100, cursor: str = None) -> Optional[Dict]:
        if not self.user_id:
            self.get_user_info()
        
        if not self.user_id:
            return None
        
        try:
            url = f'https://economy.roblox.com/v2/users/{self.user_id}/transactions'
            params = {
                'limit': min(limit, 100),
                'transactionType': 'Purchase'
            }
            if cursor:
                params['cursor'] = cursor
            
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return None
    
    def get_all_transactions(self, max_transactions: int = 500) -> List[Dict]:
        all_transactions = []
        cursor = None
        
        while len(all_transactions) < max_transactions:
            data = self.get_transactions(limit=100, cursor=cursor)
            if not data or 'data' not in data:
                break
            
            transactions = data['data']
            if not transactions:
                break
            
            all_transactions.extend(transactions)
            
            cursor = data.get('nextPageCursor')
            if not cursor:
                break
        
        return all_transactions[:max_transactions]
    
    def get_game_details(self, universe_id: int) -> Optional[Dict]:
        try:
            url = f'https://games.roblox.com/v1/games'
            params = {'universeIds': universe_id}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    return data['data'][0]
            return None
        except Exception:
            return None
    
    def parse_transactions(self, transactions: List[Dict]) -> List[Dict]:
        parsed = []
        
        for trans in transactions:
            item_name = trans.get('details', {}).get('name', 'Unknown')
            item_type = trans.get('details', {}).get('type', 'Unknown')
            amount = abs(trans.get('currency', {}).get('amount', 0))
            created = trans.get('created', '')
            
            try:
                date = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                try:
                    date = datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ')
                except:
                    date = datetime.now()
            
            universe_id = trans.get('details', {}).get('id')
            
            category = self._categorize_transaction(item_type, item_name)
            
            parsed.append({
                'date': date,
                'item': item_name,
                'type': item_type,
                'amount': amount,
                'category': category,
                'universe_id': universe_id
            })
        
        return parsed
    
    def _categorize_transaction(self, item_type: str, item_name: str) -> str:
        item_type_lower = item_type.lower()
        item_name_lower = item_name.lower()
        
        if 'game' in item_type_lower or 'pass' in item_type_lower:
            return 'Game'
        elif 'developer product' in item_type_lower:
            return 'Game'
        elif 'asset' in item_type_lower or 'catalog' in item_type_lower:
            if any(word in item_name_lower for word in ['shirt', 'pants', 'hat', 'hair', 'face', 'gear', 'accessory']):
                return 'Cosmetics'
            return 'Other'
        elif 'private server' in item_type_lower:
            return 'Game'
        elif 'trade' in item_type_lower:
            return 'Trading'
        else:
            return 'Other'
    
    def validate_cookie(self) -> bool:
        user_info = self.get_user_info()
        return user_info is not None
