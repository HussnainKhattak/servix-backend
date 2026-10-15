"""add_client_technician_roles_and_technician_profile

Revision ID: 8ccce7d0df5b
Revises: e85f6629a21b
Create Date: 2026-09-14 13:35:01.470450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8ccce7d0df5b'
down_revision: Union[str, None] = 'e85f6629a21b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------
    # 1. Update user_role_enum values without breaking existing data
    # -------------------------------------------------------------
    # Drop index on role column first
    op.drop_index(op.f('ix_users_role'), table_name='users')

    # Drop column default before changing type
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT;")

    # Temporarily convert to VARCHAR for seamless data mapping
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(50);")

    # Map legacy role values to new lowercase role enum values
    op.execute("UPDATE users SET role = 'client' WHERE role IN ('CUSTOMER', 'customer', 'CLIENT');")
    op.execute("UPDATE users SET role = 'technician' WHERE role IN ('PROVIDER', 'provider', 'TECHNICIAN');")
    op.execute("UPDATE users SET role = 'admin' WHERE role IN ('ADMIN', 'admin');")
    op.execute("UPDATE users SET role = 'client' WHERE role NOT IN ('client', 'technician', 'admin');")

    # Replace user_role_enum with updated type definition
    op.execute("DROP TYPE IF EXISTS user_role_enum CASCADE;")
    op.execute("CREATE TYPE user_role_enum AS ENUM ('client', 'technician', 'admin');")

    # Restore enum type and new default on users.role
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'::user_role_enum;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL;")

    # Recreate index on users.role
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # -------------------------------------------------------------
    # 2. Create technician enums: technician_trade_enum & availability_status_enum
    # -------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'technician_trade_enum') THEN
                CREATE TYPE technician_trade_enum AS ENUM (
                    'plumber', 'electrician', 'carpenter', 'hvac', 
                    'cleaner', 'painter', 'handyman', 'appliance_repair', 
                    'roofer', 'other'
                );
            END IF;
        END$$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'availability_status_enum') THEN
                CREATE TYPE availability_status_enum AS ENUM (
                    'available', 'busy', 'unavailable'
                );
            END IF;
        END$$;
    """)

    # -------------------------------------------------------------
    # 3. Create technician_profiles table (1:1 with users)
    # -------------------------------------------------------------
    op.create_table(
        'technician_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trade', postgresql.ENUM(
            'plumber', 'electrician', 'carpenter', 'hvac', 
            'cleaner', 'painter', 'handyman', 'appliance_repair', 
            'roofer', 'other',
            name='technician_trade_enum',
            create_type=False
        ), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('hourly_rate', sa.Float(), nullable=True),
        sa.Column('base_price', sa.Float(), nullable=True),
        sa.Column('availability_status', postgresql.ENUM(
            'available', 'busy', 'unavailable',
            name='availability_status_enum',
            create_type=False
        ), server_default='available', nullable=False),
        sa.Column('avg_rating', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('review_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('zip_code', sa.String(length=20), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    op.create_index(op.f('ix_technician_profiles_id'), 'technician_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_technician_profiles_user_id'), 'technician_profiles', ['user_id'], unique=True)
    op.create_index(op.f('ix_technician_profiles_trade'), 'technician_profiles', ['trade'], unique=False)
    op.create_index(op.f('ix_technician_profiles_availability_status'), 'technician_profiles', ['availability_status'], unique=False)
    op.create_index(op.f('ix_technician_profiles_avg_rating'), 'technician_profiles', ['avg_rating'], unique=False)
    op.create_index(op.f('ix_technician_profiles_city'), 'technician_profiles', ['city'], unique=False)
    op.create_index(op.f('ix_technician_profiles_created_at'), 'technician_profiles', ['created_at'], unique=False)
    op.create_index('ix_technician_profiles_geo', 'technician_profiles', ['latitude', 'longitude'], unique=False)
    op.create_index('ix_technician_profiles_trade_status', 'technician_profiles', ['trade', 'availability_status'], unique=False)

    # -------------------------------------------------------------
    # 4. Migrate existing provider data into technician_profiles
    # -------------------------------------------------------------
    op.execute("""
        INSERT INTO technician_profiles (
            id, user_id, trade, bio, hourly_rate, availability_status,
            avg_rating, review_count, city, state, zip_code, latitude, longitude,
            created_at, updated_at
        )
        SELECT 
            gen_random_uuid(),
            p.user_id,
            (CASE 
                WHEN LOWER(p.trade) LIKE '%electric%' THEN 'electrician'
                WHEN LOWER(p.trade) LIKE '%plumb%' THEN 'plumber'
                WHEN LOWER(p.trade) LIKE '%carpent%' THEN 'carpenter'
                WHEN LOWER(p.trade) LIKE '%clean%' THEN 'cleaner'
                WHEN LOWER(p.trade) LIKE '%hvac%' THEN 'hvac'
                WHEN LOWER(p.trade) LIKE '%paint%' THEN 'painter'
                WHEN LOWER(p.trade) LIKE '%handy%' THEN 'handyman'
                WHEN LOWER(p.trade) LIKE '%appliance%' THEN 'appliance_repair'
                WHEN LOWER(p.trade) LIKE '%roof%' THEN 'roofer'
                ELSE 'other'
            END)::technician_trade_enum,
            p.bio,
            p.hourly_rate,
            (CASE 
                WHEN p.is_available THEN 'available'
                ELSE 'unavailable'
            END)::availability_status_enum,
            COALESCE(p.avg_rating, 0.0),
            COALESCE(p.reviews_count, 0),
            p.city,
            p.state,
            p.zip_code,
            p.latitude,
            p.longitude,
            p.created_at,
            p.updated_at
        FROM providers p
        ON CONFLICT (user_id) DO NOTHING;
    """)


def downgrade() -> None:
    # 1. Drop technician_profiles table and indexes
    op.drop_table('technician_profiles')

    # 2. Drop technician enums
    op.execute("DROP TYPE IF EXISTS availability_status_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS technician_trade_enum CASCADE;")

    # 3. Revert user_role_enum to original values ('CUSTOMER', 'PROVIDER', 'ADMIN')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT;")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(50);")

    op.execute("UPDATE users SET role = 'CUSTOMER' WHERE role = 'client';")
    op.execute("UPDATE users SET role = 'PROVIDER' WHERE role = 'technician';")
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'admin';")
    op.execute("UPDATE users SET role = 'CUSTOMER' WHERE role NOT IN ('CUSTOMER', 'PROVIDER', 'ADMIN');")

    op.execute("DROP TYPE IF EXISTS user_role_enum CASCADE;")
    op.execute("CREATE TYPE user_role_enum AS ENUM ('CUSTOMER', 'PROVIDER', 'ADMIN');")

    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'CUSTOMER'::user_role_enum;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL;")

    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
