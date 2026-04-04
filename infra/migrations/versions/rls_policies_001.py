"""Add RLS policies for multi-tenancy

Revision ID: rls_policies_001
Revises: fix_queries_columns
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'rls_policies_001'
down_revision = 'fix_queries_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on each table (separate statements for asyncpg)
    op.execute("ALTER TABLE orgs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE collections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE queries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY")

    # Orgs: users can see their own org
    op.execute(
        "CREATE POLICY org_isolation ON orgs "
        "FOR SELECT USING (id = current_setting('app.current_org_id', true)::uuid)"
    )

    # Users: org isolation
    op.execute(
        "CREATE POLICY users_org_isolation ON users "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY users_org_insert ON users "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )

    # Documents: org isolation
    op.execute(
        "CREATE POLICY documents_org_isolation ON documents "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY documents_org_insert ON documents "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY documents_org_update ON documents "
        "FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::uuid) "
        "WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY documents_org_delete ON documents "
        "FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )

    # Collections: org isolation
    op.execute(
        "CREATE POLICY collections_org_isolation ON collections "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY collections_org_insert ON collections "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY collections_org_update ON collections "
        "FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::uuid) "
        "WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY collections_org_delete ON collections "
        "FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )

    # Chunks: org isolation
    op.execute(
        "CREATE POLICY chunks_org_isolation ON chunks "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY chunks_org_insert ON chunks "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY chunks_org_delete ON chunks "
        "FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )

    # Queries: org isolation
    op.execute(
        "CREATE POLICY queries_org_isolation ON queries "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY queries_org_insert ON queries "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY queries_org_update ON queries "
        "FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::uuid) "
        "WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )

    # API Keys: org isolation
    op.execute(
        "CREATE POLICY api_keys_org_isolation ON api_keys "
        "FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY api_keys_org_insert ON api_keys "
        "FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY api_keys_org_update ON api_keys "
        "FOR UPDATE USING (org_id = current_setting('app.current_org_id', true)::uuid) "
        "WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)"
    )
    op.execute(
        "CREATE POLICY api_keys_org_delete ON api_keys "
        "FOR DELETE USING (org_id = current_setting('app.current_org_id', true)::uuid)"
    )


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS org_isolation ON orgs")
    op.execute("DROP POLICY IF EXISTS users_org_isolation ON users")
    op.execute("DROP POLICY IF EXISTS users_org_insert ON users")
    op.execute("DROP POLICY IF EXISTS documents_org_isolation ON documents")
    op.execute("DROP POLICY IF EXISTS documents_org_insert ON documents")
    op.execute("DROP POLICY IF EXISTS documents_org_update ON documents")
    op.execute("DROP POLICY IF EXISTS documents_org_delete ON documents")
    op.execute("DROP POLICY IF EXISTS collections_org_isolation ON collections")
    op.execute("DROP POLICY IF EXISTS collections_org_insert ON collections")
    op.execute("DROP POLICY IF EXISTS collections_org_update ON collections")
    op.execute("DROP POLICY IF EXISTS collections_org_delete ON collections")
    op.execute("DROP POLICY IF EXISTS chunks_org_isolation ON chunks")
    op.execute("DROP POLICY IF EXISTS chunks_org_insert ON chunks")
    op.execute("DROP POLICY IF EXISTS chunks_org_delete ON chunks")
    op.execute("DROP POLICY IF EXISTS queries_org_isolation ON queries")
    op.execute("DROP POLICY IF EXISTS queries_org_insert ON queries")
    op.execute("DROP POLICY IF EXISTS queries_org_update ON queries")
    op.execute("DROP POLICY IF EXISTS api_keys_org_isolation ON api_keys")
    op.execute("DROP POLICY IF EXISTS api_keys_org_insert ON api_keys")
    op.execute("DROP POLICY IF EXISTS api_keys_org_update ON api_keys")
    op.execute("DROP POLICY IF EXISTS api_keys_org_delete ON api_keys")

    # Disable RLS
    op.execute("ALTER TABLE orgs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE collections DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chunks DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE queries DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY")
