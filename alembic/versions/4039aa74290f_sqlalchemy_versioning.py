"""sqlalchemy_versioning

Revision ID: 4039aa74290f
Revises: 71beb6c29063
Create Date: 2022-07-20 14:44:38.393158

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4039aa74290f'
down_revision = '71beb6c29063'

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('library_version',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.String(length=50), autoincrement=False, nullable=True),
    sa.Column('description', sa.String(length=200), autoincrement=False, nullable=True),
    sa.Column('public', sa.Boolean(), autoincrement=False, nullable=True),
    sa.Column('bibcode', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('date_created', sa.DateTime(), autoincrement=False, nullable=True),
    sa.Column('date_last_modified', sa.DateTime(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_library_version_end_transaction_id'), 'library_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_library_version_operation_type'), 'library_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_library_version_transaction_id'), 'library_version', ['transaction_id'], unique=False)
    op.create_table('transaction',
    sa.Column('issued_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('remote_addr', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('transaction')
    op.drop_index(op.f('ix_library_version_transaction_id'), table_name='library_version')
    op.drop_index(op.f('ix_library_version_operation_type'), table_name='library_version')
    op.drop_index(op.f('ix_library_version_end_transaction_id'), table_name='library_version')
    op.drop_table('library_version')
    # ### end Alembic commands ###
