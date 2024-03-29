# atd-knack-311

![data-flow](docs/flow.png)

This repository holds a single script which manage data flow from Knack apps to 311 CSR system. 

A separate repository, [atd-knack-proxy](https://github.com/cityofaustin/atd-knack-proxy), handles data flow from 311 to Knack apps.

The script works by fetching "activity" record updates from Knack apps, translating them into an XML messages, and posting them to the City's Enterprise Service Bus (ESB), which in turn sends the messages on to the 311 CSR system.

The script currently supports two Knack apps: the AMD Data Tracker and the Signs & Markings app. Additional apps can be added, provided they are configured in a similar fashion [docs needed].

## Configuration

### Environment

It is possible to run end-to-end tests of all systems involved in the Knack <> 311 integration. The test system credentials are available in our password store and include additional documentation.

The following environment variables are required.

- `KNACK_APP_ID`: the Knack application ID
- `KNACK_API_KEY`: the Knack API key
- `ESB_ENDPOINT`: the URL of the Enterprise Service Bus

### Certificates

A self-signed certificate and key must be present in the project's root directory and saved as `esb.cert` and `esb.pem` respectively.

### Field Mappings (`config.py`)

Each Knack app must have an entry in `config.py` which provides metadata that will be used to translate Knack records into the XML message payload.

| property name | sample value | definition 
|-|-|-
`obj` | `object_75` | knack object which stores the activity records
`view` | `view_1653` | knack view which exposes the activity records to be processed
`fields` | | dict of field mappings where each key is a variable in the XML template and each value is a knack field identifier
`fields.id` | `id` |  the built-in knack ID field - value is always `id`
`fields.emi_id` | `field_1868` | the EMI identifier field. this is an ESB message ID field that should be present in every Knack app integrated with 311.
`fields.sr_number` | `field_1232` | The service request ID string
`fields.issue_status_code_snapshot` | `field_1874` | field which captures the status current status string of the service request
`fields.esb_status` | `field_1860` | captures the processing status of the activity record. records with a value of `READY_TO_SEND` will be processed.
`fields.activity_datetime` | `field_1054` | an ISO timestamp indicating the datetime the activity occured
`fields.activity_details` | `field_1055` | text description of the activity
`fields.activity_name` | `field_1053` | a unique text string the type of activity
`fields.csr_activity_id`| `field_4299` | the unique ID of this activity in the CSR system. this number is provided by 311 and included in pagincg activity records which are created in Knack through the CSR integration. this ID must be included in the message payload in order to close/update an existing activity. I.e. it is necessary to complete paging activities in CSR.

## How it works

The Python script `send_knack_messages_to_esb.py` pushes data from Knack apps to the 311 CSR system. The data of concern are "activity" records which record actions taken by ATD staff in response to 311 service requests.

Each Knack app is configured with an object (aka table) that records these activities, and uses a status field to indicate if the record needs to be sent to 311.

`send_knack_messages_to_esb.py` fetches activity records from the Knack apps, transforms the data into an XML string, and posts the XML message to the CTM-managed Enterprise Service Bus (ESB). The ESB applies further transformations and sends the data to the 311 CSR system. If the script receives a successful response from the ESB, it takes the final step of updating the status of the activity record in Knack to prevent future processing.

## Run it

You must supply the name of a knack app (as defined in `config.py`) as a CLI argument.

```shell
$ python send_knack_messages_to_esb.py data-tracker
```

With Docker, you'll want to mount your local directory with certs and pass an environment file. 

```shell
docker run -it --rm --env-file env_file -v "$(pwd)":/app atddocker/atd-knack-311:production python send_knack_messages_to_esb.py data-tracker
```


### Docker CI

Any push to `main` or `production` will trigger a Github workflow to build and publish a new version of the Docker image to Docker Hub. The image will be tagged with the relevant branch name.
