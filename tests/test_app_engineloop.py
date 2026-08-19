import asyncio

from app.engineloop import EngineLoop


class TestEngineLoop:
    def test_submit_runs_coro_and_returns_result(self):
        loop = EngineLoop()
        loop.start()
        try:
            async def add(a, b):
                await asyncio.sleep(0.01)
                return a + b

            assert loop.submit(add(2, 3)).result(timeout=5) == 5
        finally:
            loop.stop()

    def test_stop_is_idempotent(self):
        loop = EngineLoop()
        loop.start()
        loop.stop()
        loop.stop()
