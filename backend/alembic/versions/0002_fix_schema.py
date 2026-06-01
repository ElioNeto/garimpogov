"""Fix schema: updated_at onupdate, edital_chunks created_at, embedding NOT NULL

- Adiciona onupdate=func.now() para updated_at na tabela concursos
- Adiciona coluna created_at na tabela edital_chunks
- Torna embedding NOT NULL (B5/B9)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # B9: Adiciona onupdate para updated_at (via recriação da coluna)
    # Nota: PostgreSQL não suporta ALTER COLUMN ... ON UPDATE diretamente.
    # Como alternativa, usamos um trigger para manter updated_at atualizado.
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Verifica se o trigger já existe antes de criar
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_concursos_updated_at')")
    )
    trigger_exists = result.scalar()
    if not trigger_exists:
        op.execute("""
            CREATE TRIGGER trigger_concursos_updated_at
                BEFORE UPDATE ON concursos
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

    # B5: Adiciona created_at na tabela edital_chunks
    op.add_column(
        'edital_chunks',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    # B5: Torna embedding NOT NULL (primeiro atualiza registros existentes com embedding NULL)
    op.execute(
        "UPDATE edital_chunks SET embedding = '{}'::vector(768) WHERE embedding IS NULL"
    )
    op.alter_column('edital_chunks', 'embedding', nullable=False)


def downgrade() -> None:
    # Remove trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_concursos_updated_at ON concursos")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Remove coluna created_at
    op.drop_column('edital_chunks', 'created_at')

    # Torna embedding NULLable novamente
    op.alter_column('edital_chunks', 'embedding', nullable=True)
