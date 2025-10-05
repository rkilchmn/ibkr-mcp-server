"""Trading operations endpoints."""
from fastapi import Body
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import PlaceOrderRequest, OrderResponse, OpenOrder


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
    request: Order placement request containing contract and order details
    
  Returns:
    Order response with order ID, status, and execution details
    
  Example:
    >>> await place_order({
    ...   "contract": {
    ...     "symbol": "AAPL",
    ...     "sec_type": "STK",
    ...     "exchange": "SMART",
    ...     "currency": "USD"
    ...   },
    ...   "order": {
    ...     "action": "BUY",
    ...     "total_quantity": 100,
    ...     "order_type": "LMT",
    ...     "lmt_price": 150.00,
    ...     "time_in_force": "DAY"
    ...   }
    ... })
    {
      "order_id": 1,
      "status": "Submitted",
      "symbol": "AAPL",
      "action": "BUY",
      "quantity": 100.0,
      "filled": 0.0,
      "remaining": 100.0,
      "avg_fill_price": null
    }
  """
  try:
    logger.debug(f"Placing order for {request.contract.symbol}")
    response = await ib_interface.place_order(request.contract, request.order)
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
async def cancel_order(order_id: int) -> dict:
  """Cancel an order by ID.
  
  Cancel a pending or partially filled order.
  
  Args:
    order_id: The order ID to cancel
    
  Returns:
    Cancellation status
    
  Example:
    >>> await cancel_order(order_id=1)
    {"success": true, "order_id": 1, "message": "Order cancelled successfully"}
  """
  try:
    logger.debug(f"Cancelling order {order_id}")
    success = await ib_interface.cancel_order(order_id)
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
async def get_open_orders() -> list[OpenOrder]:
  """Get all open orders.
  
  Retrieve all pending and partially filled orders.
  
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
  try:
    logger.debug("Getting open orders")
    orders = await ib_interface.get_open_orders()
    return orders
  except Exception as e:
    logger.error(f"Error in get_open_orders: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get open orders"}
    )
