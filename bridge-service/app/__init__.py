"""Flask application factory for the conversation bridge service."""

import logging

from flask import Flask

from app.channels.dingtalk.adapter import DingTalkAdapter
from app.channels.dingtalk.client import DingTalkClient
from app.channels.feishu.adapter import FeishuAdapter
from app.channels.feishu.client import FeishuClient
from app.channels.lineworks.adapter import LineWorksAdapter
from app.channels.lineworks.client import LineWorksClient
from app.config import Config
from app.core import async_runner
from app.orchestration.factory import create_orchestrator


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.debug = Config.DEBUG
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

    logging.basicConfig(level=logging.INFO)
    Config.validate_for_orchestrator()
    async_runner.start_background_loop()

    lw_client = LineWorksClient(Config)
    dingtalk_client = DingTalkClient()
    feishu_client = FeishuClient(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET)
    lineworks_adapter = LineWorksAdapter(lw_client, Config.MAX_MESSAGE_LENGTH)
    dingtalk_adapter = DingTalkAdapter(Config, Config.MAX_MESSAGE_LENGTH)
    feishu_adapter = FeishuAdapter(Config.FEISHU_VERIFICATION_TOKEN, Config.MAX_MESSAGE_LENGTH)
    orchestrator = create_orchestrator(Config)

    timeout = (
        Config.FLOWISE_TIMEOUT
        if Config.ORCHESTRATOR == "flowise"
        else Config.ORCHESTRATOR_TIMEOUT
    )

    app.extensions['lw_client'] = lw_client
    app.extensions['dingtalk_client'] = dingtalk_client
    app.extensions['feishu_client'] = feishu_client
    app.extensions['lineworks_adapter'] = lineworks_adapter
    app.extensions['dingtalk_adapter'] = dingtalk_adapter
    app.extensions['feishu_adapter'] = feishu_adapter
    app.extensions['orchestrator'] = orchestrator
    app.extensions['orchestrator_timeout'] = timeout

    from app.api.routes import bp
    app.register_blueprint(bp)

    return app
