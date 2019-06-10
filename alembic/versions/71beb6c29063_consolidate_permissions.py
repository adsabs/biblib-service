"""consolidate permissions

Revision ID: 71beb6c29063
Revises: 1c82f25a268e
Create Date: 2019-06-07 16:17:12.909645

"""

# revision identifiers, used by Alembic.
revision = '71beb6c29063'
down_revision = '1c82f25a268e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('permissions', sa.Column('permissions', postgresql.JSON(), nullable=True))
    op.alter_column('permissions',
                    'permissions',
                    type_=postgresql.JSON(),
                    postgresql_using="json_build_object('read',read,'write',write,'admin',admin,'owner',owner)")

    op.drop_column('permissions', 'read')
    op.drop_column('permissions', 'write')
    op.drop_column('permissions', 'admin')
    op.drop_column('permissions', 'owner')

def downgrade():
    op.add_column('permissions', sa.Column('read', sa.Boolean(), nullable=True))
    op.add_column('permissions', sa.Column('write', sa.Boolean(), nullable=True))
    op.add_column('permissions', sa.Column('admin', sa.Boolean(), nullable=True))
    op.add_column('permissions', sa.Column('owner', sa.Boolean(), nullable=True))

    op.alter_column('permissions',
                    'read',
                    type_=sa.Boolean(),
                    postgresql_using="(permissions->>'read')::bool")

    op.alter_column('permissions',
                    'write',
                    type_=sa.Boolean(),
                    postgresql_using="(permissions->>'write')::bool")

    op.alter_column('permissions',
                    'admin',
                    type_=sa.Boolean(),
                    postgresql_using="(permissions->>'admin')::bool")

    op.alter_column('permissions',
                    'owner',
                    type_=sa.Boolean(),
                    postgresql_using="(permissions->>'owner')::bool")

    op.drop_column('permissions', 'permissions')

