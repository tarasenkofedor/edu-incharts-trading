"""create_users_table

Revision ID: a07eb6c9d87f
Revises: 
Create Date: 2025-05-18 21:36:47.220659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a07eb6c9d87f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENUM_NAME = 'subscriptionplanenum'
ENUM_VALUES = ('FREE', 'BASIC', 'PREMIUM')
subscription_plan_enum_type = postgresql.ENUM(*ENUM_VALUES, name=ENUM_NAME, create_type=False)

def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    # Ensure the ENUM type exists
    res = conn.execute(sa.text(f"SELECT 1 FROM pg_type WHERE typname = '{ENUM_NAME}'")).scalar_one_or_none()
    if not res:
        # If it doesn't exist, create it using a temporary version of the enum that *can* create the type
        temp_enum_for_creation = postgresql.ENUM(*ENUM_VALUES, name=ENUM_NAME, create_type=True)
        temp_enum_for_creation.create(conn, checkfirst=False) # checkfirst=False as we've manually confirmed non-existence

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nickname', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('first_joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    # Initially create with a compatible placeholder type if direct ENUM usage is problematic
    sa.Column('subscription_plan', sa.String(), nullable=True), # Placeholder
    sa.Column('start_of_subscription', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_of_subscription', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_nickname'), 'users', ['nickname'], unique=True)

    # Alter the column to the actual ENUM type
    # The `subscription_plan_enum_type` here has create_type=False, so it just refers to the type.
    op.alter_column('users', 'subscription_plan',
               existing_type=sa.String(),
               type_=subscription_plan_enum_type,
               postgresql_using=f'subscription_plan::text::{ENUM_NAME}' # Required for casting
               )

def downgrade() -> None:
    """Downgrade schema."""
    # In downgrade, altering column back to string is optional if table is dropped anyway.
    # If we wanted to be precise, we'd alter it back before dropping.
    op.drop_index(op.f('ix_users_nickname'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    conn = op.get_bind()
    # Optionally, drop the ENUM type if no other table uses it and it was created by this migration context
    # This check makes sure we only drop if it exists.
    res = conn.execute(sa.text(f"SELECT 1 FROM pg_type WHERE typname = '{ENUM_NAME}'")).scalar_one_or_none()
    if res:
        # Use a temporary enum type instance that is configured to drop the type
        temp_enum_for_dropping = postgresql.ENUM(*ENUM_VALUES, name=ENUM_NAME, create_type=True) 
        temp_enum_for_dropping.drop(conn, checkfirst=False) # checkfirst=False as we've manually confirmed existence
