-- Tạo 3 role CSDL của AI-EOS và quyền ở mức database (T-005, ADR-004, Database_Design §2, §10).
-- Chạy MỘT LẦN bằng superuser, khi đang kết nối tới CSDL của AI-EOS (vd. psql -d <csdl> -f provision_roles.sql).
-- Chạy lại an toàn: chỉ tạo role còn thiếu và đặt lại thuộc tính tối thiểu.
-- KHÔNG chứa mật khẩu: đặt mật khẩu cho từng role ngoài file này (vd. \password trong psql) và đưa vào secret
-- AIEOS_DATABASE_URL (aieos_app), AIEOS_DATABASE_OWNER_URL (aieos_owner) — Implementation_Plan §7.
-- Thuộc tính REPLICATION cho aieos_backup (nếu công cụ backup cần) do T-605 quyết định.

DO $$
DECLARE
  r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['aieos_owner', 'aieos_app', 'aieos_backup'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I LOGIN', r);
    END IF;
    EXECUTE format('ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT', r);
  END LOOP;

  EXECUTE format('ALTER DATABASE %I OWNER TO aieos_owner', current_database());
  EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO aieos_app, aieos_backup', current_database());
END
$$;

-- Schema public: chỉ aieos_owner tạo được đối tượng (bảng alembic_version).
ALTER SCHEMA public OWNER TO aieos_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO aieos_app, aieos_backup;
