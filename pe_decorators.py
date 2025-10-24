import discord
import pe_global_objects as pe_global

from typing import Callable

from inspect import signature
from functools import wraps

import traceback
from rich.console import Console

console = Console(record=True)



def command(func: Callable):

    @wraps(func)
    async def phi(ctx, *args, **kwargs):

        channel = pe_global.bot.get_channel(pe_global.TESTING_CHANNEL_TO_ANNOUNCE)
        await channel.send(func.__name__)

        try:
            result = await func(ctx, *args, **kwargs)
            
        except Exception as exc:
            
            exception_name = exc.__class__.__name__
            await channel.send(exception_name)

            console.log(exc, traceback.format_exc())

            message = f"Could not process query because of a `{exception_name}` error, you can spam <@439143335932854272> and tell him he's a bad programmer. (If it's an `EulerRequestFail`, then a `/update` might solve the issue.)"
            return await ctx.respond(message)

        return result
    
    return phi