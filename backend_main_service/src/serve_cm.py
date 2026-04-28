import grpc
from datetime import datetime
from sqlalchemy import select
from database import get_db

import DB_models
import chat_pb2
import chat_pb2_grpc

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    
    # Notice: We pass 'db' directly as an argument, no Depends()
    async def _SendDirectMessage(self, request, db):
        try:
            DBMessage = DB_models.message(
                fromId=request.fromId,
                toId=request.toId,
                body=request.body,
                sentAt=datetime.fromisoformat(
                    request.sentAt.replace("Z", "+00:00")
                ),
            )
            db.add(DBMessage)
            await db.commit()
            
            return chat_pb2.MessageResponse(success=True, message_id=DBMessage.id)
        except Exception as e:
            return chat_pb2.MessageResponse(success=False, error=str(e))

    async def _SendGroupMessage(self, request, db):
        try:
            DBGroupMessage = DB_models.groupMessage(
                fromId=request.fromId,
                toId=request.toId,
                body=request.body,
                sentAt=datetime.fromisoformat(
                    request.sentAt.replace("Z", "+00:00")
                ),
            )
            
            db.add(DBGroupMessage)
            await db.flush()
            await db.refresh(DBGroupMessage)

            group_users = await db.scalars(
                select(DB_models.mapTable.userId).where(
                    DB_models.mapTable.groupId == request.toId
                )
            )
            group_users = group_users.all()

            message_receipts = [
                DB_models.messageReceipt(groupMessageId=DBGroupMessage.id, userId=u)
                for u in group_users
            ]
            db.add_all(message_receipts)

            current_user_receipt = DB_models.messageReceipt(
                groupMessageId=DBGroupMessage.id,
                userId=request.fromId,
                receivedAt=datetime.fromisoformat(
                    request.sentAt.replace("Z", "+00:00")
                ),
            )
            db.merge(current_user_receipt)
            await db.commit()

            return chat_pb2.MessageResponse(
                success=True, 
                message_id=DBGroupMessage.id, 
                userIds=group_users
            )
        except Exception as e:
            return chat_pb2.MessageResponse(success=False, error=str(e))

    # The actual gRPC endpoint exposed to the network
    async def SaveMessage(self, request, context):
        async for db in get_db():
            if request.type == "direct_message":
                return await self._SendDirectMessage(request, db)
            elif request.type == "group_message":
                return await self._SendGroupMessage(request, db)
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid message type")
                return chat_pb2.MessageResponse(success=False, error="Invalid message type")