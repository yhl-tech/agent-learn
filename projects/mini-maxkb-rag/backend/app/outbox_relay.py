"""
独立 Outbox Relay 进程入口。

运行：
    python -m app.outbox_relay
"""

import logging

from app.services.outbox_service import OutboxRelay


def main() -> None:
    """
    启动前台轮询循环，进程生命周期由外部进程管理器负责。

    该入口用于生产环境独立部署 Relay；开发环境也可以由 Web 进程启动内嵌
    Relay，但两种模式不能同时用于同一单机 SQLite 数据库。
    """

    logging.basicConfig(level=logging.INFO)
    OutboxRelay().run()


if __name__ == "__main__":
    main()
