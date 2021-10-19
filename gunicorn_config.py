import os
import sys
import traceback

import gunicorn
from gds_metrics.gunicorn import child_exit  # noqa

workers = 4
worker_class = "eventlet"
bind = "0.0.0.0:{}".format(os.getenv("PORT"))
gunicorn.SERVER_SOFTWARE = 'None'


def worker_abort(worker):
    worker.log.info("worker received ABORT")
    for stack in sys._current_frames().values():
        worker.log.error(''.join(traceback.format_stack(stack)))
