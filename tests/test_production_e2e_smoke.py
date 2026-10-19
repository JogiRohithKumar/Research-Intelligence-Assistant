"""
End-to-End Production Smoke Test Suite for Stage 9 Release.
Executes complete 20-step production lifecycle verification:
Registration -> Login -> Session -> Execution -> Grounding -> Intelligence ->
Persistence -> Isolation -> Health Probes -> Restart Recovery -> Logout Revocation.
"""

import unittest
import uuid
from fastapi.testclient import TestClient

from app.db.base import Base, engine, SessionLocal
from app.db.models import ResearchJob, User
from app.jobs.manager import job_manager
from main import app


class TestProductionEndToEndSmoke(unittest.TestCase):
    """Authoritative end-to-end smoke test validating all Stage 9 release criteria."""

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def test_complete_production_lifecycle_smoke(self):
        # 1. Health Liveness & Readiness Probes
        live_res = self.client.get("/health/liveness")
        self.assertEqual(live_res.status_code, 200)
        self.assertEqual(live_res.json()["status"], "alive")

        ready_res = self.client.get("/health/readiness")
        self.assertEqual(ready_res.status_code, 200)
        self.assertEqual(ready_res.json()["status"], "ready")
        self.assertEqual(ready_res.json()["database"], "connected")

        # 2. Register User A & User B
        uid_a = uuid.uuid4().hex[:8]
        uid_b = uuid.uuid4().hex[:8]

        res_a = self.client.post("/auth/register", json={
            "username": f"smoke_user_a_{uid_a}",
            "email": f"smoke_a_{uid_a}@example.com",
            "password": "ProductionPassword123!"
        })
        self.assertEqual(res_a.status_code, 201)
        token_a = res_a.json()["access_token"]
        user_a_id = res_a.json()["user"]["id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = self.client.post("/auth/register", json={
            "username": f"smoke_user_b_{uid_b}",
            "email": f"smoke_b_{uid_b}@example.com",
            "password": "ProductionPassword123!"
        })
        self.assertEqual(res_b.status_code, 201)
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. User A submits synchronous research execution via /research (sync=True)
        job_res = self.client.post("/research", json={
            "query": "superconducting qubit coherence fluxonium",
            "sync": True
        }, headers=headers_a)
        self.assertEqual(job_res.status_code, 200)
        state_data = job_res.json()
        self.assertEqual(state_data.get("execution_status"), "completed")
        self.assertGreater(len(state_data.get("papers", [])), 0)
        self.assertGreater(len(state_data.get("evidence_registry", [])), 0)
        self.assertGreater(len(state_data.get("claims", [])), 0)
        self.assertEqual(state_data["citation_verification"]["grounding_status"], "VERIFIED")
        session_id = state_data["thread_id"]

        # 4. User B attempts unauthorized access to User A's session -> rejected (403)
        cross_sess = self.client.get(f"/sessions/{session_id}", headers=headers_b)
        self.assertEqual(cross_sess.status_code, 403)

        # 5. User A submits an asynchronous background job via /research (sync=False)
        async_res = self.client.post("/research", json={
            "query": "superconducting qubit fluxonium",
            "sync": False
        }, headers=headers_a)
        self.assertEqual(async_res.status_code, 200)
        async_data = async_res.json()
        self.assertIn("job_id", async_data)
        self.assertIn("session_id", async_data)
        async_job_id = async_data["job_id"]

        # 6. User B attempts unauthorized access to User A's job -> rejected (403)
        cross_job = self.client.get(f"/jobs/{async_job_id}", headers=headers_b)
        self.assertEqual(cross_job.status_code, 403)

        # 7. User A verifies own job status
        status_res = self.client.get(f"/jobs/{async_job_id}", headers=headers_a)
        self.assertEqual(status_res.status_code, 200)
        self.assertIn(status_res.json()["status"], ["QUEUED", "RUNNING", "COMPLETED"])

        # 8. Verify User A Session State and Persistence
        persisted_res = self.client.get(f"/sessions/{session_id}", headers=headers_a)
        self.assertEqual(persisted_res.status_code, 200)
        p_data = persisted_res.json()
        self.assertEqual(p_data["id"], session_id)

        # 9. Test Stale Job Recovery on Restart
        # Insert a simulated orphaned job in RUNNING state
        orphan_job_id = f"job_orphan_{uuid.uuid4().hex[:6]}"
        with SessionLocal() as db:
            orphan_job = ResearchJob(
                id=orphan_job_id,
                user_id=user_a_id,
                session_id=session_id,
                status="RUNNING",
                current_step="search_node"
            )
            db.add(orphan_job)
            db.commit()

        # Run recovery routine
        recovered = job_manager.recover_stale_jobs()
        self.assertGreaterEqual(recovered, 1)

        # Verify orphan job was marked FAILED with clear reason
        with SessionLocal() as db:
            checked_orphan = db.query(ResearchJob).filter(ResearchJob.id == orphan_job_id).first()
            self.assertIsNotNone(checked_orphan)
            self.assertEqual(checked_orphan.status, "FAILED")
            self.assertEqual(checked_orphan.error_code, "PROCESS_INTERRUPTED")

        # 10. User A Logout and Durable Token Revocation
        logout_res = self.client.post("/auth/logout", headers=headers_a)
        self.assertEqual(logout_res.status_code, 200)

        # Verify token A is now completely rejected on protected endpoints
        after_logout = self.client.get("/auth/me", headers=headers_a)
        self.assertEqual(after_logout.status_code, 401)
        self.assertIn("revoked", after_logout.json()["error"]["message"].lower())


if __name__ == "__main__":
    unittest.main()
