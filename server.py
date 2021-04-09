import asyncio
import logging
import os
import signal
import threading
from datetime import datetime
from types import FrameType
from typing import Coroutine, List

HANDLED_SIGNALS = (
    signal.SIGINT,  # unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # unix signal 15. Sent by `kill <pid>`.
)

logger = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.started = False
        self.should_exit = False
        self.force_exit = False

    def run(self, hooks: List[Coroutine] = None):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.serve(hooks))

    async def serve(self, hooks: List[Coroutine] = None):
        process_id = os.getpid()
        self.install_signal_handlers()

        await self.startup(process_id)
        if self.should_exit:
            return

        await self.main_loop()

        if hooks:
            # asyncio.create_task(hk)
            # for hk in hooks:
            # asyncio.run_coroutine_threadsafe()
            # asyncio.create_task
            # TODO
            pass

        await self.shutdown(process_id)

    async def startup(self, process_id: int):
        logger.info(f"Started server [{process_id}]")

        logger.info("Server is running (Press CTRL+C to quit)")

        self.started = True

    async def main_loop(self):
        counter = 0
        should_exit = await self.on_tick(counter)
        while not should_exit:
            counter += 1
            counter = counter % 864000
            await asyncio.sleep(0.1)  # 10 ticks/s
            should_exit = await self.on_tick(counter)

    async def on_tick(self, counter: int) -> bool:

        # log a debug message every 5 seconds
        if counter % 50 == 0:
            logger.debug(f"Server running at: {datetime.utcnow()}")

        # do other cool stuff here

        # determine if we should exit
        if self.should_exit:
            return True
        return False

    async def shutdown(self, process_id: int) -> None:
        logger.info(f"Shutting down {self.force_exit=}")

        # get all of those yummy tasks
        tasks = asyncio.gather(*asyncio.all_tasks())

        # if tasks are pending, ask them to please cut it out.
        if tasks and not self.force_exit:
            msg = "Waiting for background tasks to complete. (CTRL+C to force quit)"
            logger.info(msg)

            try:
                tasks.cancel()
                # sleep to give the loop a chance to apply cancellations
                await asyncio.sleep(0.1)
            except asyncio.CancelledError as ce:
                logging.debug(f"Cancelled background tasks on exit: {ce}")

        asyncio.get_running_loop().stop()
        logger.info(f"Server process finished [{process_id}]")
        # sys.exit(1)

    def install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            # signals can only be listened to from the main thread
            return

        loop = asyncio.get_event_loop()

        for sig in HANDLED_SIGNALS:
            loop.add_signal_handler(sig, self.handle_exit, sig, None)

    def handle_exit(self, sig: int, frame: FrameType) -> None:
        logger.debug("Received exit signal")
        if self.should_exit:
            # force exit on second signal received
            self.force_exit = True
        else:
            # register first signal shutdown signal recieved
            self.should_exit = True


if __name__ == "__main__":
    logging.basicConfig()
    Server().run()
