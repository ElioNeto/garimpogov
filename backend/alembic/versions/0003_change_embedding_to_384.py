"""Change embedding dimension from 768 to 384 (sentence-transformers)

- Nova coluna temporária → copia dados → drop coluna antiga → rename
- sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) produz 384 dims
- Embeddings antigos (768) perdem significado, mas a tabela fica consistente

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona coluna temporária com 384 dims
    op.add_column(
        'edital_chunks',
        sa.Column('embedding_384', Vector(384), nullable=True),
    )

    # Converte embeddings existentes via truncamento/padding para 384
    # (perda de informação, mas mantém compatibilidade)
    op.execute("""
        UPDATE edital_chunks
        SET embedding_384 = (embedding::text::real[])[1:384]::vector(384)
        WHERE embedding IS NOT NULL
    """)

    # Drop coluna antiga
    op.drop_column('edital_chunks', 'embedding')

    # Renomeia nova coluna
    op.alter_column('edital_chunks', 'embedding_384', new_column_name='embedding')

    # Torna NOT NULL
    op.alter_column('edital_chunks', 'embedding', nullable=False)


def downgrade() -> None:
    # Reverte: adiciona coluna 768, copia com padding, drop 384
    op.add_column(
        'edital_chunks',
        sa.Column('embedding_768', Vector(768), nullable=True),
    )

    op.execute("""
        UPDATE edital_chunks
        SET embedding_768 = embedding::text::vector(768)
        WHERE embedding IS NOT NULL
    """)

    op.drop_column('edital_chunks', 'embedding')
    op.alter_column('edital_chunks', 'embedding_768', new_column_name='embedding')
    op.alter_column('edital_chunks', 'embedding', nullable=False)
