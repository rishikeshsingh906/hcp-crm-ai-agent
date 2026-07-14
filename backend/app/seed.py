"""Run with: python -m app.seed"""
from app.database import Base, engine, SessionLocal
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

demo_hcps = [
    dict(name="Dr. Anjali Rao", specialty="Cardiology", institution="Manipal Hospital",
         email="anjali.rao@example.com", phone="+91-9800000001", preferred_channel="in_person",
         notes="Prefers morning visits. Interested in cardiac trial data."),
    dict(name="Dr. Vikram Shah", specialty="Endocrinology", institution="Apollo Clinic",
         email="vikram.shah@example.com", phone="+91-9800000002", preferred_channel="virtual",
         notes="Busy schedule, prefers 15-min virtual check-ins."),
    dict(name="Dr. Priya Menon", specialty="Oncology", institution="Fortis Hospital",
         email="priya.menon@example.com", phone="+91-9800000003", preferred_channel="conference",
         notes="Engages best at medical conferences."),
]

if db.query(models.HCP).count() == 0:
    for h in demo_hcps:
        db.add(models.HCP(**h))
    db.commit()
    print(f"Seeded {len(demo_hcps)} demo HCPs.")
else:
    print("HCPs already exist, skipping seed.")

db.close()
