import sys
import asyncio
import logging
from typing import TYPE_CHECKING

import py_expression_eval
from aiohttp import web
from aiohttplimiter import Limiter, default_keyfunc

if TYPE_CHECKING:
  pass

HOST = "127.0.0.1"
PORT = 20508
MAX_RESULT_LENGTH = 10000

RATELIMIT = "60/minute"

LOGFMT = "[%(filename)s][%(asctime)s][%(levelname)s] %(message)s"
LOGDATEFMT = "%Y/%m/%d-%H:%M:%S"

sys.set_int_max_str_digits(MAX_RESULT_LENGTH)

logging.basicConfig(
  handlers = [
    logging.StreamHandler()
  ],
  format=LOGFMT,
  datefmt=LOGDATEFMT,
  level=logging.INFO,
)

limiter = Limiter(keyfunc=default_keyfunc) # limits per IP
routes = web.RouteTableDef()

def calculate(expr: str) -> float:
  p = py_expression_eval.Parser()
  expression: py_expression_eval.Expression = p.parse(expr)
  result: float = expression.evaluate({})
  return result

@routes.post("/eval")
@limiter.limit(RATELIMIT)
async def post_eval(request: web.Request) -> web.Response:
  loop = asyncio.get_running_loop()

  try:
    expr: str = await request.text()
    client_ip = request.headers.get("X-Forwarded-For","UNK?")
    logging.info("got request from %s: %s", client_ip, expr)
    result = await loop.run_in_executor(None, calculate, expr)
    try:
      str(result)
    except ValueError:
      return web.Response(text=f"Result is over maximum digit length of {MAX_RESULT_LENGTH}!",status=400)
    return web.Response(text=str(result),content_type="text/plain")
  except:
    logging.exception("yikes")
    return web.Response(text="yikes",status=400)
  
app = web.Application()
app.add_routes(routes)
web.run_app(
  app,
  host=HOST,
  port=PORT,
  access_log=None
)