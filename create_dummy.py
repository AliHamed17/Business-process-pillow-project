import pandas as pd
import numpy as np

# Create synthetic data to simulate patients-log.csv
data = {
    "patient": ["P1", "P1", "P1", "P2", "P2", "P3", "P3", "P3", "P3", "P4", "P4", "P5", "P5", "P5", "P5", "P6", "P6"],
    " action": [
        "Registration", "Triage", "Surgery",
        "Registration", "Consultation",
        "Registration", "Triage", "X-Ray", "Discharge",
        "Registration", "Surgery",
        "Registration", "Triage", "Consultation", "Surgery",
        "Registration", "Discharge"
    ],
    " DateTime": [
        "2024-01-01 10:00:00", "2024-01-01 11:00:00", "2024-01-02 09:00:00",
        "2024-01-01 08:00:00", "2024-01-01 09:30:00",
        "2024-01-03 12:00:00", "2024-01-03 12:30:00", "2024-01-03 13:00:00", "2024-01-04 10:00:00",
        "2024-01-05 07:00:00", "2024-01-05 15:00:00",
        "2024-01-06 09:00:00", "2024-01-06 09:15:00", "2024-01-06 10:00:00", "2024-01-07 08:00:00",
        "2024-01-08 11:00:00", "2024-01-08 11:30:00"
    ],
    " org:resource": ["Dr. A", "Nurse B", "Dr. C", "Dr. A", "Dr. B", "Dr. A", "Nurse B", "Tech C", "Dr. A", "Dr. B", "Dr. C", "Dr. A", "Nurse B", "Dr. B", "Dr. C", "Dr. A", "Dr. A"]
}

df = pd.DataFrame(data)
df.to_csv("patients-log.csv", index=False)
print("Created dummy patients-log.csv")
