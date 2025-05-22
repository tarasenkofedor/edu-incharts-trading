"""add_klines_table_for_timescaledb

Revision ID: 670a0da83f87
Revises: a07eb6c9d87f
Create Date: 2025-05-19 21:42:04.704689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '670a0da83f87'
down_revision: Union[str, None] = 'a07eb6c9d87f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'klines',
        # Composite Primary Key columns - primary_key=True is not set here
        # as the constraint is defined below as a table argument.
        sa.Column('symbol', sa.String(), nullable=False, index=True),
        sa.Column('timeframe', sa.String(), nullable=False, index=True),
        sa.Column('open_time', sa.DateTime(timezone=True), nullable=False, index=True),

        # Kline data fields
        sa.Column('open_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('high_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('low_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('volume', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('close_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quote_asset_volume', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('number_of_trades', sa.BigInteger(), nullable=False),
        sa.Column('taker_buy_base_asset_volume', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('taker_buy_quote_asset_volume', sa.Numeric(precision=24, scale=8), nullable=False),
        
        # Define the composite primary key
        sa.PrimaryKeyConstraint('symbol', 'timeframe', 'open_time', name='pk_klines')
        # The old UniqueConstraint('symbol', 'timeframe', 'open_time') is now redundant as it's the PK.
    )
    
    # Create the hypertable (TimescaleDB specific)
    # Note: Adjust chunk_time_interval if needed, e.g., timedelta(days=7) or similar.
    # Default chunk_time_interval is usually sufficient to start.
    op.execute("SELECT create_hypertable('klines'::regclass, 'open_time'::name);")


def downgrade() -> None:
    """Downgrade schema."""
    # Since create_hypertable is TimescaleDB specific, its removal might also need specific handling
    # if there were dependencies. For a simple table drop, this is usually fine.
    # If hypertables have specific detach/drop requirements beyond simple table drop, that would be added here.
    # For now, dropping the table itself will remove the hypertable structure as well.
    op.drop_table('klines')
