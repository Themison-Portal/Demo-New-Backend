import subprocess
import json
import sys

def main():
    try:
        # Run gcloud command
        cmd = [
            "gcloud", "logging", "read",
            'resource.type="cloud_run_revision" AND resource.labels.service_name="core-backend-eu" AND severity>="ERROR"',
            "--limit", "30",
            "--format", "json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse JSON
        logs = json.loads(result.stdout)
        
        if not logs:
            print("No ERROR logs found.")
            return

        for log in logs:
            time = log.get("timestamp")
            
            # Extract textPayload or jsonPayload message
            message = ""
            if "textPayload" in log:
                message = log["textPayload"]
            elif "jsonPayload" in log:
                payload = log["jsonPayload"]
                message = payload.get("message", str(payload))
            
            print(f"[{time}] ERROR: {message.strip()}")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    main()
