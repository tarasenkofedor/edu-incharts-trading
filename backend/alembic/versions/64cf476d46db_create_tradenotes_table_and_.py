"""create_tradenotes_table_and_tradedirectionenum_type

Revision ID: 64cf476d46db
Revises: 941c73ffbd8c
Create Date: 2025-05-22 15:03:55.573395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


# revision identifiers, used by Alembic.
revision: str = '64cf476d46db'
down_revision: Union[str, None] = '941c73ffbd8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the ENUM type using PgEnum
trade_direction_enum = PgEnum('long', 'short', name='tradedirectionenum', create_type=False)

def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    
    # Create the ENUM type in the database
    trade_direction_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table('tradenotes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('asset_ticker', sa.String(), nullable=False),
    sa.Column('timeframe', sa.String(), nullable=False),
    sa.Column('trade_direction', trade_direction_enum, nullable=False),
    sa.Column('entry_price', sa.Numeric(precision=18, scale=8), nullable=False),
    sa.Column('exit_price', sa.Numeric(precision=18, scale=8), nullable=False),
    sa.Column('margin', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('leverage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.0'),
    sa.Column('pnl', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('note_text', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tradenotes_asset_ticker'), 'tradenotes', ['asset_ticker'], unique=False)
    op.create_index(op.f('ix_tradenotes_created_at'), 'tradenotes', ['created_at'], unique=False)
    op.create_index(op.f('ix_tradenotes_id'), 'tradenotes', ['id'], unique=False)
    op.create_index('ix_tradenotes_user_asset_created', 'tradenotes', ['user_id', 'asset_ticker', 'created_at'], unique=False)
    op.create_index(op.f('ix_tradenotes_user_id'), 'tradenotes', ['user_id'], unique=False)
    op.drop_constraint('news_articles_external_article_id_key', 'news_articles', type_='unique')
    op.drop_index('ix_news_articles_external_article_id', table_name='news_articles')
    op.create_index(op.f('ix_news_articles_external_article_id'), 'news_articles', ['external_article_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_news_articles_external_article_id'), table_name='news_articles')
    op.create_index('ix_news_articles_external_article_id', 'news_articles', ['external_article_id'], unique=False)
    op.drop_index(op.f('ix_tradenotes_user_id'), table_name='tradenotes')
    op.drop_index('ix_tradenotes_user_asset_created', table_name='tradenotes')
    op.drop_index(op.f('ix_tradenotes_id'), table_name='tradenotes')
    op.drop_index(op.f('ix_tradenotes_created_at'), table_name='tradenotes')
    op.drop_index(op.f('ix_tradenotes_asset_ticker'), table_name='tradenotes')
    op.drop_table('tradenotes')
    
    # Drop the ENUM type from the database
    trade_direction_enum.drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###
