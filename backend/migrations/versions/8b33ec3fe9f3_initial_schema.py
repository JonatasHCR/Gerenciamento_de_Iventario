"""initial_schema — esquema consolidado do InvControl

Cria todas as tabelas, índices, constraints e popula o catálogo
de tipos de equipamento com os 5 tipos default.

Após rodar `alembic upgrade head`, execute o script
`backend/bootstrap_admin.py` para criar o primeiro usuário Admin.

Revision ID: 8b33ec3fe9f3
Revises:
Create Date: 2026-05-19 21:07:29.793954

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '8b33ec3fe9f3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TIPOS_SEED = [
    ('Computador', 'Desktop'),
    ('Notbook', 'Laptop / notebook'),
    ('Monitor', 'Monitor / tela'),
    ('Impressora', 'Impressora'),
    ('Scanner', 'Scanner'),
]


def upgrade() -> None:
    """Upgrade schema."""
    # ─── Tabelas-base ────────────────────────────────────────────────────
    op.create_table(
        'tb_contratos',
        sa.Column('centro_custo', sa.String(length=4), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('centro_custo'),
    )
    op.create_index(
        op.f('ix_tb_contratos_centro_custo'),
        'tb_contratos',
        ['centro_custo'],
        unique=False,
    )

    op.create_table(
        'tb_tipos_eletronico',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column(
            'ativo',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tb_tipos_eletronico_nome'),
        'tb_tipos_eletronico',
        ['nome'],
        unique=True,
    )

    op.create_table(
        'tb_users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('senha', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('Admin', 'Funcionario', 'Gestor', "
            "'Subgestor', 'Tecnico_TI' )",
            name='check_tipo_valid',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(
        op.f('ix_tb_users_id'), 'tb_users', ['id'], unique=False
    )

    # ─── Associações ─────────────────────────────────────────────────────
    op.create_table(
        'tb_associacao_user_contrato',
        sa.Column('centro_custo', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ocupacao', sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            "ocupacao IN ('Gestor', 'Funcionario','Subgestor')",
            name='check_ocupacao_valid',
        ),
        sa.ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_associacao_centro_custo',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['tb_users.id'],
            name='fk_associacao_user_id',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('centro_custo', 'user_id'),
    )
    op.create_index(
        'ix_assoc_user_contrato_user_id',
        'tb_associacao_user_contrato',
        ['user_id'],
        unique=False,
    )

    # ─── Audit log ───────────────────────────────────────────────────────
    op.create_table(
        'tb_audit_log',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column(
            'criado_em', sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['tb_users.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tb_audit_log_action'),
        'tb_audit_log',
        ['action'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_audit_log_criado_em'),
        'tb_audit_log',
        ['criado_em'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_audit_log_id'),
        'tb_audit_log',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_audit_log_target_id'),
        'tb_audit_log',
        ['target_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_audit_log_target_type'),
        'tb_audit_log',
        ['target_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_audit_log_user_id'),
        'tb_audit_log',
        ['user_id'],
        unique=False,
    )

    # ─── Cessões ─────────────────────────────────────────────────────────
    op.create_table(
        'tb_cessoes',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('responsavel', sa.String(length=255), nullable=False),
        sa.Column(
            'centro_custo_destino', sa.String(length=4), nullable=False
        ),
        sa.Column(
            'cedido_em', sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column('cedido_por_id', sa.Integer(), nullable=True),
        sa.Column(
            'devolvida_em', sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column('devolvida_por_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['cedido_por_id'], ['tb_users.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['devolvida_por_id'], ['tb_users.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tb_cessoes_id'),
        'tb_cessoes',
        ['id'],
        unique=False,
    )
    op.create_index(
        'ix_cessoes_cedido_em', 'tb_cessoes', ['cedido_em'], unique=False
    )
    op.create_index(
        'ix_cessoes_cedido_por_id',
        'tb_cessoes',
        ['cedido_por_id'],
        unique=False,
    )

    # ─── Eletrônicos ─────────────────────────────────────────────────────
    op.create_table(
        'tb_eletronicos',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column(
            'numero_serie', sa.String(length=100), nullable=False
        ),
        sa.Column(
            'numero_patrimonio', sa.String(length=100), nullable=False
        ),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('marca', sa.String(length=100), nullable=True),
        sa.Column('tipo', sa.String(length=100), nullable=False),
        sa.Column('modelo', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('ip', sa.String(length=15), nullable=True),
        sa.Column('localizacao', sa.String(length=255), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('centro_custo', sa.String(length=4), nullable=False),
        sa.CheckConstraint(
            "status IN ('Interno', 'Externo', 'Em Manutenção')",
            name='check_status_valid',
        ),
        sa.ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_eletronico_centro_custo',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero_patrimonio'),
        sa.UniqueConstraint('numero_serie'),
    )
    op.create_index(
        op.f('ix_tb_eletronicos_id'),
        'tb_eletronicos',
        ['id'],
        unique=False,
    )
    op.create_index(
        'ix_eletronicos_centro_custo',
        'tb_eletronicos',
        ['centro_custo'],
        unique=False,
    )
    op.create_index(
        'ix_eletronicos_status',
        'tb_eletronicos',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_eletronicos_tipo',
        'tb_eletronicos',
        ['tipo'],
        unique=False,
    )

    # ─── Solicitações ────────────────────────────────────────────────────
    op.create_table(
        'tb_solicitacoes',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('solicitante_id', sa.Integer(), nullable=False),
        sa.Column('centro_custo', sa.String(length=4), nullable=True),
        sa.Column(
            'ocupacao_solicitada', sa.String(length=50), nullable=True
        ),
        sa.Column('convidado_por_id', sa.Integer(), nullable=True),
        sa.Column(
            'cargo_solicitado', sa.String(length=50), nullable=True
        ),
        sa.Column(
            'centro_custo_destino', sa.String(length=4), nullable=True
        ),
        sa.Column('responsavel', sa.String(length=255), nullable=True),
        sa.Column(
            'criado_em', sa.DateTime(timezone=True), nullable=False
        ),
        sa.CheckConstraint(
            "cargo_solicitado IN ('Gestor', 'Subgestor', 'Tecnico_TI')"
            ' OR cargo_solicitado IS NULL',
            name='check_solicitacao_cargo',
        ),
        sa.CheckConstraint(
            "ocupacao_solicitada IN ('Gestor', 'Subgestor', 'Funcionario')"
            ' OR ocupacao_solicitada IS NULL',
            name='check_solicitacao_ocupacao',
        ),
        sa.CheckConstraint(
            "status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada')",
            name='check_solicitacao_status',
        ),
        sa.CheckConstraint(
            "tipo IN ('entrada_cc', 'cargo_inicial', 'cessao')",
            name='check_solicitacao_tipo',
        ),
        sa.ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_solicitacao_centro_custo',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['convidado_por_id'],
            ['tb_users.id'],
            name='fk_solicitacao_convidado_por_id',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['solicitante_id'],
            ['tb_users.id'],
            name='fk_solicitacao_solicitante_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_solicitacoes_status',
        'tb_solicitacoes',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_solicitacoes_tipo',
        'tb_solicitacoes',
        ['tipo'],
        unique=False,
    )
    op.create_index(
        'ix_solicitacoes_centro_custo',
        'tb_solicitacoes',
        ['centro_custo'],
        unique=False,
    )
    op.create_index(
        'ix_solicitacoes_solicitante_id',
        'tb_solicitacoes',
        ['solicitante_id'],
        unique=False,
    )

    # ─── Join tables ─────────────────────────────────────────────────────
    op.create_table(
        'tb_associacao_user_eletronico',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('eletronico_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['eletronico_id'],
            ['tb_eletronicos.id'],
            name='fk_associacao_eletronico_id',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['tb_users.id'],
            name='fk_associacao_user_id',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('user_id', 'eletronico_id'),
    )
    op.create_index(
        'ix_assoc_user_eletronico_user_id',
        'tb_associacao_user_eletronico',
        ['user_id'],
        unique=False,
    )

    op.create_table(
        'tb_cessao_eletronico',
        sa.Column('cessao_id', sa.Integer(), nullable=False),
        sa.Column('eletronico_id', sa.Integer(), nullable=False),
        sa.Column(
            'devolvido_em', sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column('devolvida_por_id', sa.Integer(), nullable=True),
        sa.Column('devolucao_lote', sa.Integer(), nullable=True),
        sa.Column(
            'gestor_visto_em', sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ['cessao_id'], ['tb_cessoes.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['devolvida_por_id'], ['tb_users.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['eletronico_id'], ['tb_eletronicos.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('cessao_id', 'eletronico_id'),
    )
    op.create_index(
        'ix_cessao_eletronico_eletronico_id',
        'tb_cessao_eletronico',
        ['eletronico_id'],
        unique=False,
    )

    op.create_table(
        'tb_solicitacao_eletronico',
        sa.Column('solicitacao_id', sa.Integer(), nullable=False),
        sa.Column('eletronico_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['eletronico_id'], ['tb_eletronicos.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['solicitacao_id'],
            ['tb_solicitacoes.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('solicitacao_id', 'eletronico_id'),
    )

    # ─── Seed: catálogo de tipos de equipamento ─────────────────────────
    tipos_table = sa.table(
        'tb_tipos_eletronico',
        sa.column('nome', sa.String),
        sa.column('descricao', sa.String),
    )
    op.bulk_insert(
        tipos_table,
        [{'nome': n, 'descricao': d} for n, d in _TIPOS_SEED],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tb_solicitacao_eletronico')
    op.drop_index(
        'ix_cessao_eletronico_eletronico_id',
        table_name='tb_cessao_eletronico',
    )
    op.drop_table('tb_cessao_eletronico')
    op.drop_index(
        'ix_assoc_user_eletronico_user_id',
        table_name='tb_associacao_user_eletronico',
    )
    op.drop_table('tb_associacao_user_eletronico')
    op.drop_index(
        'ix_solicitacoes_solicitante_id', table_name='tb_solicitacoes'
    )
    op.drop_index(
        'ix_solicitacoes_centro_custo', table_name='tb_solicitacoes'
    )
    op.drop_index('ix_solicitacoes_tipo', table_name='tb_solicitacoes')
    op.drop_index('ix_solicitacoes_status', table_name='tb_solicitacoes')
    op.drop_table('tb_solicitacoes')
    op.drop_index('ix_eletronicos_tipo', table_name='tb_eletronicos')
    op.drop_index('ix_eletronicos_status', table_name='tb_eletronicos')
    op.drop_index(
        'ix_eletronicos_centro_custo', table_name='tb_eletronicos'
    )
    op.drop_index(op.f('ix_tb_eletronicos_id'), table_name='tb_eletronicos')
    op.drop_table('tb_eletronicos')
    op.drop_index('ix_cessoes_cedido_por_id', table_name='tb_cessoes')
    op.drop_index('ix_cessoes_cedido_em', table_name='tb_cessoes')
    op.drop_index(op.f('ix_tb_cessoes_id'), table_name='tb_cessoes')
    op.drop_table('tb_cessoes')
    op.drop_index(op.f('ix_tb_audit_log_user_id'), table_name='tb_audit_log')
    op.drop_index(
        op.f('ix_tb_audit_log_target_type'), table_name='tb_audit_log'
    )
    op.drop_index(
        op.f('ix_tb_audit_log_target_id'), table_name='tb_audit_log'
    )
    op.drop_index(op.f('ix_tb_audit_log_id'), table_name='tb_audit_log')
    op.drop_index(
        op.f('ix_tb_audit_log_criado_em'), table_name='tb_audit_log'
    )
    op.drop_index(op.f('ix_tb_audit_log_action'), table_name='tb_audit_log')
    op.drop_table('tb_audit_log')
    op.drop_index(
        'ix_assoc_user_contrato_user_id',
        table_name='tb_associacao_user_contrato',
    )
    op.drop_table('tb_associacao_user_contrato')
    op.drop_index(op.f('ix_tb_users_id'), table_name='tb_users')
    op.drop_table('tb_users')
    op.drop_index(
        op.f('ix_tb_tipos_eletronico_nome'),
        table_name='tb_tipos_eletronico',
    )
    op.drop_table('tb_tipos_eletronico')
    op.drop_index(
        op.f('ix_tb_contratos_centro_custo'), table_name='tb_contratos'
    )
    op.drop_table('tb_contratos')
