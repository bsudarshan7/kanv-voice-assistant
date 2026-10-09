# KANV — Python Voice Assistant Web App

A local Flask web application adapted from the uploaded `kiki` / `MAIN VAI` Python scripts. The UI uses a modern dark theme, browser speech recognition, browser text-to-speech, and a typed-command fallback.

## Requirements

- Windows 11
- Python 3.10 or newer
- Google Chrome or Microsoft Edge for voice input
- Internet connection for Wikipedia, public-IP lookup, browser speech recognition, and AWS API calls
- AWS CLI configured with a least-privilege profile for EC2/CloudWatch read-only access (optional)
- Docker Desktop (optional; required only for local container checks)

## Run it on Windows 11

1. Extract the ZIP file to a folder such as `C:\Users\YourName\Documents\KANV-Voice-Assistant`.
2. Open that folder in File Explorer. Click the address bar, type `cmd`, and press Enter.
3. Create a virtual environment:

   ```bat
   py -m venv .venv
   ```

4. Activate it:

   ```bat
   .venv\Scripts\activate
   ```

5. Update pip and install dependencies:

   ```bat
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Start the Flask app:

   ```bat
   python app.py
   ```

7. (Optional, for AWS monitoring) Configure an AWS CLI profile as described in the AWS setup section below. Set the profile and region in the same terminal before starting KANV.
8. Open `http://127.0.0.1:5000` in Chrome or Edge. Keep the terminal open while using KANV. Press the microphone button and allow microphone access, or type a command in the input box.
9. Stop the server with `Ctrl+C` in the terminal.

## Supported commands

- `What is the time` / `What is the date`
- `Tell me a joke`
- `Search Python Flask` (Google results link)
- `Wikipedia Ada Lovelace` or `Search Wikipedia for machine learning` (short summary plus a Wikipedia link)
- `Open YouTube`, `Open Google`, `Open Gmail`, `Open Stack Overflow`
- `Open dictionary resilience`
- `IP address`
- `Who are you` / `Who created you`
- `Check KANV health` — local Flask endpoint health check
- `List EC2 instances` / `AWS instances` — lists EC2 instances in the configured region (AWS setup required)
- `AWS CPU for i-0123456789abcdef0` — average CloudWatch CPU utilization for the last hour (replace with your real instance ID)
- `Check Docker containers` — lists running and stopped local containers (Docker Desktop required)

Commands can be spoken or typed. Web actions return a link for you to click; the app does not automatically open a new tab after an asynchronous request.

## What changed from the original scripts

- Reused the original command ideas for time, date, Wikipedia, websites, jokes, public IP, and assistant identity.
- Replaced desktop `pyttsx3` output with browser `speechSynthesis`, and replaced server-side `speech_recognition` microphone access with the browser Web Speech API. A Flask server cannot directly listen to the visitor's browser microphone.
- Removed the hard-coded WhatsApp recipient/message. No message is sent.
- Removed hard-coded local music and VS Code paths, because those paths may not exist on another Windows account and a web app should not launch local programs or files without an explicit, safe desktop integration.
- Fixed the original uninitialized recognition-result problem by using browser recognition events, and consolidated the duplicate time handler.
- Added error handling for Wikipedia and IP lookup, a 500-character command limit, and a typed-input fallback.

## Notes and safety

- This app is intended for local use on your own computer. It binds to `127.0.0.1`, not all network interfaces.
- Do not change the server to publicly accessible hosting without adding authentication, rate limiting, and appropriate security controls.
- Browser voice recognition may send audio to the browser vendor's speech service; check your browser's privacy settings. Typed commands are sent to your local Flask app.
- The public-IP command makes a request to `https://api.ipify.org`.
- The included Flask debug server is for development only. Do not use it as a production server.

## AWS monitoring setup (optional)

KANV uses Boto3's standard credential provider chain. It does not collect, save, or ask for AWS access keys in the webpage. Use a dedicated IAM identity/profile with only the permissions you need.

1. Confirm AWS CLI is installed by running `aws --version`.
2. Create/use a dedicated IAM identity and attach the read-only policy in `aws-readonly-policy.json` (or a stricter equivalent). The policy allows only `ec2:DescribeInstances` and `cloudwatch:GetMetricStatistics`; it does not allow starting, stopping, deleting, or modifying EC2 resources.
3. Configure a local profile in Command Prompt:

   ```bat
   aws configure --profile kanv-readonly
   set AWS_PROFILE=kanv-readonly
   set AWS_REGION=ap-south-1
   ```

   Enter credentials only into the trusted AWS CLI prompt. Never paste them into chat, HTML, JavaScript, or `app.py`. If you use another region, replace `ap-south-1`.
4. Start KANV from that same terminal using `python app.py`.
5. Click **AWS EC2 instances**. If your instances are in a different region, change `AWS_REGION` and restart the app.
6. To query CPU, copy an instance ID from the list and type a command such as `AWS CPU for i-0123456789abcdef0`. EC2 CPU metrics can be absent for stopped/new instances or if the selected region/instance ID is wrong.

AWS API usage may incur normal service charges in some circumstances. The app only calls read-only describe/metric APIs. See the official [Boto3 EC2 guide](https://docs.aws.amazon.com/boto3/latest/guide/ec2-example-managing-instances.html) and [CloudWatch metric API reference](https://docs.aws.amazon.com/boto3/latest/reference/services/cloudwatch/metric/get_statistics.html).

## Docker monitoring setup (optional)

1. Install and start Docker Desktop for Windows.
2. Wait until Docker Desktop reports that the engine is running.
3. Start KANV from the same Windows account. Click **Docker containers** or type `Check Docker containers`.
4. If the SDK cannot connect, run `docker ps -a` in Command Prompt to confirm Docker is working, then restart KANV.

KANV uses Docker's Python SDK only to list container metadata. It does not run shell commands or start, stop, delete, or modify containers. See the [Docker SDK documentation](https://docs.docker.com/reference/api/engine/sdk/).

## API endpoints added

- `GET /api/devops/health` — local app health
- `GET /api/devops/aws/instances` — EC2 instance metadata (AWS credentials and region required)
- `GET /api/devops/aws/cpu?instance_id=i-...` — CloudWatch CPU average over the last hour
- `GET /api/devops/docker/containers` — local Docker container metadata

These endpoints are intended for local development. Before any remote deployment, add authentication, authorization, rate limiting, CSRF protections where relevant, and production hosting. Do not expose this development app to the public internet as-is.
