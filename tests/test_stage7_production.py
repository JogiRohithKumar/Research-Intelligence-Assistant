"""
Stage 7 Production Engineering Automated Verification Suite.
Validates authentication, multi-tenant isolation, authorization, input validation,
security headers, structured correlation logging, metrics, and error hygiene.
"""

import time
import unittest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from jose import jwt

from pydantic import ValidationError

from app.auth.security import hash_password
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, DatabaseError
from app.core.logging import SECRET_PATTERNS, SecretSanitizingFormatter
from app.core.metrics import metrics
from app.db.base import SessionLocal, get_engine, init_db
from app.db.checkpoint import get_checkpointer
from app.db.models import ReportModel, ResearchIterationModel, ResearchJob, ResearchRun, ResearchSession, User
from app.jobs.events import job_event_bus
from app.utils.stream_logger import emit_lifecycle_event
from main import app

settings = get_settings()


class TestStage7ProductionEngineering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Clean any leftover jobs from previous aborted runs
        cls.db.query(ResearchJob).delete()
        cls.db.commit()

        # Create distinct test tenants User A and User B
        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@academic.edu"
        cls.user_a_name = f"researcher_a_{uuid.uuid4().hex[:6]}"
        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@academic.edu"
        cls.user_b_name = f"researcher_b_{uuid.uuid4().hex[:6]}"
        cls.password = "ValidPassword123!"

        # Register User A
        res_a = cls.client.post("/auth/register", json={
            "username": cls.user_a_name,
            "email": cls.user_a_email,
            "password": cls.password
        })
        assert res_a.status_code == 201, f"Failed to register User A: {res_a.text}"
        data_a = res_a.json()
        cls.token_a = data_a["access_token"]
        cls.user_a_id = data_a["user"]["id"]

        # Register User B
        res_b = cls.client.post("/auth/register", json={
            "username": cls.user_b_name,
            "email": cls.user_b_email,
            "password": cls.password
        })
        assert res_b.status_code == 201, f"Failed to register User B: {res_b.text}"
        data_b = res_b.json()
        cls.token_b = data_b["access_token"]
        cls.user_b_id = data_b["user"]["id"]

    def setUp(self):
        """Clean up test tenant jobs between test cases to ensure fresh concurrency slots."""
        db = SessionLocal()
        try:
            db.query(ResearchJob).filter(
                ResearchJob.user_id.in_([self.user_a_id, self.user_b_id])
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        from app.jobs.manager import job_manager
        job_manager.shutdown(wait=True)
        cls.db.close()

    # -------------------------------------------------------------
    # 1. AUTHENTICATION TESTS
    # -------------------------------------------------------------

    def test_valid_user_login(self):
        """Verify valid user login succeeds and issues strict JWT token."""
        res = self.client.post("/auth/login", json={
            "username_or_email": self.user_a_email,
            "password": self.password
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], self.user_a_email)

    def test_invalid_login_credentials_rejected(self):
        """Verify incorrect password or non-existent user returns 401."""
        res = self.client.post("/auth/login", json={
            "username_or_email": self.user_a_email,
            "password": "WrongPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        data = res.json()
        self.assertIn("error", data)
        self.assertIn("message", data["error"])

        res_unknown = self.client.post("/auth/login", json={
            "username_or_email": "nonexistent_researcher",
            "password": self.password
        })
        self.assertEqual(res_unknown.status_code, 401)

    def test_unauthenticated_protected_endpoint_rejected(self):
        """Verify accessing protected routes without Bearer token returns 401."""
        res = self.client.get("/sessions")
        self.assertEqual(res.status_code, 401)

        res_me = self.client.get("/auth/me")
        self.assertEqual(res_me.status_code, 401)

    def test_expired_or_invalid_jwt_rejected(self):
        """Verify forged or expired tokens are strictly rejected."""
        # Forged token with invalid signature
        forged_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.tampered_signature"
        res = self.client.get("/sessions", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(res.status_code, 401)

        # Expired token
        expired_payload = {
            "sub": self.user_a_id,
            "exp": int(time.time()) - 3600,
            "iss": "research-intelligence-assistant"
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        res_exp = self.client.get("/sessions", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res_exp.status_code, 401)

    # -------------------------------------------------------------
    # 2. MULTI-TENANT ISOLATION TESTS
    # -------------------------------------------------------------

    def test_user_a_cannot_access_user_b_session(self):
        """Verify User A receives 403 Forbidden attempting to read User B's session."""
        session_b_id = f"thread_b_{uuid.uuid4().hex[:8]}"
        session_b = ResearchSession(
            id=session_b_id,
            user_id=self.user_b_id,
            title="Private Research on Topo Qubits",
            original_query="topological majorana zero modes in nanowires",
            status="COMPLETED"
        )
        self.db.add(session_b)
        self.db.commit()

        # User A attempts to read User B's session
        res = self.client.get(
            f"/sessions/{session_b_id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_a_cannot_mutate_or_delete_user_b_session(self):
        """Verify User A cannot delete User B's research session."""
        session_b_id = f"thread_b_del_{uuid.uuid4().hex[:8]}"
        session_b = ResearchSession(
            id=session_b_id,
            user_id=self.user_b_id,
            title="User B Session For Deletion Guard",
            original_query="quantum transduction via optomechanics",
            status="COMPLETED"
        )
        self.db.add(session_b)
        self.db.commit()

        # User A attempts to delete User B's session
        res = self.client.delete(
            f"/sessions/{session_b_id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 403)

        # Verify session still exists in DB
        check = self.db.query(ResearchSession).filter(ResearchSession.id == session_b_id).first()
        self.assertIsNotNone(check)

    def test_user_a_cannot_access_user_b_job_status(self):
        """Verify User A cannot poll or inspect User B's background job status."""
        job_b_id = f"job_b_{uuid.uuid4().hex[:8]}"
        job_b = ResearchJob(
            id=job_b_id,
            user_id=self.user_b_id,
            session_id=f"thread_b_{uuid.uuid4().hex[:6]}",
            status="RUNNING"
        )
        self.db.add(job_b)
        self.db.commit()

        # User A tries to view User B's job
        res = self.client.get(
            f"/jobs/{job_b_id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_a_cannot_cancel_user_b_job(self):
        """Verify User A cannot cancel User B's running research job."""
        job_b_id = f"job_b_cancel_{uuid.uuid4().hex[:8]}"
        job_b = ResearchJob(
            id=job_b_id,
            user_id=self.user_b_id,
            session_id=f"thread_b_{uuid.uuid4().hex[:6]}",
            status="RUNNING"
        )
        self.db.add(job_b)
        self.db.commit()

        # User A tries to cancel User B's job
        res = self.client.post(
            f"/jobs/{job_b_id}/cancel",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_a_cannot_subscribe_to_user_b_sse_stream(self):
        """Verify User A cannot attach to User B's live Server-Sent Events stream."""
        job_b_id = f"job_b_stream_{uuid.uuid4().hex[:8]}"
        job_b = ResearchJob(
            id=job_b_id,
            user_id=self.user_b_id,
            session_id=f"thread_b_{uuid.uuid4().hex[:6]}",
            status="RUNNING"
        )
        self.db.add(job_b)
        self.db.commit()

        # User A attempts to stream User B's job events via query token
        res = self.client.get(
            f"/jobs/{job_b_id}/stream?token={self.token_a}"
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------
    # 3. INPUT VALIDATION TESTS
    # -------------------------------------------------------------

    def test_short_query_rejected(self):
        """Verify queries shorter than 2 characters return 422 Unprocessable Entity."""
        res = self.client.post(
            "/research",
            json={"query": "a"},
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 422)

    def test_oversized_query_rejected(self):
        """Verify queries exceeding 1000 characters return 422 Unprocessable Entity."""
        oversized = "quantum " * 200  # 1600 characters
        res = self.client.post(
            "/research",
            json={"query": oversized},
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 422)

    def test_malformed_session_id_rejected(self):
        """Verify session IDs containing malicious characters return 422."""
        res = self.client.post(
            "/research",
            json={
                "query": "valid academic research query",
                "session_id": "../../../etc/passwd; DROP TABLE users;"
            },
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 422)

    # -------------------------------------------------------------
    # 4. SECURITY HEADERS & CORRELATION
    # -------------------------------------------------------------

    def test_security_headers_present(self):
        """Verify mandated OWASP security headers are present on all responses."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("geolocation=()", res.headers.get("Permissions-Policy", ""))

    def test_correlation_id_propagated(self):
        """Verify X-Request-ID is either respected or generated and returned."""
        custom_rid = "req_custom_tracer_99"
        res = self.client.get("/health", headers={"X-Request-ID": custom_rid})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Request-ID"), custom_rid)

        # Automatic generation when header not provided
        res_auto = self.client.get("/health")
        self.assertTrue(res_auto.headers.get("X-Request-ID", "").startswith("req_"))

    # -------------------------------------------------------------
    # 5. SECRET SANITIZATION IN LOGS
    # -------------------------------------------------------------

    def test_secret_scrubbing_in_logging(self):
        """Verify secrets are redacted from logging records."""
        formatter = SecretSanitizingFormatter()
        import logging
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="User supplied GEMINI_API_KEY='DUMMY_SECRET_KEY_1234567890_XYZ' and key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
            args=(), exc_info=None
        )
        formatted = formatter.format(record)
        self.assertNotIn("DUMMY_SECRET_KEY", formatted)
        self.assertNotIn("AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6", formatted)
        self.assertIn("***REDACTED***", formatted)

    # -------------------------------------------------------------
    # 6. OBSERVABILITY METRICS
    # -------------------------------------------------------------

    def test_metrics_endpoint_exposition(self):
        """Verify genuine metrics are exposed in Prometheus and JSON formats."""
        # Prometheus format
        res_prom = self.client.get("/metrics")
        self.assertEqual(res_prom.status_code, 200)
        self.assertIn("api_requests_total", res_prom.text)
        self.assertIn("research_jobs_total", res_prom.text)

        # JSON format
        res_json = self.client.get("/metrics?format=json")
        self.assertEqual(res_json.status_code, 200)
        data = res_json.json()
        self.assertIn("api", data)
        self.assertIn("uptime_seconds", data)
        self.assertIn("research_jobs", data)

    # -------------------------------------------------------------
    # 7. ASYNC JOB LIFECYCLE & IDEMPOTENCY
    # -------------------------------------------------------------

    @patch("app.jobs.manager.research_graph.invoke")
    def test_async_job_submission_and_status_polling(self, mock_invoke):
        """Verify job creation returns 200 with QUEUED status and polling endpoint works."""
        mock_invoke.return_value = {
            "query": "scalable neutral atom quantum computing optical tweezers",
            "thread_id": "thread_test",
            "current_iteration": 1,
            "grounding_status": "VERIFIED",
            "claims": [{"claim_id": "C001", "support_status": "SUPPORTED"}],
            "citations": ["Citation 1"],
            "evidence_strength": {"rating": "STRONG"},
            "iterations_history": [{
                "iteration": 1,
                "query_used": "scalable neutral atom",
                "new_papers_count": 2,
                "new_evidence_count": 4,
                "sufficiency_status": "SUFFICIENT"
            }],
            "report": "Mock research report"
        }

        res = self.client.post(
            "/research",
            json={
                "query": "scalable neutral atom quantum computing optical tweezers",
                "idempotency_key": f"idemp_test_atomic_{uuid.uuid4().hex[:6]}"
            },
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("job_id", data)
        self.assertIn("session_id", data)
        self.assertIn(data["status"], ["QUEUED", "RUNNING", "COMPLETED"])

        # Poll status
        job_id = data["job_id"]
        res_poll = self.client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_poll.status_code, 200)
        poll_data = res_poll.json()
        self.assertEqual(poll_data["job_id"], job_id)

    @patch("app.jobs.manager.research_graph.invoke")
    def test_idempotent_duplicate_submission_protection(self, mock_invoke):
        """Verify repeated submission with same idempotency key returns existing job."""
        mock_invoke.return_value = {
            "query": "photonic cluster states for fault tolerant quantum computing",
            "thread_id": "thread_test",
            "current_iteration": 1,
            "grounding_status": "VERIFIED",
            "claims": [],
            "citations": [],
            "iterations_history": [],
            "report": "Mock report"
        }

        key = f"idemp_{uuid.uuid4().hex[:10]}"
        res1 = self.client.post(
            "/research",
            json={
                "query": "photonic cluster states for fault tolerant quantum computing",
                "idempotency_key": key
            },
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res1.status_code, 200)
        job1 = res1.json()

        # Submit identical request again
        res2 = self.client.post(
            "/research",
            json={
                "query": "photonic cluster states for fault tolerant quantum computing",
                "idempotency_key": key
            },
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res2.status_code, 200)
        job2 = res2.json()

        self.assertEqual(job1["job_id"], job2["job_id"])

    def test_safe_job_cancellation(self):
        """Verify researcher can cancel their own active job."""
        # Create a job record
        job_id = f"job_cancel_test_{uuid.uuid4().hex[:8]}"
        job = ResearchJob(
            id=job_id,
            user_id=self.user_a_id,
            session_id=f"thread_cancel_{uuid.uuid4().hex[:6]}",
            status="QUEUED"
        )
        self.db.add(job)
        self.db.commit()

        # User A cancels their job
        res = self.client.post(
            f"/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "CANCELLED")

        # Verify DB state
        cancelled_job = self.db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        self.assertEqual(cancelled_job.status, "CANCELLED")

    # -------------------------------------------------------------
    # 8. ERROR HYGIENE (NO STACK TRACES TO CLIENT)
    # -------------------------------------------------------------

    def test_sanitized_error_responses_contain_no_tracebacks(self):
        """Verify internal errors do not leak stack traces, database queries, or server internals."""
        # Non-existent session
        res = self.client.get(
            "/sessions/nonexistent_session_id_999",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 404)
        err = res.json()
        self.assertNotIn("Traceback", res.text)
        self.assertNotIn("SELECT ", res.text)
        self.assertNotIn("Exception", res.text)
        self.assertIn("error", err)
        self.assertIn("request_id", err["error"])

    # -------------------------------------------------------------
    # 9. INACTIVE ACCOUNTS & REGISTRATION CONFLICTS
    # -------------------------------------------------------------

    def test_duplicate_registration_rejected(self):
        """Verify registration conflicts (duplicate email or username) return 409 Conflict."""
        # Duplicate email
        res_email = self.client.post("/auth/register", json={
            "username": f"unique_user_{uuid.uuid4().hex[:6]}",
            "email": self.user_a_email,
            "password": "ValidPassword123!"
        })
        self.assertEqual(res_email.status_code, 409)

        # Duplicate username
        res_user = self.client.post("/auth/register", json={
            "username": self.user_a_name,
            "email": f"unique_{uuid.uuid4().hex[:6]}@domain.edu",
            "password": "ValidPassword123!"
        })
        self.assertEqual(res_user.status_code, 409)

    def test_inactive_user_account_rejected(self):
        """Verify deactivated/inactive accounts cannot log in or access authenticated resources."""
        inactive_email = f"inactive_{uuid.uuid4().hex[:8]}@academic.edu"
        inactive_user = User(
            id=f"usr_inactive_{uuid.uuid4().hex[:8]}",
            username=f"inactive_{uuid.uuid4().hex[:6]}",
            email=inactive_email,
            hashed_password=hash_password("ValidPassword123!"),
            is_active=False
        )
        self.db.add(inactive_user)
        self.db.commit()

        # Login attempt rejected with 403
        res_login = self.client.post("/auth/login", json={
            "username_or_email": inactive_email,
            "password": "ValidPassword123!"
        })
        self.assertEqual(res_login.status_code, 403)
        self.assertIn("deactivated", res_login.text.lower())

        # Forged or legacy token for deactivated user rejected with 403
        token = jwt.encode(
            {"sub": inactive_user.id, "exp": int(time.time()) + 3600, "iss": "research-intelligence-assistant"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        res_auth = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_auth.status_code, 403)

    # -------------------------------------------------------------
    # 10. TOKEN REVOCATION & LOGOUT
    # -------------------------------------------------------------

    def test_token_revocation_on_logout(self):
        """Verify logging out revokes the JWT so it cannot be reused for protected access."""
        # 1. Login to get fresh token
        res_login = self.client.post("/auth/login", json={
            "username_or_email": self.user_a_email,
            "password": self.password
        })
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["access_token"]

        # 2. Token works initially
        res_me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)

        # 3. Logout to revoke token
        res_logout = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_logout.status_code, 200)

        # 4. Token is now strictly rejected with 401
        res_after = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_after.status_code, 401)
        self.assertIn("revoked", res_after.text.lower())

    # -------------------------------------------------------------
    # 11. PRODUCTION CONFIGURATION SAFETY & SQLITE DENIAL
    # -------------------------------------------------------------

    def test_production_config_rejects_insecure_defaults(self):
        """Verify production configuration strictly rejects SQLite, short secrets, and debug flags."""
        # SQLite URL in production must fail validation
        with self.assertRaises(ValidationError):
            Settings(
                ENV="production",
                DATABASE_URL="sqlite:///./prod.db",
                DATABASE_FALLBACK_SQLITE=False,
                JWT_SECRET_KEY="a_very_long_secure_secret_key_32_characters_min",
                DEBUG=False
            )

        # SQLite fallback allowed in production must fail validation
        with self.assertRaises(ValidationError):
            Settings(
                ENV="production",
                DATABASE_URL="postgresql://user:pass@localhost:5432/research_db",
                DATABASE_FALLBACK_SQLITE=True,
                JWT_SECRET_KEY="a_very_long_secure_secret_key_32_characters_min",
                DEBUG=False
            )

        # Insecure/short JWT secret in production must fail validation
        with self.assertRaises(ValidationError):
            Settings(
                ENV="production",
                DATABASE_URL="postgresql://user:pass@localhost:5432/research_db",
                DATABASE_FALLBACK_SQLITE=False,
                JWT_SECRET_KEY="short_key",
                DEBUG=False
            )

        # DEBUG=True in production must fail validation
        with self.assertRaises(ValidationError):
            Settings(
                ENV="production",
                DATABASE_URL="postgresql://user:pass@localhost:5432/research_db",
                DATABASE_FALLBACK_SQLITE=False,
                JWT_SECRET_KEY="a_very_long_secure_secret_key_32_characters_min",
                DEBUG=True
            )

    def test_production_database_and_checkpointer_deny_silent_sqlite_fallback(self):
        """Verify database engine and LangGraph checkpointer fail safely rather than silently using SQLite in production."""
        with patch("app.db.base.get_settings") as mock_base_settings, \
             patch("app.db.checkpoint.get_settings") as mock_cp_settings:
            mock_s = MagicMock()
            mock_s.is_production.return_value = True
            mock_s.DATABASE_URL = "sqlite:///./prod.db"
            mock_s.DATABASE_FALLBACK_SQLITE = False
            mock_base_settings.return_value = mock_s
            mock_cp_settings.return_value = mock_s

            # Engine creation with SQLite in production must raise ConfigurationError
            with self.assertRaises(ConfigurationError):
                get_engine()

            # Checkpointer initialization with SQLite in production must raise ConfigurationError
            with self.assertRaises(ConfigurationError):
                get_checkpointer()

            # Checkpointer initialization with broken PostgreSQL in production must raise DatabaseError
            mock_s.DATABASE_URL = "postgresql://user:pass@nonexistent-host:5432/bad_db"
            with self.assertRaises(DatabaseError):
                get_checkpointer()

    # -------------------------------------------------------------
    # 12. STRUCTURED SSE LIFECYCLE EVENT CONTRACT
    # -------------------------------------------------------------

    def test_structured_sse_lifecycle_events_contract(self):
        """Verify all 12 mandated structured lifecycle events can be published with typed payloads."""
        test_job_id = f"job_sse_test_{uuid.uuid4().hex[:8]}"

        required_lifecycle_events = [
            ("research_started", {"session_id": "sess_1", "query": "test query"}),
            ("iteration_started", {"iteration": 1, "max_iterations": 3}),
            ("search_started", {"iteration": 1, "queries": ["query 1"]}),
            ("search_completed", {"iteration": 1, "papers_count": 5}),
            ("evidence_retrieval", {"iteration": 1, "evidence_count": 12}),
            ("intelligence", {"iteration": 1, "contradictions_count": 2}),
            ("sufficiency", {"iteration": 1, "sufficiency_status": "PARTIAL"}),
            ("targeted_query", {"iteration": 1, "gap": "sample gap", "targeted_query": "gap query"}),
            ("iteration_completed", {"iteration": 1, "cumulative_evidence_count": 12}),
            ("research_completed", {"status": "COMPLETED", "duration_seconds": 4.2}),
            ("research_failed", {"status": "FAILED", "error": "simulated test error"}),
            ("research_cancelled", {"status": "CANCELLED", "message": "cancelled by user"}),
        ]

        for event_type, payload in required_lifecycle_events:
            emit_lifecycle_event(test_job_id, event_type, payload)

        recorded_events = job_event_bus.get_history(test_job_id)
        captured_types = [e["event"] for e in recorded_events]
        for event_type, _ in required_lifecycle_events:
            self.assertIn(event_type, captured_types, f"Event '{event_type}' was not captured by event bus")

    # -------------------------------------------------------------
    # 13. DURABLE PERSISTENCE, RESTART RECOVERY & TENANT ISOLATION
    # -------------------------------------------------------------

    def test_persistence_restart_and_recovery(self):
        """
        Verify:
        authenticated user -> creates research session/job -> durable state written
        -> simulated application restart (fresh DB session / client)
        -> session/job/report state recovered from storage
        -> cross-tenant ownership remains strictly enforced.
        """
        session_id = f"thread_restart_{uuid.uuid4().hex[:8]}"
        job_id = f"job_restart_{uuid.uuid4().hex[:8]}"
        run_id = f"run_restart_{uuid.uuid4().hex[:8]}"
        report_id = f"rep_restart_{uuid.uuid4().hex[:8]}"

        # 1. User A persists research state
        session_a = ResearchSession(
            id=session_id,
            user_id=self.user_a_id,
            title="Durable State Quantum Annealing",
            original_query="quantum annealing scaling limits",
            status="COMPLETED"
        )
        job_a = ResearchJob(
            id=job_id,
            user_id=self.user_a_id,
            session_id=session_id,
            run_id=run_id,
            status="COMPLETED",
            duration_seconds=12.5,
            progress_percent=100
        )
        run_a = ResearchRun(
            id=run_id,
            session_id=session_id,
            user_id=self.user_a_id,
            iteration_count=2,
            status="COMPLETED",
            grounding_status="VERIFIED"
        )
        report_a = ReportModel(
            id=report_id,
            session_id=session_id,
            user_id=self.user_a_id,
            run_id=run_id,
            markdown_content="# Quantum Annealing Durable Report\nDetailed evidence findings.",
            evidence_strength="STRONG",
            claims_count=6,
            citations_count=8,
            result_json='{"claims": ["c1"], "citations": ["s1"]}'
        )

        self.db.add(session_a)
        self.db.add(job_a)
        self.db.add(run_a)
        self.db.add(report_a)
        self.db.commit()

        # 2. Simulate Application Restart:
        # Tear down connection session, recreate fresh SessionLocal and fresh TestClient
        self.db.close()
        fresh_db = SessionLocal()
        fresh_client = TestClient(app)

        try:
            # 3. User A recovers session and verified persistent data
            res_a = fresh_client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {self.token_a}"})
            self.assertEqual(res_a.status_code, 200)
            data_a = res_a.json()
            self.assertEqual(data_a["id"], session_id)
            self.assertEqual(data_a["title"], "Durable State Quantum Annealing")
            self.assertEqual(data_a["status"], "COMPLETED")
            self.assertEqual(data_a["report_markdown"], "# Quantum Annealing Durable Report\nDetailed evidence findings.")
            self.assertEqual(data_a["result_data"], {"claims": ["c1"], "citations": ["s1"]})

            # User A recovers job status
            res_job = fresh_client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {self.token_a}"})
            self.assertEqual(res_job.status_code, 200)
            data_job = res_job.json()
            self.assertEqual(data_job["status"], "COMPLETED")
            self.assertEqual(data_job["run_id"], run_id)

            # 4. User B attempts to access recovered User A assets -> strictly 403 Forbidden
            res_b_session = fresh_client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {self.token_b}"})
            self.assertEqual(res_b_session.status_code, 403)

            res_b_job = fresh_client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {self.token_b}"})
            self.assertEqual(res_b_job.status_code, 403)

        finally:
            fresh_db.close()
            # Reopen class db session
            self.db = SessionLocal()
