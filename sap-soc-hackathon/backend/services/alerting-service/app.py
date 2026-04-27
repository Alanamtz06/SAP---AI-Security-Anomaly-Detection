# HOW TO TEST LOCALLY:
# 1. pip install -r requirements.txt
# 2. Create .env with HANA_PASS and SAP_API_KEY
# 3. python app.py

import logging
import os
import signal
import sys
from types import FrameType
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from alerter import AlertingService

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("soc.alerting")


def _main() -> None:
    if not os.environ.get("SAP_API_KEY"):
        log.error("SAP_API_KEY not set — aborting")
        sys.exit(1)

    service = AlertingService()

    def _sigterm(_signum: int, _frame: Optional[FrameType]) -> None:
        log.info("SIGTERM received — shutting down")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sigterm)

    log.info("SOC Alerting Service starting...")
    service.run()


if __name__ == "__main__":
    _main()
