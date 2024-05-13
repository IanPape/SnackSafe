"""Initial migration

Revision ID: 29e65a2a8fa7
Revises: 0f1ebed65e66
Create Date: 2024-05-02 10:06:06.579581

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '29e65a2a8fa7'
down_revision = '0f1ebed65e66'
branch_labels = None
depends_on = None

def upgrade():
    # Set existing null values to a default value (e.g., empty string)
    op.execute('UPDATE "user" SET password_hash = \'\' WHERE password_hash IS NULL')



    # Alter the column to NOT NULL
    op.alter_column('user', 'password_hash',
        existing_type=sa.String(length=255),
        nullable=False,
        server_default='',
        comment='Hashed password for user authentication'
    )


def downgrade():
    # Alter the column to be nullable again
    op.alter_column('user', 'password_hash', nullable=True)
