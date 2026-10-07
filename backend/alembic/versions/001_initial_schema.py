"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-07 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. mails
    op.create_table(
        'mails',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', sa.String(length=255), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='naukri_nvite'),
        sa.Column('raw_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('raw_body_text', sa.Text(), nullable=True),
        sa.Column('raw_body_html', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_mails_message_id', 'mails', ['message_id'], unique=True)
    op.create_index('ix_mails_received_at', 'mails', ['received_at'])
    op.create_index('ix_mails_status', 'mails', ['status'])

    # 2. candidates
    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=64), nullable=True),
        sa.Column('headline', sa.Text(), nullable=True),
        sa.Column('current_company', sa.String(length=255), nullable=True),
        sa.Column('experience_years', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('current_ctc_lpa', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('notice_raw', sa.String(length=128), nullable=True),
        sa.Column('notice_days_max', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('preferred_locations', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('education', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('merged_into', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['merged_into'], ['candidates.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_candidates_full_name', 'candidates', ['full_name'])
    op.create_index(
        'idx_candidates_email_active',
        'candidates',
        ['email'],
        unique=True,
        postgresql_where=sa.text('email IS NOT NULL AND merged_into IS NULL')
    )
    op.create_index(
        'idx_candidates_phone_active',
        'candidates',
        ['phone'],
        postgresql_where=sa.text('phone IS NOT NULL AND merged_into IS NULL')
    )
    op.create_index('idx_candidates_filter', 'candidates', ['notice_days_max', 'experience_years'])

    # 3. applications
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mail_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('job_locations', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('expected_ctc_lpa', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mail_id'], ['mails.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('candidate_id', 'mail_id', name='uq_applications_candidate_mail'),
    )

    # 4. resumes
    op.create_table(
        'resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mail_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('file_content_bytes', postgresql.BYTEA(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('text_quality', sa.String(length=32), nullable=False, server_default='ok'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mail_id'], ['mails.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_resumes_file_hash', 'resumes', ['file_hash'], unique=True)
    op.create_index('ix_resumes_candidate_id', 'resumes', ['candidate_id'])

    # 5. job_profiles
    op.create_table(
        'job_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('structured', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(length=255), nullable=False, server_default='recruiter'),
        sa.Column('confirmed_by', sa.String(length=255), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_id'], ['job_profiles.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_job_profiles_content_hash', 'job_profiles', ['content_hash'], unique=True)
    op.create_index('ix_job_profiles_status', 'job_profiles', ['status'])

    # 6. ingest_jobs
    op.create_table(
        'ingest_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mail_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['mail_id'], ['mails.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('mail_id', name='uq_ingest_jobs_mail'),
    )
    op.create_index('ix_ingest_jobs_status', 'ingest_jobs', ['status'])
    op.create_index('idx_ingest_jobs_status_poll', 'ingest_jobs', ['status', 'next_attempt_at'])

    # 7. scoring_jobs
    op.create_table(
        'scoring_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('job_profile_id', 'candidate_id', 'input_hash', name='uq_scoring_jobs_eval'),
    )
    op.create_index('ix_scoring_jobs_status', 'scoring_jobs', ['status'])
    op.create_index('idx_scoring_jobs_poll', 'scoring_jobs', ['status', 'priority', 'next_attempt_at'])

    # 8. scores
    op.create_table(
        'scores',
        sa.Column('job_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('details_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('details_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('resume_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('sub_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('must_have', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matched_skills', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('missing_skills', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('confidence', sa.String(length=32), nullable=False, server_default='high'),
        sa.Column('final_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('flags', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='complete'),
        sa.Column('model', sa.String(length=128), nullable=True),
        sa.Column('prompt_version', sa.String(length=64), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('job_profile_id', 'candidate_id'),
    )
    op.create_index('idx_scores_final', 'scores', ['job_profile_id', 'final_score'])

    # 9. ranking_runs
    op.create_table(
        'ranking_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank_by', sa.String(length=32), nullable=False, server_default='final'),
        sa.Column('top_n', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('sort_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('scored_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('created_by', sa.String(length=255), nullable=False, server_default='recruiter'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ondelete='CASCADE'),
    )

    # 10. ranking_results
    op.create_table(
        'ranking_results',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank_position', sa.Integer(), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('final_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('details_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('resume_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('missing_skills', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['ranking_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('run_id', 'rank_position'),
    )

    # 11. duplicate_flags
    op.create_table(
        'duplicate_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('candidate_a', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_b', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['candidate_a'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_b'], ['candidates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('candidate_a', 'candidate_b', name='uq_duplicate_pair'),
    )

    # 12. sync_runs
    op.create_table(
        'sync_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mailbox', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_mails', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_candidates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('existing_candidates_new_application', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_flags', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_mail_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delta_link', sa.Text(), nullable=True),
    )

    # 13. audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=False, server_default='anonymous'),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tool', sa.String(length=128), nullable=False),
        sa.Column('args_hash', sa.String(length=64), nullable=False),
        sa.Column('request_body', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_log_tool', 'audit_log', ['tool'])
    op.create_index('idx_audit_log_tool_time', 'audit_log', ['tool', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('sync_runs')
    op.drop_table('duplicate_flags')
    op.drop_table('ranking_results')
    op.drop_table('ranking_runs')
    op.drop_table('scores')
    op.drop_table('scoring_jobs')
    op.drop_table('ingest_jobs')
    op.drop_table('job_profiles')
    op.drop_table('resumes')
    op.drop_table('applications')
    op.drop_table('candidates')
    op.drop_table('mails')
