import asyncio


async def run_coroutines_and_wait(coroutines):
    if not coroutines:
        return
    futures = []
    for coroutine in coroutines:
        futures.append(
            asyncio.ensure_future(coroutine()))
    done, pending = await asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)
    for future in done:
        if future.exception() is None:
            continue
        raise future.exception()


async def run_coroutine_groups_and_wait(*coroutine_groups):
    if not coroutine_groups:
        return

    for coroutines in coroutine_groups:
        await run_coroutines_and_wait(coroutines)
