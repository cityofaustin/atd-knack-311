#!/usr/bin/env python
import argparse
import logging
import os
import sys
import time

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

# get abs path to various xml template and certs
abs_dirname = os.path.abspath(os.path.join(__file__, os.pardir))
template_filename = os.path.join(abs_dirname, "message_template.xml")
cert_filename = os.path.join(abs_dirname, "certs", "esb.cert")
key_filename = os.path.join(abs_dirname, "certs", "esb.pem")


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


def get_record_filter(*, fields):
    """Constructs a knack filter object to fetch activities that need to be sent to 311

    Args:
        fields (dict): A dict of fields from config.py which map to knack field
            identifiers.

    Returns:
        dict: A dict of Knack filter properties
    """
    filters = {
        "match": "and",
        "rules": [
            {"field": fields["emi_id"], "operator": "is not blank"},
            {
                "field": fields["esb_status"],
                "operator": "is",
                "value": "READY_TO_SEND",
            },
        ],
    }
    return filters


def build_template_dict(*, record, fields, activity_codes):
    """Prepares the data that will populate the xml message template.

    Args:
        record (dict): A knack record
        fields (dict): A dict of fields from config.py which map to knack field
            identifiers.
        activity_codes (dict): A dict of activity names from config.py which map to
            CSR activity codes.

    Returns:
        dict: a dict of data that is ready feed into the xml message template
    """
    template_dict = {name: record[field_id] or "" for name, field_id in fields.items()}
    activity_details = template_dict["activity_details"] or ""
    activity_details = encode_to_ascii(activity_details)
    activity_details = encode_special_chars(activity_details)
    template_dict["activity_details"] = activity_details

    if not template_dict["csr_activity_code"]:
        # only paging activites have a CSR activity code
        # otherwise we need to fetch it from our lookup conifg
        activity_name = template_dict["activity_name"]
        try:
            template_dict["csr_activity_code"] = activity_codes[activity_name] or ""
        except KeyError:
            raise ValueError(
                f"Activity name has no corresponding activity type code in 311 CSR: {activity_name}"
            )

    """311 and Knack to do not agree on what counts as a duplicate issue. This is because
    311 CSR has a built-in system for flagging dupe SRs based on the SR location. However,
    that dupe filter is not always effective because residents often report the same issue
     at a slightly different address. This would most commonly happen at a frontage road
      intersection where there are intersections controlled by two cabinets.
      
    Per 311, if we want to flag a duplicate issue we must use the "closed resolved" status,
    which closes the issue in 311 like a non-dupe. We do want to track this issue as a dupe
    within Knack.
    
    TLDR we must override the dupe status in knack before we sent the issue to 311. If we
    send a dupe status to 311 it will break CSR."""
    if template_dict["issue_status_code_snapshot"] == "closed_duplicate":
        template_dict["issue_status_code_snapshot"] = "closed_resolved"

    template_dict["publication_datetime"] = arrow.now().isoformat()
    return template_dict


def build_xml_payload(template_dict):
    """Populates the xml message template with record values

    Returns:
        str: a stringifed XML document with the record's data
    """
    with open(template_filename, "r") as fin:
        template = fin.read()
        return template.format(**template_dict)


def init_logger(log_level=logging.INFO):
    """Returns a module logger that streams to stdout"""
    logger = logging.getLogger("send_esb_message")
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(fmt=" %(name)s.%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def sort_by_activity_id(records, activity_id_field):
    """Sort records by the atd_activity_id field. This ensures
    that records are sent in the order they are created. We could also
    use the `modified_date` field, but Knack timestamps have minute
    precision, which is not granular enough. It is currently not
    possible to modify activities in the Knack UI, so we take
    that as a guarantee that the activity IDs lowest to highest
    are oldest to most recently updated.

    Although we can also specify the record sort order in the Knack
    table view, this method is an extra assurance that we're
    handling them in the right order.

    Args:
        records (list): list of CSR activity knackpy.Record objects

    Returns:
        list of records sorted by atd_activity_id
    """
    return sorted(records, key=lambda d: d[activity_id_field])


def send_message(*, message, endpoint, timeout=20, max_retries=3):
    """Sends an xml message to the enterprise service bus.

    Args:
        message (str): the stringified xml message
        endpoint (str): the ESB endpoint url
        timeout (int, optional): the connection timeout in seconds
        max_retries (int, optiona, default: 3): # of times to retry the request
            if a `500` error is received

    Returns:
        None

    Raises:
        HTTP exception on `400` or `500` response status codes.
        ConnectionError on DNS error
        Timeout if request timeout is exceeded
    """
    headers = {"content-type": "text/xml"}
    tries = 1
    while True:
        res = requests.post(
            endpoint,
            data=message,
            headers=headers,
            timeout=timeout,
            verify=False,
            cert=(cert_filename, key_filename),
        )
        if res.status_code == 500 and tries < max_retries:
            tries += 1
            time.sleep(2)
            continue
        res.raise_for_status()
        break


def get_update_record_payload(*, record_id, status_field, status_text):
    """Prepare a Knack record dict to update activity status as 'SENT' or 'DO_NOT_SEND'."""
    payload = {"id": record_id, status_field: status_text}
    return payload


def main(app_name):
    logger.info(f"Processing Knack > 311 messages for app: {app_name}")

    config = CONFIG[app_name]

    filters = get_record_filter(fields=config["fields"])

    logger.info(f"Initializing knackpy.App...")

    app = knackpy.App(app_id=KNACK_APP_ID, api_key=KNACK_API_KEY)

    logger.info(f"Fetching records...")

    records = app.get(config["view"], filters=filters)

    logger.info(f"{len(records)} records to process.")

    records = sort_by_activity_id(records, config["fields"]["atd_activity_id"])

    if not records:
        return

    for record in records:
        record_formatted = record.format(keys=False)

        template_dict = build_template_dict(
            record=record_formatted,
            fields=config["fields"],
            activity_codes=config["activity_codes"],
        )

        if template_dict["csr_activity_code"]:
            message = build_xml_payload(template_dict)

            logger.info(f"Sending payload {template_dict}")

            send_message(message=message, endpoint=ESB_ENDPOINT)

            logger.info(f"Updating Knack record {record['id']} with 'SENT' status")

            record_payload = get_update_record_payload(
                record_id=record["id"],
                status_field=config["fields"]["esb_status"],
                status_text="SENT",
            )
        else:
            # if there is no `csr_activity_code` the activity is to be ignored
            logger.info(
                f"Updating Knack record {record['id']} with 'DO_NOT_SEND' status"
            )
            record_payload = get_update_record_payload(
                record_id=record["id"],
                status_field=config["fields"]["esb_status"],
                status_text="DO_NOT_SEND",
            )

        app.record(data=record_payload, method="update", obj=config["obj"])


if __name__ == "__main__":
    args = cli_args()
    app_name = args.app_name
    logger = init_logger()
    main(app_name)
