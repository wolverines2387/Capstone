from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Product, Bid
import json

from django.utils import timezone

class RecomenderConsumer(AsyncWebsocketConsumer):

    connected_clients = set() 

    async def connect(self):
        # You might want to do a user authentication check here
        # If not authenticated, reject the connection
        self.product_id = self.scope['url_route']['kwargs']['product_id']

        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            await self.accept()
            self.connected_clients.add(self)

    async def disconnect(self, close_code):
        self.connected_clients.remove(self)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Check for bid_history request
        if 'request' in text_data_json and text_data_json['request'] == 'recomendation_history':
            all_recomendation = await self.get_recent_recomendation(self.product_id)
            end_time = await self.get_recomendation_end_time(self.product_id)

            end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            await self.send(json.dumps({
                'bid_history': all_recomendation,
                'end_time': end_time_str  # Send the end time as a string to the frontend
            }))
        elif 'request' in text_data_json and text_data_json['request'] == 'current_recomendation':
            current_recomendation_amount = await self.get_current_recomendation(self.product_id)  # Assuming '1' is the product_id, adjust accordingly
            await self.send(json.dumps({
                'current_bid': str(current_recomendation_amount)
            }))
        else:
            current_time = timezone.now()
            end_time = await self.get_auction_end_time(self.product_id)

            if end_time and current_time >= end_time:
                await self.send(json.dumps({
                    'error': 'The auction has ended. No new bids are accepted.'
                }))
                return


            new_bid = text_data_json['bid']
            if new_bid < 1 or new_bid > 1000000:
                await self.send(json.dumps({
                    'error': 'Bid should be between $1 and $1,000,000.'
                }))
                return

            # Get user from scope
            user = self.scope["user"]

            updated_bid = await self.update_product_bid(self.product_id, new_bid, user)

            if updated_bid is not None:
                all_bids = await self.get_recent_bids(self.product_id)
                await self.broadcast(json.dumps({
                    'new_bid': str(updated_bid),
                    'bid_history': all_bids
                }))
            else:
                await self.send(json.dumps({
                    'error': 'Failed to update bid'
                }))

    @database_sync_to_async
    def update_product_bid(self, product_id, new_bid, user):
        try:
            product = Product.objects.get(id=product_id)
            if product.current_bid is not None and product.current_bid.amount >= new_bid:
                return None
            if product.current_bid is None or product.current_bid.amount < new_bid:
                bid = Bid(user=user, product=product, amount=new_bid)
                bid.save()
                product.current_bid = bid
                product.save()
                return new_bid
            else:
                return None
        except Product.DoesNotExist:
            return None

    @database_sync_to_async
    def get_recent_bids(self, product_id):
        try:
            product = Product.objects.get(id=product_id)
            # Get the last 5 bids for the product
            bids = Bid.objects.filter(product=product).order_by('-id')[:5]
            return [{"user": bid.user.username, "amount": str(bid.amount)} for bid in bids]
        except Product.DoesNotExist:
            return []

    @database_sync_to_async
    def get_auction_end_time(self, product_id):
        try:
            product = Product.objects.get(id=product_id)
            return product.end_time
        except Product.DoesNotExist:
            return None

    @database_sync_to_async
    def get_current_bid(self, product_id):
        try:
            product = Product.objects.get(id=product_id)
            return product.current_bid.amount if product.current_bid else 0
        except Product.DoesNotExist:
            return 0

    async def broadcast(self, message):
        for client in self.connected_clients:
            await client.send(text_data=message)