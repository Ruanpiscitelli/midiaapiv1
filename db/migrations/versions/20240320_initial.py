"""Migração inicial

Revision ID: 20240320_initial
Create Date: 2024-03-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240320_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Tabela de jobs
    op.create_table(
        'jobs',
        sa.Column('job_id', sa.String(), primary_key=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('result_url', sa.String()),
        sa.Column('error_message', sa.String()),
        sa.Column('metadata', sa.String())
    )

    # Tabela de arquivos gerados
    op.create_table(
        'generated_files',
        sa.Column('file_id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_url', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id'], ondelete='CASCADE')
    )

    # Trigger para atualizar updated_at
    op.execute("""
        CREATE TRIGGER update_job_timestamp 
        AFTER UPDATE ON jobs
        BEGIN
            UPDATE jobs SET updated_at = CURRENT_TIMESTAMP 
            WHERE job_id = NEW.job_id;
        END;
    """)

def downgrade() -> None:
    op.drop_table('generated_files')
    op.drop_table('jobs') 