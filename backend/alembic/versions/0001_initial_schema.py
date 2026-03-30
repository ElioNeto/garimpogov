"""Initial schema: enable pgvector, create concursos, cargos, edital_chunks

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'concursos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('instituicao', sa.String(500), nullable=False),
        sa.Column('orgao', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='aberto'),
        sa.Column('link_edital', sa.String(2000), nullable=False, unique=True),
        sa.Column('pdf_url', sa.String(2000), nullable=True),
        sa.Column('salario_maximo', sa.Numeric(12, 2), nullable=True),
        sa.Column('data_encerramento', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'cargos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('concurso_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('concursos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(500), nullable=False),
        sa.Column('vagas', sa.Integer, nullable=True),
        sa.Column('salario', sa.Numeric(12, 2), nullable=True),
        sa.Column('requisitos', sa.Text, nullable=True),
    )

    op.create_table(
        'edital_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('concurso_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('concursos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
    )

    op.create_index('idx_edital_chunks_concurso_id', 'edital_chunks', ['concurso_id'])
    op.create_index(
        'idx_edital_chunks_embedding',
        'edital_chunks',
        ['embedding'],
        postgresql_using='ivfflat',
        postgresql_ops={'embedding': 'vector_cosine_ops'},
        postgresql_with={'lists': '100'},
    )


def downgrade() -> None:
    op.drop_table('edital_chunks')
    op.drop_table('cargos')
    op.drop_table('concursos')
    op.execute('DROP EXTENSION IF EXISTS vector')
