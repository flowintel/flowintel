"""empty message

Revision ID: 0ca756cb8128
Revises: 819665adf2f8
Create Date: 2024-01-25 14:04:52.381711

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = '0ca756cb8128'
down_revision = '819665adf2f8'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	try:
		with op.batch_alter_table('case', schema=None) as batch_op:
			batch_op.add_column(sa.Column('nb_tasks', sa.Integer(), nullable=True))
			batch_op.create_index(batch_op.f('ix_case_nb_tasks'), ['nb_tasks'], unique=False)
	except OperationalError:
		print("Column 'nb_tasks' already exist in 'case'")

	try:
		with op.batch_alter_table('task', schema=None) as batch_op:
			batch_op.add_column(sa.Column('case_order_id', sa.Integer(), nullable=True))
			batch_op.create_index(batch_op.f('ix_task_case_order_id'), ['case_order_id'], unique=False)
	except OperationalError:
		print("Column 'case_order_id' already exist in 'task'")
        
	# Connexion à la base de données (utilisez votre moteur de base de données)
	connection = op.get_bind()

	# Sélectionnez toutes les lignes de la table users
	cases = connection.execute(sa.text("SELECT id FROM 'case'")).fetchall()

    # Incrémentation du compteur pour chaque utilisateur
	for case_ in cases:
		cp_tasks = 0
		tasks = connection.execute(sa.text(f"SELECT id FROM task WHERE task.case_id={case_.id}")).fetchall()
		cp = 1
		for task in tasks:
			connection.execute(
				sa.text(f"UPDATE task SET case_order_id = {cp} WHERE id = {task.id}")
            )
			cp += 1
			cp_tasks += 1
			
		connection.execute(
			sa.text(f"UPDATE 'case' SET nb_tasks = {cp_tasks} WHERE id = {case_.id}")
		)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_task_case_order_id'))
        batch_op.drop_column('case_order_id')

    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_case_nb_tasks'))
        batch_op.drop_column('nb_tasks')

    # ### end Alembic commands ###
