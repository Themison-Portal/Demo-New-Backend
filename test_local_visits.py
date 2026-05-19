import httpx
import uuid
import datetime

BASE_URL = "http://localhost:8080"

def test_visit_workflow():
    # 1. Get a trial ID and patient ID from the seed data
    # (Assuming we have some test data)
    print("Listing trials...")
    resp = httpx.get(f"{BASE_URL}/api/trials")
    if resp.status_code != 200:
        print(f"Failed to list trials: {resp.text}")
        return
    
    trials = resp.json()
    if not trials:
        print("No trials found. Seed data might be missing.")
        return
    
    trial_id = trials[0]['id']
    print(f"Using Trial ID: {trial_id}")

    # 2. Get a patient
    print("Listing trial patients...")
    resp = httpx.get(f"{BASE_URL}/api/trial-patients")
    patients = resp.json()
    if not patients:
        print("No patients found.")
        return
    patient_id = patients[0]['patient_id']
    print(f"Using Patient ID: {patient_id}")

    # 3. Create a visit
    print("Creating a visit...")
    visit_data = {
        "patient_id": patient_id,
        "trial_id": trial_id,
        "doctor_id": str(uuid.uuid4()), # This will probably fail if doctor doesn't exist
        "visit_date": str(datetime.date.today()),
        "visit_type": "screening",
        "status": "scheduled"
    }
    
    # We might need to get a real doctor ID first
    resp = httpx.get(f"{BASE_URL}/api/members")
    members = resp.json()
    if members:
        visit_data["doctor_id"] = members[0]['id']

    resp = httpx.post(f"{BASE_URL}/api/patient-visits/", json=visit_data)
    if resp.status_code != 201:
         print(f"Failed to create visit: {resp.text}")
         return
    
    visit = resp.json()
    visit_id = visit['id']
    print(f"Created Visit ID: {visit_id}")

    # 4. List activities (should be empty if we haven't added any)
    print("Listing visit activities...")
    resp = httpx.get(f"{BASE_URL}/api/patient-visits/{visit_id}/activities")
    print(f"Activities: {resp.json()}")

if __name__ == "__main__":
    try:
        test_visit_workflow()
    except Exception as e:
        print(f"Test crashed: {e}")
