import argparse
import logging
import os
import sys

import arrow
import knackpy
import requests

from config import CONFIG

KNACK_APP_ID = os.getenv("KNACK_APP_ID")
KNACK_API_KEY = os.getenv("KNACK_API_KEY")
ESB_ENDPOINT = os.getenv("ESB_ENDPOINT")

#  invalid XLM characters to be encoded
SPECIAL_CHAR_LOOKUP = {
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
    "&": "&amp;",
}

TEMPLATE_FILENAME = "message_template.xml"


def cli_args():
    parser = argparse.ArgumentParser(
        description="Send 311 activty records from Knack to the Enterprise Service bus (ESB)"
    )
    parser.add_argument(
        "app_name",
        type=str,
        choices=["data-tracker", "signs-markings"],
        help="The name of Knack app which is the source for the message data",
    )
    return parser.parse_args()


def encode_to_ascii(text):
    """Encodes a text string to ASCII by dropping non-ASCII characters"""
    text = text.encode("ascii", errors="ignore")
    text = text.decode("ascii")
    return text


def encode_special_chars(text):
    """Encode special characters to ensure valid XML"""
    for char, replace_val in SPECIAL_CHAR_LOOKUP.items():
        text = text.replace(char, replace_val)
    return text


def get_record_filter(*, esb_status_match, fields):
    """Construct a knack filter object to fetch activities that need to be sent to 311"""
    filters = {
        "match": "and",
        "rules": [
            {"field": fields["emi_id"], "operator": "is not blank"},
            {
                "field": fields["esb_status"],
                "operator": "is",
                "value": esb_status_match,
            },
        ],
    }
    return filters


def build_template_dict(*, record, fields):
    template_dict = {name: record[field_id] for name, field_id in fields.items()}
    activity_details = template_dict["activity_details"] or ""
    activity_details = encode_to_ascii(activity_details)
    activity_details = encode_special_chars(activity_details)
    template_dict["activity_details"] = activity_details
    template_dict["publication_datetime"] = arrow.now().isoformat()
    return template_dict


def build_xml_payload(template_dict):
    with open(TEMPLATE_FILENAME, "r") as fin:
        template = fin.read()
        return template.format(**template_dict)


def init_logger(log_level=logging.INFO):
    """Return a module logger that streams to stdout"""
    logger = logging.getLogger("send_esb_message")
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(fmt=" %(name)s.%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def send_message(*, message, endpoint, timeout=20):
    """Sends an xml message to the enterprise service bus

    Args:
        message (str): the stringified xml message
        endpoint (str): the ESB endpoint url
        timeout (int, optional): the connection timeout in seconds

    Returns:
        None

    Raises:
        HTTP exception on `400` or `500` response status codes
    """
    headers = {"content-type": "text/xml"}

    res = requests.post(
        endpoint,
        data=message,
        headers=headers,
        timeout=timeout,
        verify=False,
        cert=("esb.cert", "esb.pem"),
    )

    res.raise_for_status()


def get_update_record_payload(*, record_id, status_field):
    """Prepare a Knack record dict to mark an activity recort as 'Sent'."""
    payload = {"id": record_id, status_field: "SENT"}
    return payload


def main(app_name):
    logger.info(f"Running ESB message util for app: {app_name}")
    config = CONFIG[app_name]

    filters = get_record_filter(
        esb_status_match=config["esb_status_match"], fields=config["fields"]
    )

    logger.info(f"Initializing knackpy.App...")
    app = knackpy.App(app_id=KNACK_APP_ID, api_key=KNACK_API_KEY)

    logger.info(f"Fetching records...")
    records = app.get(config["view"], filters=filters)

    logger.info(f"{len(records)} records to process.")

    if not records:
        return

    for record in records:
        # we Knackpy to format the record values, which takes care of date formatting for us
        record_formatted = record.format(keys=False)

        template_dict = build_template_dict(
            record=record_formatted, fields=config["fields"]
        )

        message = build_xml_payload(template_dict)

        send_message(message=message, endpoint=ESB_ENDPOINT)

        record_payload = get_update_record_payload(
            record_id=record.id, status_field=config["fields"]["esb_status"]
        )

        app.record(data=record_payload, method="update", obj=config["obj"])
        breakpoint()

    breakpoint()


if __name__ == "__main__":
    args = cli_args()
    app_name = args.app_name
    logger = init_logger()
    main(app_name)
