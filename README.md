# atd-knack-311

![data-flow](docs/flow.png)

Integration scripts which manage communication between ATD's Knack apps and the City's 311 system.

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

## How it works

The Python script `send_esb_message.py` pushes data from Knack apps to the 311 CSR system. The data of concern are "activity" records which record actions taken by ATD staff in response to 311 service requests.

Each Knack app is configured with an object (aka table) that records these activities, and uses a status field to indicate if the record needs to be sent to 311.

`send_esb_message.py` fetches activity records from the Knack apps, transforms the data into an XML string, and posts the XML message to the CTM-managed Enterprise Service Bus (ESB). The ESB applies further transformations and sends the data to the 311 CSR system. If the script receives a successful response from the ESB, it takes the final step of updating the status of the activity record in Knack to prevent future processing.

## Run it

You must supply the name of a knack app (as defined in `config.py`) as a CLI argument.

```shell
$ python send_esb_message.py data-tracker
```

With Docker, you'll want to mount your local directory with certs and pass an environment file. 

```shell
docker run -it --rm --env-file env_file -v "$(pwd)":/app atddocker/atd-knack-311:production python send_esb_message.py data-tracker
```


### Docker CI

Any push to `main` or `production` will trigger a Github workflow to build and publish a new version of the Docker image to Docker Hub. The image will be tagged with the relevant branch name.
