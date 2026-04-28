import grpc

class ConnectionManagerServicer: 
    async def DeliverOutboundMessage(self, request, context):
        # 1. Parse incoming request (message payload + target_user_ids).
        # 2. Iterate through target_user_ids.
        # 3. Safely acquire asyncio.Lock for each user in the shared RAM dict.
        # 4. Blast the message via the WebSocket object.
        # 5. Return DeliveryAck.
        pass