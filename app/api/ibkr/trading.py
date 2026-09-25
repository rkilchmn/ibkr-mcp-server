"""Trading operations endpoints."""
from fastapi import Body, Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, resolve_interface
from app.core.setup_logging import logger
from app.models import PlaceOrderRequest, OrderResponse, OpenOrder

ACCOUNT_ID_QUERY = Query(
  default=None,
  description="Account to use (account id from /gateway/status). Empty/omitted uses the default account.", #noqa: E501
)


@ibkr_router.post(
  "/orders/place",
  operation_id="place_order",
  response_model=OrderResponse,
)
async def place_order(
  request: PlaceOrderRequest = Body(..., description="Order placement request")
) -> OrderResponse:
  """Place a trading order.

  Submit a new order to IBKR for execution. Supports various order types including
  market, limit, stop, and stop-limit orders.

  Args:
    request: Order placement request containing contract, order details,
      and an optional account_id (empty/None uses the default account)

  Returns:
    Order response with order ID, status, and execution details

  Example:
    {
      "contract": {
        "con_id": 12345678
      },
      "order": {
        "action": "BUY",
        "total_quantity": 100,
        "order_type": "LMT",
        "lmt_price": 150.00,
        "time_in_force": "DAY"
      }
    }

  """
  iface = resolve_interface(request.account_id)
  try:
    logger.debug(
      f"Placing order for {request.contract.symbol} (account_id={request.account_id})"
    )
    response = await iface.place_order(request.contract, request.order)
    return response
  except Exception as e:
    logger.error(f"Error in place_order: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to place order"}
    )


@ibkr_router.delete(
  "/orders/{order_id}",
  operation_id="cancel_order",
  response_model=dict,
)
async def cancel_order(
  order_id: int,
  account_id: str | None = ACCOUNT_ID_QUERY,
) -> dict:
  """Cancel an order by ID.

  Cancel a pending or partially filled order.

  Args:
    order_id: The order ID to cancel
    account_id: Account to use (account id from /gateway/status). Empty/omitted uses the default account.

  Returns:
    Cancellation status

  Example:
    >>> await cancel_order(order_id=1)
    {"success": true, "order_id": 1, "message": "Order cancelled successfully"}
  """
  iface = resolve_interface(account_id)
  try:
    logger.debug(f"Cancelling order {order_id} (account_id={account_id})")
    success = await iface.cancel_order(order_id)
    return {
      "success": success,
      "order_id": order_id,
      "message": "Order cancelled successfully" if success else "Failed to cancel order"
    }
  except Exception as e:
    logger.error(f"Error in cancel_order: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": f"Failed to cancel order {order_id}"}
    )


@ibkr_router.get(
  "/orders/open",
  operation_id="get_open_orders",
  response_model=list[OpenOrder],
)
async def get_open_orders(
  account_id: str | None = ACCOUNT_ID_QUERY,
) -> list[OpenOrder]:
  """Get all open orders.

  Retrieve all pending and partially filled orders.

  Args:
    account_id: Account to use (account id from /gateway/status). Empty/omitted uses the default account.

  Returns:
    List of open orders with details
    
  Example:
    >>> await get_open_orders()
    [
      {
        "order_id": 1,
        "symbol": "AAPL",
        "sec_type": "STK",
        "action": "BUY",
        "quantity": 100.0,
        "order_type": "LMT",
        "status": "Submitted",
        "limit_price": 150.00,
        "aux_price": null,
        "filled": 0.0,
        "remaining": 100.0,
        "avg_fill_price": null
      }
    ]
  """
  iface = resolve_interface(account_id)
  try:
    logger.debug(f"Getting open orders (account_id={account_id})")
    orders = await iface.get_open_orders()
    return orders
  except Exception as e:
    logger.error(f"Error in get_open_orders: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get open orders"}
    )
