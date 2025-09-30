from ..db_class.db import Case, Task, Task_User, Case_Org

from datetime import datetime


def get_task_month_core(date_month, flag_dead_creation, user):
    # Convert "YYYY-MM" string into first day of month
    start = datetime.strptime(date_month, "%Y-%m")
    # Compute first day of next month
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1, day=1)
    else:
        end = start.replace(month=start.month+1, day=1)

    if flag_dead_creation == 'true':
        return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
                Task_User.user_id == user.id,
                Task.deadline >= start,
                Task.deadline < end
            ).all()
    else:
        return Task.query.join(Task_User, Task_User.task_id == Task.id).filter(
                Task_User.user_id == user.id,
                Task.creation_date >= start,
                Task.creation_date < end
            ).all()


def get_case_month_core(date_month, flag_dead_creation, user):
    # Convert "YYYY-MM" string into first day of month
    start = datetime.strptime(date_month, "%Y-%m")
    # Compute first day of next month
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1, day=1)
    else:
        end = start.replace(month=start.month+1, day=1)


    if flag_dead_creation == 'true':
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).filter(
            Case_Org.org_id == user.org_id,
            Case.deadline >= start,
            Case.deadline < end
        ).all()
    else:
        return Case.query.join(Case_Org, Case_Org.case_id==Case.id).filter(
            Case_Org.org_id == user.org_id,
            Case.creation_date >= start,
            Case.creation_date < end
        ).all()
