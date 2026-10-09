# KANV --- AWS & DevOps Voice Assistant

KANV is a Flask-based web assistant that brings everyday assistant
commands and practical AWS/DevOps utilities into one simple interface.
It supports typed commands and browser-based voice interaction, with a
focus on learning and monitoring cloud infrastructure.

## Features

### Personal assistant

-   Voice input through the browser's Web Speech API, where supported.
-   Spoken responses through browser speech synthesis.
-   Date and time information.
-   Wikipedia lookups.
-   Open commonly used websites.
-   Jokes, public IP lookup, and assistant identity responses.
-   Typed input as an alternative to voice commands.

### AWS and DevOps utilities

-   View EC2 instance inventory and instance states using Boto3.
-   Retrieve EC2 CPU utilization metrics from Amazon CloudWatch.
-   List Docker containers through the Docker SDK for Python.
-   Check the Flask application's health.
-   Use a web dashboard to access the available assistant and monitoring
    features.

> AWS and Docker features require the relevant account permissions and
> runtime access. CloudWatch metrics may not be available for every
> instance or time range.

## Technology stack

-   Python
-   Flask
-   HTML, CSS, and JavaScript
-   Boto3 and Amazon CloudWatch
-   Docker SDK for Python
-   Browser Web Speech API and speech synthesis

## Project structure

``` text
KANV-Voice-Assistant/
├── app.py
├── requirements.txt
├── aws-readonly-policy.json
├── templates/
│   └── index.html
└── static/
    ├── script.js
    └── style.css
```

## Requirements

-   Python 3.10 or newer
-   A modern browser for the web interface; voice features depend on
    browser support
-   Docker installed and running if you want to use Docker container
    listing
-   AWS credentials configured if you want to use AWS monitoring
    features

## Run locally on Windows

Open PowerShell in the project directory.

1.  Create a virtual environment if you do not already have one:

    ``` powershell
    py -m venv .venv
    ```

2.  Activate it:

    ``` powershell
    .\.venv\Scripts\Activate.ps1
    ```

3.  Install the dependencies:

    ``` powershell
    python -m pip install -r requirements.txt
    ```

4.  Start the Flask application:

    ``` powershell
    python app.py
    ```

5.  Open the local URL printed by Flask in your browser. If the
    application uses the default Flask development settings, this is
    commonly `http://127.0.0.1:5000`.

Use the Flask development server for local development only. Configure a
production WSGI server and appropriate security settings before
deploying publicly.

## AWS configuration

KANV uses Boto3's standard credential provider chain. Configure
credentials using an AWS profile, environment variables, or an attached
IAM role when running on AWS. Do not put AWS access keys in source code
or commit them to GitHub.

For local development, an AWS CLI profile can be configured with:

``` powershell
aws configure
```

Check that the profile can access the AWS account and region you intend
to monitor. Set the appropriate AWS region in your environment or AWS
profile if needed.

The included `aws-readonly-policy.json` is a sample policy for the
read-only EC2 inventory and CloudWatch metric operations used by the
project. Review it against the actual code and your organization's
requirements before attaching it to an IAM identity. Grant only the
permissions required for your setup.

## Docker configuration

Docker container listing requires Docker to be installed and running on
the machine where the Flask backend executes. The Docker SDK
communicates with that Docker daemon; it does not automatically inspect
containers on a different computer or remote host.

## Security notes

-   Keep AWS credentials and other secrets out of source code,
    screenshots, logs, and public repositories.
-   Use least-privilege IAM permissions.
-   The sample AWS policy is intended for read-only monitoring, not for
    starting, stopping, or deleting infrastructure.
-   Do not expose the development server directly to the public
    internet.
-   Before deployment, review authentication, authorization, input
    validation, logging, and network access.

## Current scope

KANV currently combines assistant commands with basic AWS and Docker
monitoring utilities. A documentation-grounded AI knowledge base,
retrieval-augmented generation (RAG), automated remediation, and broader
CI/CD integrations are possible future extensions and are not described
as existing features here.

## License

No license has been specified yet. Add a `LICENSE` file before
presenting this repository as open source.
