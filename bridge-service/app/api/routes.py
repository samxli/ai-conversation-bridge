"""Flask routes for chat-platform webhooks and health checks."""

import logging

from flask import Blueprint, current_app, jsonify, request

from app.config import Config
from app.core import async_runner
from app.core.messages import user_message_for
from app.core.response_validator import ResponseValidator
from app.orchestration.base import OrchestrationRequest

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


@bp.route('/')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "orchestrator": Config.ORCHESTRATOR,
        "ai_provider": Config.AI_PROVIDER,
        "chat_clients": ["lineworks", "dingtalk"],
    }), 200


def get_ai_response(user_text: str, session_id: str) -> str:
    """Invoke the configured orchestrator and validate the response."""
    orchestrator = current_app.extensions['orchestrator']
    timeout = float(current_app.extensions.get('orchestrator_timeout', Config.FLOWISE_TIMEOUT))
    result = async_runner.run_coroutine(
        orchestrator.invoke(OrchestrationRequest(message=user_text, session_id=session_id)),
        timeout=timeout + 30.0,
    )
    if result.failure is not None:
        logger.error(
            "Orchestration failure code=%s detail=%s",
            result.failure.value,
            result.detail,
        )
        return user_message_for(result.failure)

    return ResponseValidator.validate(
        str(result.text) if result.text else "",
        user_message=user_text,
    )


def message_too_long_response() -> str:
    """Return the user-facing error message for over-length messages."""
    return f"Your message is too long. Please keep it under {Config.MAX_MESSAGE_LENGTH} characters."


@bp.route('/callback', methods=['POST'])
@bp.route('/lineworks/callback', methods=['POST'])
def lineworks_callback():
    """Handle LINE WORKS message callbacks."""
    try:
        lw_client = current_app.extensions['lw_client']
        lineworks_adapter = current_app.extensions['lineworks_adapter']

        raw_body = request.get_data()
        signature = request.headers.get("X-WORKS-Signature", "")

        if not lineworks_adapter.verify_signature(raw_body, signature):
            current_app.logger.warning("Webhook signature verification failed")
            return 'Unauthorized', 401

        data = request.get_json(silent=True)
        if data is None:
            current_app.logger.warning("Invalid or empty JSON body")
            return 'Bad Request', 400

        current_app.logger.info(
            f"Received callback from user: {data.get('source', {}).get('userId', 'unknown')}"
        )

        message = lineworks_adapter.parse_inbound(data)
        if message is None:
            return 'OK', 200

        if lineworks_adapter.is_over_length(message):
            lw_client.send_message(message.reply_target, {
                "content": {
                    "type": "text",
                    "text": message_too_long_response()
                }
            })
            return 'OK', 200

        if not lw_client.validate_config():
            current_app.logger.error("Missing one or more LINE WORKS environment variables.")
            return 'Internal Server Error', 500

        ai_response_text = get_ai_response(message.text, session_id=message.session_id)

        reply_content = {
            "content": {
                "type": "text",
                "text": ai_response_text
            }
        }

        lw_client.send_message(message.reply_target, reply_content)
        current_app.logger.info(f"Sent reply to user {message.sender_id}")

        return 'OK', 200

    except Exception as e:
        current_app.logger.error(f"Error processing callback: {e}")
        return 'Internal Server Error', 500


@bp.route('/dingtalk/callback', methods=['POST'])
def dingtalk_callback():
    """Handle DingTalk HTTP-mode robot callbacks."""
    try:
        dingtalk_client = current_app.extensions['dingtalk_client']
        dingtalk_adapter = current_app.extensions['dingtalk_adapter']

        data = request.get_json(silent=True)
        if data is None:
            current_app.logger.warning("Invalid or empty DingTalk JSON body")
            return 'Bad Request', 400

        message = dingtalk_adapter.parse_inbound(data)
        if message is None:
            return 'OK', 200

        should_process, reason = dingtalk_adapter.should_process_payload(message, data)
        if not should_process:
            current_app.logger.info(reason)
            return 'OK', 200

        if dingtalk_adapter.is_over_length(message):
            current_app.logger.warning(
                f"DingTalk message from {message.sender_id} exceeds max length "
                f"({len(message.text)} > {Config.MAX_MESSAGE_LENGTH})"
            )
            dingtalk_client.send_text(message.reply_target, message_too_long_response())
            return 'OK', 200

        ai_response_text = get_ai_response(message.text, session_id=message.session_id)
        dingtalk_client.send_text(message.reply_target, ai_response_text)
        current_app.logger.info(f"Sent DingTalk reply to user {message.sender_id}")

        return 'OK', 200

    except Exception as e:
        current_app.logger.error(f"Error processing DingTalk callback: {e}")
        return 'Internal Server Error', 500
