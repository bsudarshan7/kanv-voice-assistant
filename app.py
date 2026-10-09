from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote_plus

import requests
import wikipedia
import pyjokes
from flask import Flask, jsonify, render_template, request

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:  # Keep the basic assistant usable if optional cloud packages are absent.
    boto3 = None
    BotoCoreError = type("BotoCoreError", (Exception,), {})
    ClientError = type("ClientError", (Exception,), {})
    NoCredentialsError = type("NoCredentialsError", (Exception,), {})

try:
    import docker
except ImportError:
    docker = None

app = Flask(__name__)
ASSISTANT_NAME = "KANV"

# Wikipedia can occasionally fail for ambiguous or unavailable topics. Keep the
# API response friendly instead of exposing a traceback to the browser.
def handle_command(raw_command: str) -> dict:
    command = " ".join((raw_command or "").strip().split())
    lowered = command.lower()

    if not command:
        return {"reply": "I didn't catch a command. Please try again."}

    # Read-only AWS and Docker commands. These never start, stop, delete, or modify resources.
    if any(phrase in lowered for phrase in ("list ec2", "ec2 instances", "aws instances", "list my instances", "check ec2")):
        result = get_ec2_instances()
        if not result["ok"]:
            return {"reply": result["message"]}
        instances = result["instances"]
        if not instances:
            return {"reply": f"I connected to AWS in region {result['region']}, but found no EC2 instances in this region."}
        lines = [f"AWS EC2 instances in {result['region']}: {len(instances)} found."]
        for item in instances[:8]:
            lines.append(f"{item['name']} — {item['instance_id']} — {item['state']} — {item['instance_type']}")
        return {"reply": " ".join(lines)}

    if any(phrase in lowered for phrase in ("docker containers", "list containers", "check docker", "docker status")):
        result = get_docker_containers()
        if not result["ok"]:
            return {"reply": result["message"]}
        containers = result["containers"]
        if not containers:
            return {"reply": "Docker is reachable, but no containers were found. Try starting Docker Desktop or creating a test container."}
        lines = [f"Docker reports {len(containers)} container(s)."]
        for item in containers[:8]:
            lines.append(f"{item['name']} — {item['status']} — image {item['image']}")
        return {"reply": " ".join(lines)}

    if any(phrase in lowered for phrase in ("kanv health", "app health", "health check", "check service health")):
        return {"reply": "KANV Flask application is responding. This is a local application health check; it does not verify external services."}

    if "cpu" in lowered and ("ec2" in lowered or "aws" in lowered):
        instance_id = None
        for token in command.split():
            if token.lower().startswith("i-"):
                instance_id = token
                break
        if not instance_id:
            return {"reply": "To check EC2 CPU, first list EC2 instances, then say: AWS CPU for i-xxxxxxxxxxxxxxxxx."}
        result = get_ec2_cpu(instance_id)
        if not result["ok"]:
            return {"reply": result["message"]}
        if result["average"] is None:
            return {"reply": f"CloudWatch returned no CPU datapoints for {instance_id} in the last hour. The instance may be stopped, newly launched, or in a different region."}
        return {"reply": f"The average EC2 CPU utilization for {instance_id} over the last hour is {result['average']:.1f} percent, based on available CloudWatch datapoints."}

    if lowered in {"hi", "hello", "hey", "hello kanv", "hi kanv"}:
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        return {"reply": f"{greeting}! I'm KANV. How can I help you?"}

    if "who are you" in lowered or "what is your name" in lowered:
        return {"reply": "I'm KANV, a Python voice assistant adapted from your original project and presented as a Flask web app."}

    if "who created you" in lowered:
        return {"reply": "I was adapted from the Python voice-assistant code supplied for this project."}

    if "the time" in lowered or lowered == "time" or "current time" in lowered:
        return {"reply": f"The time is {datetime.now().strftime('%I:%M %p')} ."}

    if "the date" in lowered or lowered == "date" or "today's date" in lowered or "today date" in lowered:
        return {"reply": f"Today's date is {datetime.now().strftime('%d %B %Y')} ."}

    if "tell me a joke" in lowered or lowered == "joke" or "make me laugh" in lowered:
        try:
            return {"reply": pyjokes.get_joke()}
        except Exception:
            return {"reply": "I couldn't fetch a joke just now. Please try again."}

    # Web actions are returned as links so the user deliberately chooses to open them.
    if "open youtube" in lowered or lowered == "youtube":
        return {"reply": "You can open YouTube using this link.", "action_url": "https://www.youtube.com", "action_label": "Open YouTube"}

    if "open stackoverflow" in lowered or "open stack overflow" in lowered:
        return {"reply": "You can open Stack Overflow using this link.", "action_url": "https://stackoverflow.com", "action_label": "Open Stack Overflow"}

    if "open mail" in lowered or "open gmail" in lowered:
        return {"reply": "You can open Gmail using this link.", "action_url": "https://mail.google.com", "action_label": "Open Gmail"}

    if "open google" in lowered and not lowered.startswith("open google and search"):
        return {"reply": "You can open Google using this link.", "action_url": "https://www.google.com", "action_label": "Open Google"}

    if "open dictionary" in lowered:
        term = command.lower().replace("open dictionary", "", 1).strip()
        if term:
            url = f"https://www.dictionary.com/browse/{quote_plus(term)}"
            return {"reply": f"Here is the dictionary page for {term}.", "action_url": url, "action_label": "Open dictionary entry"}
        return {"reply": "Tell me a word, for example: open dictionary resilience.", "action_url": "https://www.dictionary.com", "action_label": "Open Dictionary.com"}

    if "ip address" in lowered or lowered == "my ip":
        try:
            response = requests.get("https://api.ipify.org", timeout=5)
            response.raise_for_status()
            return {"reply": f"Your public IP address is {response.text.strip()}."}
        except requests.RequestException:
            return {"reply": "I couldn't retrieve your public IP address. Check your internet connection and try again."}

    # Search terms are treated as text and URL-encoded, never as executable commands.
    search_term = None
    if lowered.startswith("search wikipedia for "):
        search_term = command[len("search wikipedia for "):].strip()
    elif lowered.startswith("wikipedia "):
        search_term = command[len("wikipedia "):].strip()
    elif lowered.startswith("search "):
        search_term = command[len("search "):].strip()
    elif lowered.startswith("open google and search "):
        search_term = command[len("open google and search "):].strip()

    if search_term:
        if lowered.startswith("search wikipedia for ") or lowered.startswith("wikipedia "):
            try:
                summary = wikipedia.summary(search_term, sentences=2, auto_suggest=True)
                return {"reply": f"According to Wikipedia: {summary}", "action_url": f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(search_term)}", "action_label": "Open Wikipedia results"}
            except wikipedia.exceptions.DisambiguationError as exc:
                options = ", ".join(exc.options[:5])
                return {"reply": f"That topic has several meanings. Try a more specific search. Some options are: {options}.", "action_url": f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(search_term)}", "action_label": "Search Wikipedia"}
            except Exception:
                return {"reply": f"I couldn't retrieve a Wikipedia summary for {search_term}. You can still search for it here.", "action_url": f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(search_term)}", "action_label": "Search Wikipedia"}
        return {"reply": f"Here are Google search results for {search_term}.", "action_url": f"https://www.google.com/search?q={quote_plus(search_term)}", "action_label": "View Google results"}

    if any(word in lowered for word in ("play music", "open code", "send message", "send whatsapp")):
        return {"reply": "That action is not enabled in the web version. It previously depended on a hard-coded local file path, application path, or recipient. Those details were removed for safety. You can use the web links and supported commands here."}

    return {
        "reply": "I don't know that command yet. Try: time, date, tell me a joke, search cats, Wikipedia Ada Lovelace, open YouTube, open Google, open Gmail, open Stack Overflow, open dictionary resilience, or IP address."
    }


AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"


def _aws_clients():
    """Use boto3's standard credential chain; never ask for keys in the webpage."""
    if boto3 is None:
        raise RuntimeError("boto3 is not installed. Run: pip install -r requirements.txt")
    session = boto3.session.Session(region_name=AWS_REGION)
    return session.client("ec2"), session.client("cloudwatch")


def get_ec2_instances() -> dict:
    try:
        ec2, _ = _aws_clients()
        response = ec2.describe_instances()  # Read-only API operation.
        items = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                name = next((tag.get("Value", "") for tag in instance.get("Tags", []) if tag.get("Key") == "Name"), "Unnamed instance")
                items.append({
                    "name": name,
                    "instance_id": instance.get("InstanceId", "unknown"),
                    "state": instance.get("State", {}).get("Name", "unknown"),
                    "instance_type": instance.get("InstanceType", "unknown"),
                    "availability_zone": instance.get("Placement", {}).get("AvailabilityZone", "unknown"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                })
        return {"ok": True, "region": AWS_REGION, "instances": items}
    except Exception as exc:
        return {"ok": False, "message": _friendly_aws_error(exc)}


def get_ec2_cpu(instance_id: str) -> dict:
    if not instance_id.startswith("i-") or len(instance_id) < 8:
        return {"ok": False, "message": "That doesn't look like a valid EC2 instance ID. List instances and copy the ID beginning with i-."}
    try:
        _, cloudwatch = _aws_clients()
        end = datetime.now(timezone.utc)
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=end - timedelta(hours=1),
            EndTime=end,
            Period=300,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        averages = [point["Average"] for point in datapoints if "Average" in point]
        return {"ok": True, "average": sum(averages) / len(averages) if averages else None, "datapoints": len(averages)}
    except Exception as exc:
        return {"ok": False, "message": _friendly_aws_error(exc)}


def _friendly_aws_error(exc: Exception) -> str:
    name = type(exc).__name__
    if isinstance(exc, NoCredentialsError) or name == "NoCredentialsError":
        return "AWS credentials were not found. Configure a local AWS profile with `aws configure` or use an approved IAM role. Never paste access keys into KANV."
    if name in {"ProfileNotFound", "NoRegionError"}:
        return "AWS CLI profile or region is not configured. Set up an AWS profile and region, then restart KANV."
    if name in {"ClientError", "AccessDeniedException"} or hasattr(exc, "response"):
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "AWS error")
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
            return "AWS denied this read-only request. Check that your IAM identity has ec2:DescribeInstances and/or cloudwatch:GetMetricStatistics permissions."
        if code == "AuthFailure":
            return "AWS authentication failed. Check the configured AWS profile and account access."
        return f"AWS returned {code}. Check your configured region, credentials, and IAM permissions."
    if isinstance(exc, RuntimeError):
        return str(exc)
    return f"Could not query AWS ({name}). Confirm your AWS CLI profile, region, network, and IAM permissions."


def get_docker_containers() -> dict:
    if docker is None:
        return {"ok": False, "message": "Docker SDK is not installed. Run: pip install -r requirements.txt"}
    try:
        client = docker.from_env(timeout=4)
        containers = client.containers.list(all=True)  # Read-only list operation.
        result = []
        for container in containers[:50]:
            attrs = container.attrs or {}
            result.append({
                "name": (attrs.get("Name") or container.name or "unknown").lstrip("/"),
                "container_id": container.short_id,
                "image": ", ".join(tag for tag in (container.image.tags or [])[:2]) or container.image.short_id,
                "status": container.status,
            })
        client.close()
        return {"ok": True, "containers": result}
    except Exception as exc:
        name = type(exc).__name__
        if name in {"DockerException", "APIError", "NotFound"} or "docker" in str(exc).lower():
            return {"ok": False, "message": "Could not connect to Docker. Start Docker Desktop, wait until its engine is running, then retry. KANV only lists containers; it does not change them."}
        return {"ok": False, "message": f"Docker status check failed ({name}). Start Docker Desktop and try again."}


@app.get("/")
def index():
    return render_template("index.html", assistant_name=ASSISTANT_NAME)


@app.post("/api/command")
def command_api():
    payload = request.get_json(silent=True) or {}
    command_text = payload.get("command", "")
    if not isinstance(command_text, str):
        return jsonify({"reply": "Please send your command as text."}), 400
    if len(command_text) > 500:
        return jsonify({"reply": "Please keep commands under 500 characters."}), 400
    return jsonify(handle_command(command_text))


@app.get("/api/devops/health")
def devops_health_api():
    return jsonify({"ok": True, "service": "KANV Flask", "status": "healthy", "checked_at": datetime.now(timezone.utc).isoformat()})


@app.get("/api/devops/aws/instances")
def devops_aws_instances_api():
    result = get_ec2_instances()
    return jsonify(result), (200 if result["ok"] else 503)


@app.get("/api/devops/aws/cpu")
def devops_aws_cpu_api():
    instance_id = (request.args.get("instance_id") or "").strip()
    if not instance_id:
        return jsonify({"ok": False, "message": "Provide an instance_id query parameter."}), 400
    result = get_ec2_cpu(instance_id)
    return jsonify(result), (200 if result["ok"] else 503)


@app.get("/api/devops/docker/containers")
def devops_docker_containers_api():
    result = get_docker_containers()
    return jsonify(result), (200 if result["ok"] else 503)


if __name__ == "__main__":
    # Local development only. Do not expose this debug server directly to the internet.
    app.run(host="127.0.0.1", port=5000, debug=False)
