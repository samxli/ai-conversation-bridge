"""Flask application factory for the conversation bridge service."""

import logging

from flask import Flask

from app.channels.dingtalk.adapter import DingTalkAdapter
from app.channels.dingtalk.client import DingTalkClient
from app.channels.lineworks.adapter import LineWorksAdapter
from app.channels.lineworks.client import LineWorksClient
from app.config import Config
from app.orchestration.direct_llm.client import OpenRouterClient
from app.orchestration.flowise.client import FlowiseClient


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.debug = Config.DEBUG
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

    logging.basicConfig(level=logging.INFO)

    lw_client = LineWorksClient(Config)
    dingtalk_client = DingTalkClient()
    lineworks_adapter = LineWorksAdapter(lw_client, Config.MAX_MESSAGE_LENGTH)
    dingtalk_adapter = DingTalkAdapter(Config, Config.MAX_MESSAGE_LENGTH)

    if Config.AI_PROVIDER == 'openrouter':
        logging.getLogger(__name__).info("Using OpenRouter as chat provider (demo/experiment)")
        ai_client = OpenRouterClient(
            Config.OPENROUTER_API_KEY,
            Config.OPENROUTER_MODEL,
            Config.OPENROUTER_API_URL,
            Config.OPENROUTER_SYSTEM_PROMPT,
            Config.OPENROUTER_REASONING_EFFORT
        )
    else:
        logging.getLogger(__name__).info("Using Flowise as chat provider")
        ai_client = FlowiseClient(
            Config.FLOWISE_API_URL,
            Config.FLOWISE_API_KEY,
            Config.FLOWISE_TIMEOUT
        )

    app.extensions['lw_client'] = lw_client
    app.extensions['dingtalk_client'] = dingtalk_client
    app.extensions['lineworks_adapter'] = lineworks_adapter
    app.extensions['dingtalk_adapter'] = dingtalk_adapter
    app.extensions['ai_client'] = ai_client

    from app.api.routes import bp
    app.register_blueprint(bp)

    return app
