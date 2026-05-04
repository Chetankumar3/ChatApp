import json
import logging
from logging.handlers import RotatingFileHandler
import grpc
from functools import wraps

from .grpc_proto import grpc_stub_pb2 as pb2
from .grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .state import get_connection

error_logger = logging.getLogger("grpc_errors")
error_logger.setLevel(logging.ERROR)
file_handler = RotatingFileHandler(
    filename="grpc_exceptions.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - gRPC: %(message)s")
)
error_logger.addHandler(file_handler)

def handle_grpc_errors(func):
    @wraps(func)
    async def wrapper(self, request, context):
        try:
            return await func(self, request, context)
        except grpc.RpcError:
            raise
        except Exception as exc:
            error_logger.error(
                f"Unhandled gRPC Error in {func.__name__}: {str(exc)}", 
                exc_info=True
            )
            await context.abort(grpc.StatusCode.INTERNAL, "Internal CM service failure")
    return wrapper

class ConnectionManagerServicer(pb2_grpc.ConnectionManagerServicer):

    @handle_grpc_errors  # 3. Attach decorator
    async def DeliverOutboundMessage(
        self,
        request: pb2.OutboundMessage,
        context: grpc.aio.ServicerContext,
    ) -> pb2.DeliveryAck:

        payload = json.dumps({
            "type":       request.type,
            "fromId":     request.fromId,
            "toId":       request.toId,
            "body":       request.body,
            "sentAt":     request.sentAt,
            "message_id": request.message_id,
        })

        failed: list[int] = []

        for uid in request.target_user_ids:
            entry = get_connection(uid)

            if entry is None:
                failed.append(uid)
                continue

            ws, lock = entry
            async with lock:
                try:
                    await ws.send_text(payload)
                except Exception as exc:
                    # Expected application fault: Log as warning without traceback, do not abort RPC
                    error_logger.warning(f"WebSocket send failed for user {uid}: {str(exc)}")
                    failed.append(uid)

        return pb2.DeliveryAck(failed_user_ids=failed)